import { expect, test } from "@playwright/test";


const APP_PATH = "/foundation-smart-companion";


async function studentContext(browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  await context.addCookies([
    {
      name: "foundation_session",
      value: "e2e-student-token",
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "foundation_csrf",
      value: "e2e-student-csrf",
      domain: "127.0.0.1",
      path: "/",
      sameSite: "Lax",
    },
  ]);
  return context;
}


function monitorRuntime(page, failures) {
  page.on("pageerror", (error) => failures.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") failures.push(`console: ${message.text()}`);
  });
  page.on("response", (response) => {
    if (response.url().includes("/api/") && response.status() >= 400) {
      failures.push(`api: ${response.status()} ${response.request().method()} ${response.url()}`);
    }
  });
}


test("学生以两轮问答使用桌面工作台并在手机查看引用", async ({ browser }) => {
  const failures = [];
  const context = await studentContext(browser);
  const page = await context.newPage();
  monitorRuntime(page, failures);

  await page.goto(`${APP_PATH}/student/qa`);
  await expect(page.getByRole("heading", { name: "智能问答" })).toBeVisible();
  await expect(page.getByText("问答服务已连接")).toBeVisible();

  const desktopLayout = await page.locator(".qaWorkbenchGrid").evaluate((element) => {
    const styles = getComputedStyle(element);
    const conversation = element.querySelector(".qaConversationPanel")?.getBoundingClientRect();
    const evidence = element.querySelector(".qaEvidenceRail")?.getBoundingClientRect();
    const composer = element.querySelector(".qaComposer")?.getBoundingClientRect();
    return {
      display: styles.display,
      columns: styles.gridTemplateColumns,
      conversationRight: conversation?.right,
      evidenceLeft: evidence?.left,
      composerBottom: composer?.bottom,
      viewportHeight: window.innerHeight,
    };
  });
  expect(desktopLayout.display).toBe("grid");
  expect(desktopLayout.columns).not.toBe("none");
  expect(desktopLayout.evidenceLeft).toBeGreaterThan(desktopLayout.conversationRight);
  expect(desktopLayout.composerBottom).toBeLessThanOrEqual(desktopLayout.viewportHeight + 1);

  await page.getByLabel("输入问题").fill("桩侧阻力如何产生？");
  await page.getByRole("button", { name: "发送问题" }).click();
  await expect(page.locator(".qaAssistantMessage:not(.loading)")).toHaveCount(1);
  await expect(page.getByText("RAG 检索模式")).toBeVisible();
  await expect(page.getByRole("complementary", { name: "回答依据" })).toContainText("桩侧阻力");

  await page.getByLabel("输入问题").fill("它受什么影响？");
  await page.getByRole("button", { name: "发送问题" }).click();
  await expect(page.locator(".qaAssistantMessage:not(.loading)")).toHaveCount(2);
  await expect(page.getByText("2 轮回答")).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  const populatedComposer = await page.locator(".qaComposer").evaluate((element) => ({
    bottom: element.getBoundingClientRect().bottom,
    viewportHeight: window.innerHeight,
  }));
  expect(populatedComposer.bottom).toBeLessThanOrEqual(populatedComposer.viewportHeight + 1);
  await page.screenshot({ path: "output/playwright/qa-workbench-desktop.png" });

  await page.setViewportSize({ width: 1024, height: 900 });
  await page.waitForTimeout(250);
  const tabletLayout = await page.locator(".qaWorkbenchGrid").evaluate((element) => {
    const conversation = element.querySelector(".qaConversationPanel")?.getBoundingClientRect();
    const evidence = element.querySelector(".qaEvidenceRail")?.getBoundingClientRect();
    return {
      columns: getComputedStyle(element).gridTemplateColumns,
      conversationBottom: conversation?.bottom,
      evidenceTop: evidence?.top,
    };
  });
  expect(tabletLayout.columns.trim().split(/\s+/)).toHaveLength(1);
  expect(tabletLayout.evidenceTop).toBeGreaterThan(tabletLayout.conversationBottom);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "output/playwright/qa-workbench-tablet.png" });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(250);
  const mobileLayout = await page.evaluate(() => {
    const rail = document.querySelector(".qaEvidenceRail");
    const mobileEvidence = document.querySelector(".qaMobileEvidence");
    return {
      bodyClientWidth: document.body.clientWidth,
      bodyScrollWidth: document.body.scrollWidth,
      railDisplay: rail ? getComputedStyle(rail).display : null,
      mobileEvidenceDisplay: mobileEvidence ? getComputedStyle(mobileEvidence).display : null,
    };
  });
  expect(mobileLayout.bodyScrollWidth).toBeLessThanOrEqual(mobileLayout.bodyClientWidth + 1);
  expect(mobileLayout.railDisplay).toBe("none");
  expect(mobileLayout.mobileEvidenceDisplay).not.toBe("none");
  await page.screenshot({ path: "output/playwright/qa-workbench-mobile.png", fullPage: true });

  await expect.poll(() => failures, { message: "问答页不应出现运行时或 API 错误" }).toEqual([]);
  await context.close();
});
