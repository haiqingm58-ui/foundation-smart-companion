# Task 7 Report: Student Random Practice and Formal Exam APIs

## Status

`DONE`

- Base commit: `53265ed` (`fix: harden paper assembly and publication`)
- Commit: recorded after final verification
- Scope: Task 7 student assessment migration, models, schemas, selection service, APIs, client bindings, tests, and this report.

## Delivered

- Added revision `007_practice_sessions` with `practice_sessions` and ordered `practice_session_questions`, plus nullable `submissions.started_at` for formal-paper timing. Existing tables and rows are not rewritten or removed.
- Added subject-scoped random practice creation using chapter mode or one to three knowledge points, accepting 5, 10, 20, and custom counts from 1 through 100.
- Enforced active subject and exact knowledge-point subject ownership, selection without duplicates, exact `PRACTICE_QUESTION_SHORTAGE` failures, and unseen/recently incorrect priority ahead of recently correct questions.
- Stored immutable per-session answer-bearing grading snapshots server-side alongside sanitized display snapshots; pre-submit payloads omit `correctAnswer`, `rubric`, and `explanation`.
- Added owned-session resume, per-question JSON autosave, objective auto-grading, subjective/calculation pending review, practice history writes, and catalog-aware mastery updates without changing formal `Student.average_score`.
- Added formal-paper target listing, start/resume, deadline and duration countdown metadata, autosave, server-snapshot grading, result visibility controlled by `showAnswersMode`, one resumable in-progress submission, and one additional attempt only when resubmission is allowed.
- Applied formal average updates only to graded submissions of published assignments. Practice sessions never update formal averages.
- Kept the existing `/api/student/exercises/{question_id}/attempts` route intact as the legacy practice compatibility route and preserved the existing error envelope and student/target IDOR protections.
- Added the student API client methods for practice sessions and formal papers.

## TDD Evidence

Initial red run, after the Task 7 test module was written before production code:

```text
$ server/.venv/bin/pytest server/tests/test_student_assessment.py -q
FFFFF                                                                    [100%]
5 failed in 1.34s
```

The new practice routes returned `404 Not Found`, and migration 007 did not yet create the new session tables.

Subject-isolation hardening red run, after adding the cross-subject knowledge-point regression:

```text
$ server/.venv/bin/pytest server/tests/test_student_assessment.py::test_practice_selection_subject_filters_modes_counts_shortages_and_recency -q
F                                                                        [100%]
1 failed in 0.65s
```

The endpoint initially accepted a mixed-subject knowledge-point request. The selection service now returns `422` with `PRACTICE_KNOWLEDGE_POINT_SUBJECT_MISMATCH` before selecting any question.

Focused green verification:

```text
$ server/.venv/bin/pytest server/tests/test_student_assessment.py server/tests/test_student.py server/tests/test_teacher_papers.py server/tests/test_migrations.py -q
.............................................                            [100%]
45 passed in 6.91s
```

## Coverage Evidence

- `test_practice_selection_subject_filters_modes_counts_shortages_and_recency` covers subject isolation, chapter and one-to-three knowledge-point selection, 5/10/20/custom counts, no duplicate IDs, exact shortage errors, and recent-correct avoidance.
- `test_practice_resume_autosave_uses_immutable_snapshot_and_updates_mastery_only` saves and resumes a JSON answer, mutates the source question after creation, verifies snapshot grading/mastery history, and verifies formal average remains zero.
- `test_formal_papers_authorize_target_resume_autosave_deadline_and_attempt_limit` covers target listing, countdown metadata, duplicate start returning the same in-progress submission, autosave, a real assignment targeted to another student returning 404, post-submit attempt limit, and deadline rejection.
- `test_formal_submission_grades_server_snapshot_preserves_secrecy_and_handles_manual_review` covers objective grading, `never` answer secrecy, formal-average update, manual pending review, and `after_submission` result disclosure.
- `test_migration_007_preserves_existing_submission_history` upgrades a populated revision-006 database, verifies legacy student data survives, and verifies both session tables exist.

## Final Verification

```text
$ server/.venv/bin/pytest server/tests -q
........................................................................ [ 46%]
.............................s.......................................... [ 93%]
..........                                                               [100%]
153 passed, 1 skipped in 21.10s
```

```text
$ server/.venv/bin/python -m compileall -q server/application/models.py server/application/schemas/practice.py server/application/services/practice_selection.py server/application/api/student_assessment.py server/application/main.py server/migrations/versions/007_practice_sessions.py server/tests/test_student_assessment.py
[no output, exit 0]

$ git diff --check
[no output, exit 0]
```

## Concerns

Concern count: `0`.

## Review Remediation

### Status

`DONE`

- Review baseline: `c260185` (`feat: add random practice and formal exam APIs`)
- Findings addressed: Critical 1, Important 7, Minor 2.

### Security And Snapshot Changes

- Replaced key-deletion snapshot sanitization with an explicit student-safe projection. Student payloads now contain only question identity, prompt, safe option labels/text, ordinary display metadata, and answer-display fields. They never contain `sourceMetadata`, provenance, source answers, attachments, grading-only metadata, or unknown nested source fields.
- Kept protected grading feedback separate from result rendering. Per-question feedback, scores, criteria, and explanations are withheld whenever `showAnswers` is false. `never`, unclosed `after_close`, and pre-submit views do not disclose answer-bearing fields. `after_submission` and closed `after_close` reveal the solution fields deliberately.
- Added direct tests using imported-snapshot-shaped `sourceMetadata.sourceAnswer` and nested provenance values across practice, formal start/resume, `never`, `after_submission`, and `after_close` boundaries.

### Lifecycle, Grading, And Validation Changes

- Added unique submission attempt and answer constraints plus a portable SQLite/PostgreSQL partial unique index enforcing one in-progress formal attempt per assignment/student. Starts catch conflicts and resume the committed attempt; first-answer autosaves upsert safely.
- Made practice and formal submit operations conditional-state transitions. Parallel submits and response-loss retries return the committed result without duplicate practice attempts, mastery mutations, grades, or submission answers.
- Added `formal_grading.recalculate_formal_average`, shared by automatic formal grading and teacher manual grading. It persists the latest graded attempt per published/closed assignment and writes zero when there are no valid graded formal results.
- Honored `Assignment.auto_grade=False`: formal submissions remain pending review without automatic per-question scores or formal-average updates.
- Made `Submission.submitted_at` nullable in the ORM and revision 007. A started attempt has no submission timestamp. Teacher assignment completion, averages, queues, and grading now exclude/reject `in_progress` rows.
- Validated autosaves against immutable snapshots with a 16KB serialized JSON maximum. Null clears are allowed; invalid choice labels, duplicate multiple-choice labels, non-boolean judgement values, invalid fill/text shapes, over-limit text, and oversized values are rejected through the standard error envelope.
- Required timezone-aware publication/legacy assignment dates and normalized accepted values to UTC. Naive inputs fail validation before direct datetime comparison.
- Correct-history selection now uses oldest-first ordering once unseen and incorrect questions are exhausted, with seeded deterministic ties.

### Migration And IDOR Changes

- Revision 007 now adds/removes the new submission uniqueness/indexes and safely round-trips `submitted_at` nullability. The migration test seeds a populated revision-006 submission and answer, verifies upgrade preservation, then downgrades to revision 006 and verifies data and schema restoration.
- Added a second authenticated student regression that exercises foreign practice GET/autosave/submit and formal autosave/submit/result routes, plus a real non-target assignment. All return the existing 404 ownership envelope.

### Review TDD Evidence

The parallel-start regression initially failed because a query-triggered autoflush inserted the competing submission before the `IntegrityError` handler:

```text
$ server/.venv/bin/pytest server/tests/test_student_assessment.py::test_parallel_formal_starts_persist_one_in_progress_attempt -q
F                                                                        [100%]
1 failed in 0.96s
```

The trace identified `_assignment_questions()` as the query that autoflushed the pending submission. Snapshot preparation now runs before attaching the new row, so the insert is committed inside the conflict handler.

Green concurrency checks:

```text
$ server/.venv/bin/pytest server/tests/test_student_assessment.py::test_parallel_formal_starts_persist_one_in_progress_attempt -q
.                                                                        [100%]
1 passed in 0.61s

$ server/.venv/bin/pytest server/tests/test_student_assessment.py::test_parallel_first_autosaves_upsert_one_answer -q
.                                                                        [100%]
1 passed in 0.64s

$ server/.venv/bin/pytest server/tests/test_student_assessment.py::test_parallel_submits_commit_once_and_return_committed_result -q
.                                                                        [100%]
1 passed in 0.65s
```

### Review Verification

```text
$ server/.venv/bin/pytest server/tests/test_student_assessment.py server/tests/test_student.py server/tests/test_teacher.py server/tests/test_teacher_papers.py server/tests/test_migrations.py -q
......................................................................   [100%]
70 passed in 12.54s
```

```text
$ server/.venv/bin/pytest server/tests -q
........................................................................ [ 42%]
.............................s.......................................... [ 84%]
..........................                                               [100%]
169 passed, 1 skipped in 25.20s
```

Compilation of all changed Python modules and `git diff --check` completed with no output and exit code 0.

### Remaining Concerns

The available test environment is SQLite. The migration and ORM define PostgreSQL-compatible partial-index clauses, and the concurrency regression uses the production-supported SQLite engine. No PostgreSQL service was configured for a live harness run.

## Second Review Remediation

### Status

`DONE`

- Review baseline: `59eb7f5` (`fix: harden student assessment workflows`)
- Findings addressed: Critical 1, Important 3, Minor 2.

### Changes

- `after_close` answer disclosure now depends only on global assignment closure: explicit `closed` status or the assignment-level `dueAt` boundary. Per-student duration remains a write/countdown deadline and cannot disclose answers.
- Formal autosave and submit both acquire a row lock on the owned submission before checking state or changing answers. Conflict recovery re-reads that row and rejects any closed/submitting submission before writing.
- The student-safe snapshot projection now preserves known display-only image, table, and formula attachment shapes while dropping source position, OMML source, provenance, source metadata, and unknown nested fields.
- Pending formal submissions now persist and return `score=null`; teacher assignment score metrics include only final `graded` submissions.
- Revision 007 now creates and downgrades `ix_submissions_submitted_at`, matching the ORM metadata alongside the partial in-progress unique index.

### Re-review Evidence

```text
$ server/.venv/bin/pytest server/tests/test_student_assessment.py::test_after_close_never_uses_personal_duration_to_reveal server/tests/test_student_assessment.py::test_student_payload_keeps_safe_image_table_and_formula_attachments -q
..                                                                       [100%]
2 passed in 0.83s

$ server/.venv/bin/pytest server/tests/test_student_assessment.py server/tests/test_student.py server/tests/test_teacher.py server/tests/test_teacher_papers.py server/tests/test_migrations.py -q
........................................................................ [100%]
72 passed in 12.88s

$ server/.venv/bin/pytest server/tests -q
........................................................................ [ 41%]
.............................s.......................................... [ 83%]
............................                                             [100%]
171 passed, 1 skipped in 25.71s
```

Compilation of changed modules and `git diff --check` completed with no output and exit code 0.

### Remaining Concerns

The available test environment remains SQLite. PostgreSQL row-lock syntax is emitted through SQLAlchemy's portable `with_for_update()` path and partial-index DDL is defined for PostgreSQL, but no live PostgreSQL harness was configured.
