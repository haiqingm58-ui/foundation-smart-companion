import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { AuthContext } from "../../stores/AuthContext.jsx";
import { teacherApi } from "../../api/teacher.js";
import TeacherApp from "./TeacherApp.jsx";


vi.mock("../../api/teacher.js", () => ({
  teacherApi: {
    dashboard: vi.fn(async () => ({ classTotal: 1, studentTotal: 2, resourceTotal: 3, questionTotal: 4, assignmentTotal: 1, pendingGrading: 1, averageScore: 78, completionRate: 60 })),
    classes: vi.fn(async () => ({ items: [{ id: "c1", name: "土木2401班", grade: "2024", major: "土木工程" }], total: 1 })),
    students: vi.fn(async () => ({ items: [{ id: "s1", name: "王同学", studentNo: "20260001", className: "土木2401班", progress: 45, averageScore: 82, status: "active" }], total: 1 })),
    resources: vi.fn(async () => ({ items: [{ id: "r1", title: "桩基础讲义", name: "pile.pdf", chapter: "第3章 桩基础", visibility: "class", fileSize: 1024 }], total: 1 })),
    questions: vi.fn(async () => ({ items: [], total: 0 })),
    assignments: vi.fn(async () => ({ items: [], total: 0 })),
    submissions: vi.fn(async () => ({ items: [], total: 0 })),
    analytics: vi.fn(async () => ({ studentTotal: 2, averageScore: 78, averageProgress: 45, weakKnowledgePoints: [], scoreTrend: [] })),
    notices: vi.fn(async () => ({ items: [], total: 0 })),
    uploadResource: vi.fn(), createQuestion: vi.fn(), updateQuestion: vi.fn(), deleteQuestion: vi.fn(), copyQuestion: vi.fn(), createAssignment: vi.fn(), gradeSubmission: vi.fn(), createNotice: vi.fn(),
    previewQuestionImport: vi.fn(), importQuestions: vi.fn(), questionImportTemplateUrl: vi.fn(() => "/api/template.xlsx"),
  },
}));


function renderTeacher(logout = vi.fn(), initialEntry = "/teacher") {
  return render(
    <AuthContext.Provider value={{ user: { name: "周老师", role: "teacher", college: "土木工程学院" }, logout }}>
      <MemoryRouter initialEntries={[initialEntry]}><TeacherApp /></MemoryRouter>
    </AuthContext.Provider>,
  );
}


function canonicalQuestion(overrides = {}) {
  return {
    id: "canonical-question", text: "达西定律适用于何种流态？", subjectId: "soil-mechanics", chapter: "第二章 土的渗透性",
    knowledgePoints: [{ id: "soil-darcy", name: "达西定律", weight: 1 }], questionType: "单项选择题", difficulty: "中等", points: 10,
    options: [{ label: "A", text: "层流" }, { label: "B", text: "紊流" }], correctAnswer: "A",
    explanation: "考查适用条件", rubric: [{ criterion: "依据", points: 10 }], attachments: [{ kind: "formula", latex: "k" }], gradingMode: "auto", status: "active", editable: true,
    ...overrides,
  };
}


beforeEach(() => vi.clearAllMocks());


test("教师工作台展示真实统计和完整导航", async () => {
  renderTeacher();
  expect(await screen.findByRole("heading", { name: "教学工作台" })).toBeInTheDocument();
  expect(screen.getByText("2")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /资料与 RAG/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /作业批改/ })).toBeInTheDocument();
});


test("教师工作台顶部提供明确可用的退出按钮", async () => {
  const logout = vi.fn(async () => {});
  renderTeacher(logout);
  await screen.findByRole("heading", { name: "教学工作台" });
  fireEvent.click(screen.getByRole("button", { name: "从顶部退出登录" }));
  await waitFor(() => expect(logout).toHaveBeenCalledTimes(1));
});


test("教师可切换到资料库并看到真实资料", async () => {
  renderTeacher();
  await screen.findByRole("heading", { name: "教学工作台" });
  fireEvent.click(screen.getByRole("button", { name: /资料与 RAG/ }));
  expect(await screen.findByText("桩基础讲义")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("已进入 RAG 知识库")).toBeInTheDocument());
});


test("题库批量导入显示预检错误并阻止入库", async () => {
  teacherApi.previewQuestionImport.mockResolvedValueOnce({
    summary: { total: 2, valid: 1, errors: 1 },
    rows: [{ text: "桩基础题目", questionType: "简答题", chapter: "第3章 桩基础", difficulty: "基础", points: 10 }],
    errors: [{ row: 3, field: "正确答案", code: "ANSWER_REQUIRED", reason: "正确答案不能为空" }],
  });
  renderTeacher();
  await screen.findByRole("heading", { name: "教学工作台" });
  fireEvent.click(screen.getByRole("button", { name: /题库管理/ }));
  await screen.findByRole("heading", { name: "题库管理" });
  fireEvent.click(screen.getByRole("button", { name: "批量导入" }));
  expect(screen.getByRole("dialog", { name: "批量导入题库" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "下载题库模板" })).toHaveAttribute("href", "/api/template.xlsx");
  fireEvent.change(screen.getByLabelText("选择题库文件"), { target: { files: [new File(["content"], "questions.xlsx")] } });
  fireEvent.click(screen.getByRole("button", { name: "上传并预检" }));
  expect(await screen.findByText("第 3 行 · 正确答案：正确答案不能为空")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "下一步：确认导入" })).toBeDisabled();
});


test("干净的题库预检结果可以确认入库", async () => {
  const row = { text: "桩侧负摩阻力何时产生？", questionType: "简答题", chapter: "第3章 桩基础", difficulty: "中等", points: 12 };
  teacherApi.previewQuestionImport.mockResolvedValueOnce({ summary: { total: 1, valid: 1, errors: 0 }, rows: [row], errors: [] });
  teacherApi.importQuestions.mockResolvedValueOnce({ created: 1 });
  renderTeacher();
  await screen.findByRole("heading", { name: "教学工作台" });
  fireEvent.click(screen.getByRole("button", { name: /题库管理/ }));
  await screen.findByRole("heading", { name: "题库管理" });
  fireEvent.click(screen.getByRole("button", { name: "批量导入" }));
  fireEvent.change(screen.getByLabelText("选择题库文件"), { target: { files: [new File(["content"], "questions.xlsx")] } });
  fireEvent.click(screen.getByRole("button", { name: "上传并预检" }));
  const next = await screen.findByRole("button", { name: "下一步：确认导入" });
  expect(next).toBeEnabled();
  fireEvent.click(next);
  fireEvent.click(screen.getByRole("button", { name: "确认入库" }));
  await waitFor(() => expect(teacherApi.importQuestions).toHaveBeenCalledWith([row]));
});


test("编辑土力学题目时保留 canonical subjectId 和全部知识点 ID", async () => {
  const soilQuestion = {
    id: "soil-question", text: "达西定律适用于何种流态？", subjectId: "soil-mechanics", chapter: "第二章 土的渗透性",
    knowledgePoints: [{ id: "soil-darcy", name: "达西定律", weight: 0.5 }, { id: "soil-permeability", name: "土的渗透性", weight: 0.5 }],
    questionType: "单项选择题", difficulty: "中等", points: 10,
    options: [{ label: "A", text: "层流" }, { label: "B", text: "紊流" }], correctAnswer: "A",
    explanation: "考查适用条件", rubric: [], attachments: [], gradingMode: "auto", status: "active", editable: true,
  };
  teacherApi.questions.mockResolvedValueOnce({ items: [soilQuestion], total: 1 });
  teacherApi.updateQuestion.mockResolvedValueOnce(soilQuestion);
  renderTeacher(vi.fn(), "/teacher/question-bank");
  await screen.findByText(soilQuestion.text);
  fireEvent.click(screen.getByRole("button", { name: "编辑" }));
  fireEvent.click(screen.getByRole("button", { name: "保存题目" }));
  await waitFor(() => expect(teacherApi.updateQuestion).toHaveBeenCalledWith(
    soilQuestion.id,
    expect.objectContaining({ subjectId: "soil-mechanics", knowledgePointIds: ["soil-darcy", "soil-permeability"] }),
  ));
  expect(teacherApi.updateQuestion.mock.calls[0][1]).not.toHaveProperty("knowledgePoint");
});


test("共享题目只显示复制操作，复制后以待复核的可编辑副本打开", async () => {
  const shared = {
    id: "shared-import", text: "共享导入题", subjectId: "soil-mechanics", chapter: "第二章 土的渗透性",
    knowledgePoints: [{ id: "soil-darcy", name: "达西定律", weight: 1 }], questionType: "判断题", difficulty: "基础", points: 5,
    options: [], correctAnswer: true, rubric: [], attachments: [], gradingMode: "auto", source: "imported", status: "active", editable: false,
  };
  const owned = { ...shared, id: "owned-question", text: "教师自建题", source: "teacher", editable: true };
  const copied = { ...shared, id: "copied-question", text: "共享导入题（副本）", source: "teacher-copy", createdBy: "teacher-user-1", status: "review_required", editable: true };
  teacherApi.questions.mockResolvedValueOnce({ items: [shared, owned], total: 2 }).mockResolvedValueOnce({ items: [shared, owned, copied], total: 3 });
  teacherApi.copyQuestion.mockResolvedValueOnce(copied);
  teacherApi.updateQuestion.mockResolvedValueOnce(copied);
  renderTeacher(vi.fn(), "/teacher/question-bank");
  const sharedRow = (await screen.findByText(shared.text)).closest("tr");
  const ownedRow = screen.getByText(owned.text).closest("tr");
  expect(within(sharedRow).getByRole("button", { name: "复制到我的题库" })).toBeInTheDocument();
  expect(within(sharedRow).queryByRole("button", { name: "编辑" })).not.toBeInTheDocument();
  expect(within(sharedRow).queryByRole("button", { name: /删除题目/ })).not.toBeInTheDocument();
  expect(within(ownedRow).getByRole("button", { name: "编辑" })).toBeInTheDocument();
  expect(within(ownedRow).getByRole("button", { name: /删除题目/ })).toBeInTheDocument();
  fireEvent.click(within(sharedRow).getByRole("button", { name: "复制到我的题库" }));
  await waitFor(() => expect(teacherApi.copyQuestion).toHaveBeenCalledWith(shared.id));
  expect(await screen.findByText("题目副本已创建，待复核")).toBeInTheDocument();
  expect(await screen.findByRole("dialog", { name: "编辑题目" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "保存题目" }));
  await waitFor(() => expect(teacherApi.updateQuestion).toHaveBeenCalledWith(copied.id, expect.objectContaining({ subjectId: "soil-mechanics", knowledgePointIds: ["soil-darcy"] })));
});


test("教材共享题目只能复制，复制的判断题 false 保持布尔载荷", async () => {
  const textbook = canonicalQuestion({
    id: "textbook-boolean", text: "土的渗透性是否受孔隙比影响？", questionType: "判断题", options: [], correctAnswer: false,
    source: "textbook", editable: false,
  });
  const copied = canonicalQuestion({ ...textbook, id: "copied-boolean", source: "teacher-copy", createdBy: "teacher-user-1", status: "review_required", editable: true });
  teacherApi.questions.mockResolvedValueOnce({ items: [textbook], total: 1 }).mockResolvedValueOnce({ items: [textbook, copied], total: 2 });
  teacherApi.copyQuestion.mockResolvedValueOnce(copied);
  teacherApi.updateQuestion.mockResolvedValueOnce(copied);
  renderTeacher(vi.fn(), "/teacher/question-bank");
  const row = (await screen.findByText(textbook.text)).closest("tr");
  expect(within(row).getByRole("button", { name: "复制到我的题库" })).toBeInTheDocument();
  expect(within(row).queryByRole("button", { name: "编辑" })).not.toBeInTheDocument();
  expect(within(row).queryByRole("button", { name: /删除题目/ })).not.toBeInTheDocument();
  fireEvent.click(within(row).getByRole("button", { name: "复制到我的题库" }));
  expect(await screen.findByRole("dialog", { name: "编辑题目" })).toBeInTheDocument();
  expect(screen.getByLabelText("标准答案")).toHaveValue("false");
  fireEvent.click(screen.getByRole("button", { name: "保存题目" }));
  await waitFor(() => expect(teacherApi.updateQuestion).toHaveBeenCalledWith(copied.id, {
    text: copied.text, questionType: "判断题", difficulty: copied.difficulty, points: copied.points, chapter: copied.chapter,
    correctAnswer: false, explanation: copied.explanation, options: copied.options, rubric: copied.rubric, attachments: copied.attachments,
    gradingMode: copied.gradingMode, answerWordLimit: undefined, subjectId: copied.subjectId, knowledgePointIds: ["soil-darcy"],
  }));
});


test("编辑多项选择题时以 JSON 数组保留所有正确选项", async () => {
  const question = canonicalQuestion({
    id: "multiple-choice", questionType: "多项选择题", options: [{ label: "A", text: "层流" }, { label: "B", text: "紊流" }, { label: "C", text: "稳定流" }], correctAnswer: ["A", "C"],
  });
  teacherApi.questions.mockResolvedValueOnce({ items: [question], total: 1 });
  teacherApi.updateQuestion.mockResolvedValueOnce(question);
  renderTeacher(vi.fn(), "/teacher/question-bank");
  await screen.findByText(question.text);
  fireEvent.click(screen.getByRole("button", { name: "编辑" }));
  expect(screen.getByLabelText(/标准答案（JSON 字符串数组）/)).toHaveValue('["A","C"]');
  fireEvent.click(screen.getByRole("button", { name: "保存题目" }));
  await waitFor(() => expect(teacherApi.updateQuestion).toHaveBeenCalledWith(question.id, {
    text: question.text, questionType: "多项选择题", difficulty: question.difficulty, points: question.points, chapter: question.chapter,
    correctAnswer: ["A", "C"], explanation: question.explanation, options: question.options, rubric: question.rubric, attachments: question.attachments,
    gradingMode: question.gradingMode, answerWordLimit: undefined, subjectId: question.subjectId, knowledgePointIds: ["soil-darcy"],
  }));
});


test("编辑填空题时以 JSON 同义答案列表保留生产载荷", async () => {
  const question = canonicalQuestion({ id: "fill-blank", questionType: "填空题", options: [], correctAnswer: ["太沙基", "Terzaghi"] });
  teacherApi.questions.mockResolvedValueOnce({ items: [question], total: 1 });
  teacherApi.updateQuestion.mockResolvedValueOnce(question);
  renderTeacher(vi.fn(), "/teacher/question-bank");
  await screen.findByText(question.text);
  fireEvent.click(screen.getByRole("button", { name: "编辑" }));
  expect(screen.getByLabelText(/标准答案（JSON 同义答案数组）/)).toHaveValue('["太沙基","Terzaghi"]');
  fireEvent.click(screen.getByRole("button", { name: "保存题目" }));
  await waitFor(() => expect(teacherApi.updateQuestion).toHaveBeenCalledWith(question.id, {
    text: question.text, questionType: "填空题", difficulty: question.difficulty, points: question.points, chapter: question.chapter,
    correctAnswer: ["太沙基", "Terzaghi"], explanation: question.explanation, options: question.options, rubric: question.rubric, attachments: question.attachments,
    gradingMode: question.gradingMode, answerWordLimit: undefined, subjectId: question.subjectId, knowledgePointIds: ["soil-darcy"],
  }));
});


test("多项选择题的无效 JSON 在前端提示且不提交", async () => {
  const question = canonicalQuestion({ id: "invalid-json", questionType: "多项选择题", correctAnswer: ["A"] });
  teacherApi.questions.mockResolvedValueOnce({ items: [question], total: 1 });
  renderTeacher(vi.fn(), "/teacher/question-bank");
  await screen.findByText(question.text);
  fireEvent.click(screen.getByRole("button", { name: "编辑" }));
  fireEvent.change(screen.getByLabelText(/标准答案（JSON 字符串数组）/), { target: { value: "A, B" } });
  fireEvent.click(screen.getByRole("button", { name: "保存题目" }));
  expect(await screen.findByText("多项选择题答案必须是 JSON 字符串数组")).toBeInTheDocument();
  expect(teacherApi.updateQuestion).not.toHaveBeenCalled();
});


test("填空题的非字符串 JSON 列表在前端提示且不提交", async () => {
  const question = canonicalQuestion({ id: "invalid-fill", questionType: "填空题", options: [], correctAnswer: ["太沙基"] });
  teacherApi.questions.mockResolvedValueOnce({ items: [question], total: 1 });
  renderTeacher(vi.fn(), "/teacher/question-bank");
  await screen.findByText(question.text);
  fireEvent.click(screen.getByRole("button", { name: "编辑" }));
  fireEvent.change(screen.getByLabelText(/标准答案（JSON 同义答案数组）/), { target: { value: '["太沙基", 1]' } });
  fireEvent.click(screen.getByRole("button", { name: "保存题目" }));
  expect(await screen.findByText("填空题答案必须是 JSON 同义答案数组")).toBeInTheDocument();
  expect(teacherApi.updateQuestion).not.toHaveBeenCalled();
});
