import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, test, vi } from "vitest";

import QAWorkbench from "./QAWorkbench";


const sourceA = {
  id: "source-a",
  heading_path: "第3章 桩基础 > 桩侧阻力",
  documentTitle: "《基础工程》教材",
  text: "桩侧阻力由桩土界面的剪切作用发挥。",
  source_line: 126,
  kind: "textbook",
};

const sourceB = {
  id: "source-b",
  heading_path: "第3章 桩基础 > 荷载传递",
  documentTitle: "《基础工程》教材",
  text: "桩土相对位移、土层性质和施工方法都会影响侧阻力。",
  source_line: 132,
  kind: "textbook",
};

function renderWorkbench(overrides = {}) {
  const props = {
    ragChunks: [],
    qaConfig: {},
    backendStatus: "online",
    askQa: vi.fn(async () => ({
      answer: "桩侧阻力由界面剪切作用发挥。[1]",
      sources: [sourceA],
      usedLlm: true,
      llmConfigured: true,
    })),
    searchLocal: vi.fn(() => []),
    buildFallbackAnswer: vi.fn(() => "当前知识库没有足够依据。"),
    ...overrides,
  };
  render(<QAWorkbench {...props} />);
  return props;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("QAWorkbench", () => {
  test("starts with a concise welcome state and connected status", () => {
    renderWorkbench();

    expect(screen.getByRole("heading", { name: "智能问答" })).toBeInTheDocument();
    expect(screen.getByText("大模型已连接")).toBeInTheDocument();
    expect(screen.getByText("可以从这些问题开始")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "桩侧阻力是如何发挥的？" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "回答依据" })).toHaveTextContent("回答后将在这里显示教材与规范依据");
  });

  test("sends contextual follow-up history and lets earlier answers restore their sources", async () => {
    const askQa = vi
      .fn()
      .mockResolvedValueOnce({ answer: "第一轮回答 [1]", sources: [sourceA], usedLlm: true, llmConfigured: true })
      .mockResolvedValueOnce({ answer: "第二轮回答 [1]", sources: [sourceB], usedLlm: true, llmConfigured: true });
    renderWorkbench({ askQa });

    fireEvent.change(screen.getByLabelText("输入问题"), { target: { value: "桩侧阻力如何产生？" } });
    fireEvent.click(screen.getByRole("button", { name: "发送问题" }));
    expect(await screen.findByText("第一轮回答 [1]")).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "回答依据" })).toHaveTextContent("桩侧阻力由桩土界面的剪切作用发挥");

    fireEvent.change(screen.getByLabelText("输入问题"), { target: { value: "它受什么影响？" } });
    fireEvent.click(screen.getByRole("button", { name: "发送问题" }));
    expect(await screen.findByText("第二轮回答 [1]")).toBeInTheDocument();

    expect(askQa).toHaveBeenLastCalledWith({
      question: "它受什么影响？",
      mode: "教材问答",
      useLlm: true,
      history: [
        { role: "user", content: "桩侧阻力如何产生？" },
        { role: "assistant", content: "第一轮回答 [1]" },
      ],
    });
    expect(screen.getByRole("complementary", { name: "回答依据" })).toHaveTextContent("桩土相对位移");

    const transcript = screen.getByRole("log", { name: "问答记录" });
    fireEvent.click(within(transcript).getAllByRole("button", { name: /查看此回答的 1 条依据/ })[0]);
    expect(screen.getByRole("complementary", { name: "回答依据" })).toHaveTextContent("桩侧阻力由桩土界面的剪切作用发挥");
  });

  test("uses Enter to send and Shift Enter to keep editing", async () => {
    const askQa = vi.fn(async () => ({ answer: "键盘回答", sources: [sourceA], usedLlm: true, llmConfigured: true }));
    renderWorkbench({ askQa });
    const input = screen.getByLabelText("输入问题");
    fireEvent.change(input, { target: { value: "解释桩侧阻力" } });

    fireEvent.keyDown(input, { key: "Enter", shiftKey: true });
    expect(askQa).not.toHaveBeenCalled();
    fireEvent.keyDown(input, { key: "Enter", shiftKey: false });

    expect(await screen.findByText("键盘回答")).toBeInTheDocument();
    expect(askQa).toHaveBeenCalledTimes(1);
  });

  test("keeps a usable local answer when the server request fails", async () => {
    const searchLocal = vi.fn(() => [sourceA]);
    const buildFallbackAnswer = vi.fn(() => "本地教材回答");
    renderWorkbench({
      backendStatus: "offline",
      askQa: vi.fn(async () => {
        throw new Error("offline");
      }),
      searchLocal,
      buildFallbackAnswer,
    });

    fireEvent.change(screen.getByLabelText("输入问题"), { target: { value: "解释桩侧阻力" } });
    fireEvent.click(screen.getByRole("button", { name: "发送问题" }));

    expect(await screen.findByText("本地教材回答")).toBeInTheDocument();
    expect(screen.getByText("本地教材索引")).toBeInTheDocument();
    expect(searchLocal).toHaveBeenCalledWith([], "解释桩侧阻力", 5);
    expect(buildFallbackAnswer).toHaveBeenCalledWith("解释桩侧阻力", "教材问答", [sourceA], {});
  });

  test("starts a new conversation after confirmation", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderWorkbench();
    fireEvent.change(screen.getByLabelText("输入问题"), { target: { value: "解释桩侧阻力" } });
    fireEvent.click(screen.getByRole("button", { name: "发送问题" }));
    expect(await screen.findByText("桩侧阻力由界面剪切作用发挥。[1]")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "新对话" }));

    expect(screen.getByText("可以从这些问题开始")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "新对话" })).not.toBeInTheDocument();
  });
});
