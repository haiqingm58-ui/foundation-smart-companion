# College Logo Crop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the white-padded college logo with a square, tightly cropped version and remove the login-page CSS scaling workaround.

**Architecture:** Keep the shared public asset path unchanged so login, portal, and password-change views update together. Add a focused asset/style regression test, then replace only the raster asset and the login logo rendering rule.

**Tech Stack:** React 19, Vite 6, Vitest 4, CSS, JPEG asset, FFmpeg crop detection, jpegtran lossless crop

## Global Constraints

- Preserve the complete official crest and all text exactly.
- Crop only the uniform outer white area and retain approximately 3% white safety space.
- Produce a square image centered on the crest.
- Keep existing desktop and mobile logo container dimensions unchanged.
- Do not alter login-page spacing, typography, carousel, or form layout.

---

### Task 1: Add the logo asset and rendering regression test

**Files:**
- Create: `src/pages/login/LoginPage.logo.test.js`
- Read: `public/college-logo.jpg`
- Read: `src/pages/login/LoginPage.css`

**Interfaces:**
- Consumes: the shared JPEG at `public/college-logo.jpg` and `.collegeLogo img` CSS rule.
- Produces: a Vitest regression that requires a square JPEG, `object-fit: contain`, and no image transform.

- [ ] **Step 1: Write the failing test**

```js
import { readFileSync } from "node:fs";
import { describe, expect, test } from "vitest";

function readJpegSize(buffer) {
  let offset = 2;
  while (offset < buffer.length) {
    if (buffer[offset] !== 0xff) throw new Error("Invalid JPEG marker");
    const marker = buffer[offset + 1];
    const length = buffer.readUInt16BE(offset + 2);
    if (marker >= 0xc0 && marker <= 0xc3) {
      return { height: buffer.readUInt16BE(offset + 5), width: buffer.readUInt16BE(offset + 7) };
    }
    offset += 2 + length;
  }
  throw new Error("JPEG dimensions not found");
}

describe("college logo asset", () => {
  test("uses a square cropped asset and renders without scale compensation", () => {
    const logo = readFileSync(new URL("../../../public/college-logo.jpg", import.meta.url));
    const css = readFileSync(new URL("./LoginPage.css", import.meta.url), "utf8");
    const dimensions = readJpegSize(logo);
    const imageRule = css.match(/\.collegeLogo img\s*\{([^}]*)\}/)?.[1] ?? "";

    expect(dimensions.width).toBe(dimensions.height);
    expect(imageRule).toMatch(/object-fit:\s*contain/);
    expect(imageRule).not.toMatch(/transform:/);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -- src/pages/login/LoginPage.logo.test.js`

Expected: FAIL because the current JPEG is `1429x1465`, uses `object-fit: cover`, and has `transform: scale(1.35)`.

### Task 2: Crop the shared asset and remove CSS compensation

**Files:**
- Modify: `public/college-logo.jpg`
- Modify: `src/pages/login/LoginPage.css:31-37`
- Test: `src/pages/login/LoginPage.logo.test.js`

**Interfaces:**
- Consumes: the current official crest as the edit target.
- Produces: a square cropped JPEG at the same public URL and a neutral `.collegeLogo img` rendering rule.

- [ ] **Step 1: Create the cropped image**

Detect the red crest bounds independently of the source image's white background and black edge artifact. The measured visible crest bounds are approximately `x=196..1196`, `y=254..1258`. Add about 3% safety space and align the crop to JPEG MCU boundaries:

```bash
jpegtran -copy all -perfect -crop 1088x1088+160+208 \
  -outfile /tmp/college-logo-cropped.jpg public/college-logo.jpg
```

Inspect the result at original detail. Reject it if any crest text or geometry is clipped. Replace `public/college-logo.jpg` only after the visual check passes.

- [ ] **Step 2: Update the rendering rule**

Replace the `.collegeLogo img` rule with:

```css
.collegeLogo img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 50%;
}
```

- [ ] **Step 3: Run the focused test**

Run: `npm test -- src/pages/login/LoginPage.logo.test.js`

Expected: PASS with one test passing.

- [ ] **Step 4: Commit the implementation**

```bash
git add public/college-logo.jpg src/pages/login/LoginPage.css src/pages/login/LoginPage.logo.test.js
git commit -m "fix: crop college logo whitespace"
```

### Task 3: Verify visuals, regressions, and deployment

**Files:**
- Verify: `public/college-logo.jpg`
- Verify: `src/pages/login/LoginPage.css`

**Interfaces:**
- Consumes: the built application and JDCloud deployment script.
- Produces: desktop/mobile visual evidence, passing checks, a live release, and a synchronized GitHub `main` branch.

- [ ] **Step 1: Run the complete project check**

Run: `npm run check`

Expected: all frontend, backend, deployment tests, production build, and prerendering pass.

- [ ] **Step 2: Start the preview server**

Run: `npm run preview -- --port 4173`

Expected: the app is available at `http://127.0.0.1:4173/foundation-smart-companion/`.

- [ ] **Step 3: Inspect desktop and mobile screenshots**

Capture the login page at `2048x1024` and `390x844`. Verify the full crest is centered, the surrounding white margin is even, no edge is clipped, and the page has no horizontal overflow.

- [ ] **Step 4: Deploy to JDCloud**

Run: `npm run deploy:jdcloud`

Expected: a new release is activated and the deployment script completes without an SSH timeout.

- [ ] **Step 5: Verify production and push GitHub**

Run `curl` against the production health endpoint and `college-logo.jpg`, then run `git push origin main`. Confirm the server returns HTTP 200 and local `HEAD` equals `origin/main`.
