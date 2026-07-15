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
