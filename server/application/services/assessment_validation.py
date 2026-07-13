from __future__ import annotations

import unicodedata
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError


class AssessmentValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class QuestionDraftBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    subject_id: str = Field(alias="subjectId", min_length=1, max_length=64)
    knowledge_point_ids: list[str] = Field(alias="knowledgePointIds")
    text: str = Field(min_length=2, max_length=12000)
    question_type: str = Field(alias="questionType")
    options: list[dict[str, Any]] = Field(default_factory=list)
    correct_answer: Any | None = Field(default=None, alias="correctAnswer")
    points: float = Field(default=10, gt=0)
    answer_word_limit: int | None = Field(default=None, alias="answerWordLimit")
    grading_mode: str = Field(default="auto", alias="gradingMode")


class SingleChoiceDraft(QuestionDraftBase):
    question_type: Literal["单项选择题"] = Field(alias="questionType")


class MultipleChoiceDraft(QuestionDraftBase):
    question_type: Literal["多项选择题"] = Field(alias="questionType")


class BooleanDraft(QuestionDraftBase):
    question_type: Literal["判断题"] = Field(alias="questionType")


class FillBlankDraft(QuestionDraftBase):
    question_type: Literal["填空题"] = Field(alias="questionType")


class ShortAnswerDraft(QuestionDraftBase):
    question_type: Literal["简答题"] = Field(alias="questionType")


class CalculationDraft(QuestionDraftBase):
    question_type: Literal["计算题"] = Field(alias="questionType")


QuestionDraft = Annotated[
    SingleChoiceDraft | MultipleChoiceDraft | BooleanDraft | FillBlankDraft | ShortAnswerDraft | CalculationDraft,
    Field(discriminator="question_type"),
]
QUESTION_DRAFT_ADAPTER = TypeAdapter(QuestionDraft)


class ValidatedQuestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject_id: str
    knowledge_point_ids: list[str]
    text: str
    question_type: Literal["单项选择题", "多项选择题", "判断题", "填空题", "简答题", "计算题"]
    options: list[dict[str, Any]]
    correct_answer: Any | None
    points: float
    answer_word_limit: int | None
    grading_mode: Literal["auto", "manual"]


def normalize_text(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value)).split()).casefold()


def normalize_boolean(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    normalized = normalize_text(value)
    if normalized in {"true", "1", "yes", "y", "正确", "对", "是"}:
        return True
    if normalized in {"false", "0", "no", "n", "错误", "错", "否"}:
        return False
    return None


def normalize_choice_set(value: object) -> list[str] | None:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple, set)):
        return None
    normalized = {normalize_text(item) for item in value if normalize_text(item)}
    return sorted(normalized)


def normalize_fill_answers(value: object) -> list[str]:
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, (list, tuple, set)):
        return []
    return sorted({normalize_text(item) for item in values if normalize_text(item)})


def _payload_as_draft(payload: QuestionDraft | dict[str, Any]) -> QuestionDraft:
    if isinstance(payload, QuestionDraftBase):
        return payload
    try:
        return QUESTION_DRAFT_ADAPTER.validate_python(payload)
    except ValidationError as error:
        raise AssessmentValidationError("QUESTION_PAYLOAD_INVALID", "题目载荷无效") from error


def _option_labels(options: list[dict[str, Any]]) -> list[str]:
    labels = [normalize_text(option.get("label", "")) for option in options]
    if len(options) < 2 or any(not label for label in labels) or len(set(labels)) != len(labels):
        raise AssessmentValidationError("CHOICE_OPTIONS_INVALID", "选择题选项必须包含至少两个唯一标签")
    return labels


def validate_question(payload: QuestionDraft | dict[str, Any]) -> ValidatedQuestion:
    draft = _payload_as_draft(payload)
    knowledge_point_ids = [item.strip() for item in draft.knowledge_point_ids if item.strip()]
    if not 1 <= len(knowledge_point_ids) <= 3 or len(set(knowledge_point_ids)) != len(knowledge_point_ids):
        raise AssessmentValidationError("KNOWLEDGE_POINT_COUNT", "每道题必须关联一至三个不同知识点")

    correct_answer: Any | None = draft.correct_answer
    grading_mode: Literal["auto", "manual"] = "manual" if draft.question_type == "计算题" else "auto"
    if draft.question_type == "单项选择题":
        labels = _option_labels(draft.options)
        if not isinstance(correct_answer, str) or normalize_text(correct_answer) not in labels:
            raise AssessmentValidationError("SINGLE_CHOICE_ANSWER", "单项选择题必须指定一个有效答案")
        correct_answer = next(
            str(option["label"]).strip()
            for option in draft.options
            if normalize_text(option["label"]) == normalize_text(correct_answer)
        )
    elif draft.question_type == "多项选择题":
        labels = _option_labels(draft.options)
        answers = normalize_choice_set(correct_answer)
        if not answers or any(answer not in labels for answer in answers):
            raise AssessmentValidationError("MULTIPLE_CHOICE_ANSWER", "多项选择题必须指定有效答案集合")
        canonical_labels = {normalize_text(option["label"]): str(option["label"]).strip() for option in draft.options}
        correct_answer = [canonical_labels[answer] for answer in answers]
    elif draft.question_type == "判断题":
        normalized = normalize_boolean(correct_answer)
        if normalized is None:
            raise AssessmentValidationError("BOOLEAN_ANSWER", "判断题答案必须可归一化为真或假")
        correct_answer = normalized
    elif draft.question_type == "填空题":
        answers = normalize_fill_answers(correct_answer)
        if not answers:
            raise AssessmentValidationError("FILL_BLANK_ANSWER", "填空题必须至少提供一个同义答案")
        correct_answer = answers
    elif draft.question_type == "简答题":
        if draft.answer_word_limit is None or not 20 <= draft.answer_word_limit <= 2000:
            raise AssessmentValidationError("ANSWER_WORD_LIMIT", "简答题字数限制必须在二十至二千之间")
    elif draft.question_type == "计算题":
        grading_mode = "manual"

    return ValidatedQuestion(
        subject_id=draft.subject_id.strip(),
        knowledge_point_ids=knowledge_point_ids,
        text=draft.text.strip(),
        question_type=draft.question_type,
        options=draft.options,
        correct_answer=correct_answer,
        points=draft.points,
        answer_word_limit=draft.answer_word_limit,
        grading_mode=grading_mode,
    )
