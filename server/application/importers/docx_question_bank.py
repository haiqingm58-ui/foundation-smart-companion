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
EXPECTED_SOURCE_SHA256 = {
    "1-随堂检测题库.docx": "61cb992e0862e4cd3dd6d73cf86ff9b74a7c4f56fd0c22433ff880bc3bcfa0a4",
    "2-章节测验.docx": "1b606278ebfc5b4c6ddda67fbdaa1886577133852aefc4cd769896e4f6b38c93",
    "3-其他题库-1.docx": "dd57d09924d3d0bc9b99ebc760db835bf58a081b31a5fbc9e84dc7bdd822cdec",
    "4-其他题库-2.docx": "d5eaf7056f721d3ad56dbb77e545dd69a4c19fb26c988952c034e1dcc4bf1ad1",
}
EXPECTED_SOURCE_NOTE_SHA256 = "32dbc74123f66a561e6bd18ca5d0f2ce5eacf3949d83acef46304d4bcf63a7df"


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


def _append_text_token(tokens: list[dict[str, Any]], text: str) -> None:
    if not text:
        return
    if tokens and tokens[-1]["kind"] == "text":
        tokens[-1]["text"] += text
    else:
        tokens.append({"kind": "text", "text": text})


def _ordered_inline_content(
    element: etree._Element,
    archive: ZipFile,
    relationships: dict[str, str],
    assets_dir: Path,
    position: dict[str, int],
    *,
    starting_ordinal: int = 1,
    include_text: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    attachments: list[dict[str, Any]] = []
    inline_content: list[dict[str, Any]] = []
    for child in element.iterdescendants():
        qname = etree.QName(child)
        if include_text and qname.namespace == NS["w"] and qname.localname == "t":
            _append_text_token(inline_content, child.text or "")
            continue
        if include_text and qname.namespace == NS["w"] and qname.localname in {"tab", "br", "cr"}:
            _append_text_token(inline_content, "\t" if qname.localname == "tab" else "\n")
            continue
        relationship_id: str | None = None
        if qname.namespace == NS["a"] and qname.localname == "blip":
            relationship_id = child.get(f"{{{NS['r']}}}embed") or child.get(f"{{{NS['r']}}}link")
        elif qname.namespace == NS["v"] and qname.localname == "imagedata":
            relationship_id = child.get(f"{{{NS['r']}}}id")
        elif qname.namespace == NS["m"] and qname.localname in {"oMath", "oMathPara"}:
            if qname.localname == "oMath" and child.getparent() is not None and etree.QName(child.getparent()).namespace == NS["m"] and etree.QName(child.getparent()).localname == "oMathPara":
                continue
            source = etree.tostring(child, encoding="unicode", with_tail=False)
            ordinal = starting_ordinal + len(attachments)
            placeholder = f"[[attachment:{ordinal}]]"
            attachments.append({
                "kind": "formula",
                "ommlText": compact_text("".join(child.xpath(".//m:t/text()", namespaces=NS))),
                "ommlSource": source,
                "ommlSha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                "sourcePosition": position,
                "inlineOrdinal": ordinal,
                "placeholder": placeholder,
            })
            inline_content.append({"kind": "attachment", "attachmentOrdinal": ordinal, "placeholder": placeholder})
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
        ordinal = starting_ordinal + len(attachments)
        placeholder = f"[[attachment:{ordinal}]]"
        attachments.append({
            "kind": "image",
            "src": f"/foundation-smart-companion/question-assets/soil-mechanics/{asset.name}",
            "alt": "题目附图",
            "sha256": digest,
            "sourcePosition": position,
            "inlineOrdinal": ordinal,
            "placeholder": placeholder,
        })
        inline_content.append({"kind": "attachment", "attachmentOrdinal": ordinal, "placeholder": placeholder})
    text_with_placeholders = "".join(
        token.get("text", "") if token["kind"] == "text" else token["placeholder"]
        for token in inline_content
    )
    return attachments, inline_content, text_with_placeholders


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
                attachments, inline_content, text_with_placeholders = _ordered_inline_content(
                    element, archive, relationships, assets_dir, position
                )
                result.append(
                    {
                        "kind": "paragraph",
                        "text": _element_text(element),
                        "position": position,
                        "attachments": attachments,
                        "inlineContent": inline_content,
                        "textWithPlaceholders": text_with_placeholders,
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
                table_placeholder = "[[attachment:1]]"
                attachments = [{
                    "kind": "table",
                    "rows": rows,
                    "sourcePosition": position,
                    "inlineOrdinal": 1,
                    "placeholder": table_placeholder,
                }]
                inline_attachments, inline_content, text_with_placeholders = _ordered_inline_content(
                    element,
                    archive,
                    relationships,
                    assets_dir,
                    position,
                    starting_ordinal=2,
                    include_text=False,
                )
                attachments.extend(inline_attachments)
                table_token = {"kind": "attachment", "attachmentOrdinal": 1, "placeholder": table_placeholder}
                inline_content.insert(0, table_token)
                text_with_placeholders = table_placeholder + text_with_placeholders
                result.append({
                    "kind": "table",
                    "text": "",
                    "position": position,
                    "attachments": attachments,
                    "inlineContent": inline_content,
                    "textWithPlaceholders": text_with_placeholders,
                })
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
    *,
    role: str = "stem",
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
        "sourceBlocks": [_source_block(block, role)],
        "endPosition": block["position"],
    }


def _source_block(block: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        "kind": block["kind"],
        "role": role,
        "sourcePosition": block["position"],
        "text": block["text"],
        "textWithPlaceholders": block["textWithPlaceholders"],
        "inlineContent": block["inlineContent"],
    }


def _append_candidate_block(candidate: dict[str, Any], block: dict[str, Any], role: str) -> None:
    candidate["attachments"].extend(block["attachments"])
    candidate["blockSequence"].append(block["position"])
    candidate["sourceBlocks"].append(_source_block(block, role))
    candidate["endPosition"] = block["position"]


def _append_block(candidate: dict[str, Any], block: dict[str, Any], *, after_answer: bool = False) -> None:
    text = block["text"]
    if block["kind"] == "table" or not text:
        _append_candidate_block(candidate, block, "postAnswer" if after_answer else "content")
        return
    if after_answer:
        _append_candidate_block(candidate, block, "postAnswer")
        candidate["postAnswerParts"].append(text)
        return
    options = _inline_options(text)
    if options:
        _append_candidate_block(candidate, block, "option")
        candidate["options"].extend(options)
        candidate["pendingOption"] = options[-1]["label"] if not options[-1]["text"] else None
        return
    pending_label = candidate.get("pendingOption")
    if pending_label:
        _append_candidate_block(candidate, block, "optionContinuation")
        for option in reversed(candidate["options"]):
            if option["label"] == pending_label:
                option["text"] = text
                break
        candidate["pendingOption"] = None
        return
    _append_candidate_block(candidate, block, "stemContinuation")
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
        "sourceBlocks": candidate["sourceBlocks"],
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


def _attachment_occurrence_key(attachment: dict[str, Any]) -> bytes:
    return canonical_json_bytes({
        "kind": attachment.get("kind"),
        "sourcePosition": attachment.get("sourcePosition"),
        "inlineOrdinal": attachment.get("inlineOrdinal"),
    })


def _parse_document(path: Path, assets_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    blocks, stats = _blocks(path, assets_dir)
    chapter: str | None = None
    chapter_heading: str | None = None
    current_type: str | None = None
    questions: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    buffer: list[dict[str, Any]] = []
    unrecognized = 0

    def flush_post_answer_blocks() -> None:
        if current is None:
            return
        for post_block in current.pop("postAnswerBlocks", []):
            _append_block(current, post_block, after_answer=True)

    def finish_current(*, include_post_answer: bool = True) -> None:
        nonlocal current
        if current is not None:
            if include_post_answer:
                flush_post_answer_blocks()
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
                flush_post_answer_blocks()
                prefix = compact_text(trailing.group(1))
                if prefix or block["attachments"]:
                    _append_candidate_block(current, block, "postAnswer")
                if prefix:
                    current["postAnswerParts"].append(prefix)
                finish_current()
                current_type = trailing.group(2)
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
            answer_block_added = False
            if current is None:
                current = _candidate_from_buffer(buffer, current_type, chapter, chapter_heading)
                buffer.clear()
            elif current["answerFound"]:
                post_blocks = current.pop("postAnswerBlocks", [])
                finish_current(include_post_answer=False)
                current = _candidate_from_buffer(post_blocks, current_type, chapter, chapter_heading)
            if current is None:
                current = _start_candidate(block, "", current_type, chapter, chapter_heading, role="answer")
                answer_block_added = True
                unrecognized += 1
            source_answer = compact_text(answer_match.group(1))
            next_type = TRAILING_TYPE_RE.match(source_answer)
            if next_type and compact_text(next_type.group(1)):
                source_answer = compact_text(next_type.group(1))
                current_type = next_type.group(2)
            current["answer"] = source_answer
            current["answerFound"] = True
            current["answerPosition"] = block["position"]
            if not answer_block_added:
                _append_candidate_block(current, block, "answer")
            continue

        if current is None:
            buffer.append(block)
            continue
        if current["answerFound"]:
            current.setdefault("postAnswerBlocks", []).append(block)
        else:
            _append_block(current, block)

    finish_current()
    linked_attachment_keys = {
        _attachment_occurrence_key(attachment)
        for question in questions
        for attachment in question["attachments"]
    }
    all_attachments = [attachment for block in blocks for attachment in block["attachments"]]
    attachment_losses = [
        attachment for attachment in all_attachments
        if _attachment_occurrence_key(attachment) not in linked_attachment_keys
    ]
    stats["sourceQuestions"] = len(questions)
    stats["unrecognized"] = unrecognized
    stats["attachmentOccurrenceCount"] = len(all_attachments)
    stats["linkedAttachmentOccurrenceCount"] = len(all_attachments) - len(attachment_losses)
    stats["_attachmentLosses"] = attachment_losses
    return questions, stats


def _richness(item: dict[str, Any]) -> tuple[int, int, int]:
    metadata = item["sourceMetadata"]
    source_answer = metadata.get("sourceAnswer") or item.get("sourceAnswer") or ""
    return (
        len(item.get("attachments", [])),
        len(str(source_answer)),
        len(str(item.get("explanation") or "")),
    )


def _variant_identity(item: dict[str, Any]) -> bytes:
    metadata = item["sourceMetadata"]
    return canonical_json_bytes({
        "questionType": item.get("questionType"),
        "chapter": item.get("chapter"),
        "knowledgePointIds": item.get("knowledgePointIds", []),
        "sourceAnswer": compact_text(str(metadata.get("sourceAnswer", item.get("sourceAnswer", "")))).casefold(),
        "normalizedAnswer": item.get("correctAnswer", item.get("normalizedAnswer")),
        "gradingMode": item.get("gradingMode"),
        "explanation": compact_text(str(item.get("explanation") or "")).casefold(),
    })


def _review_occurrence_id(item: dict[str, Any]) -> str:
    metadata = item["sourceMetadata"]
    occurrence = hashlib.sha256(canonical_json_bytes({
        "file": metadata["file"],
        "sequence": metadata["sequence"],
        "position": metadata["position"],
    })).hexdigest()
    return f"soil-review-{item['contentFingerprint'][:16]}-{occurrence[:12]}"


def _record_as_conflict_review(record: dict[str, Any], detail: str) -> dict[str, Any]:
    item = {
        "contentFingerprint": record["contentFingerprint"],
        "text": record["text"],
        "questionType": record.get("questionType"),
        "chapter": record.get("chapter"),
        "knowledgePointIds": record.get("knowledgePointIds", []),
        "options": record.get("options", []),
        "sourceAnswer": record["sourceMetadata"].get("sourceAnswer", ""),
        "normalizedAnswer": record.get("correctAnswer"),
        "gradingMode": record.get("gradingMode"),
        "explanation": record.get("explanation"),
        "attachments": record.get("attachments", []),
        "sourceBlocks": record.get("sourceBlocks", []),
        "sourceMetadata": record["sourceMetadata"],
        "reasons": [{"code": "DUPLICATE_CONFLICT", "detail": detail}],
        "duplicateClassification": "conflicted",
    }
    item["id"] = _review_occurrence_id(item)
    return item


def _mark_conflicted_review(item: dict[str, Any], detail: str) -> None:
    if not any(reason.get("code") == "DUPLICATE_CONFLICT" for reason in item["reasons"]):
        item["reasons"].append({"code": "DUPLICATE_CONFLICT", "detail": detail})
    item["duplicateClassification"] = "conflicted"


def _deduplicate(
    records: list[dict[str, Any]],
    review_items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], int]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for record in records:
        grouped.setdefault(record["contentFingerprint"], {"records": [], "reviews": []})["records"].append(record)
    for item in review_items:
        grouped.setdefault(item["contentFingerprint"], {"records": [], "reviews": []})["reviews"].append(item)

    deduplicated_records: list[dict[str, Any]] = []
    deduplicated_reviews: list[dict[str, Any]] = []
    duplicate_occurrences: list[dict[str, Any]] = []
    for fingerprint in sorted(grouped):
        group = grouped[fingerprint]
        active_variants = {_variant_identity(item) for item in group["records"]}
        if len(active_variants) > 1:
            detail = "同一题面及语义附件存在不一致的题型、章节或答案变体，所有 active 候选均转入复核。"
            converted = [_record_as_conflict_review(item, detail) for item in group["records"]]
            for item in group["reviews"]:
                _mark_conflicted_review(item, detail)
            deduplicated_reviews.extend([*converted, *group["reviews"]])
            continue

        chosen: dict[str, Any] | None = None
        if group["records"]:
            ranked = sorted(
                group["records"],
                key=lambda item: (
                    -_richness(item)[0],
                    -_richness(item)[1],
                    -_richness(item)[2],
                    item["sourceMetadata"]["file"],
                    item["sourceMetadata"]["sequence"],
                ),
            )
            chosen = ranked[0]
            exact_duplicates = sorted(
                ranked[1:],
                key=lambda item: (item["sourceMetadata"]["file"], item["sourceMetadata"]["sequence"]),
            )
            if exact_duplicates:
                chosen["sourceMetadata"]["duplicateSources"] = [
                    item["sourceMetadata"] for item in exact_duplicates
                ]
                duplicate_occurrences.extend({
                    "classification": "exact",
                    "duplicateOfId": chosen["id"],
                    "contentFingerprint": item["contentFingerprint"],
                    "text": item["text"],
                    "questionType": item.get("questionType"),
                    "chapter": item.get("chapter"),
                    "options": item.get("options", []),
                    "sourceAnswer": item["sourceMetadata"].get("sourceAnswer", ""),
                    "attachments": item.get("attachments", []),
                    "sourceBlocks": item.get("sourceBlocks", []),
                    "sourceMetadata": item["sourceMetadata"],
                } for item in exact_duplicates)
            deduplicated_records.append(chosen)

        if group["reviews"]:
            if chosen is not None:
                detail = "同一题面及语义附件同时存在 active 与 review 变体；review 原因和来源负载完整保留。"
                for item in group["reviews"]:
                    _mark_conflicted_review(item, detail)
                    item["duplicateOfId"] = chosen["id"]
            elif len({_variant_identity(item) for item in group["reviews"]}) > 1:
                detail = "同一题面及语义附件存在不一致的复核变体，所有来源负载完整保留。"
                for item in group["reviews"]:
                    _mark_conflicted_review(item, detail)
            deduplicated_reviews.extend(group["reviews"])
    sort_key = lambda item: (item["sourceMetadata"]["file"], item["sourceMetadata"]["sequence"])
    duplicate_occurrences.sort(key=sort_key)
    deduplicated_reviews.sort(key=sort_key)
    conflicted_count = sum(item.get("duplicateClassification") == "conflicted" for item in deduplicated_reviews)
    return sorted(deduplicated_records, key=sort_key), deduplicated_reviews, duplicate_occurrences, conflicted_count


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
    attachment_loss_records: list[dict[str, Any]] = []
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
        for attachment in source_stats.pop("_attachmentLosses"):
            attachment_loss_records.append({
                "classification": "unlinked-source-attachment",
                "sourceMetadata": {
                    "file": source.name,
                    "position": attachment["sourcePosition"],
                    "inlineOrdinal": attachment["inlineOrdinal"],
                },
                "attachment": attachment,
                "reason": "附件位于未形成题目候选的源块中，作为显式损失审计记录保留。",
            })
        source_files.append(source_stats)
    source_questions = len(records) + len(review_items)
    records, review_items, duplicate_occurrences, conflicted_duplicate_count = _deduplicate(records, review_items)
    deduplicated_questions = len(records) + len(review_items)
    note_path = source_dir / "说明.txt"
    note_metadata = None
    if note_path.exists():
        note_metadata = {
            "file": note_path.name,
            "sha256": hashlib.sha256(note_path.read_bytes()).hexdigest(),
            "sizeBytes": note_path.stat().st_size,
        }
    source_archive_verified = (
        [source.name for source in sources] == EXPECTED_SOURCE_FILES
        and {item["file"]: item["sha256"] for item in source_files} == EXPECTED_SOURCE_SHA256
        and note_metadata is not None
        and note_metadata["sha256"] == EXPECTED_SOURCE_NOTE_SHA256
    )
    archive_sha = SOURCE_ARCHIVE_SHA256 if source_archive_verified else None
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
        concerns.append(f"{len(review_items)} 个来源候选项因题型、答案、知识点、重复冲突或严格模式校验不确定而保留复核。")
    if unrecognized:
        concerns.append(f"{unrecognized} 个答案标记缺少可靠的前置题目结构，已作为复核候选保留。")
    if source_archive_verified:
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
    active_attachment_count = sum(len(item["attachments"]) for item in records)
    review_attachment_count = sum(len(item["attachments"]) for item in review_items)
    exact_duplicate_attachment_count = sum(len(item["attachments"]) for item in duplicate_occurrences)
    loss_attachment_count = len(attachment_loss_records)
    source_attachment_count = sum(item["attachmentOccurrenceCount"] for item in source_files)
    accounted_attachment_count = (
        active_attachment_count
        + review_attachment_count
        + exact_duplicate_attachment_count
        + loss_attachment_count
    )
    attachment_accounting = {
        "sourceOccurrenceCount": source_attachment_count,
        "activeOccurrenceCount": active_attachment_count,
        "reviewOccurrenceCount": review_attachment_count,
        "exactDuplicateOccurrenceCount": exact_duplicate_attachment_count,
        "lossOccurrenceCount": loss_attachment_count,
        "accountedOccurrenceCount": accounted_attachment_count,
        "unaccountedOccurrenceCount": source_attachment_count - accounted_attachment_count,
    }
    if attachment_accounting["unaccountedOccurrenceCount"]:
        concerns.append(
            f"附件审计存在 {attachment_accounting['unaccountedOccurrenceCount']} 个未平衡来源出现，需复核。"
        )
    report_data = {
        "schemaVersion": 1,
        "status": "DONE_WITH_CONCERNS" if concerns else "DONE",
        "sourceArchiveSha256": archive_sha,
        "sourceArchiveVerified": source_archive_verified,
        "sourceNotes": note_metadata,
        "sourceFileCount": len(sources),
        "sourceFiles": source_files,
        "formats": formats,
        "sourceQuestions": source_questions,
        "answerMarkerCount": answer_marker_count,
        "deduplicatedQuestions": deduplicated_questions,
        "duplicateCount": len(duplicate_occurrences),
        "exactDuplicateCount": len(duplicate_occurrences),
        "conflictedDuplicateCount": conflicted_duplicate_count,
        "reviewGatedOccurrenceCount": len(review_items),
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
        "attachmentAccounting": attachment_accounting,
        "attachmentLossRecords": attachment_loss_records,
        "duplicateOccurrences": duplicate_occurrences,
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
