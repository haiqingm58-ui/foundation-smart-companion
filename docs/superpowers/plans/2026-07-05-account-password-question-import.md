# Account Password And Question Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create 18 production demo accounts, add reusable password visibility controls, and deliver a complete teacher question-bank XLSX/CSV import workflow.

**Architecture:** Keep account creation in a server-side idempotent service exposed through `server.manage`, never in frontend code. Add one reusable React password field and reuse existing portal modal/table patterns. Parse and validate question files on the server, return normalized preview rows, then revalidate and insert all questions in one transaction.

**Tech Stack:** React 19, Vitest, Lucide React, FastAPI, Pydantic, SQLAlchemy, openpyxl, pytest, PostgreSQL.

---

### Task 1: Reusable Password Visibility Field

**Files:**
- Create: `src/components/auth/PasswordField.jsx`
- Create: `src/components/auth/PasswordField.test.jsx`
- Modify: `src/components/auth/PasswordChangeGate.jsx`
- Modify: `src/pages/admin/AdminApp.jsx`
- Modify: `src/styles.css`
- Test: `src/pages/admin/AdminApp.test.jsx`

- [ ] **Step 1: Write a failing component test**

Render `PasswordField` with label `新密码`, assert the input starts as `type="password"`, click the unique `显示新密码` button, and assert it changes to `type="text"` while the button becomes `隐藏新密码`.

- [ ] **Step 2: Run the password test and verify RED**

Run: `npm test -- src/components/auth/PasswordField.test.jsx`

Expected: FAIL because `PasswordField.jsx` does not exist.

- [ ] **Step 3: Implement the focused component**

Create a label-based component accepting `label`, `name`, `value`, `onChange`, `defaultValue`, `minLength`, `required`, `autoComplete`, and `hint`. Use local `visible` state, `Eye`/`EyeOff`, and a `type="button"` toggle whose accessible name includes the field label.

- [ ] **Step 4: Replace every non-login password input**

Use `PasswordField` for current/new/confirm password in `PasswordChangeGate`, teacher wizard password, person creation password, student import password, and reset-password modal. Preserve existing form names and controlled/default values.

- [ ] **Step 5: Add stable styling and verify GREEN**

Add `.passwordFieldControl` styles with a fixed 40px icon button, focus-visible treatment, and no width shift. Run:

```bash
npm test -- src/components/auth/PasswordField.test.jsx src/pages/admin/AdminApp.test.jsx
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/components/auth src/components/auth/PasswordChangeGate.jsx src/pages/admin/AdminApp.jsx src/pages/admin/AdminApp.test.jsx src/styles.css
git commit -m "feat: add password visibility controls"
```

### Task 2: Idempotent Demo Account Creation

**Files:**
- Create: `server/application/services/demo_accounts.py`
- Create: `server/tests/test_demo_accounts.py`
- Modify: `server/manage.py`

- [ ] **Step 1: Write failing service tests**

Test `create_demo_accounts(database, count=6, password_factory=...)` against migrated SQLite. Assert it creates 6 users for each role, 6 teacher profiles, 6 student profiles, one demo class, six matching active bindings, Argon2 hashes, and `must_change_password=True`. Run it twice and assert the second run creates zero users without duplicating profiles or bindings.

- [ ] **Step 2: Run the account tests and verify RED**

Run: `server/.venv/bin/pytest server/tests/test_demo_accounts.py -q`

Expected: FAIL because the service is missing.

- [ ] **Step 3: Implement transactional account creation**

Create usernames `teacher01..06`, `student01..06`, and `admin01..06`; names `演示教师01..06`, `演示学生01..06`, and `演示管理员01..06`; teacher numbers `DEMO-T01..06`; student numbers `DEMO-S01..06`. Create `基础工程演示班` and matching teacher-student bindings. Generate a different strong password per created user through an injectable password factory and return plaintext only in the command result.

- [ ] **Step 4: Add the management command**

Add `seed-demo-accounts --count 6` to `server.manage`. Print JSON containing only `created`, `skipped`, and newly created credential rows. Run migrations before creation. Do not include hashes, salts, database URL, or secret key.

- [ ] **Step 5: Verify GREEN and command output**

Run:

```bash
server/.venv/bin/pytest server/tests/test_demo_accounts.py -q
FOUNDATION_DATABASE_URL=sqlite:////tmp/foundation-demo-test.db FOUNDATION_SECRET_KEY=test server/.venv/bin/python -m server.manage seed-demo-accounts --count 6
```

Expected: tests pass and JSON reports 18 created accounts.

- [ ] **Step 6: Commit**

```bash
git add server/application/services/demo_accounts.py server/tests/test_demo_accounts.py server/manage.py
git commit -m "feat: add demo account provisioning"
```

### Task 3: Teacher Question Import Backend

**Files:**
- Create: `server/application/services/question_imports.py`
- Modify: `server/application/schemas/teacher.py`
- Modify: `server/application/api/teacher.py`
- Modify: `server/tests/test_teacher.py`

- [ ] **Step 1: Write failing template and preview tests**

Assert `GET /api/teacher/question-import-template` returns an XLSX attachment with the documented Chinese headers. Upload a valid workbook to `/api/teacher/questions/import-preview` and assert normalized options, answer, chapter, difficulty, points, and zero errors. Upload a workbook with a formula, duplicate stem, invalid type, and missing answer; assert row-specific errors and no database writes.

- [ ] **Step 2: Write a failing transaction test**

POST normalized rows to `/api/teacher/questions/import`; assert valid rows become owned `teacher-import` questions. Include one invalid row and assert the request fails with zero partial inserts.

- [ ] **Step 3: Run backend tests and verify RED**

Run: `server/.venv/bin/pytest server/tests/test_teacher.py -q`

Expected: FAIL with missing import routes.

- [ ] **Step 4: Implement parser and validation service**

Support UTF-8 CSV and XLSX up to 5MB. Normalize the 11 documented columns, reject formulas, validate required fields and enums, build option objects for choice questions, parse multi-select answers, detect duplicate stems, and return `{rows, valid, errors, summary}` with row/field/code/reason details.

- [ ] **Step 5: Implement secured routes and transaction**

Add template, preview, and import routes under the existing teacher router. Apply `require_teacher`, rerun row validation during import, insert all rows in one session transaction with `created_by=auth.user.id`, and create an operation log entry containing only counts.

- [ ] **Step 6: Verify GREEN**

Run: `server/.venv/bin/pytest server/tests/test_teacher.py -q`

Expected: all teacher tests pass and no warnings are emitted.

- [ ] **Step 7: Commit**

```bash
git add server/application/services/question_imports.py server/application/schemas/teacher.py server/application/api/teacher.py server/tests/test_teacher.py
git commit -m "feat: add teacher question bank import API"
```

### Task 4: Teacher Question Import Interface

**Files:**
- Modify: `src/api/teacher.js`
- Modify: `src/pages/teacher/TeacherApp.jsx`
- Modify: `src/pages/teacher/TeacherApp.test.jsx`
- Modify: `src/styles.css`

- [ ] **Step 1: Write failing interaction tests**

Navigate to question-bank management, click `批量导入`, assert the dialog exposes template download and dropzone. Upload a CSV fixture, mock preview results, and assert valid/error counters and row-level errors. Assert the confirm button is disabled when errors exist and a clean preview can call the import endpoint.

- [ ] **Step 2: Run frontend tests and verify RED**

Run: `npm test -- src/pages/teacher/TeacherApp.test.jsx`

Expected: FAIL because the import action and dialog are missing.

- [ ] **Step 3: Add API client methods**

Add `previewQuestionImport(formData)`, `importQuestions(rows)`, and a template URL helper using the existing `request` and `apiUrl` conventions.

- [ ] **Step 4: Implement the three-state import modal**

Add a `批量导入` secondary action next to `新建题目`. Implement file selection and drag/drop, loading/error states, summary tiles, compact valid-row preview, row error list, back/re-upload controls, confirmation summary, and final transaction submit. Refresh the question list after success.

- [ ] **Step 5: Add responsive visual treatment**

Reuse portal panel, table, button, and status colors. Add stable dropzone, summary, error, and confirmation layout styles. At mobile width, stack summaries and actions without horizontal overflow.

- [ ] **Step 6: Verify GREEN**

Run:

```bash
npm test -- src/pages/teacher/TeacherApp.test.jsx
npm run build
```

Expected: tests and production build pass.

- [ ] **Step 7: Commit**

```bash
git add src/api/teacher.js src/pages/teacher/TeacherApp.jsx src/pages/teacher/TeacherApp.test.jsx src/styles.css
git commit -m "feat: improve teacher question import workflow"
```

### Task 5: Full Verification, Production Provisioning, And Deployment

**Files:**
- Modify only if verification uncovers a tested defect.

- [ ] **Step 1: Run the full suite**

Run: `npm run check`

Expected: all frontend, backend, deployment tests and production build pass without warnings.

- [ ] **Step 2: Browser QA locally**

Verify password controls, teacher import empty/upload/error/success states, desktop layout, and mobile layout. Confirm no console errors and no horizontal overflow.

- [ ] **Step 3: Deploy atomically**

Run: `bash scripts/deploy-platform-jdcloud.sh`

Expected: output ends with `Deployment completed: <release>-<sha>`.

- [ ] **Step 4: Provision production accounts once**

Run the deployed `server.manage seed-demo-accounts --count 6` command with production environment variables. Capture the returned credential JSON outside the repository and verify database counts increased by 6 teachers, 6 students, and 6 administrators.

- [ ] **Step 5: Verify production**

Check `/api/health`, release symlinks, systemd status, Nginx configuration, question import template status, and recent service logs. Verify all 18 new users are active and require a first-login password change.

- [ ] **Step 6: Push main and deliver credentials**

Push verified commits to GitHub `main`. Report the 18 username/password pairs directly to the user, along with the production URL and first-login password-change requirement. Do not commit the credential list.
