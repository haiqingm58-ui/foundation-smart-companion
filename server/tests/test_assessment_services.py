from __future__ import annotations

import pytest
from sqlalchemy import column, inspect, select, table

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


def test_question_draft_accepts_strict_shared_metadata_and_real_integer_points():
    validated = validate_question(
        valid_choice_payload(chapter="第二章 土的渗透性", difficulty="中等", points=12)
    )
    assert validated.chapter == "第二章 土的渗透性"
    assert validated.difficulty == "中等"
    assert validated.points == 12


@pytest.mark.parametrize(
    "field,value",
    [
        ("points", "10"),
        ("points", True),
        ("answerWordLimit", "200"),
        ("answerWordLimit", True),
        ("answerWordLimit", 200.0),
        ("subjectId", 1),
        ("knowledgePointIds", ["soil-permeability", True]),
        ("text", 1),
        ("chapter", True),
        ("difficulty", 1),
    ],
)
def test_question_draft_rejects_coerced_shared_json_types(field, value):
    payload = valid_choice_payload(**{field: value})
    if field == "answerWordLimit":
        payload.update({"questionType": "简答题", "options": [], "correctAnswer": None})
    with pytest.raises(AssessmentValidationError) as error:
        validate_question(payload)
    assert error.value.code == "QUESTION_PAYLOAD_INVALID"


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


def test_multiple_choice_allows_a_single_correct_answer():
    validated = validate_question(
        valid_choice_payload(questionType="多项选择题", correctAnswer=["A"])
    )
    assert validated.correct_answer == ["A"]


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


@pytest.mark.parametrize(
    "payload",
    [
        valid_choice_payload(options=[{"label": 1, "text": "层流"}, {"label": "B", "text": "紊流"}]),
        valid_choice_payload(options=[{"label": "A", "text": " "}, {"label": "B", "text": "紊流"}]),
        valid_choice_payload(questionType="填空题", options=[], correctAnswer=["太沙基", 1]),
        valid_choice_payload(questionType="填空题", options=[], correctAnswer={"unexpected": "shape"}),
    ],
)
def test_type_specific_question_payloads_reject_non_string_content(payload):
    with pytest.raises(AssessmentValidationError) as error:
        validate_question(payload)
    assert error.value.code == "QUESTION_PAYLOAD_INVALID"


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
    assert validated.grading_mode == "manual"


def test_calculation_validation_forces_manual_review_mode():
    validated = validate_question(
        valid_choice_payload(questionType="计算题", options=[], correctAnswer=None, gradingMode="auto")
    )
    assert validated.grading_mode == "manual"


def test_calculation_never_receives_final_auto_score():
    result = grade_objective({"questionType": "计算题", "points": 20}, "steps")
    assert result.status == "pending_review"
    assert result.score is None
    assert result.max_score == 20


def test_short_answer_never_receives_final_auto_score():
    result = grade_objective({"questionType": "简答题", "points": 20}, "说明达西定律。")
    assert result.status == "pending_review"
    assert result.score is None


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


def test_mastery_validates_allocation_list_before_mutating_session(database_url: str):
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgeMastery, KnowledgePoint, Student, Subject, User

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        subject = session.get(Subject, "soil-mechanics")
        user = User(id="atomic-user", username="atomic", password_hash="hash", role="student", role_label="学生", name="学生", student_no="20260005")
        session.add(user)
        session.flush()
        student = Student(id="atomic-student", user_id=user.id, student_no="20260005")
        point = KnowledgePoint(id="atomic-point", subject_id=subject.id, chapter="第一章", name="土粒比重", normalized_name="土粒比重")
        session.add_all([student, point])
        session.flush()

        with pytest.raises(ValueError, match="duplicate"):
            apply_mastery(
                session,
                student.id,
                [
                    MasteryAllocation(point.id, subject.id, score=80),
                    MasteryAllocation(point.id, subject.id, score=20),
                ],
            )
        assert session.scalars(select(KnowledgeMastery).where(KnowledgeMastery.student_id == student.id)).all() == []
        for allocation in (
            MasteryAllocation("missing-point", subject.id, score=80),
            MasteryAllocation(point.id, "foundation-engineering", score=80),
            MasteryAllocation(point.id, subject.id, score=80, weight=0),
            MasteryAllocation(point.id, subject.id, score=80, weight=float("nan")),
            MasteryAllocation(point.id, subject.id, score=80, weight="1"),
            MasteryAllocation(point.id, subject.id, score=float("nan")),
            MasteryAllocation(point.id, subject.id, score="80"),
        ):
            with pytest.raises(ValueError):
                apply_mastery(session, student.id, [allocation])
            assert session.scalars(select(KnowledgeMastery).where(KnowledgeMastery.student_id == student.id)).all() == []


def test_mastery_keeps_same_named_points_in_different_subjects_and_uses_running_mean(database_url: str):
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgeMastery, KnowledgePoint, Student, Subject, User

    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        foundation = session.get(Subject, "foundation-engineering")
        soil = session.get(Subject, "soil-mechanics")
        user = User(id="cross-user", username="cross", password_hash="hash", role="student", role_label="学生", name="学生", student_no="20260006")
        session.add(user)
        session.flush()
        student = Student(id="cross-student", user_id=user.id, student_no="20260006")
        foundation_point = KnowledgePoint(id="foundation-same-name", subject_id=foundation.id, chapter="第一章", name="承载力", normalized_name="承载力")
        soil_point = KnowledgePoint(id="soil-same-name", subject_id=soil.id, chapter="第一章", name="承载力", normalized_name="承载力")
        session.add_all([student, foundation_point, soil_point])
        session.flush()

        apply_mastery(session, student.id, [MasteryAllocation(foundation_point.id, foundation.id, score=80)])
        apply_mastery(session, student.id, [MasteryAllocation(soil_point.id, soil.id, score=60)])
        apply_mastery(session, student.id, [MasteryAllocation(soil_point.id, soil.id, score=80)])
        session.commit()

    with database.session() as session:
        rows = session.scalars(select(KnowledgeMastery).where(KnowledgeMastery.student_id == "cross-student").order_by(KnowledgeMastery.knowledge_point_id)).all()
        assert [(row.subject_id, row.mastery, row.attempts) for row in rows] == [
            (foundation.id, 80, 1),
            (soil.id, 70, 2),
        ]


def test_subject_mastery_migration_backfills_normalized_legacy_names_and_preserves_unmatched_rows(tmp_path):
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
        connection.execute(legacy_mastery.insert(), [
            {"id": "legacy-mastery", "student_id": "legacy-student", "knowledge_point": "  达西定律  ", "mastery": 55, "attempts": 2, "updated_at": "2026-01-01 00:00:00"},
            {"id": "unmatched-mastery", "student_id": "legacy-student", "knowledge_point": "未匹配知识点", "mastery": 45, "attempts": 1, "updated_at": "2026-01-01 00:00:00"},
        ])

    upgrade_database(database_url)
    with database.session() as session:
        mastery = session.get(KnowledgeMastery, "legacy-mastery")
        assert mastery.knowledge_point_id == "darcy-law"
        assert mastery.subject_id == "soil-mechanics"
        unmatched = session.get(KnowledgeMastery, "unmatched-mastery")
        assert unmatched.knowledge_point_id is None
        assert unmatched.subject_id is None


def test_subject_mastery_migration_merges_normalized_duplicate_legacy_rows_and_removes_legacy_unique(tmp_path):
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import KnowledgeMastery, KnowledgePoint, Student, User

    database_url = f"sqlite:///{tmp_path / 'mastery-duplicates.db'}"
    upgrade_database(database_url, "004_assessment_catalog")
    database = create_database(database_url)
    with database.session() as session:
        user = User(id="duplicate-user", username="duplicates", password_hash="hash", role="student", role_label="学生", name="学生", student_no="20260007")
        session.add(user)
        session.flush()
        session.add_all([
            Student(id="duplicate-student", user_id=user.id, student_no="20260007"),
            KnowledgePoint(id="duplicate-point", subject_id="soil-mechanics", chapter="第二章", name="达西定律", normalized_name="达西定律"),
        ])
        session.commit()
    legacy_mastery = table("knowledge_mastery", column("id"), column("student_id"), column("knowledge_point"), column("mastery"), column("attempts"), column("updated_at"))
    with database.engine.begin() as connection:
        connection.execute(legacy_mastery.insert(), [
            {"id": "duplicate-a", "student_id": "duplicate-student", "knowledge_point": "达西定律", "mastery": 40, "attempts": 1, "updated_at": "2026-01-01 00:00:00"},
            {"id": "duplicate-b", "student_id": "duplicate-student", "knowledge_point": " 达西定律 ", "mastery": 80, "attempts": 3, "updated_at": "2026-01-01 00:00:00"},
        ])

    upgrade_database(database_url)
    with database.session() as session:
        rows = session.scalars(select(KnowledgeMastery).where(KnowledgeMastery.student_id == "duplicate-student")).all()
        assert len(rows) == 1
        assert rows[0].knowledge_point_id == "duplicate-point"
        assert rows[0].attempts == 4
        assert rows[0].mastery == 70
    assert "uq_student_knowledge" not in {item["name"] for item in inspect(database.engine).get_unique_constraints("knowledge_mastery")}


def test_subject_mastery_downgrade_consolidates_same_name_cross_subject_rows(tmp_path):
    from server.application.database import create_database
    from server.application.migrations import downgrade_database, upgrade_database
    from server.application.models import KnowledgeMastery, KnowledgePoint, Student, User

    database_url = f"sqlite:///{tmp_path / 'mastery-downgrade.db'}"
    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        user = User(id="downgrade-user", username="downgrade", password_hash="hash", role="student", role_label="学生", name="学生", student_no="20260008")
        session.add(user)
        session.flush()
        session.add_all([
            Student(id="downgrade-student", user_id=user.id, student_no="20260008"),
            KnowledgePoint(id="downgrade-foundation", subject_id="foundation-engineering", chapter="第一章", name="承载力", normalized_name="承载力"),
            KnowledgePoint(id="downgrade-soil", subject_id="soil-mechanics", chapter="第一章", name="承载力", normalized_name="承载力"),
        ])
        session.flush()
        session.add_all([
            KnowledgeMastery(id="downgrade-a", student_id="downgrade-student", knowledge_point="承载力", knowledge_point_id="downgrade-foundation", subject_id="foundation-engineering", mastery=40, attempts=1),
            KnowledgeMastery(id="downgrade-b", student_id="downgrade-student", knowledge_point="承载力", knowledge_point_id="downgrade-soil", subject_id="soil-mechanics", mastery=80, attempts=3),
        ])
        session.commit()

    downgrade_database(database_url, "004_assessment_catalog")
    legacy_rows = database.engine.connect().execute(select(table("knowledge_mastery", column("id"), column("mastery"), column("attempts")))).all()
    assert legacy_rows == [("downgrade-a", 70.0, 4)]
    assert "uq_student_knowledge" in {item["name"] for item in inspect(database.engine).get_unique_constraints("knowledge_mastery")}


def test_pending_practice_attempt_survives_downgrade_and_reupgrade(tmp_path):
    from server.application.database import create_database
    from server.application.migrations import downgrade_database, upgrade_database
    from server.application.models import PracticeAttempt, Question, Student, User

    database_url = f"sqlite:///{tmp_path / 'pending-practice-roundtrip.db'}"
    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        user = User(id="pending-user", username="pending", password_hash="hash", role="student", role_label="学生", name="学生", student_no="20260009")
        session.add(user)
        session.flush()
        session.add_all([
            Student(id="pending-student", user_id=user.id, student_no="20260009"),
            Question(id="pending-question", text="计算单桩承载力。", question_type="计算题", options=[], correct_answer=None, difficulty="中等", points=20, source="textbook"),
        ])
        session.flush()
        session.add(
            PracticeAttempt(
                id="pending-attempt", student_id="pending-student", question_id="pending-question",
                answer="过程", status="pending_review", score=None, max_score=20,
                criteria_scores={}, confidence=0, feedback="待复核", attempt_number=1,
            )
        )
        session.commit()

    downgrade_database(database_url, "004_assessment_catalog")
    legacy_practice = table("practice_attempts", column("id"), column("score"))
    with database.engine.connect() as connection:
        assert "status" not in {column["name"] for column in inspect(connection).get_columns("practice_attempts")}
        assert connection.execute(select(legacy_practice)).all() == [("pending-attempt", 0.0)]

    upgrade_database(database_url)
    with database.session() as session:
        attempt = session.get(PracticeAttempt, "pending-attempt")
        assert attempt.status == "graded"
        assert attempt.score == 0
