import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { studentApi } from "../../../api/student.js";
import { AssessmentHome } from "./AssessmentHome.jsx";
import { AssessmentResult } from "./AssessmentResult.jsx";
import { ExamSession } from "./ExamSession.jsx";
import { MyPapers } from "./MyPapers.jsx";
import { PracticeSession } from "./PracticeSession.jsx";
import { RandomPracticeSetup } from "./RandomPracticeSetup.jsx";


vi.mock("../../../api/student.js", () => ({
  studentApi: {
    assessmentCatalog: vi.fn(), createPracticeSession: vi.fn(), getPracticeSession: vi.fn(),
    savePracticeAnswer: vi.fn(), submitPracticeSession: vi.fn(), papers: vi.fn(),
    startPaper: vi.fn(), saveSubmissionAnswer: vi.fn(), submitPaper: vi.fn(), paperResult: vi.fn(),
  },
}));


const soilCatalog = {
  subjects: [
    { id: "foundation-engineering", title: "基础工程", questionCount: 79 },
    { id: "soil-mechanics", title: "土力学", questionCount: 662 },
  ],
  selectedSubjectId: "soil-mechanics",
  chapters: [
    { name: "第一章 土的性质及工程分类", questionCount: 8 },
    { name: "第二章 土的渗流", questionCount: 20 },
  ],
  knowledgePoints: [
    { id: "kp-1", name: "土的三相组成", chapter: "第一章 土的性质及工程分类", questionCount: 5 },
    { id: "kp-2", name: "三相比例指标", chapter: "第一章 土的性质及工程分类", questionCount: 6 },
    { id: "kp-3", name: "达西定律", chapter: "第二章 土的渗流", questionCount: 10 },
    { id: "kp-4", name: "渗透系数", chapter: "第二章 土的渗流", questionCount: 9 },
  ],
  questionTypes: [{ name: "单项选择题", questionCount: 300 }, { name: "判断题", questionCount: 90 }],
  difficulties: [{ name: "基础", questionCount: 360 }, { name: "提高", questionCount: 120 }],
};

const foundationCatalog = {
  ...soilCatalog,
  selectedSubjectId: "foundation-engineering",
  chapters: [{ name: "桩基础", questionCount: 12 }],
  knowledgePoints: [{ id: "f-kp-1", name: "单桩承载力", chapter: "桩基础", questionCount: 12 }],
};

const question = {
  id: "q-1", subjectId: "soil-mechanics", text: "达西定律适用于哪类渗流？", questionType: "单项选择题",
  options: [{ label: "A", text: "层流" }, { label: "B", text: "紊流" }], difficulty: "基础", chapter: "第二章 土的渗流",
  knowledgePointIds: ["kp-3"], sequence: 1, points: 5, attachments: [], answer: null,
};

const practice = {
  id: "practice-1", subjectId: "soil-mechanics", mode: "chapter", chapter: "第二章 土的渗流",
  requestedCount: 1, status: "in_progress", score: null, maxScore: 0, startedAt: "2026-07-16T08:00:00Z", questions: [question],
};


beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.clear();
  vi.stubGlobal("confirm", vi.fn(() => true));
  studentApi.assessmentCatalog.mockImplementation((subjectId) => Promise.resolve(subjectId === "foundation-engineering" ? foundationCatalog : soilCatalog));
  studentApi.createPracticeSession.mockResolvedValue(practice);
  studentApi.getPracticeSession.mockResolvedValue(practice);
  studentApi.savePracticeAnswer.mockResolvedValue({ sessionId: "practice-1", questionId: "q-1", answer: "A", savedAt: "2026-07-16T08:01:00Z" });
  studentApi.submitPracticeSession.mockResolvedValue({ ...practice, status: "graded", score: 5, maxScore: 5, questions: [{ ...question, answer: "A", score: 5, maxScore: 5, feedback: "回答正确" }] });
  studentApi.papers.mockResolvedValue({ items: [], total: 0 });
});


test("随机练习按课程隔离章节和知识点并限制最多选择三个知识点", async () => {
  render(<RandomPracticeSetup onStarted={vi.fn()} />);
  expect(await screen.findByRole("button", { name: "土力学" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByText("达西定律")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "基础工程" }));
  expect(await screen.findByText("单桩承载力")).toBeInTheDocument();
  expect(screen.queryByText("达西定律")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "土力学" }));
  await screen.findByText("达西定律");
  fireEvent.click(screen.getByRole("tab", { name: "按知识点" }));
  for (const name of ["土的三相组成", "三相比例指标", "达西定律"]) {
    fireEvent.click(screen.getByLabelText(name));
  }
  expect(screen.getByLabelText("渗透系数")).toBeDisabled();
  expect(screen.getByText("已选 3 / 3 个知识点")).toBeInTheDocument();
});


test("随机练习支持题型难度和 5 10 20 自定义题量并在题量不足时阻止开始", async () => {
  render(<RandomPracticeSetup onStarted={vi.fn()} />);
  await screen.findByRole("option", { name: /第一章 土的性质及工程分类/ });
  fireEvent.click(screen.getByLabelText("单项选择题"));
  fireEvent.click(screen.getByLabelText("基础"));
  fireEvent.click(screen.getByRole("button", { name: "10 题" }));
  expect(screen.getByText("当前章节可用 8 题，不能抽取 10 题")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "开始随机练习" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "自定义" }));
  fireEvent.change(screen.getByLabelText("自定义题量"), { target: { value: "7" } });
  expect(screen.getByRole("button", { name: "开始随机练习" })).toBeEnabled();
});


test("创建随机练习提交结构化筛选条件", async () => {
  const onStarted = vi.fn();
  render(<RandomPracticeSetup onStarted={onStarted} />);
  await screen.findByRole("option", { name: /第二章 土的渗流/ });
  fireEvent.change(screen.getByLabelText("选择章节"), { target: { value: "第二章 土的渗流" } });
  fireEvent.click(screen.getByLabelText("判断题"));
  fireEvent.click(screen.getByLabelText("提高"));
  fireEvent.click(screen.getByRole("button", { name: "10 题" }));
  fireEvent.click(screen.getByRole("button", { name: "开始随机练习" }));
  await waitFor(() => expect(studentApi.createPracticeSession).toHaveBeenCalledWith({
    subjectId: "soil-mechanics", mode: "chapter", chapter: "第二章 土的渗流", knowledgePointIds: [],
    questionTypes: ["判断题"], difficulties: ["提高"], count: 10,
  }));
  expect(onStarted).toHaveBeenCalledWith(practice);
});


test("刷新后按会话编号续答且不会重新抽题", async () => {
  render(<PracticeSession sessionId="practice-1" onFinished={vi.fn()} onExit={vi.fn()} />);
  expect(await screen.findByText(question.text)).toBeInTheDocument();
  expect(studentApi.getPracticeSession).toHaveBeenCalledWith("practice-1");
  expect(studentApi.createPracticeSession).not.toHaveBeenCalled();
});


test("答案先写本地草稿再自动保存，失败后联网自动重试", async () => {
  studentApi.savePracticeAnswer.mockRejectedValueOnce(new Error("断网")).mockResolvedValueOnce({ answer: "渗流速度与水力坡降成正比" });
  render(<PracticeSession initialSession={{ ...practice, questions: [{ ...question, questionType: "填空题", options: [], text: "填写达西定律", answer: null }] }} onFinished={vi.fn()} onExit={vi.fn()} />);
  const input = await screen.findByLabelText("填写达西定律");
  fireEvent.change(input, { target: { value: "渗流速度与水力坡降成正比" } });
  expect(window.localStorage.getItem("student-practice-draft:practice-1:q-1")).toContain("水力坡降");
  expect(await screen.findByText("待重试")).toBeInTheDocument();
  window.dispatchEvent(new Event("online"));
  expect(await screen.findByText("已保存")).toBeInTheDocument();
  expect(window.localStorage.getItem("student-practice-draft:practice-1:q-1")).toBeNull();
});


test("离线保存失败时禁止跨题，避免把未同步答案留在上一题", async () => {
  const second = { ...question, id: "q-2", text: "渗透系数受哪些因素影响？", sequence: 2 };
  studentApi.savePracticeAnswer.mockRejectedValue(new Error("断网"));
  render(<PracticeSession initialSession={{ ...practice, questions: [question, second] }} onFinished={vi.fn()} onExit={vi.fn()} />);
  fireEvent.click(await screen.findByLabelText("A. 层流"));
  fireEvent.click(screen.getByRole("button", { name: "下一题" }));
  expect(await screen.findByText("当前答案尚未保存，请联网后重试。")).toBeInTheDocument();
  expect(screen.getByText(question.text)).toBeInTheDocument();
  expect(screen.queryByText(second.text)).not.toBeInTheDocument();
});


test("随机练习恢复本地草稿并在全部草稿同步前阻止提交", async () => {
  const second = { ...question, id: "q-2", text: "渗透系数受哪些因素影响？", sequence: 2 };
  window.localStorage.setItem("student-practice-draft:practice-1:q-2", JSON.stringify("B"));
  studentApi.savePracticeAnswer.mockRejectedValue(new Error("断网"));
  render(<PracticeSession initialSession={{ ...practice, questions: [question, second] }} onFinished={vi.fn()} onExit={vi.fn()} />);
  expect(await screen.findByText(second.text)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "提交练习" }));
  expect(await screen.findByText("当前答案尚未保存，请联网后重试提交。")).toBeInTheDocument();
  expect(studentApi.submitPracticeSession).not.toHaveBeenCalled();
});


test("我的试卷提供待完成进行中已提交已批改四种状态", async () => {
  studentApi.papers.mockResolvedValue({ items: [
    { assignmentId: "a-1", title: "待完成测验", teacherName: "李老师", status: "pending", totalPoints: 100, questionCount: 20, countdown: { dueAt: "2026-07-20T08:00:00Z", remainingSeconds: 7200 } },
    { assignmentId: "a-2", title: "进行中测验", teacherName: "周老师", status: "in_progress", submissionId: "s-2", totalPoints: 100, questionCount: 20, countdown: { remainingSeconds: 3600 } },
    { assignmentId: "a-3", title: "等待批改测验", teacherName: "李老师", status: "pending_review", submissionId: "s-3", totalPoints: 100, questionCount: 10, countdown: {} },
    { assignmentId: "a-4", title: "已批改测验", teacherName: "周老师", status: "graded", submissionId: "s-4", score: 88, totalPoints: 100, questionCount: 20, countdown: {} },
  ], total: 4 });
  render(<MyPapers onStart={vi.fn()} onViewResult={vi.fn()} />);
  expect(await screen.findByText("待完成测验")).toBeInTheDocument();
  expect(screen.getByText("李老师")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: "进行中 1" }));
  expect(screen.getByText("进行中测验")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: "已提交 1" }));
  expect(screen.getByText("等待批改测验")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: "已批改 1" }));
  expect(screen.getByText("88 / 100 分")).toBeInTheDocument();
});


test("正式试卷使用服务端倒计时、自动保存并确认交卷", async () => {
  studentApi.startPaper.mockResolvedValue({ submissionId: "submission-1", attemptNumber: 1, resumed: false, countdown: { remainingSeconds: 3661 }, questions: [question] });
  studentApi.saveSubmissionAnswer.mockResolvedValue({ answer: "A" });
  studentApi.submitPaper.mockResolvedValue({ submissionId: "submission-1", status: "graded", score: 5, maxScore: 5 });
  studentApi.paperResult.mockResolvedValue({ submissionId: "submission-1", status: "graded", score: 5, maxScore: 5, showAnswers: false, questions: [{ ...question, answer: "A", score: 5 }] });
  const onFinished = vi.fn();
  render(<ExamSession assignmentId="assignment-1" title="土力学测验" onFinished={onFinished} onExit={vi.fn()} />);
  expect(await screen.findByText("01:01:01")).toBeInTheDocument();
  expect(screen.queryByText("正确答案")).not.toBeInTheDocument();
  fireEvent.click(screen.getByLabelText("A. 层流"));
  await waitFor(() => expect(studentApi.saveSubmissionAnswer).toHaveBeenCalledWith("submission-1", "q-1", "A"));
  fireEvent.click(screen.getByRole("button", { name: "交卷" }));
  expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining("确认交卷"));
  await waitFor(() => expect(studentApi.submitPaper).toHaveBeenCalledWith("submission-1"));
  expect(onFinished).toHaveBeenCalledWith(expect.objectContaining({ status: "graded", showAnswers: false }));
});


test("正式试卷到期时即使最后一次自动保存被截止规则拒绝也会完成服务器结算", async () => {
  const expired = { submissionId: "submission-expired", attemptNumber: 1, countdown: { remainingSeconds: 0 }, questions: [question] };
  window.localStorage.setItem("student-paper-draft:submission-expired:q-1", JSON.stringify("A"));
  studentApi.saveSubmissionAnswer.mockRejectedValue(new Error("试卷已截止"));
  studentApi.submitPaper.mockResolvedValue({ submissionId: "submission-expired", status: "graded", score: 0, maxScore: 5 });
  studentApi.paperResult.mockResolvedValue({ submissionId: "submission-expired", status: "graded", score: 0, maxScore: 5, showAnswers: false, questions: [{ ...question, answer: null, score: 0 }] });
  const onFinished = vi.fn();
  render(<ExamSession assignmentId="assignment-expired" initialSubmission={expired} onFinished={onFinished} onExit={vi.fn()} />);
  await waitFor(() => expect(studentApi.saveSubmissionAnswer).toHaveBeenCalled());
  await waitFor(() => expect(studentApi.submitPaper).toHaveBeenCalledWith("submission-expired"));
  expect(onFinished).toHaveBeenCalledWith(expect.objectContaining({ status: "graded" }));
});


test("正式试卷恢复跨题草稿并在同步失败时阻止交卷", async () => {
  const second = { ...question, id: "q-2", text: "说明渗透系数的影响因素", sequence: 2 };
  const submission = { submissionId: "submission-drafts", attemptNumber: 1, countdown: { remainingSeconds: 3600 }, questions: [question, second] };
  window.localStorage.setItem("student-paper-draft:submission-drafts:q-2", JSON.stringify("颗粒级配与孔隙比"));
  studentApi.saveSubmissionAnswer.mockRejectedValue(new Error("断网"));
  render(<ExamSession assignmentId="assignment-drafts" initialSubmission={submission} onFinished={vi.fn()} onExit={vi.fn()} />);
  expect(await screen.findByText(second.text)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "交卷" }));
  expect(await screen.findByText("当前答案尚未保存，请联网后重试交卷。")).toBeInTheDocument();
  expect(studentApi.submitPaper).not.toHaveBeenCalled();
});


test("结果页区分随机练习掌握度与正式成绩并尊重答案公开状态", () => {
  const { rerender } = render(<AssessmentResult kind="practice" result={{ status: "pending_review", score: 6, maxScore: 10, questions: [{ ...question, status: "pending_review", feedback: "等待复核" }] }} onBack={vi.fn()} />);
  expect(screen.getByText("等待老师批改")).toBeInTheDocument();
  expect(screen.getByText("本次随机练习只更新知识点掌握度，不计入课程成绩")).toBeInTheDocument();

  rerender(<AssessmentResult kind="paper" result={{ status: "graded", score: 88, maxScore: 100, feedback: "概念掌握扎实", showAnswers: false, questions: [{ ...question, answer: "A", score: 5 }] }} onBack={vi.fn()} />);
  expect(screen.getByText("88 / 100")).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "教师总评" })).toHaveTextContent("概念掌握扎实");
  expect(screen.getByText("答案暂未公开")).toBeInTheDocument();
  expect(screen.queryByText("正确答案：A")).not.toBeInTheDocument();
});


test("练习中心可在随机练习与教师试卷间切换", async () => {
  render(<AssessmentHome />);
  expect(await screen.findByText("按章节或知识点生成专属练习")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: "我的试卷" }));
  expect(await screen.findByText("老师发布的考试与作业")).toBeInTheDocument();
});
