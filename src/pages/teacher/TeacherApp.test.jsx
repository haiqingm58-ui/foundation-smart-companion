import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
    uploadResource: vi.fn(), createQuestion: vi.fn(), deleteQuestion: vi.fn(), createAssignment: vi.fn(), gradeSubmission: vi.fn(), createNotice: vi.fn(),
    previewQuestionImport: vi.fn(), importQuestions: vi.fn(), questionImportTemplateUrl: vi.fn(() => "/api/template.xlsx"),
  },
}));


function renderTeacher() {
  return render(
    <AuthContext.Provider value={{ user: { name: "周老师", role: "teacher", college: "土木工程学院" }, logout: vi.fn() }}>
      <MemoryRouter initialEntries={["/teacher"]}><TeacherApp /></MemoryRouter>
    </AuthContext.Provider>,
  );
}


test("教师工作台展示真实统计和完整导航", async () => {
  renderTeacher();
  expect(await screen.findByRole("heading", { name: "教学工作台" })).toBeInTheDocument();
  expect(screen.getByText("2")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /资料与 RAG/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /作业批改/ })).toBeInTheDocument();
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
