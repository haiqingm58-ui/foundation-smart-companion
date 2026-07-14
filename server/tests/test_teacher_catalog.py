from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from server.application.models import KnowledgePoint, OperationLog, Question, QuestionKnowledgePoint, SessionToken
from server.application.security import token_digest
from server.tests.test_teacher import teacher_context


def csrf() -> dict[str, str]:
    return {"X-CSRF-Token": "teacher-csrf"}


def choice_payload(**overrides) -> dict:
    payload = {
        "subjectId": "soil-mechanics",
        "knowledgePointIds": ["soil-permeability"],
        "text": "达西定律适用于什么流态？",
        "questionType": "单项选择题",
        "chapter": "第二章 土的渗透性",
        "difficulty": "中等",
        "options": [{"label": "A", "text": "层流"}, {"label": "B", "text": "紊流"}],
        "correctAnswer": "A",
        "points": 10,
        "gradingMode": "auto",
    }
    payload.update(overrides)
    return payload


def seed_soil_permeability(database) -> KnowledgePoint:
    with database.session() as session:
        point = session.get(KnowledgePoint, "soil-permeability")
        if point is None:
            point = KnowledgePoint(
                id="soil-permeability", subject_id="soil-mechanics", chapter="第二章 土的渗透性",
                name="达西定律", normalized_name="达西定律",
            )
            session.add(point)
            session.commit()
        return point


def seed_shared_soil_question(database) -> str:
    seed_soil_permeability(database)
    with database.session() as session:
        point = session.get(KnowledgePoint, "soil-permeability")
        question = Question(
            id="shared-soil-question", text="共享题目：达西定律。", question_type="单项选择题",
            subject_id="soil-mechanics", chapter="第二章 土的渗透性", difficulty="基础",
            options=[{"label": "A", "text": "层流"}, {"label": "B", "text": "紊流"}],
            correct_answer="A", source="imported", created_by=None, status="active",
            knowledge_point_links=[QuestionKnowledgePoint(id="shared-soil-link", knowledge_point=point, weight=1.0)],
        )
        session.add(question)
        session.commit()
    return question.id


def seed_invalid_shared_soil_question(database) -> str:
    with database.session() as session:
        question = Question(
            id="invalid-shared-soil-question", text="失效共享题目。", question_type="判断题",
            subject_id="soil-mechanics", chapter="第二章 土的渗透性", options=[], correct_answer=True,
            source="imported", created_by=None, status="review_required",
        )
        session.add(question)
        session.commit()
    return question.id


def teacher2_client(client: TestClient, database) -> TestClient:
    with database.session() as session:
        session.add(
            SessionToken(
                id="teacher-2-session", user_id="teacher-user-2", token_hash=token_digest("teacher-2-token"),
                csrf_hash=token_digest("teacher-2-csrf"), expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        session.commit()
    other = TestClient(client.app)
    other.cookies.set("foundation_session", "teacher-2-token")
    other.cookies.set("foundation_csrf", "teacher-2-csrf")
    return other


def test_teacher_lists_subjects_and_filters_knowledge_points_with_counts(teacher_context) -> None:
    client, database, _ = teacher_context
    seed_soil_permeability(database)
    with database.session() as session:
        point = session.get(KnowledgePoint, "soil-permeability")
        session.add(
            Question(
                id="count-soil-question", text="渗透系数的量纲是什么？", question_type="判断题",
                subject_id="soil-mechanics", chapter=point.chapter, options=[], correct_answer=True,
                source="textbook", status="active",
                knowledge_point_links=[QuestionKnowledgePoint(id="count-soil-link", knowledge_point=point, weight=1.0)],
            )
        )
        session.commit()

    subjects = client.get("/api/teacher/subjects")
    assert subjects.status_code == 200
    soil = next(item for item in subjects.json()["data"]["items"] if item["id"] == "soil-mechanics")
    assert soil["knowledgePointCount"] >= 1
    assert soil["questionCount"] >= 1

    points = client.get("/api/teacher/knowledge-points?subjectId=soil-mechanics&chapter=第二章%20土的渗透性")
    assert points.status_code == 200
    item = next(item for item in points.json()["data"]["items"] if item["id"] == "soil-permeability")
    assert item["questionCount"] == 1
    assert points.json()["data"]["statusCounts"]["active"] >= 1


def test_teacher_creates_unique_owned_knowledge_points_and_cannot_mutate_shared(teacher_context) -> None:
    client, database, _ = teacher_context
    seed_soil_permeability(database)
    created = client.post(
        "/api/teacher/knowledge-points",
        json={"subjectId": "soil-mechanics", "chapter": "第二章 土的渗透性", "name": "  渗透破坏  ", "description": "临界水力坡降"},
        headers=csrf(),
    )
    assert created.status_code == 200
    point_id = created.json()["data"]["id"]
    assert created.json()["data"]["createdBy"] == "teacher-user-1"
    duplicate = client.post(
        "/api/teacher/knowledge-points",
        json={"subjectId": "soil-mechanics", "chapter": "第二章 土的渗透性", "name": "　渗透破坏　"},
        headers=csrf(),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "KNOWLEDGE_POINT_EXISTS"
    assert client.put(
        "/api/teacher/knowledge-points/soil-permeability",
        json={"subjectId": "soil-mechanics", "chapter": "第二章 土的渗透性", "name": "不可修改"},
        headers=csrf(),
    ).status_code == 403
    assert client.put(
        f"/api/teacher/knowledge-points/{point_id}",
        json={"subjectId": "soil-mechanics", "chapter": "第二章 土的渗透性", "name": "渗透破坏", "status": "inactive"},
        headers=csrf(),
    ).status_code == 200
    paged = client.get("/api/teacher/knowledge-points?subjectId=soil-mechanics&page=1&pageSize=1")
    assert paged.status_code == 200
    assert paged.json()["data"]["total"] >= 2
    assert len(paged.json()["data"]["items"]) == 1
    assert client.get("/api/teacher/knowledge-points?pageSize=101").status_code == 422


def test_teacher_creates_subject_matched_active_question_and_legacy_adapter(teacher_context) -> None:
    client, database, _ = teacher_context
    seed_soil_permeability(database)
    created = client.post("/api/teacher/questions", json=choice_payload(), headers=csrf())
    assert created.status_code == 200
    data = created.json()["data"]
    assert data["subjectId"] == "soil-mechanics"
    assert data["knowledgePoints"] == [{"id": "soil-permeability", "name": "达西定律", "weight": 1.0}]
    assert data["editable"] is True
    with database.session() as session:
        question = session.get(Question, data["id"])
        assert question.status == "active"
    listed = client.get("/api/teacher/questions?subjectId=soil-mechanics&chapter=第二章%20土的渗透性")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["data"]["items"]] == [data["id"]]

    legacy = client.post(
        "/api/teacher/questions",
        json={"text": "说明桩侧阻力的影响因素。", "questionType": "简答题", "chapter": "第3章 桩基础", "knowledgePoint": "桩侧阻力", "options": [], "correctAnswer": "土性与位移", "points": 10},
        headers=csrf(),
    )
    assert legacy.status_code == 200
    legacy_data = legacy.json()["data"]
    assert legacy_data["subjectId"] == "foundation-engineering"
    assert len(legacy_data["knowledgePoints"]) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("text", " x "),
        ("chapter", "   "),
        ("difficulty", "提高"),
        ("attachments", ["not-an-object"]),
        ("attachments", [{"kind": ""}]),
        ("rubric", ["not-an-object"]),
    ],
)
def test_teacher_rejects_untrimmed_or_unstructured_canonical_question_fields(teacher_context, field, value) -> None:
    client, database, _ = teacher_context
    seed_soil_permeability(database)
    response = client.post("/api/teacher/questions", json=choice_payload(**{field: value}), headers=csrf())
    assert response.status_code == 422


def test_teacher_accepts_structured_forward_compatible_question_metadata(teacher_context) -> None:
    client, database, _ = teacher_context
    seed_soil_permeability(database)
    response = client.post(
        "/api/teacher/questions",
        json=choice_payload(
            attachments=[
                {"kind": "image", "src": "image.png"},
                {"kind": "table", "columns": ["k"], "rows": [[1]]},
                {"kind": "formula", "latex": "k=iA"},
            ],
            rubric=[{"criterion": "单位", "points": 2}],
        ),
        headers=csrf(),
    )
    assert response.status_code == 200


def test_teacher_copies_shared_question_before_editing(teacher_context) -> None:
    client, database, _ = teacher_context
    shared_id = seed_shared_soil_question(database)
    assert client.put(f"/api/teacher/questions/{shared_id}", json=choice_payload(text="不能改共享题"), headers=csrf()).status_code == 403
    assert client.delete(f"/api/teacher/questions/{shared_id}", headers=csrf()).status_code == 403
    copied = client.post(f"/api/teacher/questions/{shared_id}/copy", headers=csrf())
    assert copied.status_code == 200
    copy_data = copied.json()["data"]
    assert copy_data["createdBy"] == "teacher-user-1"
    assert copy_data["editable"] is True
    assert copy_data["status"] == "review_required"
    updated = client.put(copy_data["id"].join(["/api/teacher/questions/", ""]), json=choice_payload(text="教师副本可编辑"), headers=csrf())
    assert updated.status_code == 200
    assert updated.json()["data"]["status"] == "active"


def test_copy_hides_other_teachers_private_question_and_keeps_invalid_shared_copy_in_review(teacher_context) -> None:
    client, database, _ = teacher_context
    seed_soil_permeability(database)
    private = client.post("/api/teacher/questions", json=choice_payload(), headers=csrf()).json()["data"]
    other = teacher2_client(client, database)
    denied = other.post(f"/api/teacher/questions/{private['id']}/copy", headers={"X-CSRF-Token": "teacher-2-csrf"})
    assert denied.status_code == 404
    own_copy = client.post(f"/api/teacher/questions/{private['id']}/copy", headers=csrf())
    assert own_copy.status_code == 200
    invalid_shared = client.post(f"/api/teacher/questions/{seed_invalid_shared_soil_question(database)}/copy", headers=csrf())
    assert invalid_shared.status_code == 200
    assert invalid_shared.json()["data"]["status"] == "review_required"


def test_teacher_question_list_filters_and_paginates(teacher_context) -> None:
    client, database, _ = teacher_context
    seed_soil_permeability(database)
    with database.session() as session:
        secondary = KnowledgePoint(id="filter-secondary", subject_id="soil-mechanics", chapter="筛选章节", name="临界坡降", normalized_name="临界坡降")
        shared = Question(
            id="filter-shared", text="共享关键字", question_type="判断题", subject_id="soil-mechanics", chapter="筛选章节",
            difficulty="基础", options=[], correct_answer=True, source="imported", created_by=None, status="active",
            knowledge_point_links=[QuestionKnowledgePoint(id="filter-shared-link", knowledge_point=secondary)],
        )
        owned = Question(
            id="filter-owned", text="教师关键字", question_type="判断题", subject_id="soil-mechanics", chapter="筛选章节",
            difficulty="困难", options=[], correct_answer=False, source="teacher", created_by="teacher-user-1", status="active",
            knowledge_point_links=[QuestionKnowledgePoint(id="filter-owned-link", knowledge_point=secondary)],
        )
        other = Question(
            id="filter-other", text="另一章题目", question_type="单项选择题", subject_id="soil-mechanics", chapter="其他章节",
            difficulty="中等", options=[{"label": "A", "text": "是"}, {"label": "B", "text": "否"}], correct_answer="A",
            source="teacher", created_by="teacher-user-1", status="active",
            knowledge_point_links=[QuestionKnowledgePoint(id="filter-other-link", knowledge_point_id="soil-permeability")],
        )
        session.add_all([secondary, shared, owned, other])
        session.commit()

    base = "/api/teacher/questions?subjectId=soil-mechanics"
    assert client.get(f"{base}&chapter=筛选章节").json()["data"]["total"] == 2
    assert client.get(f"{base}&knowledgePointId=filter-secondary").json()["data"]["total"] == 2
    assert client.get(f"{base}&questionType=判断题").json()["data"]["total"] == 2
    assert client.get(f"{base}&difficulty=困难").json()["data"]["items"][0]["id"] == "filter-owned"
    assert client.get(f"{base}&source=imported").json()["data"]["items"][0]["id"] == "filter-shared"
    assert client.get(f"{base}&keyword=教师关键字").json()["data"]["items"][0]["id"] == "filter-owned"
    assert client.get(f"{base}&search=共享关键字").json()["data"]["items"][0]["id"] == "filter-shared"
    first = client.get(f"{base}&page=1&pageSize=1").json()["data"]
    second = client.get(f"{base}&page=2&pageSize=1").json()["data"]
    assert first["total"] == 3
    assert len(first["items"]) == len(second["items"]) == 1
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert client.get(f"{base}&pageSize=101").status_code == 422


def test_teacher_merges_owned_points_transactionally_and_audits(teacher_context) -> None:
    client, database, _ = teacher_context
    with database.session() as session:
        source = KnowledgePoint(id="merge-source", subject_id="soil-mechanics", chapter="第二章 土的渗透性", name="渗流破坏", normalized_name="渗流破坏", created_by="teacher-user-1")
        target = KnowledgePoint(id="merge-target", subject_id="soil-mechanics", chapter="第二章 土的渗透性", name="管涌", normalized_name="管涌", created_by="teacher-user-1")
        question = Question(
            id="merge-question", text="管涌与渗流破坏的关系。", question_type="判断题", subject_id="soil-mechanics",
            chapter="第二章 土的渗透性", options=[], correct_answer=True, source="teacher", created_by="teacher-user-1", status="active",
            knowledge_point_links=[
                QuestionKnowledgePoint(id="merge-source-link", knowledge_point=source, weight=0.4),
                QuestionKnowledgePoint(id="merge-target-link", knowledge_point=target, weight=0.6),
            ],
        )
        session.add_all([source, target, question])
        session.commit()

    assert client.delete("/api/teacher/knowledge-points/merge-source", headers=csrf()).status_code == 409
    merged = client.post("/api/teacher/knowledge-points/merge-source/merge", json={"targetId": "merge-target"}, headers=csrf())
    assert merged.status_code == 200
    with database.session() as session:
        question = session.get(Question, "merge-question")
        links = session.scalars(select(QuestionKnowledgePoint).where(QuestionKnowledgePoint.question_id == question.id)).all()
        assert [(link.knowledge_point_id, link.weight) for link in links] == [("merge-target", 1.0)]
        assert question.status == "active"
        assert session.get(KnowledgePoint, "merge-source") is None
        assert session.scalar(select(OperationLog).where(OperationLog.action == "knowledge_point.merge")) is not None


def test_teacher_merge_rolls_back_when_audit_fails(teacher_context, monkeypatch) -> None:
    client, database, _ = teacher_context
    with database.session() as session:
        source = KnowledgePoint(id="rollback-source", subject_id="soil-mechanics", chapter="第二章", name="源点", normalized_name="源点", created_by="teacher-user-1")
        target = KnowledgePoint(id="rollback-target", subject_id="soil-mechanics", chapter="第二章", name="目标点", normalized_name="目标点", created_by="teacher-user-1")
        question = Question(
            id="rollback-question", text="回滚题目。", question_type="判断题", subject_id="soil-mechanics", chapter="第二章",
            options=[], correct_answer=True, source="teacher", created_by="teacher-user-1", status="active",
            knowledge_point_links=[
                QuestionKnowledgePoint(id="rollback-source-link", knowledge_point=source, weight=0.4),
                QuestionKnowledgePoint(id="rollback-target-link", knowledge_point=target, weight=0.6),
            ],
        )
        session.add_all([source, target, question])
        session.commit()

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("server.application.api.teacher_catalog.add_log", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        client.post("/api/teacher/knowledge-points/rollback-source/merge", json={"targetId": "rollback-target"}, headers=csrf())
    with database.session() as session:
        assert session.get(KnowledgePoint, "rollback-source") is not None
        question = session.get(Question, "rollback-question")
        links = session.scalars(select(QuestionKnowledgePoint).where(QuestionKnowledgePoint.question_id == question.id)).all()
        assert sorted((link.knowledge_point_id, link.weight) for link in links) == [("rollback-source", 0.4), ("rollback-target", 0.6)]
        assert question.status == "active"
