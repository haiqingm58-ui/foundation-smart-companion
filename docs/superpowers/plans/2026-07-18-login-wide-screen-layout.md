# Login Wide-Screen Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the login card proportionate on 1920px and 2560px full-screen displays without changing the approved standard desktop or mobile layouts.

**Architecture:** Add one large-screen media query to the page-local login CSS. The page uses a flexible middle grid row, the card scales within explicit width and height bounds, and the login panel receives a bounded column width while the carousel absorbs remaining growth. Extend the existing Playwright layout test to guard all four target viewports.

**Tech Stack:** React 19, CSS Grid, Vitest, Playwright, Vite

## Global Constraints

- Activate the enhancement only at viewport width `>= 1500px` and viewport height `>= 900px`.
- Use `width: min(2080px, 100%)` for the wide-screen card.
- Use `height: clamp(560px, calc(100vh - 360px), 900px)` for the wide-screen card.
- Keep the wide-screen login panel between `560px` and `680px`.
- Keep the Logo at `120px` on desktop and `78px` at `560px` and below.
- Preserve the exact copyright text `All Rights Reserved @2026`.
- Do not change authentication, CAPTCHA, role selection, carousel timing, image assets, colors, copy, form controls, or authenticated pages.

---

### Task 1: Guard And Implement The Wide-Screen Geometry

**Files:**
- Modify: `tests/e2e/login-layout.spec.mjs`
- Modify: `src/pages/login/LoginPage.css`

**Interfaces:**
- Consumes: Existing `.authPage`, `.authBrand`, `.authColumns`, `.loginCard`, `.collegeLogo`, and `.authCopyright` DOM contracts.
- Produces: A large-screen CSS breakpoint and browser-level geometry assertions for `1920 × 1080` and `2560 × 1440`.

- [ ] **Step 1: Extend the layout reader and add failing wide-screen assertions**

Extend `readLayout` while preserving its existing overlap value:

```js
const brand = rectOf(".authBrand");
const card = rectOf(".authColumns");
const loginPanel = rectOf(".loginCard");
const footer = rectOf(".authCopyright");

return {
  viewport: { width: window.innerWidth, height: window.innerHeight },
  page: {
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    scrollHeight: document.documentElement.scrollHeight,
  },
  brand,
  logo: rectOf(".collegeLogo"),
  card,
  loginPanel,
  footer,
  overlap: card && footer ? Math.max(0, card.bottom - footer.top) : null,
  footerText: document.querySelector(".authCopyright")?.textContent,
};
```

After the existing mobile assertions, add:

```js
for (const expected of [
  { viewport: { width: 1920, height: 1080 }, card: { width: 1792, height: 720 } },
  { viewport: { width: 2560, height: 1440 }, card: { width: 2080, height: 900 } },
]) {
  await page.setViewportSize(expected.viewport);
  const wide = await readLayout(page);
  const topGap = wide.card.top - wide.brand.bottom;
  const bottomGap = wide.footer.top - wide.card.bottom;
  const areaRatio = (wide.card.width * wide.card.height)
    / (wide.viewport.width * wide.viewport.height);

  expect(wide.card.width).toBeCloseTo(expected.card.width, 0);
  expect(wide.card.height).toBeCloseTo(expected.card.height, 0);
  expect(wide.loginPanel.width).toBeGreaterThanOrEqual(560);
  expect(wide.loginPanel.width).toBeLessThanOrEqual(680);
  expect(areaRatio).toBeGreaterThanOrEqual(0.5);
  expect(Math.abs(topGap - bottomGap)).toBeLessThanOrEqual(2);
  expect(bottomGap).toBeGreaterThanOrEqual(18);
  expect(wide.page.scrollWidth).toBeLessThanOrEqual(wide.page.clientWidth + 1);
}
```

- [ ] **Step 2: Run the focused browser test and verify RED**

Run:

```bash
npx playwright test tests/e2e/login-layout.spec.mjs
```

Expected: FAIL at the first wide-screen card-width assertion because the current card remains `1360px × 540px`.

- [ ] **Step 3: Add the large-screen CSS contract**

Insert this query before the existing `@media (max-width: 900px)` block:

```css
@media (min-width: 1500px) and (min-height: 900px) {
  .authPage {
    grid-template-rows: auto minmax(0, 1fr) auto;
  }

  .authColumns {
    width: min(2080px, 100%);
    height: clamp(560px, calc(100vh - 360px), 900px);
    margin-top: 0;
    align-self: center;
    grid-template-columns: minmax(0, 1fr) clamp(560px, 34vw, 680px);
  }
}
```

- [ ] **Step 4: Run the focused browser test and verify GREEN**

Run:

```bash
npx playwright test tests/e2e/login-layout.spec.mjs
```

Expected: 1 test passes. The existing 1440px and 390px assertions remain green, and both wide-screen assertions pass.

- [ ] **Step 5: Run the focused unit tests**

Run:

```bash
npx vitest run src/pages/login/LoginPage.test.jsx src/pages/login/LoginPage.logo.test.js
```

Expected: 7 login tests pass.

- [ ] **Step 6: Commit the implementation**

```bash
git add tests/e2e/login-layout.spec.mjs src/pages/login/LoginPage.css
git commit -m "fix: scale login layout on large screens"
```

---

### Task 2: Visual QA And Release

**Files:**
- Modify: `design-qa.md`
- Create: `screenshots/login-wide-after-1920.png`
- Create: `screenshots/login-wide-comparison.png`
- Create: `screenshots/login-wide-regression-1440.png`
- Create: `screenshots/login-wide-regression-mobile.png`

**Interfaces:**
- Consumes: Updated login route at `/foundation-smart-companion/login` and the existing production screenshot `/tmp/foundation-login-wide-1920.png` as before-state evidence.
- Produces: Visual comparison evidence, a passing design-QA record, deployed server release, and GitHub CI verification.

- [ ] **Step 1: Run the complete local gate**

Run:

```bash
npm run check
npm run test:e2e
```

Expected: 52 or more frontend tests pass, 230 backend tests pass with 2 conditional skips, deployment utility tests pass, production build and prerender pass, and both browser journeys pass.

- [ ] **Step 2: Capture the wide and regression viewports**

Start the local backend and Vite app with the existing E2E fixture database, then capture the login page at:

```text
1920 × 1080 -> screenshots/login-wide-after-1920.png
1440 × 1024 -> screenshots/login-wide-regression-1440.png
390 × 844   -> screenshots/login-wide-regression-mobile.png
```

At each viewport, read `.authBrand`, `.authColumns`, `.loginCard`, and `.authCopyright` rectangles. Expected: no overlap, no horizontal overflow, exact copyright copy, and the sizes from Task 1.

- [ ] **Step 3: Create and inspect the before/after comparison**

Place the before-state 1920 screenshot and `login-wide-after-1920.png` together in:

```text
screenshots/login-wide-comparison.png
```

Inspect the combined image for card proportion, balanced vertical spacing, image crop, form width, text fit, borders, radii, and footer placement. Fix any P0/P1/P2 issue and repeat the capture before proceeding.

- [ ] **Step 4: Record design QA**

Append a section to `design-qa.md` with:

```text
source visual truth: /tmp/foundation-login-wide-1920.png
implementation screenshot: screenshots/login-wide-after-1920.png
comparison evidence: screenshots/login-wide-comparison.png
viewports: 1920 × 1080, 1440 × 1024, 390 × 844
findings: no actionable P0/P1/P2 findings
final result: passed
```

- [ ] **Step 5: Commit QA evidence**

```bash
git add design-qa.md screenshots/login-wide-after-1920.png screenshots/login-wide-comparison.png screenshots/login-wide-regression-1440.png screenshots/login-wide-regression-mobile.png
git commit -m "docs: record wide-screen login QA"
```

- [ ] **Step 6: Request independent code review**

Provide the reviewer the design specification, this plan, and the implementation Git range. Resolve all Critical and Important findings before merging.

- [ ] **Step 7: Merge and deploy**

Fast-forward the approved branch into `main`, then run:

```bash
npm run deploy:jdcloud
git push origin main
```

Expected: the deployment script reports a release ending in the merged commit SHA, the API service is active, and the public health endpoint returns `status: ok`.

- [ ] **Step 8: Verify production and GitHub CI**

Open:

```text
http://111.228.5.243/foundation-smart-companion/login/
```

At `1920 × 1080`, verify the deployed card is `1792px × 720px`, the copyright is visible, CAPTCHA loads, no horizontal overflow exists, and browser console errors are empty. Confirm `origin/main`, the active server release, and the successful GitHub Actions run all use the same commit SHA.
