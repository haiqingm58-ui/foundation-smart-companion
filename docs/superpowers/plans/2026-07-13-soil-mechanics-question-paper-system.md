# Soil Mechanics Question Bank and Paper System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an independent soil mechanics question bank with many-to-many knowledge points, reusable paper assembly, formal online exams, student random practice, and Word/PDF exports while preserving all existing foundation-engineering records.

**Architecture:** Extend the current FastAPI, SQLAlchemy and Alembic backend with subject-scoped assessment entities and immutable publication snapshots. Keep normalized source content in a tracked corpus manifest, import it idempotently into SQLite/PostgreSQL-compatible tables, and expose focused teacher/student APIs consumed by lazily loaded React feature modules. Existing question, assignment, submission and practice endpoints remain as compatibility adapters during migration.

**Tech Stack:** React 19, React Router 7, Vite 6, FastAPI, Pydantic, SQLAlchemy 2, Alembic, python-docx, Pillow, ReportLab 4, pypdf, Vitest, Testing Library, Pytest, Playwright.

## Global Constraints

- Keep “基础工程” and “土力学” as separate subjects; never merge their chapters, knowledge points, questions, practice statistics, or grades.
- Preserve all existing questions, assignments, submissions, practice attempts, and learning progress during migration.
- Every active question must reference 1 to 3 knowledge points; each knowledge point may reference any number of questions.
- Soil mechanics starts with an approximately 50-item shared knowledge-point catalog; teachers may add subject-scoped points.
- Shared imported questions are read-only; teachers edit only copied or self-created questions.
- Supported question types are single choice, multiple choice, true/false, fill blank, short answer with a 20–2000 word limit, and calculation.
- Calculation questions are teacher-graded; AI may suggest but never finalize a calculation score.
- Random practice updates mastery and history but never formal course grades; published papers do update formal grades.
- Published assignments store immutable question snapshots and never expose answers or rubrics before submission.
- DOCX import must preserve source order, images, structured tables, formulas, source location, and an auditable review list.
- Word/PDF export must support question paper, answer sheet, and answer key variants with Chinese text, images, tables, formulas, and stable page breaks.
- Teacher operations are scoped to owned students/classes and audited; student access is scoped to published targets.
- All API errors use the existing `{success, message, code, requestId}` envelope.

---

### Task 1: Subject, Knowledge Point, and Question Schema

**Files:**
- Create: `server/migrations/versions/004_assessment_catalog.py`
- Modify: `server/application/models.py`
- Modify: `server/application/legacy_import.py`
- Test: `server/tests/test_migrations.py`

**Interfaces:**
- Produces: `Subject`, `KnowledgePoint`, `QuestionKnowledgePoint`, and subject-aware `Question` records.
- Produces: `Question.knowledge_points` relation and compatibility field `Question.knowledge_point` retained for one release.
- Consumes: existing Alembic revision `003_submission_feedback`.

- [ ] **Step 1: Write a failing migration test for preservation and backfill**

Add a test that upgrades the legacy fixture, creates the existing foundation subject, assigns every legacy question to it, creates knowledge-point rows from non-empty legacy strings, and preserves the old IDs:

```python
def test_assessment_catalog_migration_backfills_legacy_questions(tmp_path, database_url):
    from server.application.database import create_database
    from server.application.migrations import upgrade_database
    from server.application.models import Question, QuestionKnowledgePoint, Subject

    make_legacy_database(tmp_path / "legacy.db")
    upgrade_database(database_url)
    database = create_database(database_url)
    with database.session() as session:
        foundation = session.get(Subject, "foundation-engineering")
        question = session.get(Question, "exercise-old")
        links = session.scalars(
            select(QuestionKnowledgePoint).where(QuestionKnowledgePoint.question_id == question.id)
        ).all()
        assert foundation.title == "基础工程"
        assert question.subject_id == foundation.id
        assert len(links) == 1
```

- [ ] **Step 2: Run the migration test and confirm the missing-table failure**

Run: `server/.venv/bin/pytest server/tests/test_migrations.py::test_assessment_catalog_migration_backfills_legacy_questions -q`

Expected: FAIL because `Subject` and revision `004_assessment_catalog` do not exist.

- [ ] **Step 3: Add the normalized catalog models and migration**

Implement these exact tables and columns:

```python
class Subject(Base):
    __tablename__ = "subjects"
    id = mapped_column(String(64), primary_key=True)
    title = mapped_column(String(120), nullable=False, unique=True)
    slug = mapped_column(String(120), nullable=False, unique=True)
    status = mapped_column(String(24), nullable=False, default="active")
    sort_order = mapped_column(Integer, nullable=False, default=0)

class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"
    __table_args__ = (UniqueConstraint("subject_id", "normalized_name", name="uq_subject_knowledge_name"),)
    id = mapped_column(String(96), primary_key=True)
    subject_id = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter = mapped_column(String(160), nullable=False, index=True)
    name = mapped_column(String(160), nullable=False)
    normalized_name = mapped_column(String(160), nullable=False)
    description = mapped_column(Text, nullable=False, default="")
    status = mapped_column(String(24), nullable=False, default="active")
    sort_order = mapped_column(Integer, nullable=False, default=0)
    created_by = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

class QuestionKnowledgePoint(Base):
    __tablename__ = "question_knowledge_points"
    __table_args__ = (UniqueConstraint("question_id", "knowledge_point_id", name="uq_question_knowledge_point"),)
    id = mapped_column(String(96), primary_key=True)
    question_id = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    knowledge_point_id = mapped_column(ForeignKey("knowledge_points.id", ondelete="RESTRICT"), nullable=False, index=True)
    weight = mapped_column(Float, nullable=False, default=1.0)
```

Add to `questions`: `subject_id`, `attachments`, `answer_word_limit`, `grading_mode`, `status`, `source_metadata`, and `content_fingerprint`. Revision 004 must seed `foundation-engineering` and `soil-mechanics`, backfill existing questions into foundation engineering, create deterministic knowledge-point IDs, and leave the legacy `knowledge_point` string intact.

- [ ] **Step 4: Run migration and regression tests**

Run: `server/.venv/bin/pytest server/tests/test_migrations.py server/tests/test_teacher.py server/tests/test_student.py -q`

Expected: PASS with no deleted legacy rows.

- [ ] **Step 5: Commit the catalog schema**

```bash
git add server/application/models.py server/application/legacy_import.py server/migrations/versions/004_assessment_catalog.py server/tests/test_migrations.py
git commit -m "feat: add subject scoped assessment catalog"
```

### Task 2: Assessment Validation, Grading, and Mastery Services

**Files:**
- Create: `server/application/services/assessment_validation.py`
- Create: `server/application/services/grading.py`
- Create: `server/application/services/mastery.py`
- Create: `server/tests/test_assessment_services.py`
- Modify: `server/application/models.py`
- Create: `server/migrations/versions/005_subject_mastery.py`

**Interfaces:**
- Produces: `validate_question(payload: QuestionDraft) -> ValidatedQuestion`.
- Produces: `grade_objective(question_snapshot: dict, answer: object) -> GradeResult`.
- Produces: `apply_mastery(session, student_id: str, allocations: list[MasteryAllocation]) -> None`.
- Consumes: `Subject`, `KnowledgePoint`, and `QuestionKnowledgePoint` from Task 1.

- [ ] **Step 1: Write failing service tests for every supported type**

Cover single choice uniqueness, multiple-choice sets, boolean normalization, fill-blank synonyms, short-answer word limits, calculation manual grading, and the 1–3 knowledge-point rule:

```python
@pytest.mark.parametrize("knowledge_ids", [[], ["a", "b", "c", "d"]])
def test_question_requires_one_to_three_knowledge_points(knowledge_ids):
    with pytest.raises(AssessmentValidationError) as error:
        validate_question(valid_choice_payload(knowledgePointIds=knowledge_ids))
    assert error.value.code == "KNOWLEDGE_POINT_COUNT"

def test_calculation_never_receives_final_auto_score():
    result = grade_objective({"questionType": "计算题", "points": 20}, "steps")
    assert result.status == "pending_review"
    assert result.score is None
```

- [ ] **Step 2: Verify tests fail before implementation**

Run: `server/.venv/bin/pytest server/tests/test_assessment_services.py -q`

Expected: FAIL on missing modules.

- [ ] **Step 3: Implement typed validation and deterministic objective grading**

Use Pydantic discriminated models and normalize objective answers before comparison. Return this stable result shape:

```python
@dataclass(frozen=True)
class GradeResult:
    status: Literal["graded", "pending_review"]
    score: float | None
    max_score: float
    criteria_scores: dict[str, float]
    confidence: float
    feedback: str
```

Add `knowledge_point_id` and `subject_id` to `knowledge_mastery`, backfill from normalized legacy strings, and make `(student_id, knowledge_point_id)` unique. Multiple-point scores use configured normalized weights; absent weights are equal.

- [ ] **Step 4: Run service and legacy student tests**

Run: `server/.venv/bin/pytest server/tests/test_assessment_services.py server/tests/test_student.py -q`

Expected: PASS; random-practice grading still does not change `Student.average_score`.

- [ ] **Step 5: Commit validation and scoring**

```bash
git add server/application/services server/application/models.py server/migrations/versions/005_subject_mastery.py server/tests/test_assessment_services.py server/tests/test_student.py
git commit -m "feat: validate and grade subject assessments"
```

### Task 3: Teacher Knowledge Point and Question APIs

**Files:**
- Create: `server/application/api/teacher_catalog.py`
- Create: `server/application/schemas/assessment.py`
- Create: `server/application/services/question_service.py`
- Modify: `server/application/main.py`
- Modify: `server/application/api/teacher.py`
- Modify: `server/application/schemas/teacher.py`
- Modify: `src/api/teacher.js`
- Test: `server/tests/test_teacher_catalog.py`
- Test: `server/tests/test_teacher.py`

**Interfaces:**
- Produces: `GET /api/teacher/subjects`.
- Produces: `GET|POST|PUT /api/teacher/knowledge-points` and `POST /api/teacher/knowledge-points/{id}/merge`.
- Produces: subject-aware `GET|POST|PUT|DELETE /api/teacher/questions` and `POST /api/teacher/questions/{id}/copy`.
- Consumes: `validate_question` and ownership helpers from existing teacher dependencies.

- [ ] **Step 1: Write failing API tests for catalog permissions and question links**

Assert filtering by subject/chapter, question counts, unique normalized names, 1–3 links, shared-question read-only behavior, teacher copy behavior, merge rewiring, and operation logs:

```python
def test_teacher_copies_shared_question_before_editing(teacher_context):
    client, database, _ = teacher_context
    shared_id = seed_shared_soil_question(database)
    assert client.put(f"/api/teacher/questions/{shared_id}", json=edit_payload(), headers=csrf()).status_code == 403
    copied = client.post(f"/api/teacher/questions/{shared_id}/copy", headers=csrf())
    assert copied.status_code == 200
    assert copied.json()["data"]["createdBy"] == "teacher-user-1"
```

- [ ] **Step 2: Run the catalog API tests and confirm 404 failures**

Run: `server/.venv/bin/pytest server/tests/test_teacher_catalog.py -q`

Expected: FAIL because the catalog router is absent.

- [ ] **Step 3: Implement the router and keep old request compatibility**

Mount `teacher_catalog.router`. Accept `knowledgePointIds` as canonical input; when an old request contains `knowledgePoint`, resolve or create a teacher-owned point in `foundation-engineering`, then persist the relation. Serialize every question as:

```json
{
  "id": "question-id",
  "subjectId": "soil-mechanics",
  "chapter": "第二章 土的渗透性",
  "knowledgePoints": [{"id": "soil-permeability", "name": "达西定律", "weight": 1.0}],
  "questionType": "单项选择题",
  "attachments": [],
  "editable": false
}
```

Reject deletion of a referenced knowledge point with `KNOWLEDGE_POINT_IN_USE`; merge it transactionally and log `knowledge_point.merge`.

- [ ] **Step 4: Run teacher API regression tests**

Run: `server/.venv/bin/pytest server/tests/test_teacher_catalog.py server/tests/test_teacher.py -q`

Expected: PASS for both new and old question payloads.

- [ ] **Step 5: Commit teacher catalog APIs**

```bash
git add server/application/api server/application/schemas server/application/services/question_service.py server/application/main.py src/api/teacher.js server/tests/test_teacher_catalog.py server/tests/test_teacher.py
git commit -m "feat: add teacher knowledge point and question APIs"
```

### Task 4: Soil Mechanics DOCX Corpus Parser and Curated Catalog

**Files:**
- Create: `server/application/importers/__init__.py`
- Create: `server/application/importers/docx_question_bank.py`
- Create: `server/application/importers/question_normalization.py`
- Create: `server/application/importers/report.py`
- Create: `content/question-banks/soil-mechanics/knowledge-points.json`
- Create: `content/question-banks/soil-mechanics/manifest.json`
- Create: `content/question-banks/soil-mechanics/import-report.json`
- Create: `public/question-assets/soil-mechanics/`
- Modify: `.gitignore`
- Test: `server/tests/test_docx_question_bank.py`

**Interfaces:**
- Produces: `parse_question_bank(source_dir: Path, output_dir: Path) -> ImportReport`.
- Produces: deterministic normalized manifest schema version `1` and SHA-256 image assets.
- Consumes: the four supplied DOCX files and `说明.txt` from the user archive.

- [ ] **Step 1: Preserve the supplied source outside Git and create a synthetic parser fixture test**

Add `.source-question-banks/` to `.gitignore`, copy the extracted source files into `.source-question-banks/soil-mechanics/`, and generate a miniature DOCX in the test containing a heading, single choice, answer, table, and image. Assert that paragraphs, relationships, tables, inline drawings, and source positions survive normalization.

```python
def test_parser_preserves_question_media_table_and_source_location(tmp_path):
    source = build_docx_fixture(tmp_path)
    report = parse_question_bank(source.parent, tmp_path / "out")
    item = load_manifest(tmp_path / "out")["questions"][0]
    assert item["correctAnswer"] == ["A"]
    assert item["attachments"][0]["kind"] == "image"
    assert item["attachments"][1]["kind"] == "table"
    assert item["sourceMetadata"]["file"] == source.name
    assert report.unrecognized == 0
```

- [ ] **Step 2: Run the parser test and confirm failure**

Run: `server/.venv/bin/pytest server/tests/test_docx_question_bank.py -q`

Expected: FAIL because the importer package is missing.

- [ ] **Step 3: Implement ordered DOCX parsing and deterministic normalization**

Walk each document XML body in order, resolving paragraphs, tables, drawings and Office Math objects. Normalize type names, boolean answers, option labels, whitespace, full-width punctuation, and content fingerprints. Store tables as `{kind:"table", rows:[[...]]}`, formulas as OMML-derived text plus source XML, and images as `{kind:"image", src:"/foundation-smart-companion/question-assets/soil-mechanics/<sha>.<ext>", alt:"题目附图"}`. Deduplicate by normalized stem plus options, preferring the richest answer/attachment record.

- [ ] **Step 4: Add the curated 50-point catalog and parse the real four-document corpus**

`knowledge-points.json` must contain stable IDs, chapters, names, descriptions, status, and sort order for approximately 50 teaching points. Run:

`server/.venv/bin/python -m server.application.importers.docx_question_bank --source .source-question-banks/soil-mechanics --output content/question-banks/soil-mechanics --public-assets public/question-assets/soil-mechanics`

Expected: all four DOCX files appear in `import-report.json`; `sourceQuestions >= 1000`; `imageCount >= 300`; `tableCount >= 8`; every normalized question is either valid or listed in `reviewItems` with file and position.

- [ ] **Step 5: Validate generated data and commit only normalized outputs**

Run: `server/.venv/bin/pytest server/tests/test_docx_question_bank.py -q`

Run: `server/.venv/bin/python -m server.application.importers.report content/question-banks/soil-mechanics/manifest.json content/question-banks/soil-mechanics/import-report.json`

Expected: PASS and exit code 0; no source DOCX or ZIP is staged.

```bash
git add .gitignore server/application/importers server/tests/test_docx_question_bank.py content/question-banks/soil-mechanics public/question-assets/soil-mechanics
git commit -m "feat: normalize soil mechanics question corpus"
```

### Task 5: Idempotent Corpus Import Command

**Files:**
- Create: `server/application/services/question_bank_import.py`
- Modify: `server/manage.py`
- Modify: `scripts/deploy-platform-jdcloud.sh`
- Test: `server/tests/test_question_bank_import.py`
- Test: `scripts/tests/deploy-utils.test.sh`

**Interfaces:**
- Produces: `import_question_bank(database, manifest_path: Path, actor_id: str | None) -> ImportSummary`.
- Produces: `python -m server.manage import-question-bank <manifest>`.
- Consumes: manifest schema version `1` from Task 4.

- [ ] **Step 1: Write failing idempotency and rollback tests**

Test first import, unchanged second import, richer-record update, invalid link rollback, shared ownership, and import operation logs:

```python
def test_manifest_import_is_idempotent(database, soil_manifest):
    first = import_question_bank(database, soil_manifest, None)
    second = import_question_bank(database, soil_manifest, None)
    assert first.created > 0
    assert second.created == 0
    assert second.unchanged == first.created
```

- [ ] **Step 2: Run tests and confirm missing service failure**

Run: `server/.venv/bin/pytest server/tests/test_question_bank_import.py -q`

Expected: FAIL on missing import service.

- [ ] **Step 3: Implement transactional upsert and CLI**

Validate the whole manifest before opening the write transaction. Upsert subjects and knowledge points by stable ID, questions by source ID/fingerprint, links by composite key, and set imported questions to `source="soil-mechanics-bank"`, `status="active"`, `created_by=None`. Print JSON:

```json
{"created": 1044, "updated": 0, "unchanged": 0, "review": 0, "subjectId": "soil-mechanics"}
```

- [ ] **Step 4: Add deployment migration and corpus import before symlink switch**

After `server.manage migrate`, execute:

```bash
"${SOURCE_RELEASE}/server/.venv/bin/python" -m server.manage import-question-bank "${SOURCE_RELEASE}/content/question-banks/soil-mechanics/manifest.json"
```

Update the shell test to assert migration precedes import and import precedes service restart.

- [ ] **Step 5: Run import, deployment, and migration tests; commit**

Run: `server/.venv/bin/pytest server/tests/test_question_bank_import.py server/tests/test_migrations.py -q`

Run: `npm run test:deploy`

Expected: PASS.

```bash
git add server/application/services/question_bank_import.py server/manage.py scripts/deploy-platform-jdcloud.sh server/tests/test_question_bank_import.py scripts/tests/deploy-utils.test.sh
git commit -m "feat: import shared question banks idempotently"
```

### Task 6: Reusable Papers, Assembly, Publication Snapshots

**Files:**
- Create: `server/migrations/versions/006_papers_and_snapshots.py`
- Modify: `server/application/models.py`
- Create: `server/application/schemas/paper.py`
- Create: `server/application/services/paper_assembly.py`
- Create: `server/application/api/teacher_papers.py`
- Modify: `server/application/main.py`
- Test: `server/tests/test_teacher_papers.py`

**Interfaces:**
- Produces: `Paper`, `PaperQuestion`, and `Assignment.paper_id`.
- Produces: `assemble_paper(session, Blueprint) -> AssemblyPreview` with shortages instead of silent fallback.
- Produces: `GET|POST|PUT|DELETE /api/teacher/papers`, `POST /api/teacher/papers/generate-preview`, `POST /api/teacher/papers/{id}/publish`.

- [ ] **Step 1: Write failing paper assembly and publication tests**

Cover manual order/sections/points, automatic subject/chapter/knowledge/type/difficulty quotas, deterministic no-duplicate selection with seed, explicit shortages, ownership, copying, and immutable snapshot publication:

```python
def test_published_assignment_keeps_question_snapshot(teacher_context):
    assignment_id = publish_paper(teacher_context)
    edit_source_question(teacher_context, text="修改后的题干")
    detail = get_assignment(teacher_context, assignment_id)
    assert detail["questions"][0]["snapshot"]["text"] != "修改后的题干"
```

- [ ] **Step 2: Run tests and confirm missing models/endpoints**

Run: `server/.venv/bin/pytest server/tests/test_teacher_papers.py -q`

Expected: FAIL because paper tables are absent.

- [ ] **Step 3: Implement paper models and blueprint assembly**

Create `papers(id, subject_id, title, description, duration_minutes, total_points, status, version, created_by, created_at, updated_at)` and `paper_questions(id, paper_id, question_id, section_title, sequence, points)`. Add `paper_id`, `duration_minutes`, and `show_answers_mode` to assignments; add `question_snapshot JSON` to assignment questions. A blueprint contains rows of `{chapterIds, knowledgePointIds, questionTypes, difficulties, count, pointsEach}` and returns `{questions, coverage, typeDistribution, difficultyDistribution, duplicateRisk, shortages}`.

- [ ] **Step 4: Implement publish-time authorization and snapshots**

Verify every target belongs to the teacher, reject a paper with shortages or zero questions, serialize each question without losing attachments/rubric, and store answers only in server-side snapshots. Log `paper.publish` with paper, assignment, and target counts.

- [ ] **Step 5: Run tests and commit**

Run: `server/.venv/bin/pytest server/tests/test_teacher_papers.py server/tests/test_teacher.py -q`

Expected: PASS.

```bash
git add server/application/models.py server/application/schemas/paper.py server/application/services/paper_assembly.py server/application/api/teacher_papers.py server/application/main.py server/migrations/versions/006_papers_and_snapshots.py server/tests/test_teacher_papers.py
git commit -m "feat: add reusable papers and immutable publication"
```

### Task 7: Student Random Practice and Formal Exam APIs

**Files:**
- Create: `server/migrations/versions/007_practice_sessions.py`
- Modify: `server/application/models.py`
- Create: `server/application/schemas/practice.py`
- Create: `server/application/services/practice_selection.py`
- Create: `server/application/api/student_assessment.py`
- Modify: `server/application/main.py`
- Modify: `server/application/api/student.py`
- Modify: `src/api/student.js`
- Test: `server/tests/test_student_assessment.py`

**Interfaces:**
- Produces: `PracticeSession`, `PracticeSessionQuestion`, resumable answers, and immutable random-practice snapshots.
- Produces: `POST /api/student/practice-sessions`, `GET /api/student/practice-sessions/{id}`, `PUT .../answers/{questionId}`, `POST .../submit`.
- Produces: `GET /api/student/papers`, `POST /api/student/assignments/{id}/start`, `PUT /api/student/submissions/{id}/answers/{questionId}`, `POST .../submit`, `GET .../result`.

- [ ] **Step 1: Write failing random selection and formal exam tests**

Test subject isolation, chapter mode, 1–3 knowledge-point mode, 5/10/20/custom counts, no duplicates, recent-correct avoidance, shortage errors, resume, autosave, target authorization, deadline, countdown metadata, answer secrecy, objective auto-grading, pending manual review, and grade separation.

```python
def test_random_practice_updates_mastery_not_formal_average(student_context):
    session = create_practice(student_context, subject="soil-mechanics", count=5)
    submit_practice(student_context, session)
    dashboard = student_context[0].get("/api/student/dashboard").json()["data"]
    assert dashboard["student"]["averageScore"] == 0
    assert get_mastery_total(student_context[1]) > 0
```

- [ ] **Step 2: Run tests and confirm missing API failures**

Run: `server/.venv/bin/pytest server/tests/test_student_assessment.py -q`

Expected: FAIL with 404 for the new routes.

- [ ] **Step 3: Implement practice sessions and secure snapshots**

Create `practice_sessions` and `practice_session_questions` with selection criteria, status, sequence, sanitized snapshot, answer, score and timestamps. The GET response removes `correctAnswer`, `rubric`, and `explanation` until submission. Selection samples without replacement and ranks unseen or recently incorrect items ahead of recently correct items.

- [ ] **Step 4: Implement formal exam start, autosave, submit, and result**

Create one `in_progress` submission per permitted attempt, autosave per-question JSON answers, reject post-deadline writes, auto-grade objective items from server snapshots, leave subjective/calculation items pending, and reveal result fields according to `show_answers_mode`. Keep the current exercise-attempt route as a compatibility adapter to the grading/mastery service.

- [ ] **Step 5: Run student, teacher, and security tests; commit**

Run: `server/.venv/bin/pytest server/tests/test_student_assessment.py server/tests/test_student.py server/tests/test_teacher_papers.py -q`

Expected: PASS.

```bash
git add server/application/models.py server/application/schemas/practice.py server/application/services/practice_selection.py server/application/api/student_assessment.py server/application/api/student.py server/application/main.py server/migrations/versions/007_practice_sessions.py src/api/student.js server/tests/test_student_assessment.py
git commit -m "feat: add random practice and formal exam APIs"
```

### Task 8: Word and PDF Paper Export

**Files:**
- Modify: `server/requirements.txt`
- Create: `server/application/services/paper_export.py`
- Modify: `server/application/api/teacher_papers.py`
- Create: `server/tests/test_paper_export.py`
- Create: `server/tests/fixtures/export_expected.json`

**Interfaces:**
- Produces: `render_paper(paper, variant: Literal["questions","answer-sheet","answers"], format: Literal["docx","pdf"], options: ExportOptions) -> bytes`.
- Produces: `GET /api/teacher/papers/{id}/export?format=docx|pdf&variant=questions|answer-sheet|answers`.
- Consumes: immutable paper/question serialization from Task 6.

- [ ] **Step 1: Write failing structural export tests**

Build a paper containing Chinese text, a choice list, short answer, calculation formula, image, and table. Assert DOCX relationships/media/tables/headings and PDF pages/text are present; assert answer keys do not appear in question variants.

```python
def test_question_export_never_contains_answer_key(sample_paper):
    docx_bytes = render_paper(sample_paper, "questions", "docx", ExportOptions())
    text = extract_docx_text(docx_bytes)
    assert "参考答案" not in text
    assert "正确答案：A" not in text
```

- [ ] **Step 2: Add ReportLab and verify tests fail on missing renderer**

Add `reportlab>=4.2,<5` to `server/requirements.txt`, install it in `server/.venv`, then run:

`server/.venv/bin/pytest server/tests/test_paper_export.py -q`

Expected: FAIL because `paper_export` is missing.

- [ ] **Step 3: Implement DOCX and PDF renderers**

Use python-docx for Word and ReportLab with `UnicodeCIDFont("STSong-Light")` for Chinese PDF text. Keep each stem plus its attachments in one block when space allows; repeat table headers; include student information fields; support title, subject, duration, total score, section headings, per-question points, and optional answer content.

- [ ] **Step 4: Add API streaming and audit logging**

Return `application/vnd.openxmlformats-officedocument.wordprocessingml.document` or `application/pdf` with RFC 5987 filenames. Verify teacher ownership and log `paper.export` without mutating paper/publication state.

- [ ] **Step 5: Render sample files and visually inspect every page**

Run: `server/.venv/bin/pytest server/tests/test_paper_export.py -q`

Generate all six variants into `/tmp/foundation-paper-export/`. Render DOCX via the bundled documents `render_docx.py` and PDF via Poppler, inspect the PNG pages for Chinese glyphs, clipped formulas, split tables, missing images, and blank pages, then fix until clean.

- [ ] **Step 6: Commit exports**

```bash
git add server/requirements.txt server/application/services/paper_export.py server/application/api/teacher_papers.py server/tests/test_paper_export.py server/tests/fixtures/export_expected.json
git commit -m "feat: export papers to Word and PDF"
```

### Task 9: Teacher Knowledge Point and Dynamic Question Editor UI

**Files:**
- Create: `src/pages/teacher/assessment/TeacherAssessmentShell.jsx`
- Create: `src/pages/teacher/assessment/KnowledgePointLibrary.jsx`
- Create: `src/pages/teacher/assessment/QuestionBank.jsx`
- Create: `src/pages/teacher/assessment/QuestionEditor.jsx`
- Create: `src/pages/teacher/assessment/KnowledgePointPicker.jsx`
- Create: `src/pages/teacher/assessment/AttachmentPreview.jsx`
- Create: `src/pages/teacher/assessment/assessment.css`
- Modify: `src/pages/teacher/TeacherApp.jsx`
- Modify: `src/pages/teacher/QuestionImportModal.jsx`
- Test: `src/pages/teacher/assessment/TeacherAssessment.test.jsx`

**Interfaces:**
- Produces: teacher navigation entries “知识点库” and “题库管理”.
- Consumes: subject/catalog/question APIs from Task 3.

- [ ] **Step 1: Write failing UI tests for the full teacher edit flow**

Mock APIs and test subject/chapter filters, finite KP counts, related-question drawer, searchable 1–3 picker, fourth-selection rejection, dynamic type fields, word-limit bounds, calculation manual badge, copy-shared action, validation errors, and empty/loading/error states.

```jsx
it("limits a question to three knowledge points", async () => {
  render(<QuestionEditor initialValue={draft} />);
  await selectKnowledgePoints(["kp-1", "kp-2", "kp-3"]);
  expect(screen.getByText("已选 3/3")).toBeVisible();
  await user.click(screen.getByRole("option", { name: "第四个知识点" }));
  expect(screen.getByText("每道题最多关联 3 个知识点")).toBeVisible();
});
```

- [ ] **Step 2: Run UI tests and confirm missing component failures**

Run: `npm test -- src/pages/teacher/assessment/TeacherAssessment.test.jsx`

Expected: FAIL on missing modules.

- [ ] **Step 3: Implement compact operational layouts and dynamic editor**

Use a restrained full-width table/list layout, a right-side editor drawer, Lucide icons with tooltips, 6px card radii maximum, stable control dimensions, visible `:focus-visible`, and no nested cards. Render type-specific controls exactly from the selected question type; preserve structured image/table attachments without raw HTML.

- [ ] **Step 4: Integrate with existing teacher shell and improved import flow**

Keep existing dashboard/student/resource features. Replace the old question pane with `TeacherAssessmentShell`, retain XLSX/CSV import, and add the shared DOCX corpus status/report view. Do not expose source file paths to students.

- [ ] **Step 5: Run teacher frontend regression tests and commit**

Run: `npm test -- src/pages/teacher/assessment/TeacherAssessment.test.jsx src/pages/teacher/TeacherApp.test.jsx`

Expected: PASS.

```bash
git add src/pages/teacher/assessment src/pages/teacher/TeacherApp.jsx src/pages/teacher/QuestionImportModal.jsx
git commit -m "feat: add teacher knowledge and question workbench"
```

### Task 10: Teacher Paper Builder, Publication, Grading, and Export UI

**Files:**
- Create: `src/pages/teacher/assessment/PaperList.jsx`
- Create: `src/pages/teacher/assessment/PaperBuilder.jsx`
- Create: `src/pages/teacher/assessment/BlueprintBuilder.jsx`
- Create: `src/pages/teacher/assessment/PublicationDialog.jsx`
- Create: `src/pages/teacher/assessment/SubmissionGrading.jsx`
- Create: `src/pages/teacher/assessment/ExportMenu.jsx`
- Modify: `src/api/teacher.js`
- Modify: `src/pages/teacher/assessment/TeacherAssessmentShell.jsx`
- Test: `src/pages/teacher/assessment/PaperWorkflow.test.jsx`

**Interfaces:**
- Produces: teacher navigation entries “组卷中心”, “考试与作业”, and “批改与成绩分析”.
- Consumes: paper/publication/export APIs from Tasks 6 and 8.

- [ ] **Step 1: Write failing end-to-end component tests for paper work**

Test manual add/reorder/section/points, blueprint shortage display, coverage metrics, save/copy/version, target selection limited to bound students/classes, publication snapshot confirmation, grading score override, and six export actions.

```jsx
it("shows shortages without silently relaxing the blueprint", async () => {
  mockGeneratePreview({ questions: [], shortages: [{ label: "多选题/渗透", missing: 3 }] });
  render(<PaperBuilder paper={draftPaper} />);
  await user.click(screen.getByRole("button", { name: "生成预览" }));
  expect(screen.getByText("多选题/渗透还缺 3 题")).toBeVisible();
  expect(screen.getByRole("button", { name: "发布试卷" })).toBeDisabled();
});
```

- [ ] **Step 2: Run tests and confirm missing component failures**

Run: `npm test -- src/pages/teacher/assessment/PaperWorkflow.test.jsx`

Expected: FAIL on missing modules.

- [ ] **Step 3: Implement manual and blueprint paper builder**

Use tabs for manual/automatic mode, searchable question table for selection, stable drag/reorder buttons with arrow icons, editable sections and points, and a persistent summary band for total score, coverage, type mix, difficulty mix, duplicate risk, and shortages. Disable publication whenever validation or shortage errors exist.

- [ ] **Step 4: Implement publication, grading, and downloads**

Publication uses date/time/duration/toggle controls and bound-target selection. Grading shows snapshot, student answer, rubric, auto-score confidence, calculation manual status, per-step scores, feedback and final total. Export uses one menu with Word/PDF and question/answer-sheet/answer variants.

- [ ] **Step 5: Run frontend tests and commit**

Run: `npm test -- src/pages/teacher/assessment/PaperWorkflow.test.jsx src/pages/teacher/assessment/TeacherAssessment.test.jsx src/pages/teacher/TeacherApp.test.jsx`

Expected: PASS.

```bash
git add src/pages/teacher/assessment src/api/teacher.js
git commit -m "feat: add teacher paper and grading workflows"
```

### Task 11: Student Subject Practice and My Papers UI

**Files:**
- Create: `src/pages/student/assessment/AssessmentHome.jsx`
- Create: `src/pages/student/assessment/RandomPracticeSetup.jsx`
- Create: `src/pages/student/assessment/PracticeSession.jsx`
- Create: `src/pages/student/assessment/MyPapers.jsx`
- Create: `src/pages/student/assessment/ExamSession.jsx`
- Create: `src/pages/student/assessment/AssessmentResult.jsx`
- Create: `src/pages/student/assessment/assessment.css`
- Modify: `src/App.jsx`
- Modify: `src/api/student.js`
- Test: `src/pages/student/assessment/StudentAssessment.test.jsx`

**Interfaces:**
- Produces: student “练习中心” subject switch and “我的试卷” workflow.
- Consumes: practice/formal exam APIs from Task 7.

- [ ] **Step 1: Write failing student journey tests**

Test subject isolation, chapter vs knowledge-point selection, 1–3 picker, 5/10/20/custom counts, available-count validation, refresh resume, local retry draft, autosave status, pending/in-progress/submitted/graded filters, countdown, confirm submit, hidden answers before submit, pending manual review, and mastery-only random results.

```jsx
it("resumes an unfinished random session without drawing new questions", async () => {
  mockSession({ id: "practice-1", status: "in_progress", questions: snapshots });
  render(<PracticeSession sessionId="practice-1" />);
  expect(await screen.findByText(snapshots[0].text)).toBeVisible();
  expect(createPracticeSession).not.toHaveBeenCalled();
});
```

- [ ] **Step 2: Run tests and confirm missing component failures**

Run: `npm test -- src/pages/student/assessment/StudentAssessment.test.jsx`

Expected: FAIL on missing modules.

- [ ] **Step 3: Implement random practice with resilient autosave**

Render a subject segmented control, chapter/knowledge-point mode tabs, type/difficulty menus and count stepper. Save the current answer in localStorage before each API write, show “已保存/待重试”, replay failed writes on reconnect, and clear the local draft after server acknowledgment. Use stable question dimensions and structured attachment rendering.

- [ ] **Step 4: Implement My Papers and formal exam session**

Show four status tabs with deadlines and teacher names. Start only authorized papers, persist the active submission ID, autosave answers, display a server-derived countdown, require submit confirmation, and render result fields only when returned by the API. Never derive or bundle answer keys client-side.

- [ ] **Step 5: Integrate into the existing student app and commit**

Replace the static exercise bank path in `src/App.jsx` with the new assessment modules while retaining the current overview, textbook, graph, QA, cases, resources, and report pages.

Run: `npm test -- src/pages/student/assessment/StudentAssessment.test.jsx src/App.test.jsx`

Expected: PASS.

```bash
git add src/pages/student/assessment src/App.jsx src/api/student.js
git commit -m "feat: add student practice and paper experiences"
```

### Task 12: Full Verification, Production Deployment, and GitHub Sync

**Files:**
- Create: `tests/e2e/assessment.spec.mjs`
- Modify: `playwright.config.mjs`
- Modify: `README.md`
- Modify: `scripts/deploy-platform-jdcloud.sh`
- Modify: `package.json`

**Interfaces:**
- Produces: automated teacher-to-student acceptance coverage and production import verification.
- Consumes: every previous task.

- [ ] **Step 1: Add failing Playwright acceptance coverage**

Automate teacher login, soil subject selection, question filtering, paper creation/publication, student login, assigned-paper start/autosave/submit, teacher grading, student result viewing, random practice creation/resume, and one DOCX/PDF download. Assert no uncaught browser errors and no failed `/api/` responses.

- [ ] **Step 2: Run the new E2E test against a local full stack**

Run migrations and corpus import in a temporary database, start FastAPI and Vite preview, then run:

`npx playwright test tests/e2e/assessment.spec.mjs`

Expected before fixes: FAIL at the first uncovered integration defect. Fix each defect with a regression assertion until PASS.

- [ ] **Step 3: Run the complete quality gate**

Run: `npm run check`

Run: `npx playwright test tests/e2e/assessment.spec.mjs`

Run: `git diff --check`

Expected: all commands PASS; build output contains separate lazy teacher/student chunks; no source DOCX/ZIP, secrets, local database, or upload directory is tracked.

- [ ] **Step 4: Verify generated corpus counts locally**

Run the import twice against a clean temporary database. Record exact subjects, knowledge points, questions, duplicates, images, tables, review items, and unchanged second-import counts in `README.md`. Verify every active imported question has 1–3 valid knowledge-point links.

- [ ] **Step 5: Deploy to JDCloud and verify the public site**

Run: `npm run deploy:jdcloud`

Expected: the deploy script builds/tests, migrates, imports the corpus, atomically switches releases, restarts the API, reloads Nginx, and passes health/login checks at `http://111.228.5.243/foundation-smart-companion/`.

Use browser verification for desktop and mobile: teacher question bank, paper builder, student random practice, My Papers, submission, grading, exports, refresh/resume, and logout. Confirm API responses contain no correct answers before submission.

- [ ] **Step 6: Verify production database counts and idempotency**

Over SSH, run `server.manage import-question-bank` once more and require `created=0`. Query and record production counts by subject plus the number of active questions missing 1–3 links; the latter must be zero. Sample at least one item from each source DOCX and verify its text, answer, attachment, and source metadata.

- [ ] **Step 7: Commit acceptance/docs, push GitHub, and verify remote**

```bash
git add tests/e2e/assessment.spec.mjs playwright.config.mjs README.md scripts/deploy-platform-jdcloud.sh package.json
git commit -m "test: verify assessment workflows end to end"
git push origin codex/soil-mechanics-assessment
```

Open or update the pull request, verify GitHub checks, and compare the remote branch SHA with local `git rev-parse HEAD`. Only then merge/push to the production branch according to the repository’s existing deployment convention.

---

## Completion Evidence

- Alembic upgrades a legacy database without row loss and a second upgrade is a no-op.
- Soil mechanics appears as an independent subject with approximately 50 knowledge points and the exact imported/review counts recorded from the supplied corpus.
- Every active question has 1–3 knowledge-point links; reverse knowledge-point question counts are correct.
- Teachers can create/copy/filter/edit questions, manually or automatically assemble reusable papers, publish snapshots, grade subjective/calculation responses, and download six export variants.
- Students can create resumable random practice by chapter or knowledge point and complete teacher-assigned papers with autosave and correct answer visibility rules.
- Random practice changes mastery only; formal paper completion changes the formal course result only after grading rules are satisfied.
- DOCX/PDF render inspection passes for Chinese, images, tables, formulas and page breaks.
- Backend, frontend, deployment, E2E, build, public production, and GitHub SHA checks all pass.
