import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { teacherApi } from "../../../api/teacher.js";
import { BlueprintBuilder } from "./BlueprintBuilder.jsx";
import { ExportMenu } from "./ExportMenu.jsx";
import { PaperBuilder } from "./PaperBuilder.jsx";
import { PaperList } from "./PaperList.jsx";
import { PublicationDialog } from "./PublicationDialog.jsx";
import { SubmissionGrading } from "./SubmissionGrading.jsx";


vi.mock("../../../api/teacher.js", () => ({
  teacherApi: {
    papers: vi.fn(), paper: vi.fn(), createPaper: vi.fn(), updatePaper: vi.fn(), copyPaper: vi.fn(), deletePaper: vi.fn(),
    generatePaperPreview: vi.fn(), publishPaper: vi.fn(), paperExportUrl: vi.fn((id, format, variant) => `/api/teacher/papers/${id}/export?format=${format}&variant=${variant}`),
    questions: vi.fn(), knowledgePoints: vi.fn(), classes: vi.fn(), students: vi.fn(), assignments: vi.fn(),
    submissions: vi.fn(), submission: vi.fn(), gradeSubmission: vi.fn(),
  },
}));


const subjects = [{ id: "soil-mechanics", title: "土力学", questionCount: 120, knowledgePointCount: 50 }];
const points = [
  { id: "kp-1", subjectId: "soil-mechanics", chapter: "第二章 土的渗透性", name: "达西定律" },
  { id: "kp-2", subjectId: "soil-mechanics", chapter: "第二章 土的渗透性", name: "渗透系数" },
];
const questions = [
  { id: "q-1", subjectId: "soil-mechanics", chapter: "第二章 土的渗透性", text: "达西定律适用于哪种流态？", questionType: "单项选择题", difficulty: "基础", points: 5, knowledgePoints: [{ id: "kp-1", name: "达西定律" }] },
  { id: "q-2", subjectId: "soil-mechanics", chapter: "第二章 土的渗透性", text: "说明渗透系数的影响因素。", questionType: "简答题", difficulty: "中等", points: 10, knowledgePoints: [{ id: "kp-2", name: "渗透系数" }] },
];


beforeEach(() => {
  vi.clearAllMocks();
  teacherApi.questions.mockResolvedValue({ items: questions, total: 2 });
  teacherApi.knowledgePoints.mockResolvedValue({ items: points, total: 2 });
  teacherApi.papers.mockResolvedValue({ items: [], total: 0 });
  teacherApi.assignments.mockResolvedValue({ items: [], total: 0 });
  teacherApi.classes.mockResolvedValue({ items: [{ id: "class-1", name: "基础工程演示班", grade: "2026", major: "土木工程" }], total: 1 });
  teacherApi.students.mockResolvedValue({ items: [{ id: "student-1", name: "张同学", studentNo: "20260001", classId: "class-1", className: "基础工程演示班" }], total: 1 });
  teacherApi.submissions.mockResolvedValue({ items: [], total: 0 });
});


test("手动组卷可选题、调整顺序章节分值并保存结构化试卷", async () => {
  const onSaved = vi.fn();
  teacherApi.createPaper.mockResolvedValue({ id: "paper-1", version: 1 });
  render(<PaperBuilder subjects={subjects} onSaved={onSaved} onCancel={vi.fn()} />);

  expect(await screen.findByText(questions[0].text)).toBeInTheDocument();
  fireEvent.click(within(screen.getByText(questions[0].text).closest("tr")).getByRole("button", { name: "加入试卷" }));
  fireEvent.click(within(screen.getByText(questions[1].text).closest("tr")).getByRole("button", { name: "加入试卷" }));
  fireEvent.click(screen.getByRole("button", { name: `下移 ${questions[0].text}` }));
  fireEvent.change(screen.getByLabelText(`章节 ${questions[1].text}`), { target: { value: "一、简答题" } });
  fireEvent.change(screen.getByLabelText(`分值 ${questions[1].text}`), { target: { value: "15" } });
  fireEvent.change(screen.getByLabelText("试卷标题"), { target: { value: "土力学单元测验" } });
  fireEvent.click(screen.getByRole("button", { name: "保存试卷" }));

  await waitFor(() => expect(teacherApi.createPaper).toHaveBeenCalledWith(expect.objectContaining({
    subjectId: "soil-mechanics",
    title: "土力学单元测验",
    assemblyMode: "manual",
    questions: [
      expect.objectContaining({ questionId: "q-2", sequence: 1, sectionTitle: "一、简答题", points: 15 }),
      expect.objectContaining({ questionId: "q-1", sequence: 2 }),
    ],
  })));
  expect(onSaved).toHaveBeenCalled();
});


test("自动组卷准确展示缺题且不静默放宽条件", async () => {
  teacherApi.generatePaperPreview.mockResolvedValue({
    questions: [], coverage: {}, typeDistribution: {}, difficultyDistribution: {}, duplicateRisk: 0,
    shortages: [{ row: 1, requested: 5, available: 2, missing: 3, criteria: { questionTypes: ["多项选择题"], knowledgePointIds: ["kp-1"] } }],
  });
  render(<BlueprintBuilder subjectId="soil-mechanics" knowledgePoints={points} onApply={vi.fn()} />);

  fireEvent.change(screen.getByLabelText("第 1 行题型"), { target: { value: "多项选择题" } });
  fireEvent.change(screen.getByLabelText("第 1 行知识点"), { target: { value: "kp-1" } });
  fireEvent.change(screen.getByLabelText("第 1 行题量"), { target: { value: "5" } });
  fireEvent.click(screen.getByRole("button", { name: "生成预览" }));

  expect(await screen.findByText("第 1 组还缺 3 题（需要 5 题，当前 2 题）")).toBeInTheDocument();
  expect(screen.getByText("系统未放宽任何章节、知识点、题型或难度条件")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "使用本次组卷结果" })).toBeDisabled();
});


test("自动组卷预览显示覆盖度、题型难度和重复风险", async () => {
  teacherApi.generatePaperPreview.mockResolvedValue({
    questions, coverage: { "kp-1": 1, "kp-2": 1 }, typeDistribution: { 单项选择题: 1, 简答题: 1 },
    difficultyDistribution: { 基础: 1, 中等: 1 }, duplicateRisk: 0, shortages: [],
  });
  const onApply = vi.fn();
  render(<BlueprintBuilder subjectId="soil-mechanics" knowledgePoints={points} onApply={onApply} />);
  fireEvent.click(screen.getByRole("button", { name: "生成预览" }));
  expect(await screen.findByText("覆盖 2 个知识点")).toBeInTheDocument();
  expect(screen.getByText("重复风险 0")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "使用本次组卷结果" }));
  expect(onApply).toHaveBeenCalledWith(expect.objectContaining({ shortages: [] }), expect.any(Array));
});


test("自动组卷保存时沿用教师确认预览的随机种子", async () => {
  const dateSpy = vi.spyOn(Date, "now").mockReturnValueOnce(101).mockReturnValueOnce(202);
  teacherApi.generatePaperPreview.mockResolvedValue({
    questions, coverage: { "kp-1": 1, "kp-2": 1 }, typeDistribution: {}, difficultyDistribution: {}, duplicateRisk: 0, shortages: [],
  });
  teacherApi.createPaper.mockResolvedValue({ id: "paper-auto", version: 1 });
  render(<PaperBuilder subjects={subjects} onSaved={vi.fn()} onCancel={vi.fn()} />);
  await screen.findByText(questions[0].text);
  fireEvent.click(screen.getByRole("tab", { name: "自动组卷" }));
  fireEvent.click(screen.getByRole("button", { name: "生成预览" }));
  await screen.findByText("覆盖 2 个知识点");
  fireEvent.click(screen.getByRole("button", { name: "使用本次组卷结果" }));
  fireEvent.change(screen.getByLabelText("试卷标题"), { target: { value: "自动组卷测验" } });
  fireEvent.click(screen.getByRole("button", { name: "保存试卷" }));
  await waitFor(() => expect(teacherApi.createPaper).toHaveBeenCalled());
  expect(teacherApi.createPaper.mock.calls[0][0].seed).toBe(teacherApi.generatePaperPreview.mock.calls[0][0].seed);
  dateSpy.mockRestore();
});


test("试卷列表展示版本并可复制为新草稿", async () => {
  const paper = { id: "paper-1", subjectId: "soil-mechanics", title: "渗流测验", status: "ready", version: 3, questionCount: 12, totalPoints: 100, durationMinutes: 60, updatedAt: "2026-07-16T08:00:00Z" };
  teacherApi.papers.mockResolvedValueOnce({ items: [paper], total: 1 }).mockResolvedValueOnce({ items: [paper, { ...paper, id: "paper-copy", title: "渗流测验 副本", status: "draft", version: 1 }], total: 2 });
  teacherApi.copyPaper.mockResolvedValue({ ...paper, id: "paper-copy", status: "draft", version: 1 });
  render(<PaperList subjects={subjects} defaultTab="papers" notify={vi.fn()} />);
  expect(await screen.findByText("v3")).toBeInTheDocument();
  const row = screen.getByText("渗流测验").closest("tr");
  fireEvent.click(within(row).getByRole("button", { name: "复制试卷 渗流测验" }));
  await waitFor(() => expect(teacherApi.copyPaper).toHaveBeenCalledWith("paper-1"));
  expect(await screen.findByText("渗流测验 副本")).toBeInTheDocument();
});


test("发布只提供绑定目标并明确生成不可变快照", async () => {
  const paper = { id: "paper-1", title: "土力学期中测验", description: "", durationMinutes: 90, totalPoints: 100, questionCount: 20, shortages: [] };
  teacherApi.publishPaper.mockResolvedValue({ assignmentId: "assignment-1", targetCount: 1, status: "published" });
  render(<PublicationDialog paper={paper} classes={[{ id: "class-1", name: "基础工程演示班" }]} students={[{ id: "student-1", name: "张同学", studentNo: "20260001", classId: "class-1" }]} onClose={vi.fn()} onPublished={vi.fn()} />);

  expect(screen.getByText("发布后题目、答案、评分规则和附件将生成不可变快照")).toBeInTheDocument();
  expect(screen.queryByText("其他教师班级")).not.toBeInTheDocument();
  fireEvent.click(screen.getByLabelText("班级 基础工程演示班"));
  fireEvent.change(screen.getByLabelText("截止时间"), { target: { value: "2026-07-20T18:00" } });
  fireEvent.click(screen.getByRole("button", { name: "确认发布" }));
  await waitFor(() => expect(teacherApi.publishPaper).toHaveBeenCalledWith("paper-1", expect.objectContaining({ classIds: ["class-1"], studentIds: [] })));
});


test("批改界面展示快照答案评分项并允许总分复核", async () => {
  const submission = { id: "submission-1", assignmentTitle: "土力学期中测验", studentName: "张同学", studentNo: "20260001", status: "pending_review", score: null, submittedAt: "2026-07-16T08:00:00Z" };
  teacherApi.submissions.mockResolvedValue({ items: [submission], total: 1 });
  teacherApi.submission.mockResolvedValue({ ...submission, totalPoints: 20, feedback: "", questions: [{
    questionId: "q-2", text: "说明渗透系数的影响因素。", questionType: "简答题", answer: "与土粒级配和孔隙比有关。", points: 20,
    rubric: [{ criterion: "指出级配", points: 8 }, { criterion: "指出孔隙比", points: 8 }], score: null, criteriaScores: {}, confidence: 0.52, gradingMode: "manual",
  }] });
  teacherApi.gradeSubmission.mockResolvedValue({ id: "submission-1", score: 18, status: "graded" });
  render(<SubmissionGrading notify={vi.fn()} />);

  const row = (await screen.findByText("土力学期中测验")).closest("tr");
  fireEvent.click(within(row).getByRole("button", { name: "开始批改" }));
  expect(await screen.findByText("与土粒级配和孔隙比有关。")).toBeInTheDocument();
  expect(screen.getByText("AI 评分置信度 52%")).toBeInTheDocument();
  expect(screen.getByText("指出级配（8 分）")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("题目得分 说明渗透系数的影响因素。"), { target: { value: "18" } });
  fireEvent.change(screen.getByLabelText("最终总分"), { target: { value: "18" } });
  fireEvent.change(screen.getByLabelText("总体评语"), { target: { value: "概念准确，表达清晰。" } });
  fireEvent.click(screen.getByRole("button", { name: "保存批改" }));
  await waitFor(() => expect(teacherApi.gradeSubmission).toHaveBeenCalledWith("submission-1", expect.objectContaining({
    score: 18,
    feedback: "概念准确，表达清晰。",
    answers: [expect.objectContaining({ questionId: "q-2", score: 18 })],
  })));
});


test("导出菜单提供题目、答题卡、参考答案的 Word 与 PDF 六种文件", () => {
  render(<ExportMenu paperId="paper-1" />);
  fireEvent.click(screen.getByRole("button", { name: "导出试卷" }));
  const menu = screen.getByRole("menu", { name: "试卷导出格式" });
  expect(within(menu).getAllByRole("menuitem")).toHaveLength(6);
  expect(within(menu).getByRole("menuitem", { name: "Word 试题" })).toHaveAttribute("href", expect.stringContaining("format=docx&variant=questions"));
  expect(within(menu).getByRole("menuitem", { name: "PDF 答题卡" })).toHaveAttribute("href", expect.stringContaining("format=pdf&variant=answer-sheet"));
  expect(within(menu).getByRole("menuitem", { name: "PDF 参考答案" })).toHaveAttribute("href", expect.stringContaining("format=pdf&variant=answers"));
});
