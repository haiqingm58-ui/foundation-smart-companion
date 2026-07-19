import { useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpen,
  Bot,
  Check,
  ChevronDown,
  ChevronUp,
  Copy,
  Database,
  Plus,
  RefreshCcw,
  Send,
  Sparkles,
  UserRound,
} from "lucide-react";


const MODES = ["教材问答", "规范问答", "学习辅导"];

const STARTERS = {
  教材问答: ["桩侧阻力是如何发挥的？", "浅基础设计需要验算哪些内容？", "地基承载力特征值如何修正？"],
  规范问答: ["桩基础设计主要参考哪些规范？", "基坑支护设计应关注哪些要求？", "规范资料不足时应该如何核对？"],
  学习辅导: ["帮我梳理桩基础这一章", "沉降计算最容易错在哪里？", "给我一道地基承载力复习题"],
};

const FOLLOW_UPS = {
  教材问答: ["能用更简单的话解释吗？", "相关公式和适用条件是什么？", "这一知识点常见错误有哪些？"],
  规范问答: ["对应的设计检查项有哪些？", "这个结论适用于哪些工程条件？", "还需要老师确认哪些条文？"],
  学习辅导: ["请用三点帮我记忆", "给我一道题检验掌握度", "和上一章有什么联系？"],
};

const SOURCE_TYPE_LABELS = {
  textbook: "教材",
  standard: "规范",
  regulation: "规范",
  teacher: "教师资料",
  upload: "教师资料",
};

function cleanText(value = "") {
  return String(value).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function sourceTitle(source) {
  return source.heading_path || source.heading || source.title || source.documentTitle || "课程资料";
}

function sourceExcerpt(source) {
  return cleanText(source.excerpt || source.text || "暂无可显示的摘录。") || "暂无可显示的摘录。";
}

function sourceMeta(source) {
  const type = SOURCE_TYPE_LABELS[source.kind || source.sourceType] || "课程资料";
  const location = source.page
    ? `第 ${source.page} 页`
    : source.source_line || source.line
      ? `原文位置 ${source.source_line || source.line}`
      : "已匹配原文";
  return `${type} · ${location}`;
}

function answerLabel(message) {
  if (message.origin === "local") return "本地教材索引";
  if (message.usedLlm) return "大模型回答";
  return "RAG 检索回答";
}

function SourceCard({ source, sourceKey, expanded, onToggle }) {
  const excerpt = sourceExcerpt(source);
  const canExpand = excerpt.length > 180;
  return (
    <article className="qaSourceCard">
      <div className="qaSourceCardTopline">
        <span>{sourceMeta(source)}</span>
        {typeof source.score === "number" && <em>相关度 {Math.round(source.score)}</em>}
      </div>
      <strong>{sourceTitle(source)}</strong>
      <p className={expanded ? "expanded" : ""}>{excerpt}</p>
      {canExpand && (
        <button type="button" className="qaSourceExpand" onClick={() => onToggle(sourceKey)} aria-expanded={expanded}>
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          {expanded ? "收起摘录" : "展开摘录"}
        </button>
      )}
    </article>
  );
}

export default function QAWorkbench({
  ragChunks = [],
  qaConfig = {},
  backendStatus = "offline",
  askQa,
  searchLocal,
  buildFallbackAnswer,
}) {
  const [mode, setMode] = useState("教材问答");
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [requestStatus, setRequestStatus] = useState("idle");
  const [activeMessageId, setActiveMessageId] = useState(null);
  const [expandedSources, setExpandedSources] = useState(() => new Set());
  const [copiedMessageId, setCopiedMessageId] = useState(null);
  const [llmAvailable, setLlmAvailable] = useState(backendStatus === "online");
  const sequence = useRef(0);
  const transcriptRef = useRef(null);

  const isLoading = requestStatus === "loading";
  const assistantMessages = useMemo(() => messages.filter((message) => message.role === "assistant"), [messages]);
  const activeMessage = assistantMessages.find((message) => message.id === activeMessageId) || assistantMessages.at(-1) || null;
  const activeSources = activeMessage?.sources ?? [];
  const connectionLabel = backendStatus !== "online" ? "本地检索可用" : llmAvailable ? "大模型已连接" : "RAG 检索模式";

  useEffect(() => {
    if (!transcriptRef.current) return;
    transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
  }, [messages, requestStatus]);

  function nextId(prefix) {
    sequence.current += 1;
    return `${prefix}-${sequence.current}`;
  }

  function boundedHistory(rows = messages) {
    return rows
      .filter((message) => ["user", "assistant"].includes(message.role) && message.content)
      .map((message) => ({ role: message.role, content: message.content }))
      .slice(-6);
  }

  function buildAssistantMessage({ question, answer, sources, usedLlm, origin = "server", answerMode = mode, history = [] }) {
    return {
      id: nextId("assistant"),
      role: "assistant",
      content: answer,
      sources: Array.isArray(sources) ? sources : [],
      usedLlm: Boolean(usedLlm),
      origin,
      question,
      mode: answerMode,
      history,
    };
  }

  async function sendQuestion(explicitQuestion) {
    const question = cleanText(explicitQuestion ?? draft);
    if (!question || isLoading) return;
    const history = boundedHistory();
    const userMessage = { id: nextId("user"), role: "user", content: question, mode };
    setMessages((current) => [...current, userMessage]);
    setDraft("");
    setRequestStatus("loading");

    try {
      const data = await askQa({ question, mode, useLlm: true, history });
      const answer = cleanText(data?.answer);
      if (!answer) throw new Error("EMPTY_QA_ANSWER");
      const assistantMessage = buildAssistantMessage({
        question,
        answer,
        sources: data.sources,
        usedLlm: data.usedLlm,
        answerMode: mode,
        history,
      });
      if (typeof data.llmConfigured === "boolean") setLlmAvailable(data.llmConfigured);
      setMessages((current) => [...current, assistantMessage]);
      setActiveMessageId(assistantMessage.id);
      setRequestStatus("idle");
    } catch {
      const localSources = searchLocal(ragChunks, question, 5);
      const localAnswer = buildFallbackAnswer(question, mode, localSources, qaConfig);
      const assistantMessage = buildAssistantMessage({
        question,
        answer: localAnswer,
        sources: localSources,
        usedLlm: false,
        origin: "local",
        answerMode: mode,
        history,
      });
      setMessages((current) => [...current, assistantMessage]);
      setActiveMessageId(assistantMessage.id);
      setRequestStatus("idle");
    }
  }

  async function retryAnswer(message) {
    if (isLoading) return;
    setRequestStatus("loading");
    try {
      const data = await askQa({
        question: message.question,
        mode: message.mode,
        useLlm: true,
        history: message.history,
      });
      const answer = cleanText(data?.answer);
      if (!answer) throw new Error("EMPTY_QA_ANSWER");
      setMessages((current) => current.map((item) => (
        item.id === message.id
          ? { ...item, content: answer, sources: data.sources ?? [], usedLlm: Boolean(data.usedLlm), origin: "server" }
          : item
      )));
      if (typeof data.llmConfigured === "boolean") setLlmAvailable(data.llmConfigured);
    } catch {
      const localSources = searchLocal(ragChunks, message.question, 5);
      setMessages((current) => current.map((item) => (
        item.id === message.id
          ? {
              ...item,
              content: buildFallbackAnswer(message.question, message.mode, localSources, qaConfig),
              sources: localSources,
              usedLlm: false,
              origin: "local",
            }
          : item
      )));
    } finally {
      setActiveMessageId(message.id);
      setRequestStatus("idle");
    }
  }

  async function copyAnswer(message) {
    try {
      await navigator.clipboard?.writeText(message.content);
      setCopiedMessageId(message.id);
      window.setTimeout(() => setCopiedMessageId(null), 1600);
    } catch {
      setCopiedMessageId(null);
    }
  }

  function startNewConversation() {
    if (messages.length && !window.confirm("开始新对话将清空当前页面中的问答记录，是否继续？")) return;
    setMessages([]);
    setDraft("");
    setActiveMessageId(null);
    setExpandedSources(new Set());
    setRequestStatus("idle");
  }

  function toggleSource(sourceKey) {
    setExpandedSources((current) => {
      const next = new Set(current);
      if (next.has(sourceKey)) next.delete(sourceKey);
      else next.add(sourceKey);
      return next;
    });
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendQuestion();
    }
  }

  return (
    <section className="qaWorkbenchPage">
      <header className="qaWorkbenchHeader">
        <div>
          <p className="qaEyebrow">课程助教</p>
          <h1>智能问答</h1>
          <p>围绕教材、规范和教师知识库连续提问，每个结论都保留检索依据。</p>
        </div>
        <span className={`qaConnectionBadge ${backendStatus === "online" ? "online" : "offline"}`}>
          <i aria-hidden="true" />
          {connectionLabel}
        </span>
      </header>

      <div className="qaWorkbenchGrid">
        <section className="qaConversationPanel" aria-label="智能问答对话">
          <div className="qaConversationToolbar">
            <div>
              <strong>学习对话</strong>
              <span>{assistantMessages.length ? `${assistantMessages.length} 轮回答` : "可连续追问上下文"}</span>
            </div>
            {messages.length > 0 && (
              <button type="button" className="qaNewConversation" onClick={startNewConversation}>
                <Plus size={16} />
                新对话
              </button>
            )}
          </div>

          <div className="qaTranscript" role="log" aria-label="问答记录" aria-live="polite" ref={transcriptRef}>
            {messages.length === 0 ? (
              <div className="qaWelcome">
                <span className="qaWelcomeIcon"><Sparkles size={22} /></span>
                <h2>可以从这些问题开始</h2>
                <p>选择一个示例，或在下方输入你正在学习的问题。</p>
                <div className="qaStarterGrid">
                  {STARTERS[mode].map((prompt) => (
                    <button type="button" key={prompt} onClick={() => sendQuestion(prompt)}>{prompt}</button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((message) => (
                message.role === "user" ? (
                  <article className="qaUserMessage" key={message.id}>
                    <div className="qaUserText">
                      <span>我的问题</span>
                      <p>{message.content}</p>
                    </div>
                    <span className="qaAvatar user"><UserRound size={17} /></span>
                  </article>
                ) : (
                  <article className={`qaAssistantMessage ${activeMessageId === message.id ? "active" : ""}`} key={message.id}>
                    <div className="qaAssistantIdentity">
                      <span className="qaAvatar assistant"><Bot size={18} /></span>
                      <div>
                        <strong>课程助教</strong>
                        <span>{answerLabel(message)} · {message.mode}</span>
                      </div>
                    </div>
                    <p className="qaAnswerText">{message.content}</p>
                    <div className="qaMessageActions">
                      <button
                        type="button"
                        className="qaEvidenceButton"
                        onClick={() => setActiveMessageId(message.id)}
                        aria-label={`查看此回答的 ${message.sources.length} 条依据`}
                      >
                        <BookOpen size={15} />
                        {message.sources.length} 条依据
                      </button>
                      <button type="button" className="qaIconButton" onClick={() => copyAnswer(message)} aria-label="复制回答" title="复制回答">
                        {copiedMessageId === message.id ? <Check size={15} /> : <Copy size={15} />}
                      </button>
                      <button type="button" className="qaIconButton" onClick={() => retryAnswer(message)} aria-label="重新生成这条回答" title="重新生成">
                        <RefreshCcw size={15} />
                      </button>
                    </div>
                    {activeMessageId === message.id && (
                      <div className="qaFollowUps" aria-label="推荐追问">
                        {FOLLOW_UPS[message.mode].map((prompt) => (
                          <button type="button" key={prompt} onClick={() => setDraft(prompt)}>{prompt}</button>
                        ))}
                      </div>
                    )}
                    <details className="qaMobileEvidence">
                      <summary>查看本轮回答依据（{message.sources.length}）</summary>
                      <div className="qaMobileSourceList">
                        {message.sources.map((source, index) => {
                          const sourceKey = `${message.id}-mobile-${source.id || index}`;
                          return (
                            <SourceCard
                              key={sourceKey}
                              source={source}
                              sourceKey={sourceKey}
                              expanded={expandedSources.has(sourceKey)}
                              onToggle={toggleSource}
                            />
                          );
                        })}
                      </div>
                    </details>
                  </article>
                )
              ))
            )}

            {isLoading && (
              <article className="qaAssistantMessage loading" aria-label="正在生成回答">
                <div className="qaAssistantIdentity">
                  <span className="qaAvatar assistant"><Bot size={18} /></span>
                  <div><strong>课程助教</strong><span>正在检索教材与知识库</span></div>
                </div>
                <div className="qaTyping" aria-hidden="true"><i /><i /><i /></div>
              </article>
            )}
          </div>

          <div className="qaComposer">
            <div className="qaModeTabs" role="tablist" aria-label="问答模式">
              {MODES.map((item) => (
                <button
                  type="button"
                  role="tab"
                  aria-selected={mode === item}
                  className={mode === item ? "active" : ""}
                  key={item}
                  onClick={() => setMode(item)}
                >
                  {item}
                </button>
              ))}
            </div>
            <div className="qaComposerRow">
              <label className="qaSrOnly" htmlFor="qa-question">输入问题</label>
              <textarea
                id="qa-question"
                value={draft}
                rows={2}
                maxLength={1000}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={`向课程助教提问，当前为${mode}…`}
              />
              <button type="button" className="qaSendButton" aria-label="发送问题" onClick={() => sendQuestion()} disabled={!draft.trim() || isLoading}>
                <Send size={18} />
                <span>发送</span>
              </button>
            </div>
            <span className="qaComposerHint">Enter 发送 · Shift + Enter 换行</span>
          </div>
        </section>

        <aside className="qaEvidenceRail" role="complementary" aria-label="回答依据">
          <div className="qaEvidenceHeader">
            <div>
              <span className="qaEvidenceIcon"><Database size={17} /></span>
              <div><strong>回答依据</strong><span>随当前回答同步</span></div>
            </div>
            {activeMessage && <em>{activeSources.length} 条</em>}
          </div>

          {activeMessage ? (
            <>
              <div className="qaEvidenceSummary">
                <span>{activeMessage.mode}</span>
                <strong>{answerLabel(activeMessage)}</strong>
                <p>已从课程知识库中选取与本轮问题最相关的材料。</p>
              </div>
              <div className="qaSourceList">
                {activeSources.length ? activeSources.map((source, index) => {
                  const sourceKey = `${activeMessage.id}-${source.id || index}`;
                  return (
                    <SourceCard
                      key={sourceKey}
                      source={source}
                      sourceKey={sourceKey}
                      expanded={expandedSources.has(sourceKey)}
                      onToggle={toggleSource}
                    />
                  );
                }) : <p className="qaEvidenceEmpty">本轮回答没有可显示的引用，请换一个更具体的问题。</p>}
              </div>
            </>
          ) : (
            <div className="qaEvidencePlaceholder">
              <span><BookOpen size={22} /></span>
              <strong>回答后将在这里显示教材与规范依据</strong>
              <p>你可以查看资料名称、章节位置和匹配到的原文摘录。</p>
            </div>
          )}

          <div className="qaRetrievalNote">
            <Check size={15} />
            回答遵循“先检索、后生成”，资料不足时会明确提示。
          </div>
        </aside>
      </div>
    </section>
  );
}
