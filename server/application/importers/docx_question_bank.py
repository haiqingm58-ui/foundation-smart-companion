from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
from collections import Counter
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from lxml import etree

from .question_normalization import (
    KNOWLEDGE_POINTS,
    SUBJECT_ID,
    canonical_json_bytes,
    CHAPTERS,
    compact_text,
    normalize_candidate,
    strip_question_prefix,
)
from .report import ImportReport


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "v": "urn:schemas-microsoft-com:vml",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
}
ANSWER_RE = re.compile(r"^(?:\u6b63确答案|\u53c2考答案|\u7b54案)\s*[:\uff1a]\s*(.*)$")
OPTION_RE = re.compile(r"^([A-Ha-h])\s*[.\u3001\uff0e:\uff1a\)]\s*(.*)$")
TYPE_HEADING_RE = re.compile(
    r"^(?:[\u4e00-\u5341\d]+\s*[.\u3001\uff0e]\s*)?"
    r"(\u5355选题|\u5355项选择题|\u591a选题|\u591a项选择题|\u9009择题|\u5224断题|\u586b空题|\u7b80答题|\u8ba1算题)"
    r"(?:[\(\uff08].*[\)\uff09])?$"
)
TRAILING_TYPE_RE = re.compile(r"^(.*?)[\(\uff08]([\u4e00-\u9fff]{1,10}题)[\)\uff09]\s*$")
NUMBERED_QUESTION_RE = re.compile(r"^[\uf06c\u2022]?\s*(?:\d+(?:\.\d+)+|\d+[.\u3001\uff0e])\s*\S")
NUMBER_PREFIX_RE = re.compile(r"^[\uf06c\u2022]?\s*(?:\d+(?:\.\d+)+|\d+[.\u3001\uff0e])\s*")
CHAPTER_HEADING_RE = re.compile(r"^第[\u4e00-\u5341百\d]+章")
INLINE_OPTION_RE = re.compile(r"(?:^|\s)[\(\uff08]([A-Ha-h])[\)\uff09]\s*")
ANSWER_CONTINUATION_RE = re.compile(r"^(?:[\(\uff08]\d+[\)\uff09]|\u7b2c[\u4e00-\u5341\d]+空\s*[:\uff1a])\s*(.*)$")
SOURCE_ARCHIVE_SHA256 = "4f37093bad985a68ffb6deb296a5da9c33fac56fdbe51e0c831d913079b1a04f"
EXPECTED_SOURCE_FILES = [
    "1-随堂检测题库.docx",
    "2-章节测验.docx",
    "3-其他题库-1.docx",
    "4-其他题库-2.docx",
]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(payload))


def _relationships(archive: ZipFile) -> dict[str, str]:
    root = etree.fromstring(archive.read("word/_rels/document.xml.rels"))
    return {
        item.get("Id"): item.get("Target")
        for item in root.xpath("/rel:Relationships/rel:Relationship", namespaces=NS)
        if item.get("Id") and item.get("Target")
    }


def _element_text(element: etree._Element) -> str:
    return compact_text("".join(element.xpath(".//w:t/text() | .//m:t/text()", namespaces=NS)))


def _image_extension(data: bytes, target: str) -> str:
    signatures = ((b"\x89PNG\r\n\x1a\n", ".png"), (b"\xff\xd8\xff", ".jpg"), (b"GIF8", ".gif"), (b"BM", ".bmp"))
    for signature, suffix in signatures:
        if data.startswith(signature):
            return suffix
    suffix = Path(target).suffix.lower()
    return suffix if re.fullmatch(r"\.[a-z0-9]{1,5}", suffix) else ".bin"


def _ordered_inline_attachments(
    element: etree._Element,
    archive: ZipFile,
    relationships: dict[str, str],
    assets_dir: Path,
    position: dict[str, int],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for child in element.iterdescendants():
        qname = etree.QName(child)
        relationship_id: str | None = None
        if qname.namespace == NS["a"] and qname.localname == "blip":
            relationship_id = child.get(f"{{{NS['r']}}}embed") or child.get(f"{{{NS['r']}}}link")
        elif qname.namespace == NS["v"] and qname.localname == "imagedata":
            relationship_id = child.get(f"{{{NS['r']}}}id")
        elif qname.namespace == NS["m"] and qname.localname in {"oMath", "oMathPara"}:
            if qname.localname == "oMath" and child.getparent() is not None and etree.QName(child.getparent()).namespace == NS["m"] and etree.QName(child.getparent()).localname == "oMathPara":
                continue
            result.append(
                {
                    "kind": "formula",
                    "ommlText": compact_text("".join(child.xpath(".//m:t/text()", namespaces=NS))),
                    "ommlSource": etree.tostring(child, encoding="unicode", with_tail=False),
                    "sourcePosition": position,
                }
            )
            continue
        if relationship_id is None:
            continue
        target = relationships.get(relationship_id)
        if not target:
            continue
        member = posixpath.normpath(posixpath.join("word", target))
        data = archive.read(member)
        digest = hashlib.sha256(data).hexdigest()
        suffix = _image_extension(data, target)
        asset = assets_dir / f"{digest}{suffix}"
        asset.parent.mkdir(parents=True, exist_ok=True)
        if not asset.exists():
            asset.write_bytes(data)
        result.append(
            {
                "kind": "image",
                "src": f"/foundation-smart-companion/question-assets/soil-mechanics/{asset.name}",
                "alt": "题目附图",
                "sha256": digest,
                "sourcePosition": position,
            }
        )
    return result


def _iter_body_blocks(parent: etree._Element):
    for child in parent:
        kind = etree.QName(child).localname
        if kind in {"p", "tbl"}:
            yield child
        elif kind != "sectPr":
            yield from _iter_body_blocks(child)


def _blocks(path: Path, assets_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with ZipFile(path) as archive:
        relationships = _relationships(archive)
        root = etree.fromstring(archive.read("word/document.xml"))
        body = root.find("w:body", namespaces=NS)
        if body is None:
            return [], {}
        result: list[dict[str, Any]] = []
        paragraph_index = 0
        table_index = 0
        table_row_count = 0
        for block_index, element in enumerate(_iter_body_blocks(body), start=1):
            kind = etree.QName(element).localname
            if kind == "p":
                paragraph_index += 1
                position = {"blockIndex": block_index, "paragraphIndex": paragraph_index}
                result.append(
                    {
                        "kind": "paragraph",
                        "text": _element_text(element),
                        "position": position,
                        "attachments": _ordered_inline_attachments(element, archive, relationships, assets_dir, position),
                    }
                )
            elif kind == "tbl":
                table_index += 1
                position = {"blockIndex": block_index, "tableIndex": table_index}
                rows = [
                    [_element_text(cell) for cell in row.xpath("./w:tc", namespaces=NS)]
                    for row in element.xpath("./w:tr", namespaces=NS)
                ]
                table_row_count += len(rows)
                attachments = [{"kind": "table", "rows": rows, "sourcePosition": position}]
                attachments.extend(_ordered_inline_attachments(element, archive, relationships, assets_dir, position))
                result.append({"kind": "table", "text": "", "position": position, "attachments": attachments})
        inline_attachments = [attachment for block in result for attachment in block["attachments"]]
        image_attachments = [item for item in inline_attachments if item["kind"] == "image"]
        formula_attachments = [item for item in inline_attachments if item["kind"] == "formula"]
        stats = {
            "file": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "sizeBytes": path.stat().st_size,
            "blockCount": len(result),
            "paragraphCount": paragraph_index,
            "tableCount": table_index,
            "tableRowCount": table_row_count,
            "imageCount": len(image_attachments),
            "uniqueImageContentCount": len({item["sha256"] for item in image_attachments}),
            "mediaPartCount": len([name for name in archive.namelist() if name.startswith("word/media/") and not name.endswith("/")]),
            "ommlCount": len(formula_attachments),
            "answerMarkerCount": sum(
                1 for block in result if block["kind"] == "paragraph" and ANSWER_RE.match(block["text"])
            ),
        }
        return result, stats


def _chapter_for_heading(text: str) -> str | None:
    if not text or len(text) > 48:
        return None
    normalized = compact_text(text).replace(" ", "")
    if normalized == "绪论":
        return CHAPTERS[0]
    patterns = [
        (8, r"(?:第八章|8[.\uff0e]?)?地基承载力"),
        (7, r"(?:第七章|7[.\uff0e]?)?(?:边坡|土坡)稳定性?"),
        (6, r"(?:第六章|6[.\uff0e]?)?土压力"),
        (5, r"(?:(?:第五章|5[.\uff0e]?)?土的抗剪(?:强度)?|(?:三[.\uff0e]?)?土的强度)"),
        (4, r"(?:(?:第四章|4[.\uff0e]?)?土的压缩性与地基沉降|(?:2[.\uff0e]?)?土的固结)"),
        (3, r"(?:第三章|3[.\uff0e]?)?土中应力"),
        (2, r"(?:第二章|2[.\uff0e]?)?土(?:的|中)(?:渗流|渗透性?)"),
        (1, r"(?:(?:第一章|每一章|1[.\uff0e]?)?(?:土的性质及工程分类|土地性质及工程分类|土的性质)|土的组成|土的物理性质(?:及分类测验)?|土粒特征|土的物理状态|土的压实性)"),
    ]
    for number, pattern in patterns:
        if re.fullmatch(pattern, normalized):
            return CHAPTERS[number]
    return None


def _type_heading(text: str) -> str | None:
    match = TYPE_HEADING_RE.match(compact_text(text))
    return match.group(1) if match else None


def _strip_number_prefix(text: str) -> str:
    return compact_text(NUMBER_PREFIX_RE.sub("", text, count=1))


def _inline_options(text: str) -> list[dict[str, str]]:
    simple = OPTION_RE.match(text)
    if simple:
        return [{"label": simple.group(1).upper(), "text": compact_text(simple.group(2))}]
    matches = list(INLINE_OPTION_RE.finditer(text))
    if not matches:
        return []
    options = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        options.append({"label": match.group(1).upper(), "text": compact_text(text[match.end():end])})
    return options


def _start_candidate(
    block: dict[str, Any],
    stem: str,
    original_type: str | None,
    chapter: str | None,
    chapter_heading: str | None,
) -> dict[str, Any]:
    return {
        "textParts": [stem] if stem else [],
        "originalTypeLabel": original_type,
        "position": block["position"],
        "options": [],
        "pendingOption": None,
        "attachments": list(block["attachments"]),
        "chapter": chapter,
        "chapterHeading": chapter_heading,
        "answer": "",
        "answerFound": False,
        "answerPosition": None,
        "postAnswerParts": [],
        "blockSequence": [block["position"]],
        "endPosition": block["position"],
    }


def _append_block(candidate: dict[str, Any], block: dict[str, Any], *, after_answer: bool = False) -> None:
    candidate["attachments"].extend(block["attachments"])
    candidate["blockSequence"].append(block["position"])
    candidate["endPosition"] = block["position"]
    text = block["text"]
    if block["kind"] == "table" or not text:
        return
    if after_answer:
        candidate["postAnswerParts"].append(text)
        return
    options = _inline_options(text)
    if options:
        candidate["options"].extend(options)
        candidate["pendingOption"] = options[-1]["label"] if not options[-1]["text"] else None
        return
    pending_label = candidate.get("pendingOption")
    if pending_label:
        for option in reversed(candidate["options"]):
            if option["label"] == pending_label:
                option["text"] = text
                break
        candidate["pendingOption"] = None
        return
    candidate["textParts"].append(text)


def _infer_type(candidate: dict[str, Any]) -> tuple[str | None, str | None]:
    original_type = candidate.get("originalTypeLabel")
    answer = compact_text(candidate.get("answer", ""))
    answer_letters = re.sub(r"[\s,\uff0c\u3001;\uff1b/]+", "", answer).upper()
    if candidate["options"] and re.fullmatch(r"[A-H]+", answer_letters or ""):
        if len(answer_letters) == 1:
            return "单项选择题", "根据选项和单字母答案推断"
        return "多项选择题", "根据选项和多字母答案推断"
    if answer.casefold() in {"正确", "错误", "对", "错", "是", "否", "true", "false", "1", "0"}:
        return "判断题", "根据真假答案推断"
    stem = " ".join(candidate["textParts"])
    if "_" in stem or "第一空" in answer or ANSWER_CONTINUATION_RE.match(answer):
        return "填空题", "根据空格和分空答案推断"
    if original_type == "选择题":
        return None, None
    return None, None


def _finish_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    answer = candidate.get("answer", "")
    explanation_parts: list[str] = []
    if not answer:
        continuation_answers = []
        for text in candidate["postAnswerParts"]:
            match = ANSWER_CONTINUATION_RE.match(text)
            if match and compact_text(match.group(1)):
                continuation_answers.append(compact_text(match.group(1)))
            else:
                explanation_parts.append(text)
        if continuation_answers:
            answer = "; ".join(continuation_answers)
    else:
        explanation_parts = candidate["postAnswerParts"]
    inferred_type, type_inference = _infer_type({**candidate, "answer": answer})
    return {
        "text": compact_text(" ".join(candidate["textParts"])),
        "originalTypeLabel": candidate.get("originalTypeLabel"),
        "inferredType": inferred_type,
        "typeInference": type_inference,
        "position": candidate["position"],
        "options": candidate["options"],
        "attachments": candidate["attachments"],
        "chapter": candidate.get("chapter"),
        "chapterHeading": candidate.get("chapterHeading"),
        "answer": answer,
        "answerFound": candidate["answerFound"],
        "answerPosition": candidate.get("answerPosition"),
        "endPosition": candidate.get("endPosition"),
        "blockSequence": candidate["blockSequence"],
        "explanation": compact_text(" ".join(explanation_parts)) or None,
    }


def _candidate_from_buffer(
    blocks: list[dict[str, Any]],
    original_type: str | None,
    chapter: str | None,
    chapter_heading: str | None,
) -> dict[str, Any] | None:
    substantive = [block for block in blocks if block["text"] or block["attachments"]]
    if not substantive:
        return None
    first = substantive[0]
    candidate = _start_candidate(first, _strip_number_prefix(first["text"]), original_type, chapter, chapter_heading)
    for block in substantive[1:]:
        _append_block(candidate, block)
    return candidate


def _parse_document(path: Path, assets_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    blocks, stats = _blocks(path, assets_dir)
    chapter: str | None = None
    chapter_heading: str | None = None
    current_type: str | None = None
    questions: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    buffer: list[dict[str, Any]] = []
    unrecognized = 0

    def finish_current() -> None:
        nonlocal current
        if current is not None:
            questions.append(_finish_candidate(current))
            current = None

    for block in blocks:
        text = block["text"]
        answer_match = ANSWER_RE.match(text) if block["kind"] == "paragraph" else None
        heading_chapter = _chapter_for_heading(text)
        heading_type = _type_heading(text)
        explicit_stem, explicit_type = strip_question_prefix(text)
        is_numbered = bool(NUMBERED_QUESTION_RE.match(text)) and not explicit_type

        if heading_chapter:
            finish_current()
            chapter = heading_chapter
            chapter_heading = text
            current_type = None
            buffer.clear()
            continue
        if CHAPTER_HEADING_RE.match(text):
            finish_current()
            chapter = None
            chapter_heading = text
            current_type = None
            buffer.clear()
            continue
        if heading_type:
            finish_current()
            current_type = heading_type
            buffer.clear()
            continue

        if current is not None and current["answerFound"]:
            trailing = TRAILING_TYPE_RE.match(text)
            if trailing and trailing.group(2):
                prefix = compact_text(trailing.group(1))
                if prefix:
                    current["postAnswerParts"].append(prefix)
                    current["blockSequence"].append(block["position"])
                    current["endPosition"] = block["position"]
                finish_current()
                current = _start_candidate(block, "", trailing.group(2), chapter, chapter_heading)
                buffer.clear()
                continue

        if explicit_type or is_numbered:
            finish_current()
            stem = explicit_stem if explicit_type else _strip_number_prefix(text)
            original_type = explicit_type or current_type
            current = _start_candidate(block, stem, original_type, chapter, chapter_heading)
            buffer.clear()
            continue

        if answer_match:
            if current is None:
                current = _candidate_from_buffer(buffer, current_type, chapter, chapter_heading)
                buffer.clear()
            elif current["answerFound"]:
                post_blocks = current.pop("postAnswerBlocks", [])
                finish_current()
                current = _candidate_from_buffer(post_blocks, current_type, chapter, chapter_heading)
            if current is None:
                current = _start_candidate(block, "", current_type, chapter, chapter_heading)
                unrecognized += 1
            source_answer = compact_text(answer_match.group(1))
            next_type = TRAILING_TYPE_RE.match(source_answer)
            if next_type and compact_text(next_type.group(1)):
                source_answer = compact_text(next_type.group(1))
                current_type = next_type.group(2)
            current["answer"] = source_answer
            current["answerFound"] = True
            current["answerPosition"] = block["position"]
            current["blockSequence"].append(block["position"])
            current["endPosition"] = block["position"]
            continue

        if current is None:
            buffer.append(block)
            continue
        if current["answerFound"]:
            current.setdefault("postAnswerBlocks", []).append(block)
            _append_block(current, block, after_answer=True)
        else:
            _append_block(current, block)

    finish_current()
    stats["sourceQuestions"] = len(questions)
    stats["unrecognized"] = unrecognized
    return questions, stats


def _richness(item: dict[str, Any]) -> tuple[int, int, int]:
    metadata = item["sourceMetadata"]
    source_answer = metadata.get("sourceAnswer") or item.get("sourceAnswer") or ""
    return (
        len(item.get("attachments", [])),
        len(str(source_answer)),
        len(str(item.get("explanation") or "")),
    )


def _deduplicate(
    records: list[dict[str, Any]],
    review_items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for record in records:
        grouped.setdefault(record["contentFingerprint"], {"records": [], "reviews": []})["records"].append(record)
    for item in review_items:
        grouped.setdefault(item["contentFingerprint"], {"records": [], "reviews": []})["reviews"].append(item)

    deduplicated_records: list[dict[str, Any]] = []
    deduplicated_reviews: list[dict[str, Any]] = []
    for fingerprint in sorted(grouped):
        group = grouped[fingerprint]
        candidates = group["records"] if group["records"] else group["reviews"]
        ranked = sorted(
            candidates,
            key=lambda item: (
                -_richness(item)[0],
                -_richness(item)[1],
                -_richness(item)[2],
                item["sourceMetadata"]["file"],
                item["sourceMetadata"]["sequence"],
            ),
        )
        chosen = ranked[0]
        all_items = sorted(
            [*group["records"], *group["reviews"]],
            key=lambda item: (item["sourceMetadata"]["file"], item["sourceMetadata"]["sequence"]),
        )
        duplicate_sources = [
            item["sourceMetadata"]
            for item in all_items
            if item is not chosen
        ]
        if duplicate_sources:
            chosen["sourceMetadata"]["duplicateSources"] = duplicate_sources
        if group["records"]:
            deduplicated_records.append(chosen)
        else:
            deduplicated_reviews.append(chosen)
    sort_key = lambda item: (item["sourceMetadata"]["file"], item["sourceMetadata"]["sequence"])
    return sorted(deduplicated_records, key=sort_key), sorted(deduplicated_reviews, key=sort_key)


def parse_question_bank(
    source_dir: Path,
    output_dir: Path,
    public_assets_dir: Path | None = None,
) -> ImportReport:
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)
    assets_dir = Path(public_assets_dir) if public_assets_dir is not None else output_dir / "question-assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for stale_asset in assets_dir.iterdir():
        if stale_asset.is_file() or stale_asset.is_symlink():
            stale_asset.unlink()
    records: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []
    source_files: list[dict[str, Any]] = []
    sources = sorted(source_dir.glob("*.docx"), key=lambda item: item.name)
    for source in sources:
        parsed_questions, source_stats = _parse_document(source, assets_dir)
        active_candidates = 0
        review_candidates = 0
        for sequence, parsed in enumerate(parsed_questions, start=1):
            record, review_item = normalize_candidate(parsed, source.name, sequence)
            if record is not None:
                records.append(record)
                active_candidates += 1
            if review_item is not None:
                review_items.append(review_item)
                review_candidates += 1
        source_stats["activeCandidates"] = active_candidates
        source_stats["reviewCandidates"] = review_candidates
        source_files.append(source_stats)
    source_questions = len(records) + len(review_items)
    records, review_items = _deduplicate(records, review_items)
    deduplicated_questions = len(records) + len(review_items)
    is_supplied_corpus = [source.name for source in sources] == EXPECTED_SOURCE_FILES
    archive_sha = SOURCE_ARCHIVE_SHA256 if is_supplied_corpus else None
    note_path = source_dir / "说明.txt"
    note_metadata = None
    if note_path.exists():
        note_metadata = {
            "file": note_path.name,
            "sha256": hashlib.sha256(note_path.read_bytes()).hexdigest(),
            "sizeBytes": note_path.stat().st_size,
        }
    manifest = {
        "schemaVersion": 1,
        "subject": {"id": SUBJECT_ID, "title": "土力学", "slug": SUBJECT_ID, "status": "active", "sortOrder": 1},
        "knowledgePoints": KNOWLEDGE_POINTS,
        "questions": records,
        "sourceArchiveSha256": archive_sha,
    }
    image_count = sum(item["imageCount"] for item in source_files)
    table_count = sum(item["tableCount"] for item in source_files)
    answer_marker_count = sum(item["answerMarkerCount"] for item in source_files)
    omml_count = sum(item["ommlCount"] for item in source_files)
    unrecognized = sum(item["unrecognized"] for item in source_files)
    asset_count = len([path for path in assets_dir.iterdir() if path.is_file()])
    reason_counts = Counter(
        reason["code"]
        for item in review_items
        for reason in item["reasons"]
    )
    concerns: list[str] = []
    if review_items:
        concerns.append(f"{len(review_items)} 个去重后候选项因题型、答案、知识点或严格模式校验不确定而保留复核。")
    if unrecognized:
        concerns.append(f"{unrecognized} 个答案标记缺少可靠的前置题目结构，已作为复核候选保留。")
    if is_supplied_corpus:
        if source_questions < 1000:
            concerns.append(f"来源候选仅 {source_questions} 个，低于计划阈值 1000。")
        if image_count < 300:
            concerns.append(f"图像引用仅 {image_count} 个，低于计划阈值 300。")
        if table_count < 8:
            concerns.append(f"表格仅 {table_count} 个，低于计划阈值 8。")
    formats = ["DOCX", "WordprocessingML paragraphs"]
    if image_count:
        formats.append("DrawingML/VML images")
    if table_count:
        formats.append("WordprocessingML tables")
    if omml_count:
        formats.append("Office Math Markup Language")
    report_data = {
        "schemaVersion": 1,
        "status": "DONE_WITH_CONCERNS" if concerns else "DONE",
        "sourceArchiveSha256": archive_sha,
        "sourceNotes": note_metadata,
        "sourceFileCount": len(sources),
        "sourceFiles": source_files,
        "formats": formats,
        "sourceQuestions": source_questions,
        "answerMarkerCount": answer_marker_count,
        "deduplicatedQuestions": deduplicated_questions,
        "duplicateCount": source_questions - deduplicated_questions,
        "activeQuestions": len(records),
        "reviewQuestions": len(review_items),
        "imageCount": image_count,
        "imageAssetCount": asset_count,
        "imageContentDuplicateCount": max(image_count - asset_count, 0),
        "mediaPartCount": sum(item["mediaPartCount"] for item in source_files),
        "tableCount": table_count,
        "tableRowCount": sum(item["tableRowCount"] for item in source_files),
        "ommlCount": omml_count,
        "unrecognized": unrecognized,
        "reviewReasonCounts": dict(sorted(reason_counts.items())),
        "concerns": concerns,
        "reviewItems": review_items,
    }
    _write_json(output_dir / "knowledge-points.json", KNOWLEDGE_POINTS)
    _write_json(output_dir / "manifest.json", manifest)
    _write_json(output_dir / "import-report.json", report_data)
    return ImportReport(report_data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize a soil-mechanics DOCX question-bank corpus.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--public-assets", type=Path)
    args = parser.parse_args(argv)
    report = parse_question_bank(args.source, args.output, args.public_assets)
    data = report.to_dict()
    summary_keys = (
        "status", "sourceFileCount", "sourceQuestions", "answerMarkerCount",
        "deduplicatedQuestions", "activeQuestions", "reviewQuestions",
        "imageCount", "imageAssetCount", "tableCount", "ommlCount", "unrecognized",
    )
    print(json.dumps({key: data[key] for key in summary_keys}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
