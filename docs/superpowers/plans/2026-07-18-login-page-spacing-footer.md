# Login Page Spacing And Footer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the desktop login brand 16px lower and add the exact copyright text `All Rights Reserved @2026` at the page bottom without covering content.

**Architecture:** Keep the existing `LoginPage` component and page-local CSS. Add one semantic footer as the third grid item, reserve a flexible final grid row on desktop, and fall back to natural document flow at 900px and below.

**Tech Stack:** React 19, CSS Grid, Vitest, Testing Library, Playwright, Vite

## Global Constraints

- Keep the college logo at exactly 120px on desktop and 78px at 560px and below.
- Set the desktop page top padding to exactly 36px; preserve 20px at 900px and below.
- Render the exact text `All Rights Reserved @2026`.
- Use 12px muted neutral text with no footer bar, divider, fixed positioning, or new dependency.
- Do not change authentication, CAPTCHA, role selection, carousel behavior, or image assets.

---

### Task 1: Add The Copyright Layout Contract

**Files:**
- Modify: `src/pages/login/LoginPage.test.jsx`
- Modify: `src/pages/login/LoginPage.logo.test.js`
- Modify: `src/pages/login/LoginPage.jsx`
- Modify: `src/pages/login/LoginPage.css`

**Interfaces:**
- Consumes: Existing `LoginPage` render tree and `.authPage` grid.
- Produces: Semantic `.authCopyright` footer containing `All Rights Reserved @2026`.

- [ ] **Step 1: Write failing component and CSS contract tests**

Add this component test to `LoginPage.test.jsx`:

```jsx
test("登录页展示版权声明", () => {
  renderLogin();
  expect(screen.getByText("All Rights Reserved @2026")).toBeInTheDocument();
});
```

Add this test to the existing `college logo asset` describe block in `LoginPage.logo.test.js`:

```js
test("reserves desktop footer space and lowers the brand without resizing the logo", () => {
  const css = readFileSync(resolve(process.cwd(), "src/pages/login/LoginPage.css"), "utf8");
  const pageRule = css.match(/\.authPage\s*\{([^}]*)\}/)?.[1] ?? "";
  const logoRule = css.match(/\.collegeLogo\s*\{([^}]*)\}/)?.[1] ?? "";
  const footerRule = css.match(/\.authCopyright\s*\{([^}]*)\}/)?.[1] ?? "";

  expect(pageRule).toMatch(/padding:\s*36px/);
  expect(pageRule).toMatch(/grid-template-rows:\s*auto auto minmax\(24px, 1fr\)/);
  expect(logoRule).toMatch(/width:\s*120px/);
  expect(logoRule).toMatch(/height:\s*120px/);
  expect(footerRule).toMatch(/align-self:\s*end/);
});
```

- [ ] **Step 2: Run the targeted tests and verify RED**

Run:

```bash
npx vitest run src/pages/login/LoginPage.test.jsx src/pages/login/LoginPage.logo.test.js
```

Expected: the copyright query fails and the CSS contract test reports the current `20px` padding and missing footer rule.

- [ ] **Step 3: Implement the semantic footer**

Append the footer after `.authColumns` in `LoginPage.jsx`:

```jsx
<footer className="authCopyright">All Rights Reserved @2026</footer>
```

- [ ] **Step 4: Implement the responsive layout**

Update the desktop `.authPage` rule in `LoginPage.css`:

```css
.authPage {
  min-height: 100vh;
  background: #eef4f9;
  color: #172538;
  padding: 36px clamp(22px, 4vw, 64px) 24px;
  display: grid;
  grid-template-rows: auto auto minmax(24px, 1fr);
  gap: 18px;
}
```

Add the footer rule:

```css
.authCopyright {
  align-self: end;
  color: #75859a;
  font-size: 12px;
  line-height: 1.5;
  text-align: center;
}
```

Update the 900px media query so content flows naturally:

```css
.authPage {
  grid-template-rows: auto auto auto;
  align-content: start;
  padding: 20px 16px 24px;
}

.authCopyright {
  margin-top: 8px;
}
```

- [ ] **Step 5: Run targeted tests and verify GREEN**

Run:

```bash
npx vitest run src/pages/login/LoginPage.test.jsx src/pages/login/LoginPage.logo.test.js
```

Expected: 7 login tests pass with no failures.

- [ ] **Step 6: Commit the implementation**

```bash
git add src/pages/login/LoginPage.jsx src/pages/login/LoginPage.css src/pages/login/LoginPage.test.jsx src/pages/login/LoginPage.logo.test.js
git commit -m "fix: rebalance login header and add copyright"
```

### Task 2: Visual QA And Release

**Files:**
- Modify: `design-qa.md`
- Create: `screenshots/login-spacing-desktop.png`
- Create: `screenshots/login-spacing-mobile.png`

**Interfaces:**
- Consumes: Updated login page at `/foundation-smart-companion/login`.
- Produces: Desktop/mobile visual evidence, a passing QA record, and the deployed release.

- [ ] **Step 1: Run the full automated gate**

```bash
npm run check
npm run test:e2e
```

Expected: frontend tests, backend tests, deployment tests, production build, prerender, and the teacher/student browser journey all pass.

- [ ] **Step 2: Capture desktop and mobile login states**

Run the local app and capture `/foundation-smart-companion/login` at `1440 × 1024` and `390 × 844`. Save screenshots at the paths above.

Verify with browser DOM measurements:

```js
({
  horizontalOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  logoTop: document.querySelector('.collegeLogo').getBoundingClientRect().top,
  footerBottomGap: innerHeight - document.querySelector('.authCopyright').getBoundingClientRect().bottom,
})
```

Expected desktop: `horizontalOverflow` is `0`, `logoTop` is `36`, and the footer is visible below the card without overlap. Expected mobile: `horizontalOverflow` is `0` and the footer follows the login content.

- [ ] **Step 3: Record design QA**

Append a login-page section to `design-qa.md` containing the source screenshot path, both implementation screenshot paths, viewport measurements, no P0/P1/P2 findings, and `final result: passed`. If any overlap, clipping, or spacing mismatch exists, fix it and repeat Step 2 before marking the report passed.

- [ ] **Step 4: Commit QA evidence**

```bash
git add design-qa.md screenshots/login-spacing-desktop.png screenshots/login-spacing-mobile.png
git commit -m "test: verify responsive login page spacing"
```

- [ ] **Step 5: Deploy and verify production**

```bash
npm run deploy:jdcloud
curl -fsS http://111.228.5.243/foundation-smart-companion/api/health
```

Expected: deployment completes with the new release ID and the public API reports `status: ok`.

- [ ] **Step 6: Push GitHub and verify CI**

```bash
git push origin main
git ls-remote --heads origin main
```

Expected: remote `main` points to the final local commit and the `CI` workflow finishes successfully.
