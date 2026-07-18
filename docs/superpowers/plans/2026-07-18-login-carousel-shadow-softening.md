# Login Carousel Shadow Softening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the login carousel's black-heavy bottom overlay and broad card shadow with the approved softer academy-blue treatment.

**Architecture:** Keep the existing login component structure and change only two CSS declarations in `LoginPage.css`. Extend the existing login layout E2E test to read computed styles, then use browser screenshots and the established `design-qa.md` record to verify the visual result without changing geometry or interactions.

**Tech Stack:** React 19, Vite 6, CSS, Playwright, Vitest, FastAPI test server, in-app browser visual QA.

## Global Constraints

- Use `.carouselTint` value `linear-gradient(180deg, rgba(22, 73, 122, 0) 34%, rgba(22, 73, 122, 0.16) 62%, rgba(22, 63, 115, 0.72) 100%)`.
- Use `.authColumns` value `0 10px 24px rgba(53, 84, 115, 0.08)`.
- Do not change images, copy, component structure, geometry, responsive breakpoints, or login interactions.
- Do not change Logo, button, input, or focus shadows.
- Preserve the current 1440, 1920, 2560, breakpoint-boundary, and mobile layout assertions.

---

## Execution Setup

- [ ] Create an isolated worktree from `main` and install dependencies.

```bash
git worktree add .worktrees/login-shadow-softening -b codex/login-shadow-softening
cd .worktrees/login-shadow-softening
npm ci
ln -s /Users/georisklab02/Documents/教材/foundation-smart-companion/server/.venv server/.venv
npm test
```

Expected: 9 frontend test files and 52 tests pass before changes.

### Task 1: Lock and implement the softer visual treatment

**Files:**
- Modify: `tests/e2e/login-layout.spec.mjs`
- Modify: `src/pages/login/LoginPage.css:40-63`

**Interfaces:**
- Consumes: Existing `.authColumns` and `.carouselTint` selectors rendered by `LoginPage`.
- Produces: `readLayout(page).visualStyles` with `cardShadow` and `tintBackgroundImage` strings for regression assertions.

- [ ] **Step 1: Extend the layout reader with computed visual styles**

Inside `page.evaluate`, add:

```js
const cardElement = document.querySelector(".authColumns");
const tintElement = document.querySelector(".carouselTint");
const cardStyle = cardElement ? getComputedStyle(cardElement) : null;
const tintStyle = tintElement ? getComputedStyle(tintElement) : null;
```

Add this property to the returned object:

```js
visualStyles: {
  cardShadow: cardStyle?.boxShadow ?? null,
  tintBackgroundImage: tintStyle?.backgroundImage ?? null,
},
```

- [ ] **Step 2: Add failing assertions for the approved values**

After the existing 1440 desktop geometry assertions, add:

```js
expect(desktop.visualStyles.cardShadow).toContain("rgba(53, 84, 115, 0.08)");
expect(desktop.visualStyles.cardShadow).toContain("0px 10px 24px");
expect(desktop.visualStyles.tintBackgroundImage).toContain("rgba(22, 73, 122, 0) 34%");
expect(desktop.visualStyles.tintBackgroundImage).toContain("rgba(22, 73, 122, 0.16) 62%");
expect(desktop.visualStyles.tintBackgroundImage).toContain("rgba(22, 63, 115, 0.72) 100%");
```

- [ ] **Step 3: Run the focused test and verify RED**

Run:

```bash
npm run test:e2e -- tests/e2e/login-layout.spec.mjs
```

Expected: FAIL because the current card shadow contains `rgba(37, 69, 101, 0.12)` and the current tint does not contain the approved academy-blue stops.

- [ ] **Step 4: Apply the minimal CSS implementation**

Replace only these declarations:

```css
.authColumns {
  box-shadow: 0 10px 24px rgba(53, 84, 115, .08);
}

.carouselTint {
  background: linear-gradient(
    180deg,
    rgba(22, 73, 122, 0) 34%,
    rgba(22, 73, 122, .16) 62%,
    rgba(22, 63, 115, .72) 100%
  );
}
```

Keep every other declaration in both rules unchanged.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run:

```bash
npm run test:e2e -- tests/e2e/login-layout.spec.mjs
npx vitest run src/pages/login/LoginPage.logo.test.js src/pages/login/LoginPage.test.jsx
```

Expected: the login E2E test and all login unit tests pass; the existing geometry assertions remain unchanged.

- [ ] **Step 6: Commit the implementation**

```bash
git add src/pages/login/LoginPage.css tests/e2e/login-layout.spec.mjs
git commit -m "style: soften login carousel shadows"
```

### Task 2: Visual QA, complete verification, and release

**Files:**
- Create: `screenshots/login-shadow-before-1440.png`
- Create: `screenshots/login-shadow-after-1440.png`
- Create: `screenshots/login-shadow-after-mobile.png`
- Create: `screenshots/login-shadow-comparison.png`
- Modify: `design-qa.md`

**Interfaces:**
- Consumes: The approved style values from Task 1 and the current production screenshot at `/tmp/foundation-login-shadow-current.png`.
- Produces: A committed before/after visual comparison and a `final result: passed` QA record.

- [ ] **Step 1: Preserve the current production reference**

```bash
cp /tmp/foundation-login-shadow-current.png screenshots/login-shadow-before-1440.png
```

Expected: the tracked source image is 1440 x 1024 and shows the current dark lower overlay and broad card shadow.

- [ ] **Step 2: Start the local backend and frontend for browser QA**

Terminal A:

```bash
server/.venv/bin/python tests/e2e/prepare_e2e.py
FOUNDATION_DATABASE_URL="sqlite:///$(pwd)/output/e2e/e2e.db" \
FOUNDATION_SECRET_KEY=qa-only-secret \
FOUNDATION_DATA_DIR=/tmp/foundation-shadow-data \
FOUNDATION_UPLOAD_DIR=/tmp/foundation-shadow-uploads \
FOUNDATION_COOKIE_PATH=/ \
server/.venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8000
```

Terminal B:

```bash
npm run dev -- --host 127.0.0.1 --port 5173
```

Expected: API health is available at `http://127.0.0.1:8000/api/health` and login is available at `http://127.0.0.1:5173/foundation-smart-companion/login`.

- [ ] **Step 3: Capture and inspect the implementation in the in-app browser**

At 1440 x 1024, save `screenshots/login-shadow-after-1440.png`. At 390 x 844, save `screenshots/login-shadow-after-mobile.png`.

For both viewports verify:

```text
authColumns/card overlap = 0
document scrollWidth <= document clientWidth + 1
CAPTCHA naturalWidth > 0
loginServerError is absent
copyright = All Rights Reserved @2026
```

At 1440 additionally verify computed styles contain all five strings asserted in Task 1.

- [ ] **Step 4: Build one comparison image and inspect it**

```bash
server/.venv/bin/python -c 'from PIL import Image,ImageDraw; b=Image.open("screenshots/login-shadow-before-1440.png").convert("RGB"); a=Image.open("screenshots/login-shadow-after-1440.png").convert("RGB"); out=Image.new("RGB",(2880,1074),"white"); out.paste(b,(0,50)); out.paste(a,(1440,50)); d=ImageDraw.Draw(out); d.text((24,18),"BEFORE",fill="#172538"); d.text((1464,18),"AFTER",fill="#172538"); d.line((1440,0,1440,1074),fill="#c9d6e3",width=2); out.save("screenshots/login-shadow-comparison.png")'
```

Inspect the combined image and confirm the image bottom reads as blue rather than black, the outer shadow is visibly lighter, text remains legible, and no layout or cropping changed.

- [ ] **Step 5: Record the visual QA**

Append a section to `design-qa.md` containing:

```markdown
source visual truth path: screenshots/login-shadow-before-1440.png
implementation desktop screenshot path: screenshots/login-shadow-after-1440.png
implementation mobile screenshot path: screenshots/login-shadow-after-mobile.png
comparison evidence path: screenshots/login-shadow-comparison.png
viewports: desktop 1440 x 1024; mobile 390 x 844

**Findings**
- No actionable P0/P1/P2 findings.

**Verification**
- Card shadow uses `rgba(53, 84, 115, 0.08) 0px 10px 24px`.
- Carousel tint uses the approved three academy-blue stops.
- Login geometry, CAPTCHA, controls, copyright, and horizontal overflow checks pass.

final result: passed
```

- [ ] **Step 6: Run complete verification**

Stop the local QA servers, then run:

```bash
npm run check
npm run test:e2e
git diff --check
```

Expected: 52 frontend tests pass; 230 backend tests pass with 2 skips; deploy utility tests pass; the Vite build and 8-route prerender pass; both Playwright flows pass; `git diff --check` reports no errors.

- [ ] **Step 7: Commit QA evidence and request independent review**

```bash
git add design-qa.md screenshots/login-shadow-before-1440.png screenshots/login-shadow-after-1440.png screenshots/login-shadow-after-mobile.png screenshots/login-shadow-comparison.png
git commit -m "docs: record login shadow visual QA"
```

Request a read-only review of the range from the pre-implementation commit through the QA commit. Resolve every Critical or Important finding and rerun affected tests.

- [ ] **Step 8: Merge, deploy, push, and verify production**

Fast-forward the reviewed branch into `main`, rerun `npm run check` and `npm run test:e2e`, then execute:

```bash
npm run deploy:jdcloud
git push origin main
```

Verify:

```bash
curl -fsS http://111.228.5.243/foundation-smart-companion/api/health
ssh -o BatchMode=yes jdcloud 'systemctl is-active foundation-smart-companion-api.service; readlink -f /opt/foundation-smart-companion'
gh run list --branch main --limit 5
```

Open `http://111.228.5.243/foundation-smart-companion/login/` in the in-app browser at 1440 x 1024. Confirm the approved computed styles, CAPTCHA load, no console errors, no overlap, no horizontal overflow, and exact copyright copy before completing the task.
