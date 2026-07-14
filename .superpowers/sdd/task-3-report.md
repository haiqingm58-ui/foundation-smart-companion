# Task 3 Report

## Status

Complete.

## Interfaces

- Added teacher subject, knowledge-point CRUD/merge, and subject-aware question CRUD/copy APIs.
- Question writes use `subjectId` and `knowledgePointIds`, call `validate_question`, and serialize linked knowledge points with weights and editability.
- Legacy `knowledgePoint` payloads adapt only to `foundation-engineering` and create or resolve one matching link.
- Added corresponding teacher client methods.

## Permissions

- Shared questions (`created_by=None`) are read-only; copying creates a teacher-owned editable question.
- Knowledge-point update, delete, and merge require teacher ownership.
- Referenced points cannot be deleted; merge requires same-subject owned points and records `knowledge_point.merge`.

## Tests

- `server/.venv/bin/pytest server/tests/test_teacher_catalog.py server/tests/test_teacher.py -q`
- Result: `13 passed`.
- `server/.venv/bin/python -m compileall -q server/application`
- `git diff --check`

## SHA

`cfa0bba9a6053d9fad07941d09d11b78a3edc438`

## Concerns

No known functional blockers. The focused catalog and teacher regression suites passed; the full server suite was not run for this task.

## Fix Review

### Status

All Critical and Important findings, plus the meaningful Minor gaps, are addressed.

### Fixes

- Copy now permits only shared questions or the requesting teacher's own question; another teacher's private question returns `404`.
- Question and knowledge-point listings support complete filters, bounded pagination, correct totals, grouped counts, and eager question-link loading.
- Copies always begin as `review_required`; canonical editing validates and activates valid copies.
- Canonical validation trims required catalog strings before constraints, accepts only `基础`/`中等`/`困难`, and enforces structured rubric and attachment objects while retaining image/table/formula metadata compatibility.
- Legacy imports explicitly reject a missing knowledge point without creating a zero-link active question.
- Knowledge-point merge bulk-loads affected links, deduplicates and normalizes in memory, and rolls back cleanly when audit logging fails.

### Exact Outputs

```text
server/.venv/bin/pytest server/tests -q
101 passed in 11.64s

npm test -- --run
Test Files  6 passed (6)
Tests  16 passed (16)

npm run build
vite build: built successfully
Prerendered 8 routes with SEO metadata.
```

`server/.venv/bin/python -m compileall -q server/application` and `git diff --check` completed successfully.

### SHA

Implementation commit: `c6518ea9c142232b5f9eeb18f1e83dde893803f7`

### Concerns

No known functional blockers.

## Frontend Integration Review

### Status

Complete. Canonical teacher question edits preserve their API subject and all linked knowledge points; shared rows are copy-only and copies open as editable `review_required` records.

### Interfaces and Permissions

- Existing canonical questions submit `subjectId` and `knowledgePointIds` only. The legacy singular `knowledgePoint` field remains available only for the explicitly labelled new foundation-engineering flow.
- Question list display joins canonical knowledge-point names without changing the current layout.
- `editable` controls edit/delete visibility. Read-only non-textbook shared questions offer `teacherApi.copyQuestion`; the returned teacher-owned copy is refreshed and selected for editing.

### Tests

Added TeacherApp component coverage for canonical multi-knowledge-point updates, read-only shared copy controls and review-required editable copies, and teacher-owned edit/delete controls.

### Exact Outputs

```text
npm test -- src/pages/teacher/TeacherApp.test.jsx
Test Files  1 passed (1)
Tests  7 passed (7)

server/.venv/bin/pytest server/tests/test_teacher_catalog.py server/tests/test_teacher.py -q
24 passed in 3.97s

npm test -- --run
Test Files  6 passed (6)
Tests  18 passed (18)

npm run build
vite build: built successfully
Prerendered 8 routes with SEO metadata.
```

`git diff --check` completed successfully before the implementation commit.

### SHA

Implementation commit: `ec293a957bf778d7219d8cb5a53c9d5238ae0e81`

### Concerns

No known functional blockers. Task 9 remains responsible for replacing the read-only canonical knowledge-point display with a full multi-select editor.

## Typed Answer UI Review

### Status

Complete. Every read-only shared question, including textbook rows, is copy-only. Canonical edits now preserve the boolean, multiple-choice, and fill-blank answer shapes required by the API.

### Interfaces and Permissions

- `editable` is the sole client-side decision for edit/delete versus copy. The server continues to omit private questions outside the teacher's visibility scope.
- Judgment answers use an explicit true/false control and submit a boolean. Multiple-choice and fill-blank answers use labelled JSON string-array fields and submit arrays of strings.
- Invalid JSON or non-string/empty array entries are rejected locally without calling the teacher API. Existing options, rubric, attachments, subject ID, knowledge-point IDs, grading mode, and answer word limit are retained on update.

### Tests

Added production-shape component tests for textbook copy-only rows, a copied false judgment answer, multiple-choice answer arrays, fill-blank synonym arrays, and invalid local JSON/format handling.

### Exact Outputs

```text
npm test -- src/pages/teacher/TeacherApp.test.jsx
Test Files  1 passed (1)
Tests  12 passed (12)

server/.venv/bin/pytest server/tests/test_teacher_catalog.py server/tests/test_teacher.py -q
24 passed in 3.94s

npm test -- --run
Test Files  6 passed (6)
Tests  23 passed (23)

npm run build
vite build: built successfully
Prerendered 8 routes with SEO metadata.
```

`git diff --check` completed successfully before the implementation commit.

### SHA

Implementation commit: `7f32675ce4883810312c3673f33e162225f442d8`

### Concerns

No known functional blockers. Task 9 remains responsible for the full canonical knowledge-point multi-select editor and richer answer-authoring controls.
