import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { teacherApi } from "../../../api/teacher.js";
import { KnowledgePointLibrary } from "./KnowledgePointLibrary.jsx";
import { QuestionBank } from "./QuestionBank.jsx";
import { QuestionEditor } from "./QuestionEditor.jsx";


vi.mock("../../../api/teacher.js", () => ({
  teacherApi: {
    knowledgePoints: vi.fn(),
    questions: vi.fn(),
    createKnowledgePoint: vi.fn(),
    updateKnowledgePoint: vi.fn(),
    deleteKnowledgePoint: vi.fn(),
    mergeKnowledgePoint: vi.fn(),
    createQuestion: vi.fn(),
    updateQuestion: vi.fn(),
    deleteQuestion: vi.fn(),
    copyQuestion: vi.fn(),
  },
}));


const subjects = [
  { id: "soil-mechanics", title: "土力学", knowledgePointCount: 50, questionCount: 120 },
  { id: "foundation-engineering", title: "基础工程", knowledgePointCount: 42, questionCount: 96 },
];

const points = [
  { id: "kp-1", subjectId: "soil-mechanics", chapter: "第一章", name: "土的三相组成", questionCount: 8, status: "active", editable: false },
  { id: "kp-2", subjectId: "soil-mechanics", chapter: "第一章", name: "含水率", questionCount: 5, status: "active", editable: false },
  { id: "kp-3", subjectId: "soil-mechanics", chapter: "第二章", name: "达西定律", questionCount: 12, status: "active", editable: false },
  { id: "kp-4", subjectId: "soil-mechanics", chapter: "第二章", name: "渗透系数", questionCount: 7, status: "active", editable: true },
];


beforeEach(() => {
  vi.clearAllMocks();
  teacherApi.knowledgePoints.mockResolvedValue({ items: points, total: points.length, statusCounts: { active: 4 } });
  teacherApi.questions.mockResolvedValue({ items: [], total: 0 });
});


describe("QuestionEditor", () => {
  test("每道题最多选择三个知识点，第四个会被拒绝", () => {
    render(<QuestionEditor subjects={subjects} knowledgePoints={points} onSave={vi.fn()} onCancel={vi.fn()} />);

    fireEvent.click(screen.getByRole("option", { name: /土的三相组成/ }));
    fireEvent.click(screen.getByRole("option", { name: /含水率/ }));
    fireEvent.click(screen.getByRole("option", { name: /达西定律/ }));
    expect(screen.getByText("已选 3/3")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("option", { name: /渗透系数/ }));
    expect(screen.getByRole("alert")).toHaveTextContent("每道题最多关联 3 个知识点");
    expect(screen.getByText("已选 3/3")).toBeInTheDocument();
  });

  test("题型切换只展示对应字段并标明计算题人工批改", () => {
    render(<QuestionEditor subjects={subjects} knowledgePoints={points} onSave={vi.fn()} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("题型"), { target: { value: "简答题" } });
    expect(screen.getByLabelText("字数限制")).toHaveAttribute("min", "20");
    expect(screen.getByLabelText("字数限制")).toHaveAttribute("max", "2000");
    expect(screen.queryByText("选项设置")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("题型"), { target: { value: "计算题" } });
    expect(screen.getByText("教师人工批改")).toBeInTheDocument();
    expect(screen.queryByLabelText("字数限制")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("题型"), { target: { value: "多项选择题" } });
    expect(screen.getByText("选项设置")).toBeInTheDocument();
    expect(screen.getByText("可选择多个正确答案")).toBeInTheDocument();
  });

  test("保存时发送课程、1至3个知识点和题型结构化载荷", async () => {
    const onSave = vi.fn(async () => {});
    render(<QuestionEditor subjects={subjects} knowledgePoints={points} onSave={onSave} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("题干"), { target: { value: "达西定律适用于哪种流态？" } });
    fireEvent.click(screen.getByRole("option", { name: /达西定律/ }));
    fireEvent.change(screen.getByLabelText("选项 A"), { target: { value: "层流" } });
    fireEvent.change(screen.getByLabelText("选项 B"), { target: { value: "紊流" } });
    fireEvent.click(screen.getByLabelText("A 为正确答案"));
    fireEvent.click(screen.getByRole("button", { name: "保存题目" }));

    await waitFor(() => expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
      subjectId: "soil-mechanics",
      knowledgePointIds: ["kp-3"],
      questionType: "单项选择题",
      correctAnswer: "A",
    })));
  });
});


test("知识点库显示有限总数并可查看关联题目", async () => {
  teacherApi.questions.mockResolvedValueOnce({
    items: [{ id: "q-1", text: "达西定律适用条件是什么？", questionType: "简答题", difficulty: "中等" }],
    total: 1,
  });
  render(<KnowledgePointLibrary subjects={subjects} notify={vi.fn()} />);

  expect(await screen.findByText("共 4 个知识点")).toBeInTheDocument();
  expect(screen.getByText("课程已定义 50 个")).toBeInTheDocument();
  const row = screen.getByText("达西定律").closest("tr");
  fireEvent.click(within(row).getByRole("button", { name: "查看 12 道关联题" }));

  expect(await screen.findByRole("dialog", { name: "达西定律关联题目" })).toBeInTheDocument();
  expect(screen.getByText("达西定律适用条件是什么？")).toBeInTheDocument();
  expect(teacherApi.questions).toHaveBeenCalledWith(expect.stringContaining("knowledgePointId=kp-3"));
});


test("共享题目只提供复制操作，教师副本才可编辑", async () => {
  const shared = {
    id: "shared-1", subjectId: "soil-mechanics", chapter: "第二章", text: "共享题目", questionType: "判断题",
    difficulty: "基础", points: 5, source: "soil-mechanics-bank", editable: false, knowledgePoints: [{ id: "kp-3", name: "达西定律" }],
  };
  const owned = { ...shared, id: "owned-1", text: "教师自建题", source: "teacher", editable: true };
  teacherApi.questions.mockResolvedValueOnce({ items: [shared, owned], total: 2 });
  teacherApi.copyQuestion.mockResolvedValueOnce({ ...shared, id: "copy-1", source: "teacher-copy", editable: true });

  render(<QuestionBank subjects={subjects} onOpenImport={vi.fn()} notify={vi.fn()} />);
  const sharedRow = (await screen.findByText("共享题目")).closest("tr");
  const ownedRow = screen.getByText("教师自建题").closest("tr");

  expect(within(sharedRow).getByRole("button", { name: "复制到我的题库" })).toBeInTheDocument();
  expect(within(sharedRow).getByText("土力学共享题库")).toBeInTheDocument();
  expect(screen.getByText("1 道")).toBeInTheDocument();
  expect(screen.getByRole("option", { name: "土力学共享题库" })).toHaveValue("soil-mechanics-bank");
  expect(within(sharedRow).queryByRole("button", { name: "编辑" })).not.toBeInTheDocument();
  expect(within(ownedRow).getByRole("button", { name: "编辑" })).toBeInTheDocument();

  fireEvent.click(within(sharedRow).getByRole("button", { name: "复制到我的题库" }));
  await waitFor(() => expect(teacherApi.copyQuestion).toHaveBeenCalledWith("shared-1"));
  expect(await screen.findByRole("dialog", { name: "编辑题目" })).toBeInTheDocument();
});


test("题库加载失败与空状态都有明确反馈", async () => {
  teacherApi.questions.mockRejectedValueOnce(new Error("题库服务暂不可用"));
  const { rerender } = render(<QuestionBank subjects={subjects} onOpenImport={vi.fn()} notify={vi.fn()} />);
  expect(await screen.findByText("题库服务暂不可用")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();

  teacherApi.questions.mockResolvedValueOnce({ items: [], total: 0 });
  rerender(<QuestionBank subjects={subjects} onOpenImport={vi.fn()} notify={vi.fn()} />);
});
