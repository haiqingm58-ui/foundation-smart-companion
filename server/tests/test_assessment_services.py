from __future__ import annotations

import pytest
from sqlalchemy import column, select, table

from server.application.services.assessment_validation import AssessmentValidationError, validate_question
from server.application.services.grading import grade_objective
from server.application.services.mastery import MasteryAllocation, apply_mastery


def valid_choice_payload(**overrides):
    payload = {
        "subjectId": "soil-mechanics",
        "knowledgePointIds": ["soil-permeability"],
        "text": "达西定律适用于什么流态？",
        "questionType": "单项选择题",
        "options": [
            {"label": "A", "text": "层流"},
            {"label": "B", "text": "紊流"},
        ],
        "correctAnswer": "A",
        "points": 10,
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize("knowledge_ids", [[], ["a", "b", "c", "d"]])
def test_question_requires_one_to_three_knowledge_points(knowledge_ids):
    with pytest.raises(AssessmentValidationError) as error:
        validate_question(valid_choice_payload(knowledgePointIds=knowledge_ids))
    assert error.value.code == "KNOWLEDGE_POINT_COUNT"


def test_single_choice_requires_exactly_one_known_option():
    with pytest.raises(AssessmentValidationError) as error:
        validate_question(valid_choice_payload(correctAnswer=["A", "B"]))
    assert error.value.code == "SINGLE_CHOICE_ANSWER"


def test_multiple_choice_normalizes_answer_set_and_grades_without_order():
    validated = validate_question(
        valid_choice_payload(
            questionType="多项选择题",
            correctAnswer=["B", "A", "B"],
        )
    )

    assert validated.correct_answer == ["A", "B"]
    result = grade_objective(
        {"questionType": "多项选择题", "correctAnswer": ["A", "B"], "points": 12},
        ["B", "A", "A"],
    )
    assert result.status == "graded"
    assert result.score == 12


def test_boolean_answers_are_normalized_for_validation_and_grading():
    validated = validate_question(
        valid_choice_payload(questionType="判断题", options=[], correctAnswer="正确")
    )

    assert validated.correct_answer is True
    assert grade_objective(
        {"questionType": "判断题", "correctAnswer": "对", "points": 5}, "是"
    ).score == 5


def test_fill_blank_accepts_normalized_synonyms():
    validated = validate_question(
        valid_choice_payload(questionType="填空题", options=[], correctAnswer=["太沙基", "Terzaghi"])
    )

    assert validated.correct_answer == ["terzaghi", "太沙基"]
    assert grade_objective(
        {"questionType": "填空题", "correctAnswer": ["太沙基", "Terzaghi"], "points": 8},
        "  ＴＥＲＺＡＧＨＩ  ",
    ).score == 8


def test_short_answer_requires_a_20_to_2000_word_limit():
    with pytest.raises(AssessmentValidationError) as error:
        validate_question(
            valid_choice_payload(
                questionType="简答题", options=[], correctAnswer=None, answerWordLimit=19
            )
        )
    assert error.value.code == "ANSWER_WORD_LIMIT"

    validated = validate_question(
        valid_choice_payload(
            questionType="简答题", options=[], correctAnswer=None, answerWordLimit=200
        )
    )
    assert validated.answer_word_limit == 200


def test_calculation_never_receives_final_auto_score():
    result = grade_objective({"questionType": "计算题", "points": 20}, "steps")
    assert result.status == "pending_review"
    assert result.score is None
    assert result.max_score == 20


def test_mastery_uses_normalized_link_weights_and_equal_fallback(database_url: str):
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgeMastery, KnowledgePoint, Student, Subject, User

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        subject = session.get(Subject, "soil-mechanics")
        student_user = User(
            id="mastery-user", username="mastery-student", password_hash="hash", role="student",
            role_label="学生", name="学生", student_no="20260003",
        )
        student = Student(id="mastery-student", user_id=student_user.id, student_no="20260003")
        points = [
            KnowledgePoint(
                id=point_id, subject_id=subject.id, chapter="第一章", name=name,
                normalized_name=name,
            )
            for point_id, name in (("point-a", "孔隙比"), ("point-b", "含水率"), ("point-c", "渗透系数"))
        ]
        session.add(student_user)
        session.flush()
        session.add_all([student, *points])
        session.flush()

        apply_mastery(
            session,
            student.id,
            [
                MasteryAllocation("point-a", "soil-mechanics", score=80, weight=3),
                MasteryAllocation("point-b", "soil-mechanics", score=80, weight=1),
                MasteryAllocation("point-c", "soil-mechanics", score=80),
            ],
        )
        session.commit()

    with database.session() as session:
        rows = {
            row.knowledge_point_id: row
            for row in session.scalars(select(KnowledgeMastery).where(KnowledgeMastery.student_id == "mastery-student"))
        }
        assert rows["point-a"].mastery == 48
        assert rows["point-b"].mastery == 16
        assert rows["point-c"].mastery == 16
        assert {row.knowledge_point_id for row in rows.values()} == {"point-a", "point-b", "point-c"}


def test_subject_mastery_migration_backfills_normalized_legacy_names(tmp_path):
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgeMastery, KnowledgePoint, Student, User

    database_url = f"sqlite:///{tmp_path / 'mastery-backfill.db'}"
    upgrade_database(database_url, "004_assessment_catalog")
    database = create_database(database_url)
    with database.session() as session:
        user = User(
            id="legacy-user", username="legacy-mastery", password_hash="hash", role="student",
            role_label="学生", name="旧学生", student_no="20260004",
        )
        session.add(user)
        session.flush()
        session.add(Student(id="legacy-student", user_id=user.id, student_no="20260004"))
        session.add(
            KnowledgePoint(
                id="darcy-law", subject_id="soil-mechanics", chapter="第二章", name="达西定律",
                normalized_name="达西定律",
            )
        )
        session.commit()
    legacy_mastery = table(
        "knowledge_mastery",
        column("id"),
        column("student_id"),
        column("knowledge_point"),
        column("mastery"),
        column("attempts"),
        column("updated_at"),
    )
    with database.engine.begin() as connection:
        connection.execute(
            legacy_mastery.insert().values(
                    id="legacy-mastery", student_id="legacy-student", knowledge_point="  达西定律  ",
                    mastery=55, attempts=2, updated_at="2026-01-01 00:00:00",
            )
        )

    upgrade_database(database_url)
    with database.session() as session:
        mastery = session.get(KnowledgeMastery, "legacy-mastery")
        assert mastery.knowledge_point_id == "darcy-law"
        assert mastery.subject_id == "soil-mechanics"
