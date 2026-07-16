import { expect, test } from "@playwright/test";


const APP_PATH = "/foundation-smart-companion";
const QUESTION = "下列不属于土的三大特性之一的是";
const PAPER_TITLE = "E2E 土力学测验";
const TEACHER_FEEDBACK = "概念判断准确，继续保持当前复习节奏。";


async function authenticatedContext(browser, role) {
  const context = await browser.newContext();
  await context.addCookies([
    {
      name: "foundation_session",
      value: `e2e-${role}-token`,
      domain: "127.0.0.1",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    },
    {
      name: "foundation_csrf",
      value: `e2e-${role}-csrf`,
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


test("教师组卷发布、学生作答、教师批改、学生查看与随机续答形成完整闭环", async ({ browser }) => {
  const runtimeFailures = [];
  const teacherContext = await authenticatedContext(browser, "teacher");
  const teacherPage = await teacherContext.newPage();
  monitorRuntime(teacherPage, runtimeFailures);

  await teacherPage.goto(`${APP_PATH}/teacher/question-bank`);
  await expect(teacherPage.getByRole("heading", { name: "题库管理" })).toBeVisible();
  const questionFilters = teacherPage.locator(".assessmentQuestionFilters");
  await questionFilters.locator("label").filter({ hasText: "课程" }).locator("select").selectOption("soil-mechanics");
  await questionFilters.getByPlaceholder("搜索题干").fill(QUESTION);
  const bankRow = teacherPage.locator(".assessmentQuestionTable tbody tr").filter({ hasText: QUESTION });
  await expect(bankRow).toHaveCount(1);
  await expect(bankRow).toContainText("单项选择题");

  await teacherPage.goto(`${APP_PATH}/teacher/papers`);
  await expect(teacherPage.getByRole("heading", { name: "组卷中心" })).toBeVisible();
  await teacherPage.getByRole("button", { name: "新建试卷" }).click();
  const paperDialog = teacherPage.getByRole("dialog", { name: "新建试卷" });
  await expect(paperDialog).toBeVisible();
  await paperDialog.getByLabel("试卷课程").selectOption("soil-mechanics");
  await paperDialog.getByLabel("试卷标题").fill(PAPER_TITLE);
  await paperDialog.getByLabel("搜索可选题目").fill(QUESTION);
  const candidateRow = paperDialog.locator(".paperCandidateTable tbody tr").filter({ hasText: QUESTION });
  await expect(candidateRow).toHaveCount(1);
  await candidateRow.getByRole("button", { name: "加入试卷" }).click();
  await paperDialog.getByLabel("保存状态").selectOption("ready");
  await paperDialog.getByRole("button", { name: "保存试卷" }).click();
  await expect(paperDialog).toBeHidden();

  const paperRow = teacherPage.locator(".paperListTable tbody tr").filter({ hasText: PAPER_TITLE });
  await expect(paperRow).toHaveCount(1);
  await expect(paperRow).toContainText("1 题 / 10 分");
  await teacherPage.screenshot({ path: "output/playwright/assessment-teacher-desktop.png", fullPage: true });

  await teacherPage.setViewportSize({ width: 390, height: 844 });
  await teacherPage.waitForTimeout(250);
  const teacherMobileGeometry = await teacherPage.evaluate(() => ({
    viewport: window.innerWidth,
    bodyClientWidth: document.body.clientWidth,
    bodyScrollWidth: document.body.scrollWidth,
  }));
  expect(teacherMobileGeometry.bodyScrollWidth).toBeLessThanOrEqual(teacherMobileGeometry.bodyClientWidth + 1);
  await teacherPage.screenshot({ path: "output/playwright/assessment-teacher-mobile.png", fullPage: true });
  await teacherPage.setViewportSize({ width: 1440, height: 1000 });

  const downloadPromise = teacherPage.waitForEvent("download");
  await paperRow.getByRole("button", { name: "导出" }).click();
  await paperRow.getByRole("menuitem", { name: "Word 试题" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.docx$/);

  await paperRow.getByRole("button", { name: `发布试卷 ${PAPER_TITLE}` }).click();
  const publicationDialog = teacherPage.getByRole("dialog", { name: "发布试卷" });
  await publicationDialog.getByLabel("班级 基础工程演示班").check();
  const dueAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().slice(0, 16);
  await publicationDialog.getByLabel("截止时间").fill(dueAt);
  await publicationDialog.getByLabel("客观题自动判分").uncheck();
  await publicationDialog.getByRole("button", { name: "确认发布" }).click();
  await expect(publicationDialog).toBeHidden();
  await expect(teacherPage.getByRole("heading", { name: "考试与作业" })).toBeVisible();
  await expect(teacherPage.getByText(PAPER_TITLE, { exact: true })).toBeVisible();

  const studentContext = await authenticatedContext(browser, "student");
  const studentPage = await studentContext.newPage();
  monitorRuntime(studentPage, runtimeFailures);
  await studentPage.goto(`${APP_PATH}/student/practice`);
  await expect(studentPage.getByRole("heading", { name: "课程评测与自主练习" })).toBeVisible();
  await studentPage.getByRole("tab", { name: "我的试卷" }).click();
  const studentPaper = studentPage.locator(".studentPaperList article").filter({ hasText: PAPER_TITLE });
  await expect(studentPaper).toBeVisible();
  await studentPaper.getByRole("button", { name: "开始作答" }).click();
  await expect(studentPage.getByRole("heading", { name: QUESTION })).toBeVisible();
  await studentPage.getByLabel("B. 复杂性").check();
  await expect(studentPage.getByText("已保存", { exact: true })).toBeVisible();
  studentPage.once("dialog", (dialog) => dialog.accept());
  await studentPage.getByRole("button", { name: "交卷" }).click();
  await expect(studentPage.getByRole("heading", { name: "等待老师批改" })).toBeVisible();
  await studentPage.screenshot({ path: "output/playwright/assessment-student-result.png", fullPage: true });

  await teacherPage.goto(`${APP_PATH}/teacher/grading`);
  await expect(teacherPage.getByRole("heading", { name: "批改与成绩分析" })).toBeVisible();
  const submissionRow = teacherPage.locator(".assessmentTable tbody tr").filter({ hasText: PAPER_TITLE });
  await expect(submissionRow).toContainText("端到端学生");
  await submissionRow.getByRole("button", { name: "开始批改" }).click();
  const gradingDialog = teacherPage.getByRole("dialog", { name: "批改学生试卷" });
  const questionScore = gradingDialog.getByLabel(`题目得分 ${QUESTION}`);
  const questionMax = await questionScore.getAttribute("max");
  await questionScore.fill(questionMax);
  await gradingDialog.getByLabel("最终总分").fill(questionMax);
  await gradingDialog.getByLabel("总体评语").fill(TEACHER_FEEDBACK);
  await gradingDialog.getByRole("button", { name: "保存批改" }).click();
  await expect(gradingDialog).toBeHidden();

  await studentPage.reload();
  await studentPage.getByRole("tab", { name: "我的试卷" }).click();
  await studentPage.getByRole("tab", { name: /已批改\s+1/ }).click();
  const gradedPaper = studentPage.locator(".studentPaperList article").filter({ hasText: PAPER_TITLE });
  await gradedPaper.getByRole("button", { name: "查看结果" }).click();
  await expect(studentPage.getByRole("heading", { name: "本次作答已完成" })).toBeVisible();
  await expect(studentPage.getByText(TEACHER_FEEDBACK, { exact: true })).toBeVisible();
  await studentPage.screenshot({ path: "output/playwright/assessment-student-graded.png", fullPage: true });

  await studentPage.getByRole("button", { name: "返回" }).click();
  await studentPage.getByRole("tab", { name: "随机练习" }).click();
  await studentPage.getByRole("button", { name: "土力学" }).click();
  await studentPage.getByLabel("选择章节").selectOption("绪论");
  await studentPage.getByRole("button", { name: "开始随机练习" }).click();
  const firstQuestion = await studentPage.locator(".studentQuestionBody h2").textContent();
  expect(firstQuestion).toBeTruthy();
  const activeSessionId = await studentPage.evaluate(() => window.localStorage.getItem("student-active-practice-session"));
  expect(activeSessionId).toBeTruthy();
  await studentPage.reload();
  await expect(studentPage.locator(".studentQuestionBody h2")).toHaveText(firstQuestion);
  await studentPage.setViewportSize({ width: 390, height: 844 });
  const mobileGeometry = await studentPage.evaluate(() => {
    const session = document.querySelector(".studentSessionLayout");
    const page = document.querySelector(".studentAssessmentPage");
    const stage = document.querySelector(".studentQuestionStage");
    const actions = document.querySelector(".studentQuestionActions");
    const buttons = [...(actions?.querySelectorAll("button") || [])];
    return {
      viewport: window.innerWidth,
      body: { clientWidth: document.body.clientWidth, scrollWidth: document.body.scrollWidth },
      page: page ? { left: page.getBoundingClientRect().left, right: page.getBoundingClientRect().right, clientWidth: page.clientWidth, scrollWidth: page.scrollWidth } : null,
      session: session ? { left: session.getBoundingClientRect().left, right: session.getBoundingClientRect().right, clientWidth: session.clientWidth, scrollWidth: session.scrollWidth } : null,
      stage: stage ? { left: stage.getBoundingClientRect().left, right: stage.getBoundingClientRect().right, clientWidth: stage.clientWidth, scrollWidth: stage.scrollWidth } : null,
      actions: actions ? { left: actions.getBoundingClientRect().left, right: actions.getBoundingClientRect().right, clientWidth: actions.clientWidth, scrollWidth: actions.scrollWidth } : null,
      buttons: buttons.map((button) => ({ text: button.textContent, left: button.getBoundingClientRect().left, right: button.getBoundingClientRect().right, width: button.getBoundingClientRect().width })),
      sessionFits: Boolean(session) && session.scrollWidth <= session.clientWidth + 1,
      actionsFit: Boolean(actions) && actions.getBoundingClientRect().right <= window.innerWidth + 1,
      buttonsFit: buttons.every((button) => button.getBoundingClientRect().right <= window.innerWidth + 1),
    };
  });
  expect(mobileGeometry.sessionFits).toBe(true);
  expect(mobileGeometry.actionsFit).toBe(true);
  expect(mobileGeometry.buttonsFit).toBe(true);
  await studentPage.screenshot({ path: "output/playwright/assessment-student-mobile.png", fullPage: true });

  await expect.poll(() => runtimeFailures, { message: "页面运行时或 API 不应出现错误" }).toEqual([]);
  await teacherContext.close();
  await studentContext.close();
});
