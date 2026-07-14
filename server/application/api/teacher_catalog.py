from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from ..errors import APIError
from ..models import KnowledgePoint, Question, QuestionKnowledgePoint, Subject
from ..schemas.assessment import KnowledgePointInput, KnowledgePointMergeInput
from ..services.assessment_validation import normalize_text
from ..services.audit import add_log
from ..services.question_service import (
    apply_prepared_question,
    create_question,
    normalize_link_weights,
    normalize_question_link_weights,
    prepare_question,
    question_payload,
)
from .auth import client_ip
from .dependencies import AuthContext, require_teacher


router = APIRouter(prefix="/api/teacher", tags=["teacher-catalog"])


def _point_payload(point: KnowledgePoint, question_count: int = 0) -> dict:
    return {
        "id": point.id, "subjectId": point.subject_id, "chapter": point.chapter, "name": point.name,
        "description": point.description, "status": point.status, "createdBy": point.created_by,
        "questionCount": question_count, "editable": False,
    }


def _owned_point(session, point_id: str, actor_id: str) -> KnowledgePoint:
    point = session.get(KnowledgePoint, point_id)
    if point is None:
        raise APIError(404, "知识点不存在", "KNOWLEDGE_POINT_NOT_FOUND")
    if point.created_by != actor_id:
        raise APIError(403, "只能修改本人创建的知识点", "KNOWLEDGE_POINT_READ_ONLY")
    return point


@router.get("/subjects")
def subjects(request: Request, _auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        point_counts = dict(session.execute(select(KnowledgePoint.subject_id, func.count(KnowledgePoint.id)).group_by(KnowledgePoint.subject_id)).all())
        question_counts = dict(session.execute(select(Question.subject_id, func.count(Question.id)).group_by(Question.subject_id)).all())
        items = [
            {
                "id": subject.id, "title": subject.title, "slug": subject.slug, "status": subject.status,
                "sortOrder": subject.sort_order, "knowledgePointCount": point_counts.get(subject.id, 0),
                "questionCount": question_counts.get(subject.id, 0),
            }
            for subject in session.scalars(select(Subject).order_by(Subject.sort_order, Subject.title)).all()
        ]
    return request.app.state.success(request, {"items": items, "total": len(items)})


@router.get("/knowledge-points")
def knowledge_points(
    request: Request, subjectId: str | None = None, chapter: str | None = None, status: str | None = None,
    page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), auth: AuthContext = Depends(require_teacher),
):
    with request.app.state.database.session() as session:
        filters = []
        if subjectId:
            filters.append(KnowledgePoint.subject_id == subjectId)
        if chapter:
            filters.append(KnowledgePoint.chapter == chapter)
        status_counts = dict(session.execute(select(KnowledgePoint.status, func.count(KnowledgePoint.id)).where(*filters).group_by(KnowledgePoint.status)).all())
        if status:
            filters.append(KnowledgePoint.status == status)
        total = session.scalar(select(func.count(KnowledgePoint.id)).where(*filters)) or 0
        link_counts = (
            select(QuestionKnowledgePoint.knowledge_point_id.label("point_id"), func.count(QuestionKnowledgePoint.id).label("question_count"))
            .group_by(QuestionKnowledgePoint.knowledge_point_id)
            .subquery()
        )
        rows = session.execute(
            select(KnowledgePoint, func.coalesce(link_counts.c.question_count, 0))
            .outerjoin(link_counts, link_counts.c.point_id == KnowledgePoint.id)
            .where(*filters)
            .order_by(KnowledgePoint.sort_order, KnowledgePoint.name, KnowledgePoint.id)
            .offset((page - 1) * pageSize)
            .limit(pageSize)
        ).all()
        items = []
        for point, question_count in rows:
            payload = _point_payload(point, int(question_count))
            payload["editable"] = point.created_by == auth.user.id
            items.append(payload)
    return request.app.state.success(request, {"items": items, "total": total, "statusCounts": status_counts})


@router.post("/knowledge-points")
def create_knowledge_point(body: KnowledgePointInput, request: Request, auth: AuthContext = Depends(require_teacher)):
    normalized_name = normalize_text(body.name)
    if not normalized_name:
        raise APIError(422, "知识点不能为空", "KNOWLEDGE_POINT_REQUIRED")
    with request.app.state.database.session() as session:
        subject = session.get(Subject, body.subject_id)
        if subject is None:
            raise APIError(404, "课程不存在", "SUBJECT_NOT_FOUND")
        if subject.status != "active":
            raise APIError(409, "课程当前不可用", "SUBJECT_INACTIVE")
        if session.scalar(select(KnowledgePoint.id).where(KnowledgePoint.subject_id == body.subject_id, KnowledgePoint.normalized_name == normalized_name)):
            raise APIError(409, "同一课程下知识点名称不能重复", "KNOWLEDGE_POINT_EXISTS")
        point = KnowledgePoint(
            id=str(uuid4()), subject_id=body.subject_id, chapter=body.chapter.strip(), name=" ".join(body.name.split()),
            normalized_name=normalized_name, description=body.description.strip(), status=body.status, created_by=auth.user.id,
        )
        session.add(point)
        add_log(session, auth.user.id, "knowledge_point.create", "knowledge_point", point.id, {"subjectId": point.subject_id}, client_ip(request))
        session.commit()
        payload = _point_payload(point)
        payload["editable"] = True
    return request.app.state.success(request, payload, "知识点创建成功")


@router.put("/knowledge-points/{point_id}")
def update_knowledge_point(point_id: str, body: KnowledgePointInput, request: Request, auth: AuthContext = Depends(require_teacher)):
    normalized_name = normalize_text(body.name)
    if not normalized_name:
        raise APIError(422, "知识点不能为空", "KNOWLEDGE_POINT_REQUIRED")
    with request.app.state.database.session() as session:
        point = _owned_point(session, point_id, auth.user.id)
        if body.subject_id != point.subject_id:
            raise APIError(422, "知识点所属课程不可修改", "KNOWLEDGE_POINT_SUBJECT_IMMUTABLE")
        duplicate = session.scalar(select(KnowledgePoint.id).where(KnowledgePoint.subject_id == point.subject_id, KnowledgePoint.normalized_name == normalized_name, KnowledgePoint.id != point.id))
        if duplicate:
            raise APIError(409, "同一课程下知识点名称不能重复", "KNOWLEDGE_POINT_EXISTS")
        point.chapter = body.chapter.strip()
        point.name = " ".join(body.name.split())
        point.normalized_name = normalized_name
        point.description = body.description.strip()
        point.status = body.status
        add_log(session, auth.user.id, "knowledge_point.update", "knowledge_point", point.id, {"status": point.status}, client_ip(request))
        session.commit()
        payload = _point_payload(point)
        payload["editable"] = True
    return request.app.state.success(request, payload)


@router.delete("/knowledge-points/{point_id}")
def delete_knowledge_point(point_id: str, request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        point = _owned_point(session, point_id, auth.user.id)
        if session.scalar(select(QuestionKnowledgePoint.id).where(QuestionKnowledgePoint.knowledge_point_id == point.id)):
            raise APIError(409, "知识点仍被题目引用", "KNOWLEDGE_POINT_IN_USE")
        session.delete(point)
        add_log(session, auth.user.id, "knowledge_point.delete", "knowledge_point", point.id, {}, client_ip(request))
        session.commit()
    return request.app.state.success(request, {})


@router.post("/knowledge-points/{point_id}/merge")
def merge_knowledge_point(point_id: str, body: KnowledgePointMergeInput, request: Request, auth: AuthContext = Depends(require_teacher)):
    if point_id == body.target_id:
        raise APIError(422, "合并目标必须不同", "KNOWLEDGE_POINT_MERGE_TARGET_INVALID")
    with request.app.state.database.session() as session:
        source = _owned_point(session, point_id, auth.user.id)
        target = _owned_point(session, body.target_id, auth.user.id)
        if source.subject_id != target.subject_id:
            raise APIError(422, "只能合并同一课程的知识点", "KNOWLEDGE_POINT_SUBJECT_MISMATCH")
        source_links = session.scalars(select(QuestionKnowledgePoint).where(QuestionKnowledgePoint.knowledge_point_id == source.id)).all()
        affected_question_ids = {link.question_id for link in source_links}
        affected_links = session.scalars(
            select(QuestionKnowledgePoint)
            .where(QuestionKnowledgePoint.question_id.in_(affected_question_ids))
            .order_by(QuestionKnowledgePoint.question_id, QuestionKnowledgePoint.id)
        ).all() if affected_question_ids else []
        target_links = {link.question_id: link for link in affected_links if link.knowledge_point_id == target.id}
        deleted_link_ids: set[str] = set()
        for link in source_links:
            existing = target_links.get(link.question_id)
            if existing:
                existing.weight += link.weight
                session.delete(link)
                deleted_link_ids.add(link.id)
            else:
                link.knowledge_point_id = target.id
        normalize_link_weights([link for link in affected_links if link.id not in deleted_link_ids])
        session.delete(source)
        session.flush()
        add_log(session, auth.user.id, "knowledge_point.merge", "knowledge_point", point_id, {"targetId": target.id, "questionCount": len(affected_question_ids)}, client_ip(request))
        session.commit()
    return request.app.state.success(request, {"id": body.target_id, "mergedId": point_id})


@router.get("/questions")
def questions(
    request: Request, subjectId: str | None = None, chapter: str | None = None, knowledgePointId: str | None = None,
    questionType: str | None = None, difficulty: str | None = None, source: str | None = None, keyword: str = "", search: str = "",
    page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=100), auth: AuthContext = Depends(require_teacher),
):
    with request.app.state.database.session() as session:
        filters = [or_(Question.created_by == auth.user.id, Question.created_by.is_(None))]
        if subjectId:
            filters.append(Question.subject_id == subjectId)
        if knowledgePointId:
            filters.append(QuestionKnowledgePoint.knowledge_point_id == knowledgePointId)
        query_text = keyword or search
        if query_text:
            filters.append(Question.text.like(f"%{query_text}%"))
        if chapter:
            filters.append(Question.chapter == chapter)
        if questionType:
            filters.append(Question.question_type == questionType)
        if difficulty:
            filters.append(Question.difficulty == difficulty)
        if source:
            filters.append(Question.source == source)
        base = select(Question).where(*filters)
        if knowledgePointId:
            base = base.join(QuestionKnowledgePoint, QuestionKnowledgePoint.question_id == Question.id)
        count_query = base.order_by(None).subquery()
        total = session.scalar(select(func.count(func.distinct(count_query.c.id)))) or 0
        records = session.scalars(
            base.options(selectinload(Question.knowledge_point_links).selectinload(QuestionKnowledgePoint.knowledge_point))
            .order_by(Question.created_at.desc(), Question.id)
            .offset((page - 1) * pageSize)
            .limit(pageSize)
        ).unique().all()
        items = [question_payload(item, auth.user.id) for item in records]
    return request.app.state.success(request, {"items": items, "total": total})


@router.post("/questions")
def create_catalog_question(body: dict, request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        question = create_question(body, session, auth.user.id)
        add_log(session, auth.user.id, "question.create", "question", question.id, {"subjectId": question.subject_id}, client_ip(request))
        session.commit()
        payload = question_payload(question, auth.user.id)
    return request.app.state.success(request, payload, "题目创建成功")


def _owned_question(session, question_id: str, actor_id: str) -> Question:
    question = session.get(Question, question_id)
    if question is None:
        raise APIError(404, "题目不存在", "QUESTION_NOT_FOUND")
    if question.created_by != actor_id:
        raise APIError(403, "共享题目只读，请先复制", "QUESTION_READ_ONLY")
    return question


@router.put("/questions/{question_id}")
def update_catalog_question(question_id: str, body: dict, request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        question = _owned_question(session, question_id, auth.user.id)
        prepared = prepare_question(body, session, auth.user.id)
        apply_prepared_question(question, prepared, session)
        add_log(session, auth.user.id, "question.update", "question", question.id, {}, client_ip(request))
        session.commit()
        payload = question_payload(question, auth.user.id)
    return request.app.state.success(request, payload)


@router.delete("/questions/{question_id}")
def delete_catalog_question(question_id: str, request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        question = _owned_question(session, question_id, auth.user.id)
        session.delete(question)
        add_log(session, auth.user.id, "question.delete", "question", question_id, {}, client_ip(request))
        session.commit()
    return request.app.state.success(request, {})


@router.post("/questions/{question_id}/copy")
def copy_catalog_question(question_id: str, request: Request, auth: AuthContext = Depends(require_teacher)):
    with request.app.state.database.session() as session:
        source = session.scalar(
            select(Question)
            .options(selectinload(Question.knowledge_point_links))
            .where(Question.id == question_id)
        )
        if source is None or source.created_by not in {None, auth.user.id}:
            raise APIError(404, "题目不存在", "QUESTION_NOT_FOUND")
        copied = Question(
            id=str(uuid4()), text=source.text, question_type=source.question_type, options=source.options,
            correct_answer=source.correct_answer, explanation=source.explanation, rubric=source.rubric,
            difficulty=source.difficulty, points=source.points, chapter=source.chapter, subject_id=source.subject_id,
            attachments=source.attachments, answer_word_limit=source.answer_word_limit, grading_mode=source.grading_mode,
            status="review_required", source="teacher-copy", created_by=auth.user.id, source_metadata=source.source_metadata,
            content_fingerprint=source.content_fingerprint,
            knowledge_point_links=[
                QuestionKnowledgePoint(id=str(uuid4()), knowledge_point_id=link.knowledge_point_id, weight=link.weight)
                for link in source.knowledge_point_links
            ],
        )
        session.add(copied)
        session.flush()
        normalize_question_link_weights(session, {copied.id})
        add_log(session, auth.user.id, "question.copy", "question", copied.id, {"sourceQuestionId": source.id}, client_ip(request))
        session.commit()
        payload = question_payload(copied, auth.user.id)
    return request.app.state.success(request, payload, "题目副本已创建")
