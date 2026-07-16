import { resolve } from "node:path";
import { defineConfig, devices } from "@playwright/test";


const root = resolve(import.meta.dirname);
const e2eRoot = resolve(root, "output/e2e");
const serverEnv = {
  ...process.env,
  FOUNDATION_DATABASE_URL: `sqlite:///${resolve(e2eRoot, "e2e.db")}`,
  FOUNDATION_SECRET_KEY: "e2e-only-secret",
  FOUNDATION_DATA_DIR: resolve(e2eRoot, "data"),
  FOUNDATION_UPLOAD_DIR: resolve(e2eRoot, "uploads"),
  FOUNDATION_COOKIE_PATH: "/",
};


export default defineConfig({
  testDir: "./tests/e2e",
  outputDir: "./output/playwright/results",
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  reporter: [["list"], ["html", { outputFolder: "output/playwright/report", open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer: [
    {
      command: "server/.venv/bin/python tests/e2e/prepare_e2e.py && server/.venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8000",
      cwd: root,
      env: serverEnv,
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173",
      cwd: root,
      url: "http://127.0.0.1:5173/foundation-smart-companion/login",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
  projects: [
    {
      name: "chromium-desktop",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
