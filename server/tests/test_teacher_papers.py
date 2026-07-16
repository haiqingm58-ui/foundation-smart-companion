from __future__ import annotations

from copy import deepcopy
import json

from sqlalchemy import inspect, select, text

from server.tests.test_teacher import teacher_context
from server.tests.test_teacher_catalog import teacher2_client


def csrf(token: str = "teacher-csrf") -> dict[str, str]:
    return {"X-CSRF-Token": token}


def seed_question(
    database,
    question_id: str,
    *,
    point_id: str = "soil-paper-point",
    point_name: str = "达西定律",
    chapter: str = "第二章 土的渗透性",
    question_type: str = "单项选择题",
    difficulty: str = "基础",
    created_by: str | None = None,
    text_value: str | None = None,
    attachments: list[dict] | None = None,
    source_metadata: dict | None = None,
    rubric: list[dict] | None = None,
    correct_answer="A",
) -> str:
    from server.application.models import KnowledgePoint, Question, QuestionKnowledgePoint

    with database.session() as session:
        point = session.get(KnowledgePoint, point_id)
        if point is None:
            point = KnowledgePoint(
                id=point_id,
                subject_id="soil-mechanics",
                chapter=chapter,
                name=point_name,
                normalized_name=point_name,
            )
            session.add(point)
            session.flush()
        question = Question(
            id=question_id,
            text=text_value or f"题目 {question_id}",
            question_type=question_type,
            options=[{"label": "A", "text": "层流"}, {"label": "B", "text": "紊流"}]
            if question_type == "单项选择题"
            else [],
            correct_answer=correct_answer,
            explanation="保留的解析",
            rubric=rubric or [],
            difficulty=difficulty,
            points=10,
            chapter=chapter,
            subject_id="soil-mechanics",
            attachments=attachments or [],
            source_metadata=source_metadata or {},
            source="teacher" if created_by else "soil-mechanics-bank",
            created_by=created_by,
            status="active",
            knowledge_point_links=[
                QuestionKnowledgePoint(id=f"link-{question_id}", knowledge_point_id=point_id)
            ],
        )
        session.add(question)
        session.commit()
    return question_id


def manual_paper_payload(question_ids: list[str], **overrides) -> dict:
    payload = {
        "subjectId": "soil-mechanics",
        "title": "土力学单元测试",
        "description": "可重复使用的手动试卷",
        "durationMinutes": 90,
        "status": "draft",
        "assemblyMode": "manual",
        "questions": [
            {
                "questionId": question_id,
                "sectionTitle": "一、选择题" if index == 1 else "二、综合题",
                "sequence": index,
                "points": index * 5,
            }
            for index, question_id in enumerate(question_ids, start=1)
        ],
    }
    payload.update(overrides)
    return payload


def create_manual_paper(client, question_ids: list[str], **overrides) -> dict:
    response = client.post(
        "/api/teacher/papers",
        json=manual_paper_payload(question_ids, **overrides),
        headers=csrf(),
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_migration_006_preserves_legacy_assignments_and_questions(tmp_path) -> None:
    from server.application.database import create_database
    from server.application.migrations import upgrade_database

    database_url = f"sqlite:///{tmp_path / 'paper-migration.db'}"
    upgrade_database(database_url, "005_subject_mastery")
    database = create_database(database_url)
    now = "2026-07-14 00:00:00"
    with database.engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users (
                    id, username, password_hash, password_algorithm, role, role_label, name,
                    status, college, school, must_change_password, created_at, updated_at
                ) VALUES (
                    'legacy-teacher-user', 'legacy-teacher', 'hash', 'argon2', 'teacher', '指导老师', '旧教师',
                    'active', '土木工程学院', '湖南大学', 0, :now, :now
                )
                """
            ),
            {"now": now},
        )
        connection.execute(
            text(
                "INSERT INTO teachers (id, user_id, teacher_no, college, course, created_at) "
                "VALUES ('legacy-teacher', 'legacy-teacher-user', 'LT1', '土木工程学院', '基础工程', :now)"
            ),
            {"now": now},
        )
        connection.execute(
            text(
                """
                INSERT INTO questions (
                    id, text, question_type, options, rubric, difficulty, points, subject_id,
                    attachments, grading_mode, status, source_metadata, source, created_at, updated_at
                ) VALUES (
                    'legacy-question', '旧题干', '简答题', '[]', '[]', '基础', 10, 'soil-mechanics',
                    '[]', 'manual', 'review_required', '{}', 'textbook', :now, :now
                )
                """
            ),
            {"now": now},
        )
        connection.execute(
            text(
                """
                INSERT INTO assignments (
                    id, title, description, teacher_id, total_points, allow_resubmit,
                    auto_grade, status, created_at
                ) VALUES ('legacy-assignment', '旧作业', '不能丢失', 'legacy-teacher', 10, 0, 0, 'published', :now)
                """
            ),
            {"now": now},
        )
        connection.execute(
            text(
                "INSERT INTO assignment_questions (id, assignment_id, question_id, sequence, points) "
                "VALUES ('legacy-assignment-question', 'legacy-assignment', 'legacy-question', 1, 10)"
            )
        )

    upgrade_database(database_url)
    inspector = inspect(database.engine)
    assert {"papers", "paper_questions"}.issubset(inspector.get_table_names())
    assert {"paper_id", "duration_minutes", "show_answers_mode", "publication_key"}.issubset(
        {column["name"] for column in inspector.get_columns("assignments")}
    )
    assert "question_snapshot" in {
        column["name"] for column in inspector.get_columns("assignment_questions")
    }
    assert next(
        column for column in inspector.get_columns("assignment_questions")
        if column["name"] == "question_snapshot"
    )["nullable"] is False
    with database.engine.connect() as connection:
        assignment = connection.execute(
            text(
                "SELECT title, description, total_points, paper_id, duration_minutes, show_answers_mode "
                "FROM assignments WHERE id = 'legacy-assignment'"
            )
        ).one()
        assignment_question = connection.execute(
            text(
                "SELECT question_id, sequence, points, question_snapshot FROM assignment_questions "
                "WHERE id = 'legacy-assignment-question'"
            )
        ).one()
    assert assignment == ("旧作业", "不能丢失", 10.0, None, None, "after_submission")
    assert assignment_question[:3] == ("legacy-question", 1, 10.0)
    snapshot = assignment_question.question_snapshot
    if isinstance(snapshot, str):
        snapshot = json.loads(snapshot)
    assert snapshot["id"] == "legacy-question"
    assert snapshot["text"] == "旧题干"
    assert snapshot["sequence"] == 1
    assert snapshot["points"] == 10


def test_manual_paper_preserves_order_sections_points_and_is_reusable(teacher_context) -> None:
    from server.application.models import OperationLog, Paper, PaperQuestion

    client, database, _ = teacher_context
    first = seed_question(database, "paper-manual-1")
    second = seed_question(
        database,
        "paper-manual-2",
        point_id="soil-paper-point-2",
        point_name="渗透系数",
        question_type="简答题",
        correct_answer=None,
    )
    payload = manual_paper_payload([first, second])
    payload["questions"] = [
        {"questionId": second, "sectionTitle": "二、简答题", "sequence": 2, "points": 15},
        {"questionId": first, "sectionTitle": "一、选择题", "sequence": 1, "points": 5},
    ]
    created = client.post("/api/teacher/papers", json=payload, headers=csrf())
    assert created.status_code == 200, created.text
    paper = created.json()["data"]
    assert paper["totalPoints"] == 20
    assert [(item["questionId"], item["sectionTitle"], item["sequence"], item["points"]) for item in paper["questions"]] == [
        (first, "一、选择题", 1, 5.0),
        (second, "二、简答题", 2, 15.0),
    ]
    listed = client.get("/api/teacher/papers")
    detailed = client.get(f"/api/teacher/papers/{paper['id']}")
    assert listed.json()["data"]["items"][0]["id"] == paper["id"]
    assert detailed.json()["data"]["questions"] == paper["questions"]
    with database.session() as session:
        stored = session.get(Paper, paper["id"])
        rows = session.scalars(
            select(PaperQuestion).where(PaperQuestion.paper_id == paper["id"]).order_by(PaperQuestion.sequence)
        ).all()
        assert stored.total_points == 20
        assert [row.question_id for row in rows] == [first, second]
        assert session.scalar(
            select(OperationLog).where(OperationLog.action == "paper.create", OperationLog.target_id == paper["id"])
        ) is not None


def test_automatic_preview_honors_all_quotas_and_distributions_without_duplicates(teacher_context) -> None:
    client, database, _ = teacher_context
    for index in range(4):
        seed_question(database, f"auto-choice-{index}")
    for index in range(2):
        seed_question(
            database,
            f"auto-judgment-{index}",
            point_id="soil-shear-point",
            point_name="库仑定律",
            chapter="第五章 土的抗剪强度",
            question_type="判断题",
            difficulty="困难",
            correct_answer=True,
        )
    seed_question(database, "near-miss-difficulty", difficulty="中等")
    body = {
        "subjectId": "soil-mechanics",
        "seed": 20260714,
        "rows": [
            {
                "chapterIds": ["第二章 土的渗透性"],
                "knowledgePointIds": ["soil-paper-point"],
                "questionTypes": ["单项选择题"],
                "difficulties": ["基础"],
                "count": 3,
                "pointsEach": 4,
                "sectionTitle": "一、选择题",
            },
            {
                "chapterIds": ["第五章 土的抗剪强度"],
                "knowledgePointIds": ["soil-shear-point"],
                "questionTypes": ["判断题"],
                "difficulties": ["困难"],
                "count": 2,
                "pointsEach": 6,
                "sectionTitle": "二、判断题",
            },
        ],
    }
    preview = client.post("/api/teacher/papers/generate-preview", json=body, headers=csrf())
    assert preview.status_code == 200, preview.text
    data = preview.json()["data"]
    ids = [item["questionId"] for item in data["questions"]]
    assert len(ids) == len(set(ids)) == 5
    assert data["shortages"] == []
    assert data["typeDistribution"] == {"单项选择题": 3, "判断题": 2}
    assert data["difficultyDistribution"] == {"基础": 3, "困难": 2}
    assert data["coverage"] == {"soil-paper-point": 3, "soil-shear-point": 2}
    assert data["duplicateRisk"] == 0
    assert [item["points"] for item in data["questions"]] == [4, 4, 4, 6, 6]


def test_automatic_preview_is_seed_deterministic_and_reports_exact_shortage(teacher_context) -> None:
    client, database, _ = teacher_context
    for index in range(4):
        seed_question(database, f"deterministic-{index}")
    body = {
        "subjectId": "soil-mechanics",
        "seed": 77,
        "rows": [{
            "chapterIds": ["第二章 土的渗透性"],
            "knowledgePointIds": ["soil-paper-point"],
            "questionTypes": ["单项选择题"],
            "difficulties": ["基础"],
            "count": 3,
            "pointsEach": 5,
        }],
    }
    first = client.post("/api/teacher/papers/generate-preview", json=body, headers=csrf()).json()["data"]
    second = client.post("/api/teacher/papers/generate-preview", json=body, headers=csrf()).json()["data"]
    assert [item["questionId"] for item in first["questions"]] == [
        item["questionId"] for item in second["questions"]
    ]

    shortage_body = deepcopy(body)
    shortage_body["rows"][0]["count"] = 7
    shortage = client.post(
        "/api/teacher/papers/generate-preview", json=shortage_body, headers=csrf()
    ).json()["data"]
    assert len(shortage["questions"]) == 4
    assert shortage["shortages"] == [{
        "row": 1,
        "requested": 7,
        "available": 4,
        "missing": 3,
        "criteria": {
            "chapterIds": ["第二章 土的渗透性"],
            "knowledgePointIds": ["soil-paper-point"],
            "questionTypes": ["单项选择题"],
            "difficulties": ["基础"],
        },
    }]


def test_automatic_preview_globally_reserves_question_for_narrow_later_row(teacher_context) -> None:
    client, database, _ = teacher_context
    seed_question(
        database,
        "broad-general",
        point_id="broad-general-point",
        point_name="广义候选知识点",
    )
    seed_question(
        database,
        "broad-specific",
        point_id="broad-specific-point",
        point_name="狭义候选知识点",
    )
    response = client.post(
        "/api/teacher/papers/generate-preview",
        json={
            "subjectId": "soil-mechanics",
            "seed": 2,
            "rows": [
                {
                    "chapterIds": [],
                    "knowledgePointIds": [],
                    "questionTypes": ["单项选择题"],
                    "difficulties": ["基础"],
                    "count": 1,
                    "pointsEach": 4,
                    "sectionTitle": "广义题",
                },
                {
                    "chapterIds": [],
                    "knowledgePointIds": ["broad-specific-point"],
                    "questionTypes": ["单项选择题"],
                    "difficulties": ["基础"],
                    "count": 1,
                    "pointsEach": 9,
                    "sectionTitle": "限定题",
                },
            ],
        },
        headers=csrf(),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["shortages"] == []
    assert [
        (item["questionId"], item["sectionTitle"], item["points"])
        for item in data["questions"]
    ] == [
        ("broad-general", "广义题", 4.0),
        ("broad-specific", "限定题", 9.0),
    ]


def test_automatic_preview_solves_multi_row_overlap_with_augmenting_paths(teacher_context) -> None:
    client, database, _ = teacher_context
    for suffix, point_name in (
        ("alpha", "重叠知识点 A"),
        ("beta", "重叠知识点 B"),
        ("gamma", "重叠知识点 C"),
    ):
        seed_question(
            database,
            f"overlap-{suffix}",
            point_id=f"overlap-{suffix}-point",
            point_name=point_name,
        )
    response = client.post(
        "/api/teacher/papers/generate-preview",
        json={
            "subjectId": "soil-mechanics",
            "seed": 0,
            "rows": [
                {
                    "chapterIds": [],
                    "knowledgePointIds": [],
                    "questionTypes": ["单项选择题"],
                    "difficulties": ["基础"],
                    "count": 1,
                    "pointsEach": 3,
                    "sectionTitle": "全部候选",
                },
                {
                    "chapterIds": [],
                    "knowledgePointIds": ["overlap-alpha-point", "overlap-beta-point"],
                    "questionTypes": ["单项选择题"],
                    "difficulties": ["基础"],
                    "count": 1,
                    "pointsEach": 5,
                    "sectionTitle": "A 或 B",
                },
                {
                    "chapterIds": [],
                    "knowledgePointIds": ["overlap-alpha-point"],
                    "questionTypes": ["单项选择题"],
                    "difficulties": ["基础"],
                    "count": 1,
                    "pointsEach": 8,
                    "sectionTitle": "仅 A",
                },
            ],
        },
        headers=csrf(),
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["shortages"] == []
    assert len({item["questionId"] for item in data["questions"]}) == 3
    by_section = {item["sectionTitle"]: item for item in data["questions"]}
    assert by_section["仅 A"]["questionId"] == "overlap-alpha"
    assert by_section["A 或 B"]["questionId"] == "overlap-beta"
    assert by_section["全部候选"]["questionId"] == "overlap-gamma"
    assert {section: item["points"] for section, item in by_section.items()} == {
        "全部候选": 3.0,
        "A 或 B": 5.0,
        "仅 A": 8.0,
    }


def test_paper_ownership_copy_and_private_question_rules(teacher_context) -> None:
    from server.application.models import OperationLog

    client, database, _ = teacher_context
    shared_id = seed_question(database, "paper-shared")
    own_id = seed_question(database, "paper-own", created_by="teacher-user-1")
    private_other_id = seed_question(
        database,
        "paper-private-other",
        point_id="paper-private-point",
        point_name="私有知识点",
        created_by="teacher-user-2",
    )
    paper = create_manual_paper(client, [shared_id, own_id])
    copied = client.post(f"/api/teacher/papers/{paper['id']}/copy", headers=csrf())
    assert copied.status_code == 200
    copy_data = copied.json()["data"]
    assert copy_data["id"] != paper["id"]
    assert copy_data["status"] == "draft"
    assert [item["questionId"] for item in copy_data["questions"]] == [shared_id, own_id]
    other = teacher2_client(client, database)
    for method, path in (
        (other.get, f"/api/teacher/papers/{paper['id']}"),
        (other.post, f"/api/teacher/papers/{paper['id']}/copy"),
        (other.delete, f"/api/teacher/papers/{paper['id']}"),
    ):
        response = method(path, headers=csrf("teacher-2-csrf"))
        assert response.status_code == 404
        assert set(response.json()) == {"success", "message", "code", "requestId"}
    denied_update = other.put(
        f"/api/teacher/papers/{paper['id']}",
        json=manual_paper_payload([shared_id], title="越权修改"),
        headers=csrf("teacher-2-csrf"),
    )
    denied_publish = other.post(
        f"/api/teacher/papers/{paper['id']}/publish",
        json={"studentIds": ["student-2"], "classIds": []},
        headers=csrf("teacher-2-csrf"),
    )
    for response in (denied_update, denied_publish):
        assert response.status_code == 404
        assert response.json()["code"] == "PAPER_NOT_FOUND"
        assert set(response.json()) == {"success", "message", "code", "requestId"}
    private_question = client.post(
        "/api/teacher/papers",
        json=manual_paper_payload([private_other_id]),
        headers=csrf(),
    )
    assert private_question.status_code == 404
    assert private_question.json()["code"] == "QUESTION_NOT_FOUND"
    with database.session() as session:
        copy_log = session.scalar(
            select(OperationLog).where(
                OperationLog.action == "paper.copy", OperationLog.target_id == copy_data["id"]
            )
        )
        assert copy_log.detail["sourcePaperId"] == paper["id"]


def test_paper_update_and_delete_are_audited_transactionally(teacher_context) -> None:
    from server.application.models import OperationLog, Paper

    client, database, _ = teacher_context
    question_id = seed_question(database, "paper-audit-question")
    paper = create_manual_paper(client, [question_id], title="审计试卷")
    updated = client.put(
        f"/api/teacher/papers/{paper['id']}",
        json=manual_paper_payload([question_id], title="审计试卷修订"),
        headers=csrf(),
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["version"] == 2
    deleted = client.delete(f"/api/teacher/papers/{paper['id']}", headers=csrf())
    assert deleted.status_code == 200

    with database.session() as session:
        assert session.get(Paper, paper["id"]) is None
        logs = session.scalars(
            select(OperationLog)
            .where(
                OperationLog.target_id == paper["id"],
                OperationLog.action.in_(["paper.update", "paper.delete"]),
            )
            .order_by(OperationLog.created_at, OperationLog.action)
        ).all()
        assert {log.action for log in logs} == {"paper.update", "paper.delete"}
        update_log = next(log for log in logs if log.action == "paper.update")
        delete_log = next(log for log in logs if log.action == "paper.delete")
        assert update_log.detail == {"version": 2}
        assert delete_log.detail == {}


def test_publish_authorizes_students_and_classes_and_logs_targets(teacher_context) -> None:
    from server.application.models import Assignment, AssignmentTarget, OperationLog

    client, database, _ = teacher_context
    paper = create_manual_paper(client, [seed_question(database, "publish-target-question")])
    forbidden = client.post(
        f"/api/teacher/papers/{paper['id']}/publish",
        json={"studentIds": ["student-2"], "classIds": []},
        headers=csrf(),
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "PAPER_TARGET_FORBIDDEN"
    unknown_class = client.post(
        f"/api/teacher/papers/{paper['id']}/publish",
        json={"studentIds": [], "classIds": ["class-unknown"]},
        headers=csrf(),
    )
    assert unknown_class.status_code == 403

    published = client.post(
        f"/api/teacher/papers/{paper['id']}/publish",
        json={
            "studentIds": [],
            "classIds": ["class-1"],
            "durationMinutes": 60,
            "showAnswersMode": "after_close",
        },
        headers=csrf(),
    )
    assert published.status_code == 200, published.text
    assert "correctAnswer" not in published.text
    assignment_id = published.json()["data"]["assignmentId"]
    assert published.json()["data"]["targetCount"] == 1
    with database.session() as session:
        assignment = session.get(Assignment, assignment_id)
        targets = session.scalars(
            select(AssignmentTarget).where(AssignmentTarget.assignment_id == assignment_id)
        ).all()
        log = session.scalar(
            select(OperationLog).where(
                OperationLog.action == "paper.publish", OperationLog.target_id == paper["id"]
            )
        )
        assert assignment.paper_id == paper["id"]
        assert assignment.duration_minutes == 60
        assert assignment.show_answers_mode == "after_close"
        assert [(target.student_id, target.class_id) for target in targets] == [("student-1", "class-1")]
        assert log.detail == {
            "paperId": paper["id"], "assignmentId": assignment_id, "targetCount": 1
        }


def test_publish_is_idempotent_for_the_same_publication_key(teacher_context) -> None:
    from server.application.models import Assignment, AssignmentTarget, OperationLog

    client, database, _ = teacher_context
    paper = create_manual_paper(client, [seed_question(database, "publish-idempotent-question")])
    payload = {
        "studentIds": ["student-1"],
        "classIds": [],
        "publicationKey": "publish-idempotent-0001",
    }
    first = client.post(f"/api/teacher/papers/{paper['id']}/publish", json=payload, headers=csrf())
    second = client.post(f"/api/teacher/papers/{paper['id']}/publish", json=payload, headers=csrf())

    assert first.status_code == second.status_code == 200
    assert first.json()["data"] == second.json()["data"]
    with database.session() as session:
        assignments = session.scalars(
            select(Assignment).where(Assignment.paper_id == paper["id"])
        ).all()
        assert len(assignments) == 1
        assert assignments[0].publication_key == payload["publicationKey"]
        assert session.query(AssignmentTarget).filter_by(assignment_id=assignments[0].id).count() == 1
        assert session.query(OperationLog).filter_by(action="paper.publish", target_id=paper["id"]).count() == 1


def test_publish_rejects_zero_question_and_automatic_shortage_papers(teacher_context) -> None:
    client, database, _ = teacher_context
    empty = create_manual_paper(client, [])
    empty_publish = client.post(
        f"/api/teacher/papers/{empty['id']}/publish",
        json={"studentIds": ["student-1"], "classIds": []},
        headers=csrf(),
    )
    assert empty_publish.status_code == 409
    assert empty_publish.json()["code"] == "PAPER_EMPTY"

    seed_question(database, "short-paper-only")
    automatic = client.post(
        "/api/teacher/papers",
        json={
            "subjectId": "soil-mechanics",
            "title": "缺题自动试卷",
            "assemblyMode": "automatic",
            "seed": 5,
            "blueprintRows": [{
                "chapterIds": ["第二章 土的渗透性"],
                "knowledgePointIds": ["soil-paper-point"],
                "questionTypes": ["单项选择题"],
                "difficulties": ["基础"],
                "count": 2,
                "pointsEach": 10,
            }],
        },
        headers=csrf(),
    )
    assert automatic.status_code == 200, automatic.text
    automatic_data = automatic.json()["data"]
    assert automatic_data["shortages"][0]["missing"] == 1
    shortage_publish = client.post(
        f"/api/teacher/papers/{automatic_data['id']}/publish",
        json={"studentIds": ["student-1"], "classIds": []},
        headers=csrf(),
    )
    assert shortage_publish.status_code == 409
    assert shortage_publish.json()["code"] == "PAPER_HAS_SHORTAGES"


def test_upsert_cannot_forge_or_demote_server_owned_published_state(teacher_context) -> None:
    from server.application.models import Paper

    client, database, _ = teacher_context
    forged_empty = client.post(
        "/api/teacher/papers",
        json=manual_paper_payload([], status="published", title="伪造空试卷"),
        headers=csrf(),
    )
    assert forged_empty.status_code == 422
    assert forged_empty.json()["code"] == "VALIDATION_ERROR"

    empty = create_manual_paper(client, [], title="空试卷草稿")
    forged_empty_update = client.put(
        f"/api/teacher/papers/{empty['id']}",
        json=manual_paper_payload([], status="published", title="伪造空试卷更新"),
        headers=csrf(),
    )
    assert forged_empty_update.status_code == 422

    shortage_payload = {
        "subjectId": "soil-mechanics",
        "title": "缺题试卷草稿",
        "assemblyMode": "automatic",
        "seed": 11,
        "blueprintRows": [{
            "chapterIds": ["不存在的章节"],
            "knowledgePointIds": [],
            "questionTypes": ["单项选择题"],
            "difficulties": ["基础"],
            "count": 1,
            "pointsEach": 10,
        }],
    }
    forged_shortage = client.post(
        "/api/teacher/papers",
        json={**shortage_payload, "status": "published"},
        headers=csrf(),
    )
    assert forged_shortage.status_code == 422
    shortage = client.post(
        "/api/teacher/papers", json=shortage_payload, headers=csrf()
    ).json()["data"]
    assert shortage["shortages"][0]["missing"] == 1
    forged_shortage_update = client.put(
        f"/api/teacher/papers/{shortage['id']}",
        json={**shortage_payload, "status": "published"},
        headers=csrf(),
    )
    assert forged_shortage_update.status_code == 422

    question_id = seed_question(database, "state-owned-question")
    publishable = create_manual_paper(client, [question_id], title="正式发布状态")
    published = client.post(
        f"/api/teacher/papers/{publishable['id']}/publish",
        json={"studentIds": ["student-1"], "classIds": []},
        headers=csrf(),
    )
    assert published.status_code == 200
    published_empty_update = client.put(
        f"/api/teacher/papers/{publishable['id']}",
        json=manual_paper_payload([], status="draft", title="不得清空已发布试卷"),
        headers=csrf(),
    )
    assert published_empty_update.status_code == 409
    assert published_empty_update.json()["code"] == "PUBLISHED_PAPER_CONTENT_INVALID"
    published_shortage_update = client.put(
        f"/api/teacher/papers/{publishable['id']}",
        json={**shortage_payload, "status": "draft", "title": "不得缺题的已发布试卷"},
        headers=csrf(),
    )
    assert published_shortage_update.status_code == 409
    assert published_shortage_update.json()["code"] == "PUBLISHED_PAPER_CONTENT_INVALID"
    edited = client.put(
        f"/api/teacher/papers/{publishable['id']}",
        json=manual_paper_payload(
            [question_id], status="draft", title="已发布试卷内容修订"
        ),
        headers=csrf(),
    )
    assert edited.status_code == 200
    assert edited.json()["data"]["status"] == "published"
    with database.session() as session:
        assert session.get(Paper, empty["id"]).status == "draft"
        assert session.get(Paper, shortage["id"]).status == "draft"
        assert session.get(Paper, publishable["id"]).status == "published"


def test_paper_and_publication_titles_are_trimmed_and_blank_titles_are_atomic(teacher_context) -> None:
    from server.application.models import Assignment, OperationLog, Paper

    client, database, _ = teacher_context
    blank_create = client.post(
        "/api/teacher/papers",
        json=manual_paper_payload([], title="   \t "),
        headers=csrf(),
    )
    assert blank_create.status_code == 422
    assert set(blank_create.json()) == {"success", "message", "code", "requestId"}

    question_id = seed_question(database, "trimmed-title-question")
    created = create_manual_paper(client, [question_id], title="  保留的试卷名  ")
    assert created["title"] == "保留的试卷名"
    blank_update = client.put(
        f"/api/teacher/papers/{created['id']}",
        json=manual_paper_payload([question_id], title=" \n "),
        headers=csrf(),
    )
    assert blank_update.status_code == 422
    blank_publish = client.post(
        f"/api/teacher/papers/{created['id']}/publish",
        json={"studentIds": ["student-1"], "classIds": [], "title": "   "},
        headers=csrf(),
    )
    assert blank_publish.status_code == 422

    trimmed_publish = client.post(
        f"/api/teacher/papers/{created['id']}/publish",
        json={"studentIds": ["student-1"], "classIds": [], "title": "  正式考试名  "},
        headers=csrf(),
    )
    assert trimmed_publish.status_code == 200
    with database.session() as session:
        paper = session.get(Paper, created["id"])
        assignments = session.scalars(select(Assignment).where(Assignment.paper_id == paper.id)).all()
        publish_logs = session.scalars(
            select(OperationLog).where(
                OperationLog.action == "paper.publish", OperationLog.target_id == paper.id
            )
        ).all()
        assert paper.title == "保留的试卷名"
        assert [assignment.title for assignment in assignments] == ["正式考试名"]
        assert len(publish_logs) == 1


def test_publication_snapshot_is_rich_server_side_and_immutable_after_source_edit(teacher_context) -> None:
    from server.application.models import AssignmentQuestion, Question

    client, database, _ = teacher_context
    attachments = [
        {"kind": "image", "path": "/question-assets/soil/test.png", "alt": "渗流图"},
        {"kind": "table", "rows": [["土层", "k"], ["粘土", "1e-7"]]},
        {"kind": "formula", "latex": "q=kAi"},
    ]
    source_metadata = {
        "sourceBlocks": [{"type": "paragraph", "text": "原始富文本"}],
        "tables": [[["参数", "数值"], ["k", "1e-7"]]],
        "formulas": ["q=kAi"],
    }
    rubric = [{"criterion": "公式", "points": 4}, {"criterion": "过程", "points": 6}]
    question_id = seed_question(
        database,
        "snapshot-rich-question",
        created_by="teacher-user-1",
        question_type="计算题",
        text_value="已知 $q=kAi$，计算渗流量。",
        attachments=attachments,
        source_metadata=source_metadata,
        rubric=rubric,
        correct_answer={"value": 12.5, "unit": "cm3/s"},
    )
    paper = create_manual_paper(client, [question_id])
    published = client.post(
        f"/api/teacher/papers/{paper['id']}/publish",
        json={"studentIds": ["student-1"], "classIds": []},
        headers=csrf(),
    )
    assert published.status_code == 200
    assert "cm3/s" not in published.text
    assignment_id = published.json()["data"]["assignmentId"]
    with database.session() as session:
        row = session.scalar(
            select(AssignmentQuestion).where(AssignmentQuestion.assignment_id == assignment_id)
        )
        original_snapshot = deepcopy(row.question_snapshot)
        assert original_snapshot["text"] == "已知 $q=kAi$，计算渗流量。"
        assert original_snapshot["correctAnswer"] == {"value": 12.5, "unit": "cm3/s"}
        assert original_snapshot["attachments"] == attachments
        assert original_snapshot["sourceMetadata"] == source_metadata
        assert original_snapshot["rubric"] == rubric
        question = session.get(Question, question_id)
        question.text = "修改后的题干"
        question.correct_answer = {"value": 99, "unit": "m3/s"}
        question.attachments = []
        session.commit()

    with database.session() as session:
        row = session.scalar(
            select(AssignmentQuestion).where(AssignmentQuestion.assignment_id == assignment_id)
        )
        assert row.question_snapshot == original_snapshot
        assert row.question_snapshot["text"] != session.get(Question, question_id).text


def test_legacy_assignment_route_creates_an_immutable_question_snapshot(teacher_context) -> None:
    from server.application.models import Assignment, AssignmentQuestion, Question

    client, database, _ = teacher_context
    question_id = seed_question(database, "legacy-route-question")
    response = client.post(
        "/api/teacher/assignments",
        json={
            "title": "旧作业接口",
            "studentIds": ["student-1"],
            "questionIds": [question_id],
            "totalPoints": 10,
            "status": "published",
        },
        headers=csrf(),
    )
    assert response.status_code == 200, response.text
    with database.session() as session:
        assignment = session.get(Assignment, response.json()["data"]["id"])
        row = session.scalar(
            select(AssignmentQuestion).where(AssignmentQuestion.assignment_id == assignment.id)
        )
        assert assignment.paper_id is None
        assert assignment.duration_minutes is None
        assert assignment.show_answers_mode == "after_submission"
        original_snapshot = deepcopy(row.question_snapshot)
        assert original_snapshot["id"] == question_id
        assert original_snapshot["text"] == "题目 legacy-route-question"
        session.get(Question, question_id).text = "题库后来修改的题干"
        session.commit()
    with database.session() as session:
        row = session.scalar(
            select(AssignmentQuestion).where(AssignmentQuestion.assignment_id == assignment.id)
        )
        assert row.question_snapshot == original_snapshot
