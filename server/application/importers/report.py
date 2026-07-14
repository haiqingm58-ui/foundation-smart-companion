from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from server.application.services.assessment_validation import AssessmentValidationError, validate_question

from .question_normalization import SUBJECT_ID, content_fingerprint


class ReportValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ImportReport:
    data: dict[str, Any]

    @property
    def unrecognized(self) -> int:
        return int(self.data.get("unrecognized", 0))

    def to_dict(self) -> dict[str, Any]:
        return self.data


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReportValidationError(f"无法读取 JSON：{path}") from error
    if not isinstance(payload, dict):
        raise ReportValidationError(f"JSON 根节点必须是对象：{path}")
    return payload


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReportValidationError(message)


def _image_asset_path(manifest_path: Path, filename: str) -> Path | None:
    local = manifest_path.parent / "question-assets" / filename
    if local.is_file():
        return local
    if len(manifest_path.parents) > 3:
        public = manifest_path.parents[3] / "public" / "question-assets" / "soil-mechanics" / filename
        if public.is_file():
            return public
    return None


def _image_asset_dir(manifest_path: Path) -> Path | None:
    local = manifest_path.parent / "question-assets"
    if local.is_dir():
        return local
    if len(manifest_path.parents) > 3:
        public = manifest_path.parents[3] / "public" / "question-assets" / "soil-mechanics"
        if public.is_dir():
            return public
    return None


def _validate_attachments(manifest_path: Path, attachments: Any, question_id: str) -> None:
    _require(isinstance(attachments, list), f"{question_id}: attachments 必须是数组")
    for attachment in attachments:
        _require(isinstance(attachment, dict), f"{question_id}: 附件必须是对象")
        kind = attachment.get("kind")
        _require(kind in {"image", "table", "formula"}, f"{question_id}: 附件类型无效")
        position = attachment.get("sourcePosition")
        _require(isinstance(position, dict) and isinstance(position.get("blockIndex"), int), f"{question_id}: 附件缺少源位置")
        ordinal = attachment.get("inlineOrdinal")
        placeholder = attachment.get("placeholder")
        _require(isinstance(ordinal, int) and ordinal >= 1, f"{question_id}: 附件缺少行内顺序")
        _require(placeholder == f"[[attachment:{ordinal}]]", f"{question_id}: 附件占位符无效")
        if kind == "table":
            rows = attachment.get("rows")
            _require(isinstance(rows, list) and all(isinstance(row, list) for row in rows), f"{question_id}: 表格行无效")
        elif kind == "formula":
            _require(isinstance(attachment.get("ommlText"), str), f"{question_id}: 公式缺少 OMML 文本")
            _require(isinstance(attachment.get("ommlSource"), str) and "oMath" in attachment["ommlSource"], f"{question_id}: 公式缺少 OMML 源码")
            expected_digest = hashlib.sha256(attachment["ommlSource"].encode("utf-8")).hexdigest()
            _require(attachment.get("ommlSha256") == expected_digest, f"{question_id}: OMML SHA-256 无效")
        else:
            digest = attachment.get("sha256")
            src = attachment.get("src")
            _require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None, f"{question_id}: 图像 SHA-256 无效")
            _require(isinstance(src, str) and src.startswith("/foundation-smart-companion/question-assets/soil-mechanics/"), f"{question_id}: 图像路径无效")
            filename = Path(src).name
            _require(filename.startswith(digest + "."), f"{question_id}: 图像文件名与 SHA-256 不匹配")
            asset = _image_asset_path(manifest_path, filename)
            _require(asset is not None, f"{question_id}: 图像资产不存在：{filename}")
            _require(hashlib.sha256(asset.read_bytes()).hexdigest() == digest, f"{question_id}: 图像内容 SHA-256 不匹配")


def _validate_source_blocks(source_blocks: Any, attachments: list[dict[str, Any]], item_id: str) -> None:
    _require(isinstance(source_blocks, list) and source_blocks, f"{item_id}: sourceBlocks 必须是非空数组")
    for block in source_blocks:
        _require(isinstance(block, dict), f"{item_id}: sourceBlocks 项必须是对象")
        _require(block.get("kind") in {"paragraph", "table"}, f"{item_id}: sourceBlocks 类型无效")
        _require(isinstance(block.get("role"), str) and block["role"], f"{item_id}: sourceBlocks 缺少角色")
        position = block.get("sourcePosition")
        _require(isinstance(position, dict) and isinstance(position.get("blockIndex"), int), f"{item_id}: sourceBlocks 缺少源位置")
        _require(isinstance(block.get("text"), str), f"{item_id}: sourceBlocks 文本无效")
        _require(isinstance(block.get("textWithPlaceholders"), str), f"{item_id}: sourceBlocks 占位文本无效")
        inline_content = block.get("inlineContent")
        _require(isinstance(inline_content, list), f"{item_id}: inlineContent 必须是数组")
        reconstructed = ""
        for token in inline_content:
            _require(isinstance(token, dict) and token.get("kind") in {"text", "attachment"}, f"{item_id}: inlineContent 项无效")
            if token["kind"] == "text":
                _require(isinstance(token.get("text"), str), f"{item_id}: inlineContent 文本无效")
                reconstructed += token["text"]
            else:
                ordinal = token.get("attachmentOrdinal")
                placeholder = token.get("placeholder")
                _require(isinstance(ordinal, int) and placeholder == f"[[attachment:{ordinal}]]", f"{item_id}: inlineContent 附件引用无效")
                reconstructed += placeholder
        _require(reconstructed == block["textWithPlaceholders"], f"{item_id}: sourceBlocks 无法按顺序重构")
    for attachment in attachments:
        matching_blocks = [
            block for block in source_blocks
            if block["sourcePosition"] == attachment["sourcePosition"]
        ]
        _require(matching_blocks, f"{item_id}: 附件源块未保留")
        _require(any(
            token.get("kind") == "attachment"
            and token.get("attachmentOrdinal") == attachment["inlineOrdinal"]
            and token.get("placeholder") == attachment["placeholder"]
            for block in matching_blocks
            for token in block["inlineContent"]
        ), f"{item_id}: 附件行内位置未保留")


def validate_generated_files(manifest_path: Path, report_path: Path) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    report_path = Path(report_path)
    manifest = _load_json(manifest_path)
    report = _load_json(report_path)
    _require(manifest.get("schemaVersion") == 1, "manifest schemaVersion 必须为 1")
    _require(report.get("schemaVersion") == 1, "report schemaVersion 必须为 1")
    subject = manifest.get("subject")
    _require(isinstance(subject, dict) and subject.get("id") == SUBJECT_ID, "manifest 课程必须为 soil-mechanics")

    catalog = manifest.get("knowledgePoints")
    _require(isinstance(catalog, list), "knowledgePoints 必须是数组")
    catalog_ids: set[str] = set()
    for point in catalog:
        _require(isinstance(point, dict), "知识点必须是对象")
        identifier = point.get("id")
        _require(isinstance(identifier, str) and identifier not in catalog_ids, "知识点 ID 必须唯一")
        catalog_ids.add(identifier)
        _require(point.get("subjectId") == SUBJECT_ID, f"{identifier}: 知识点课程无效")
        _require(point.get("status") in {"active", "inactive"}, f"{identifier}: 知识点状态无效")
        _require(all(isinstance(point.get(key), str) and point[key].strip() for key in ("chapter", "name", "description")), f"{identifier}: 知识点字段不完整")
        _require(isinstance(point.get("sortOrder"), int), f"{identifier}: sortOrder 必须是整数")

    questions = manifest.get("questions")
    _require(isinstance(questions, list), "questions 必须是数组")
    question_ids: set[str] = set()
    fingerprints: set[str] = set()
    payload_keys = {
        "subjectId", "knowledgePointIds", "text", "questionType", "chapter", "difficulty",
        "options", "correctAnswer", "points", "answerWordLimit", "gradingMode",
    }
    for question in questions:
        _require(isinstance(question, dict), "题目必须是对象")
        identifier = question.get("id")
        fingerprint = question.get("contentFingerprint")
        _require(isinstance(identifier, str) and identifier not in question_ids, "题目 ID 必须唯一")
        _require(isinstance(fingerprint, str) and re.fullmatch(r"[0-9a-f]{64}", fingerprint) is not None and fingerprint not in fingerprints, f"{identifier}: 内容指纹无效或重复")
        question_ids.add(identifier)
        fingerprints.add(fingerprint)
        _require(question.get("status") == "active", f"{identifier}: manifest 只能包含 active 题目")
        point_ids = question.get("knowledgePointIds")
        _require(isinstance(point_ids, list) and 1 <= len(point_ids) <= 3 and len(set(point_ids)) == len(point_ids), f"{identifier}: 知识点数量无效")
        _require(all(point_id in catalog_ids for point_id in point_ids), f"{identifier}: 题目引用了未编目知识点")
        _require(content_fingerprint(question.get("text", ""), question.get("options", []), question.get("attachments", [])) == fingerprint, f"{identifier}: 内容指纹不匹配")
        metadata = question.get("sourceMetadata")
        _require(isinstance(metadata, dict) and isinstance(metadata.get("file"), str), f"{identifier}: 缺少源文件")
        _require(isinstance(metadata.get("position"), dict) and isinstance(metadata["position"].get("blockIndex"), int), f"{identifier}: 缺少源位置")
        _require(isinstance(metadata.get("sequence"), int), f"{identifier}: 缺少源顺序")
        _validate_attachments(manifest_path, question.get("attachments"), identifier)
        _validate_source_blocks(question.get("sourceBlocks"), question["attachments"], identifier)
        try:
            validate_question({key: question.get(key) for key in payload_keys})
        except AssessmentValidationError as error:
            raise ReportValidationError(f"{identifier}: {error.code}: {error}") from error

    review_items = report.get("reviewItems")
    _require(isinstance(review_items, list), "reviewItems 必须是数组")
    _require(report.get("activeQuestions") == len(questions), "activeQuestions 与 manifest 不一致")
    _require(report.get("reviewQuestions") == len(review_items), "reviewQuestions 与 reviewItems 不一致")
    _require(report.get("deduplicatedQuestions") == len(questions) + len(review_items), "deduplicatedQuestions 计数不一致")
    duplicate_occurrences = report.get("duplicateOccurrences")
    _require(isinstance(duplicate_occurrences, list), "duplicateOccurrences 必须是数组")
    _require(report.get("duplicateCount") == len(duplicate_occurrences), "duplicateCount 与 duplicateOccurrences 不一致")
    _require(report.get("exactDuplicateCount") == len(duplicate_occurrences), "exactDuplicateCount 与 duplicateOccurrences 不一致")
    _require(report.get("sourceQuestions") == report.get("deduplicatedQuestions") + len(duplicate_occurrences), "sourceQuestions 计数不一致")
    _require(report.get("reviewGatedOccurrenceCount") == len(review_items), "reviewGatedOccurrenceCount 与 reviewItems 不一致")
    source_files = report.get("sourceFiles")
    _require(isinstance(source_files, list) and report.get("sourceFileCount") == len(source_files), "sourceFiles 计数不一致")
    source_names = [item.get("file") for item in source_files if isinstance(item, dict)]
    _require(len(source_names) == len(source_files) and len(set(source_names)) == len(source_names), "sourceFiles 文件名无效或重复")
    for key in ("sourceQuestions", "answerMarkerCount", "imageCount", "tableCount", "tableRowCount", "ommlCount", "unrecognized"):
        _require(
            report.get(key) == sum(item.get(key, 0) for item in source_files),
            f"{key} 与逐文件统计不一致",
        )
    expected_reason_counts = Counter(
        reason.get("code")
        for item in review_items
        if isinstance(item, dict)
        for reason in item.get("reasons", [])
        if isinstance(reason, dict)
    )
    _require(dict(sorted(expected_reason_counts.items())) == report.get("reviewReasonCounts"), "reviewReasonCounts 与 reviewItems 不一致")
    for item in review_items:
        _require(isinstance(item, dict) and isinstance(item.get("reasons"), list) and item["reasons"], "复核项必须包含原因")
        metadata = item.get("sourceMetadata")
        _require(isinstance(metadata, dict) and metadata.get("file") in source_names, "复核项源文件无效")
        _require(isinstance(metadata.get("position"), dict) and isinstance(metadata["position"].get("blockIndex"), int), "复核项源位置无效")
        _validate_attachments(manifest_path, item.get("attachments"), item.get("id", "review-item"))
        _validate_source_blocks(item.get("sourceBlocks"), item["attachments"], item.get("id", "review-item"))
    conflicted_count = sum(item.get("duplicateClassification") == "conflicted" for item in review_items)
    _require(report.get("conflictedDuplicateCount") == conflicted_count, "conflictedDuplicateCount 与 reviewItems 不一致")

    for index, item in enumerate(duplicate_occurrences, start=1):
        item_id = f"duplicate-{index}"
        _require(isinstance(item, dict) and item.get("classification") == "exact", f"{item_id}: 精确重复记录无效")
        _require(item.get("duplicateOfId") in question_ids, f"{item_id}: duplicateOfId 无效")
        metadata = item.get("sourceMetadata")
        _require(isinstance(metadata, dict) and metadata.get("file") in source_names, f"{item_id}: 源文件无效")
        _validate_attachments(manifest_path, item.get("attachments"), item_id)
        _validate_source_blocks(item.get("sourceBlocks"), item["attachments"], item_id)

    loss_records = report.get("attachmentLossRecords")
    _require(isinstance(loss_records, list), "attachmentLossRecords 必须是数组")
    for index, record in enumerate(loss_records, start=1):
        item_id = f"attachment-loss-{index}"
        _require(isinstance(record, dict) and record.get("classification") == "unlinked-source-attachment", f"{item_id}: 损失记录无效")
        metadata = record.get("sourceMetadata")
        _require(isinstance(metadata, dict) and metadata.get("file") in source_names, f"{item_id}: 源文件无效")
        _validate_attachments(manifest_path, [record.get("attachment")], item_id)

    source_attachment_count = sum(item.get("attachmentOccurrenceCount", 0) for item in source_files)
    _require(source_attachment_count == report.get("imageCount") + report.get("tableCount") + report.get("ommlCount"), "来源附件统计不一致")
    expected_accounting = {
        "sourceOccurrenceCount": source_attachment_count,
        "activeOccurrenceCount": sum(len(item["attachments"]) for item in questions),
        "reviewOccurrenceCount": sum(len(item["attachments"]) for item in review_items),
        "exactDuplicateOccurrenceCount": sum(len(item["attachments"]) for item in duplicate_occurrences),
        "lossOccurrenceCount": len(loss_records),
    }
    expected_accounting["accountedOccurrenceCount"] = sum(
        expected_accounting[key]
        for key in (
            "activeOccurrenceCount",
            "reviewOccurrenceCount",
            "exactDuplicateOccurrenceCount",
            "lossOccurrenceCount",
        )
    )
    expected_accounting["unaccountedOccurrenceCount"] = (
        expected_accounting["sourceOccurrenceCount"] - expected_accounting["accountedOccurrenceCount"]
    )
    _require(report.get("attachmentAccounting") == expected_accounting, "attachmentAccounting 与保留负载不一致")
    _require(expected_accounting["unaccountedOccurrenceCount"] == 0, "存在未审计的来源附件")

    asset_dir = _image_asset_dir(manifest_path)
    image_asset_count = report.get("imageAssetCount")
    if image_asset_count:
        _require(asset_dir is not None, "图像资产目录不存在")
        asset_files = sorted(path for path in asset_dir.iterdir() if path.is_file())
        _require(len(asset_files) == image_asset_count, "imageAssetCount 与资产文件数不一致")
        for asset in asset_files:
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            _require(asset.name.startswith(digest + "."), f"资产文件名与内容 SHA-256 不一致：{asset.name}")
    _require(manifest.get("sourceArchiveSha256") == report.get("sourceArchiveSha256"), "源归档 SHA-256 不一致")
    _require(isinstance(report.get("sourceArchiveVerified"), bool), "sourceArchiveVerified 必须为布尔值")
    _require(report.get("sourceArchiveVerified") == (report.get("sourceArchiveSha256") is not None), "源归档验证状态不一致")
    _require(report.get("status") in {"DONE", "DONE_WITH_CONCERNS"}, "报告状态无效")
    _require(report.get("status") == ("DONE_WITH_CONCERNS" if report.get("concerns") else "DONE"), "报告状态与 concerns 不一致")
    return {
        "activeQuestions": len(questions),
        "reviewQuestions": len(review_items),
        "status": report["status"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate normalized question-bank manifest and import report files.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(validate_generated_files(args.manifest, args.report), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
