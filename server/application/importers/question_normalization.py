from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any

from server.application.services.assessment_validation import AssessmentValidationError, validate_question


SUBJECT_ID = "soil-mechanics"

CHAPTERS = {
    0: "绪论",
    1: "第一章 土的性质及工程分类",
    2: "第二章 土的渗流",
    3: "第三章 土中应力",
    4: "第四章 土的压缩性与地基沉降",
    5: "第五章 土的抗剪强度",
    6: "第六章 土压力",
    7: "第七章 土坡稳定性",
    8: "第八章 地基承载力",
}


def _point(identifier: str, chapter: int, order: int, name: str, description: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "subjectId": SUBJECT_ID,
        "chapter": CHAPTERS[chapter],
        "name": name,
        "description": description,
        "status": "active",
        "sortOrder": chapter * 100 + order,
    }


KNOWLEDGE_POINTS = [
    _point("sm-00-scope", 0, 1, "土力学研究对象", "土体的工程性质、研究内容与学科任务。"),
    _point("sm-00-engineering-problems", 0, 2, "土力学工程问题", "变形、强度和渗透三类基本工程问题。"),
    _point("sm-00-soil-characteristics", 0, 3, "土的工程特性", "土的碎散性、三相性、自然变异性和多相耦合。"),
    _point("sm-01-origin-weathering", 1, 1, "土的成因与风化", "岩石风化、搬运沉积及各类成因土的特征。"),
    _point("sm-01-three-phase", 1, 2, "土的三相组成", "土颗粒、土中水和土中气体的组成及关系。"),
    _point("sm-01-particle-gradation", 1, 3, "颗粒粒径与级配", "粒组划分、级配曲线、不均匀系数与曲率系数。"),
    _point("sm-01-mineral-water", 1, 4, "土粒矿物与土中水", "粘土矿物、结合水、自由水及其对土性的影响。"),
    _point("sm-01-phase-indices", 1, 5, "三相比例指标", "含水率、密度、孔隙比、孔隙率和饱和度的换算。"),
    _point("sm-01-consistency-limits", 1, 6, "界限含水率与稠度", "液限、塑限、塑性指数、液性指数与粘性土状态。"),
    _point("sm-01-classification", 1, 7, "土的工程分类", "粗粒土、细粒土和特殊土的命名与分类依据。"),
    _point("sm-01-structure", 1, 8, "土的结构与构造", "单粒、蜂窝、絮状结构及土的构造特征。"),
    _point("sm-01-capillarity", 1, 9, "毛细现象", "毛细水上升、毛细压力及假粘聚力。"),
    _point("sm-01-compaction", 1, 10, "土的压实性", "击实曲线、最优含水率、最大干密度与压实度。"),
    _point("sm-02-darcy-law", 2, 1, "达西定律", "达西定律的适用条件、水力坡降与渗流量计算。"),
    _point("sm-02-permeability", 2, 2, "渗透系数", "渗透系数的影响因素、量纲及室内外测定方法。"),
    _point("sm-02-flow-net", 2, 3, "流网及渗流计算", "等势线、流线、流网性质和平面渗流量计算。"),
    _point("sm-02-seepage-force", 2, 4, "渗透力", "渗透力的方向、大小及其对有效重度的影响。"),
    _point("sm-02-critical-gradient", 2, 5, "临界水力坡降", "流土和沸腾发生时的临界水力条件。"),
    _point("sm-02-seepage-failure", 2, 6, "渗透破坏与防治", "管涌、流土、接触冲刷的判别和反滤防治。"),
    _point("sm-03-geostatic-stress", 3, 1, "土中自重应力", "分层土、地下水位和毛细带条件下的自重应力。"),
    _point("sm-03-effective-stress", 3, 2, "有效应力原理", "总应力、孔隙水压力与有效应力之间的关系。"),
    _point("sm-03-base-pressure", 3, 3, "基底压力与基底附加压力", "偏心和中心荷载下的基底压力分布及扣除自重。"),
    _point("sm-03-vertical-stress", 3, 4, "竖向附加应力", "集中荷载和分布荷载引起的竖向附加应力计算。"),
    _point("sm-03-stress-coefficient", 3, 5, "附加应力系数", "矩形、条形和圆形基础下的应力系数与角点法。"),
    _point("sm-03-stress-distribution", 3, 6, "土中应力分布", "附加应力的深度衰减、扩散和应力泡特征。"),
    _point("sm-04-compressibility-indices", 4, 1, "土的压缩性指标", "压缩系数、压缩模量、压缩指数和体积压缩系数。"),
    _point("sm-04-consolidation-test", 4, 2, "固结试验与压缩曲线", "侧限压缩试验、e-p与 e-lgp 曲线的绘制和应用。"),
    _point("sm-04-preconsolidation", 4, 3, "先期固结压力与OCR", "正常固结、欠固结、超固结状态及超固结比。"),
    _point("sm-04-layer-summation", 4, 4, "分层总和法", "地基最终沉降量的分层、应力取值和逐层汇总。"),
    _point("sm-04-one-dimensional-consolidation", 4, 5, "一维固结理论", "一维固结微分方程、排水边界、时间因数与固结系数。"),
    _point("sm-04-consolidation-degree", 4, 6, "固结度与沉降历时", "平均固结度、孔压消散、排水距离和固结时间计算。"),
    _point("sm-04-settlement-components", 4, 7, "地基沉降组成", "瞬时沉降、主固结沉降、次固结沉降及不均匀沉降。"),
    _point("sm-05-mohr-circle", 5, 1, "土中一点应力状态", "平面应力转换、主应力和摩尔应力圆。"),
    _point("sm-05-mohr-coulomb", 5, 2, "摩尔-库仑强度理论", "粘聚力、内摩擦角、强度包线与极限平衡条件。"),
    _point("sm-05-direct-shear", 5, 3, "直接剪切试验", "快剪、固结快剪、慢剪的条件、成果和局限。"),
    _point("sm-05-triaxial", 5, 4, "三轴剪切试验", "UU、CU、CD 三轴试验的排水固结条件与强度参数。"),
    _point("sm-05-effective-strength", 5, 5, "总应力与有效应力强度", "孔隙水压力对抗剪强度的影响及两类强度指标。"),
    _point("sm-05-stress-path", 5, 6, "应力路径", "p-q 应力平面中的总应力路径、有效应力路径与破坏线。"),
    _point("sm-05-soil-strength-behavior", 5, 7, "砂土与粘性土强度特性", "剪胀剪缩、峰值与残余强度、正常固结与超固结行为。"),
    _point("sm-06-pressure-states", 6, 1, "静止、主动与被动土压力", "挡土墙位移方向和大小与三种土压力状态的关系。"),
    _point("sm-06-rankine", 6, 2, "朗肯土压力理论", "朗肯理论假定、主被动土压力系数、分布和合力。"),
    _point("sm-06-coulomb", 6, 3, "库仑土压力理论", "滑动土楔、墙背摩擦、填土坡角与极值土压力。"),
    _point("sm-06-layered-backfill", 6, 4, "成层填土与地面荷载", "成层土、地下水和均布荷载作用下的土压力分布。"),
    _point("sm-06-retaining-wall", 6, 5, "挡土墙稳定验算", "重力式挡土墙的抗滑、抗倾覆和基底承载力验算。"),
    _point("sm-07-slope-failure", 7, 1, "土坡失稳形式与因素", "滑坡类型、滑动面形态及降雨、地下水和荷载影响。"),
    _point("sm-07-circular-slip", 7, 2, "圆弧滑动面稳定分析", "瑞典条分法、毕肖普法和稳定安全系数。"),
    _point("sm-07-stabilization", 7, 3, "土坡加固与排水", "减载、反压、排水、支挡和土体加固的稳定措施。"),
    _point("sm-08-failure-modes", 8, 1, "地基破坏模式", "整体剪切、局部剪切和冲切破坏的条件与特征。"),
    _point("sm-08-ultimate-capacity", 8, 2, "地基极限承载力", "普朗德尔、太沙基等极限承载力公式的构成和适用条件。"),
    _point("sm-08-capacity-factors", 8, 3, "承载力影响因素与修正", "基础宽度、埋深、荷载偏心倾斜和地下水对承载力的影响。"),
]


def compact_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).replace("\u00a0", " ").split())


def _attachment_identity(attachment: dict[str, Any]) -> dict[str, Any]:
    kind = attachment.get("kind")
    if kind == "image":
        return {"kind": kind, "sha256": attachment.get("sha256")}
    if kind == "table":
        return {
            "kind": kind,
            "rows": [
                [compact_text(str(cell)).casefold() for cell in row]
                for row in attachment.get("rows", [])
            ],
        }
    if kind == "formula":
        source = str(attachment.get("ommlSource") or "")
        return {
            "kind": kind,
            "ommlText": compact_text(str(attachment.get("ommlText") or "")).casefold(),
            "ommlSha256": attachment.get("ommlSha256") or hashlib.sha256(source.encode("utf-8")).hexdigest(),
        }
    return {"kind": kind}


def content_fingerprint(
    text: str,
    options: list[dict[str, str]],
    attachments: list[dict[str, Any]] | None = None,
) -> str:
    payload = {
        "text": compact_text(text).casefold(),
        "options": [
            {"label": compact_text(option["label"]).upper(), "text": compact_text(option["text"]).casefold()}
            for option in options
        ],
        "attachments": [_attachment_identity(attachment) for attachment in attachments or []],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def strip_question_prefix(text: str) -> tuple[str, str | None]:
    match = re.match(
        r"^\s*(?:\d+(?:\.\d+)*[.\u3001\uff0e]?)?\s*[\(\uff08]([\u4e00-\u9fff]{1,10}题)[\)\uff09]\s*(.*)$",
        text,
    )
    if not match:
        return compact_text(text), None
    return compact_text(match.group(2)), match.group(1)


def canonical_type(original_type: str | None) -> str | None:
    if original_type in {"单选题", "单项选择题"}:
        return "单项选择题"
    if original_type in {"多选题", "多项选择题"}:
        return "多项选择题"
    if original_type in {"判断题", "填空题", "简答题", "计算题"}:
        return original_type
    return None


def knowledge_point_ids(text: str, chapter: str | None) -> list[str]:
    combined = compact_text(f"{chapter or ''} {text}")
    rules = [
        ("sm-00-engineering-problems", ("变形问题", "强度问题", "渗透问题")),
        ("sm-00-soil-characteristics", ("碎散性", "三相性", "天然性")),
        ("sm-01-origin-weathering", ("风化", "坡积", "残积", "冲积", "搬运")),
        ("sm-01-three-phase", ("三相", "土颗粒", "土中气")),
        ("sm-01-particle-gradation", ("级配", "粒径", "颗粒组成", "不均匀系数", "曲率系数")),
        ("sm-01-mineral-water", ("高岭石", "蒙脱石", "伊利石", "结合水")),
        ("sm-01-phase-indices", ("含水率", "孔隙比", "孔隙率", "饱和度", "干密度", "比重")),
        ("sm-01-consistency-limits", ("液限", "塑限", "塑性指数", "液性指数", "稠度")),
        ("sm-01-classification", ("土的分类", "粉质粘土", "砂土分类", "粘性土分类")),
        ("sm-01-structure", ("絮状", "蜂窝", "单粒结构", "土的结构")),
        ("sm-01-capillarity", ("毛细", "假粘聚力")),
        ("sm-01-compaction", ("击实", "压实", "最优含水率", "最大干密度")),
        ("sm-02-darcy-law", ("达西", "达西")),
        ("sm-02-permeability", ("渗透系数", "渗透性")),
        ("sm-02-flow-net", ("流网", "等势线", "流线")),
        ("sm-02-seepage-force", ("渗透力", "渗流力")),
        ("sm-02-critical-gradient", ("临界水力坡降", "临界坡降")),
        ("sm-02-seepage-failure", ("管涌", "流土", "流砂", "渗透破坏")),
        ("sm-03-geostatic-stress", ("自重应力",)),
        ("sm-03-effective-stress", ("有效应力", "孔隙水压力")),
        ("sm-03-base-pressure", ("基底压力", "基底附加压力")),
        ("sm-03-stress-coefficient", ("应力系数", "角点法")),
        ("sm-03-stress-distribution", ("应力泡", "应力分布")),
        ("sm-03-vertical-stress", ("附加应力", "布氏解", "竖向应力")),
        ("sm-04-compressibility-indices", ("压缩系数", "压缩模量", "压缩指数")),
        ("sm-04-consolidation-test", ("固结试验", "e-p", "e-lgp")),
        ("sm-04-preconsolidation", ("先期固结", "超固结", "ocr")),
        ("sm-04-layer-summation", ("分层总和", "最终沉降")),
        ("sm-04-one-dimensional-consolidation", ("一维固结", "固结系数", "时间因数")),
        ("sm-04-consolidation-degree", ("固结度", "孔压消散")),
        ("sm-04-settlement-components", ("瞬时沉降", "主固结沉降", "次固结")),
        ("sm-05-mohr-circle", ("摩尔圆", "主应力")),
        ("sm-05-mohr-coulomb", ("摩尔-库仑", "库仑定律", "粘聚力", "内摩擦角")),
        ("sm-05-direct-shear", ("直剪", "快剪", "慢剪")),
        ("sm-05-triaxial", ("三轴", "uu试验", "cu试验", "cd试验")),
        ("sm-05-effective-strength", ("有效应力强度", "总应力强度")),
        ("sm-05-stress-path", ("应力路径",)),
        ("sm-05-soil-strength-behavior", ("剪胀", "剪缩", "峰值强度", "残余强度")),
        ("sm-06-pressure-states", ("主动土压力", "被动土压力", "静止土压力")),
        ("sm-06-rankine", ("朗肯", "朗金")),
        ("sm-06-coulomb", ("库仑土压力", "滑动土楔")),
        ("sm-06-layered-backfill", ("成层", "填土面", "地面荷载")),
        ("sm-06-retaining-wall", ("挡土墙", "抗倾覆", "抗滑")),
        ("sm-07-slope-failure", ("边坡", "土坡", "滑坡")),
        ("sm-07-circular-slip", ("条分法", "毕肖普", "圆弧滑动")),
        ("sm-07-stabilization", ("土坡加固", "反压", "排水孔")),
        ("sm-08-failure-modes", ("整体剪切", "局部剪切", "冲切破坏")),
        ("sm-08-ultimate-capacity", ("极限承载力", "地基承载力", "太沙基")),
        ("sm-08-capacity-factors", ("承载力系数", "宽度修正", "埋深修正")),
    ]
    lowered = combined.casefold()
    matches = [identifier for identifier, terms in rules if any(term.casefold() in lowered for term in terms)]
    if matches:
        return list(dict.fromkeys(matches))[:3]
    defaults = {
        CHAPTERS[0]: "sm-00-scope",
        CHAPTERS[1]: "sm-01-phase-indices",
        CHAPTERS[2]: "sm-02-permeability",
        CHAPTERS[3]: "sm-03-vertical-stress",
        CHAPTERS[4]: "sm-04-compressibility-indices",
        CHAPTERS[5]: "sm-05-mohr-coulomb",
        CHAPTERS[6]: "sm-06-pressure-states",
        CHAPTERS[7]: "sm-07-slope-failure",
        CHAPTERS[8]: "sm-08-ultimate-capacity",
    }
    return [defaults[chapter]] if chapter in defaults else []


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _choice_labels(value: str) -> list[str]:
    compact = re.sub(r"[\s,\uff0c\u3001;\uff1b/]+", "", unicodedata.normalize("NFKC", value)).upper()
    return list(compact) if compact and re.fullmatch(r"[A-H]+", compact) else []


def normalize_candidate(
    parsed: dict[str, Any],
    source_file: str,
    sequence: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    question_type = canonical_type(parsed.get("originalTypeLabel")) or parsed.get("inferredType")
    point_ids = knowledge_point_ids(parsed["text"], parsed["chapter"])
    fingerprint = content_fingerprint(parsed["text"], parsed["options"], parsed["attachments"])
    source_metadata = {
        "file": source_file,
        "position": parsed["position"],
        "originalTypeLabel": parsed.get("originalTypeLabel"),
        "sequence": sequence,
        "sourceAnswer": parsed.get("answer", ""),
    }
    for key in ("answerPosition", "endPosition", "chapterHeading", "blockSequence", "typeInference"):
        if parsed.get(key) is not None:
            source_metadata[key] = parsed[key]
    reasons: list[dict[str, str]] = []
    if question_type is None:
        reasons.append({"code": "UNSUPPORTED_TYPE", "detail": f"未支持的原始题型：{parsed.get('originalTypeLabel') or '未标注'}"})
    if not point_ids:
        reasons.append({"code": "UNMAPPED_KNOWLEDGE_POINT", "detail": "无法可靠映射到策展知识点"})
    if not parsed.get("answerFound", True):
        reasons.append({"code": "MISSING_ANSWER_MARKER", "detail": "题目未找到明确答案标记"})

    source_answer = parsed.get("answer", "")
    correct_answer: Any = source_answer
    grading_mode = "auto"
    answer_word_limit = None
    option_labels = {option["label"] for option in parsed["options"]}
    if question_type == "单项选择题":
        labels = _choice_labels(source_answer)
        if len(labels) != 1 or labels[0] not in option_labels:
            reasons.append({"code": "INVALID_CHOICE_ANSWER", "detail": "单选答案未对应唯一有效选项"})
        else:
            correct_answer = labels[0]
    elif question_type == "多项选择题":
        labels = _choice_labels(source_answer)
        if not labels or len(set(labels)) != len(labels) or any(label not in option_labels for label in labels):
            reasons.append({"code": "INVALID_CHOICE_ANSWER", "detail": "多选答案未对应有效选项集合"})
        else:
            correct_answer = sorted(labels)
    elif question_type == "判断题":
        normalized = compact_text(source_answer).casefold()
        if normalized in {"正确", "对", "是", "true", "1"}:
            correct_answer = True
        elif normalized in {"错误", "错", "否", "false", "0"}:
            correct_answer = False
        else:
            reasons.append({"code": "INVALID_BOOLEAN_ANSWER", "detail": "判断题答案不能归一化为真或假"})
    elif question_type == "填空题":
        answers = [part.strip() for part in re.split(r"[;\uff1b]", source_answer) if part.strip()]
        if not answers:
            reasons.append({"code": "MISSING_FILL_ANSWER", "detail": "填空题缺少可用答案"})
        else:
            correct_answer = answers
    elif question_type == "简答题":
        correct_answer = None
        grading_mode = "manual"
        answer_word_limit = 200
    elif question_type == "计算题":
        correct_answer = None
        grading_mode = "manual"

    record = {
        "id": f"soil-{fingerprint[:24]}",
        "subjectId": SUBJECT_ID,
        "knowledgePointIds": point_ids,
        "text": parsed["text"],
        "questionType": question_type,
        "chapter": parsed["chapter"],
        "difficulty": "基础",
        "options": parsed["options"],
        "correctAnswer": correct_answer,
        "explanation": parsed.get("explanation"),
        "rubric": [],
        "points": 10,
        "attachments": parsed["attachments"],
        "sourceBlocks": parsed["sourceBlocks"],
        "answerWordLimit": answer_word_limit,
        "gradingMode": grading_mode,
        "status": "active",
        "sourceMetadata": source_metadata,
        "contentFingerprint": fingerprint,
    }
    if not reasons:
        validation_payload = {
            key: value
            for key, value in record.items()
            if key
            in {
                "subjectId",
                "knowledgePointIds",
                "text",
                "questionType",
                "chapter",
                "difficulty",
                "options",
                "correctAnswer",
                "points",
                "answerWordLimit",
                "gradingMode",
            }
        }
        try:
            validate_question(validation_payload)
        except AssessmentValidationError as error:
            reasons.append({"code": error.code, "detail": str(error)})
    if not reasons:
        return record, None
    occurrence_fingerprint = hashlib.sha256(
        canonical_json_bytes({"file": source_file, "sequence": sequence, "position": parsed["position"]})
    ).hexdigest()
    return None, {
        "id": f"soil-review-{fingerprint[:16]}-{occurrence_fingerprint[:12]}",
        "contentFingerprint": fingerprint,
        "text": parsed["text"],
        "questionType": question_type,
        "chapter": parsed["chapter"],
        "knowledgePointIds": point_ids,
        "options": parsed["options"],
        "sourceAnswer": source_answer,
        "normalizedAnswer": correct_answer,
        "gradingMode": grading_mode,
        "explanation": parsed.get("explanation"),
        "attachments": parsed["attachments"],
        "sourceBlocks": parsed["sourceBlocks"],
        "sourceMetadata": source_metadata,
        "reasons": reasons,
    }
