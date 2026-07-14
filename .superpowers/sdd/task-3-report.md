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
