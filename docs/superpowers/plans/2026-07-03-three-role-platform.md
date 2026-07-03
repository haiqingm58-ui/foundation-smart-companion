# Three-Role Teaching Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing Foundation Engineering student app into a production-backed student, teacher, and administrator platform without removing current learning features.

**Architecture:** Keep React/Vite and FastAPI, split the frontend into role layouts and feature modules, and split the backend into a compatibility entrypoint plus focused application modules. Use SQLAlchemy and Alembic so isolated tests can use SQLite while production runs on a localhost-only PostgreSQL database. Import the current SQLite users, exercises, documents, and settings transactionally, retain the original SQLite file as a rollback source, and use database-backed sessions and server-side ownership checks.

**Tech Stack:** React 19, React Router, Vite 6, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Argon2, Pillow, Vitest, Testing Library, Pytest, HTTPX, Playwright.

---

### Task 1: Test Harness And Application Skeleton

**Files:**
- Modify: `package.json`
- Modify: `server/requirements.txt`
- Create: `vitest.config.mjs`
- Create: `src/test/setup.js`
- Create: `server/tests/conftest.py`
- Create: `server/application/__init__.py`
- Create: `server/application/config.py`
- Create: `server/application/database.py`

- [ ] Add frontend and backend test dependencies and scripts.
- [ ] Write a failing backend fixture test proving each test gets an isolated database.
- [ ] Run `server/.venv/bin/pytest server/tests/test_database.py -q` and confirm it fails before the database helper exists.
- [ ] Implement database URL configuration and SQLAlchemy connection/session helpers, with SQLite foreign keys enabled in tests.
- [ ] Run the focused test and confirm it passes.
- [ ] Run the existing Vite build to protect the student app baseline.

### Task 2: Versioned Database Migrations

**Files:**
- Create: `server/application/migrations.py`
- Create: `server/migrations/001_three_role_core.sql`
- Create: `server/migrations/002_learning_and_content.sql`
- Create: `server/tests/test_migrations.py`

- [ ] Write failing tests that migrate a copy of the current four-table database and preserve its users, exercises, documents, and settings.
- [ ] Add Alembic versioning and transactional migrations.
- [ ] Add compatible tables: `teachers`, `students`, `classes`, `teacher_student_bindings`, `sessions`, `captcha_records`, `login_attempts`, `resources`, `questions`, `assignments`, `assignment_questions`, `assignment_targets`, `submissions`, `submission_answers`, `learning_progress`, `knowledge_mastery`, `notices`, and `operation_logs`.
- [ ] Add unique constraints for usernames, teacher numbers, student numbers, and active bindings.
- [ ] Seed role profiles for the three existing accounts and migrate the 79 existing exercise payloads into relational questions without deleting the source rows.
- [ ] Verify migration idempotency and rollback on invalid SQL.

### Task 3: Real Authentication, Captcha, Sessions, And Role Guards

**Files:**
- Create: `server/application/security.py`
- Create: `server/application/services/captcha.py`
- Create: `server/application/api/auth.py`
- Create: `server/application/api/dependencies.py`
- Create: `server/tests/test_auth.py`
- Modify: `server/app.py`
- Modify: `server/.env.example`

- [ ] Write failing tests for valid login, invalid/expired/reused captcha, wrong password, disabled account, lockout after five failures, logout, and `/auth/me`.
- [ ] Generate four-character captcha images with ambiguous characters removed, store only a keyed digest, and expire records after 120 seconds.
- [ ] Hash new passwords with Argon2 and retain a verified legacy PBKDF2 upgrade path.
- [ ] Store opaque session-token digests in the database and set an HttpOnly SameSite=Lax cookie scoped to `/foundation-smart-companion`.
- [ ] Add CSRF validation for mutating cookie-authenticated requests.
- [ ] Add student, teacher, and administrator dependencies that reject mismatched roles on the server.
- [ ] Remove bearer-token and offline-demo authentication from the formal path.

### Task 4: Administrator APIs And Transactional Teacher-Student Wizard

**Files:**
- Create: `server/application/schemas/admin.py`
- Create: `server/application/services/imports.py`
- Create: `server/application/api/admin.py`
- Create: `server/tests/test_admin.py`

- [ ] Write failing tests for administrator dashboard counts, user CRUD, duplicate identifiers, status changes, password resets, class CRUD, binding management, and audit logs.
- [ ] Write a failing transaction test where one invalid student causes the teacher-and-students creation transaction to roll back.
- [ ] Implement `POST /api/admin/teachers-with-students` with manual, CSV, and XLSX validation results.
- [ ] Reject formula cells and CSV formula prefixes, repeated rows, existing accounts, missing names, and missing classes.
- [ ] Implement a downloadable XLSX import template.
- [ ] Require confirmation metadata for teacher deletion and force reassignment or unbinding instead of deleting students.

### Task 5: Teacher Resources, Questions, Assignments, And Analytics

**Files:**
- Create: `server/application/schemas/teacher.py`
- Create: `server/application/services/storage.py`
- Create: `server/application/services/rag.py`
- Create: `server/application/api/teacher.py`
- Create: `server/tests/test_teacher.py`

- [ ] Write failing ownership tests proving a teacher cannot see another teacher's students or class data.
- [ ] Implement searchable, sortable, paginated teacher student lists and student detail summaries.
- [ ] Store uploaded files under a generated UUID name outside the web root; validate MIME type, extension, size, and path containment.
- [ ] Extract text from Markdown, TXT, PDF, DOCX, PPTX, and XLSX files and index searchable chunks for RAG.
- [ ] Implement question CRUD for six question types, batch import, copy, delete, and chapter/knowledge-point filters.
- [ ] Implement assignment creation, targeting, publication, submission counts, grading queues, and class analytics.
- [ ] Record all destructive and publishing actions in `operation_logs`.

### Task 6: Student Progress, Exercises, Reports, And RAG

**Files:**
- Create: `server/application/api/student.py`
- Create: `server/application/api/qa.py`
- Create: `server/tests/test_student.py`
- Create: `server/tests/test_qa.py`

- [ ] Write failing tests for dashboard summaries, progress updates, question attempts, assignment submission, and report calculations.
- [ ] Persist exercise attempts and criterion scores instead of relying on React state or localStorage.
- [ ] Calculate progress, average score, mastery, weak points, and rank from stored activity.
- [ ] Keep textbook chunks server-side and return only ranked citations.
- [ ] Separate textbook, standards, and tutoring retrieval sources.
- [ ] Use the configured OpenAI-compatible model when available and return an explicit retrieval-only response when it is not.

### Task 7: Frontend Router, API Client, Auth Store, And Role Layouts

**Files:**
- Create: `src/api/client.js`
- Create: `src/api/auth.js`
- Create: `src/api/student.js`
- Create: `src/api/teacher.js`
- Create: `src/api/admin.js`
- Create: `src/router/index.jsx`
- Create: `src/router/RoleGuard.jsx`
- Create: `src/stores/AuthContext.jsx`
- Create: `src/layouts/StudentLayout.jsx`
- Create: `src/layouts/TeacherLayout.jsx`
- Create: `src/layouts/AdminLayout.jsx`
- Modify: `src/main.jsx`
- Modify: `src/App.jsx`

- [ ] Write failing Vitest tests for unauthenticated redirects and all invalid cross-role navigation combinations.
- [ ] Implement BrowserRouter using `/foundation-smart-companion` as basename.
- [ ] Use `credentials: include`, unified response parsing, CSRF headers, and visible server errors.
- [ ] Restore the user from `/api/auth/me`; never trust localStorage for roles.
- [ ] Lazy-load student, teacher, and administrator route groups.
- [ ] Preserve all existing student learning pages while moving them behind `StudentLayout`.

### Task 8: Login Experience With Supplied College Logo

**Files:**
- Create: `public/college-logo.jpg`
- Create: `src/pages/login/LoginPage.jsx`
- Create: `src/pages/login/LoginPage.css`
- Create: `src/components/auth/LoginCarousel.jsx`
- Create: `src/components/auth/RoleSelector.jsx`
- Create: `src/components/auth/CaptchaInput.jsx`
- Create: `src/pages/login/LoginPage.test.jsx`

- [ ] Optimize and copy the supplied Hunan University College of Civil Engineering logo.
- [ ] Write failing component tests for required fields, role keyboard selection, captcha refresh, password visibility, loading state, and server error display.
- [ ] Implement the 55/45 desktop layout, circular logo, six-slide engineering carousel, 4.5-second timing, hover pause, arrow controls, dots, swipe gestures, and reduced-motion behavior.
- [ ] Use emoji role icons and verify the selected role matches the server-returned role.
- [ ] Remove the old capability panel and all displayed demo credentials.
- [ ] Implement responsive tablet and mobile layouts without horizontal overflow.

### Task 9: Teacher And Administrator Workspaces

**Files:**
- Create: `src/components/common/DataTable.jsx`
- Create: `src/components/common/ConfirmDialog.jsx`
- Create: `src/components/common/ToastProvider.jsx`
- Create: `src/components/common/FileUploader.jsx`
- Create: `src/pages/teacher/*`
- Create: `src/pages/admin/*`
- Create: `src/components/admin/TeacherStudentWizard.jsx`
- Create: `src/components/admin/ImportPreview.jsx`
- Create: `src/pages/teacher/TeacherWorkspace.test.jsx`
- Create: `src/pages/admin/AdminWorkspace.test.jsx`

- [ ] Write failing tests for search, filtering, pagination, sorting, empty/loading/error states, confirmation dialogs, and wizard navigation.
- [ ] Implement all teacher navigation entries with functional data tables, forms, uploads, question management, assignment publishing, grading, analytics, and notices.
- [ ] Implement all administrator navigation entries with functional account, teacher, student, class, binding, import, log, and settings workflows.
- [ ] Implement the three-step teacher-and-students wizard with manual rows, pasted tables, XLSX/CSV upload, import preview, and transaction result display.
- [ ] Ensure every destructive action uses the shared dialog rather than `alert`.

### Task 10: Quality, Deployment, And Rollback

**Files:**
- Create: `server/tests/test_permissions.py`
- Create: `tests/e2e/auth-roles.spec.js`
- Modify: `vite.config.mjs`
- Modify: `scripts/deploy-jdcloud.sh`
- Modify: `README.md`
- Modify: `/etc/nginx/conf.d/foundation-smart-companion.conf` on the server after backup

- [ ] Run backend unit and integration tests, frontend unit tests, lint, type/build checks, and browser end-to-end tests.
- [ ] Verify login at desktop, tablet, and mobile viewports and inspect console/network errors.
- [ ] Run the migration against a copy of the production database before touching production.
- [ ] Upload source and static assets into timestamped release directories.
- [ ] Install and configure a localhost-only PostgreSQL service, create a least-privilege application role, run the Alembic migration, and transactionally import the current SQLite data before restarting the backend.
- [ ] Add the prefixed API Nginx location while retaining the temporary root `/api/` compatibility route; run `nginx -t` before reload.
- [ ] Verify direct refresh for login, student, teacher, and administrator routes.
- [ ] Push the completed branch, merge to `main` after verification, and document exact rollback commands.
