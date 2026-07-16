import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2, Send, X } from "lucide-react";
import { studentApi } from "../../../api/student.js";
import { QuestionAnswer, QuestionAttachments } from "./QuestionAnswer.jsx";
import { saveStatusLabel, useAnswerAutosave } from "./useAnswerAutosave.js";


export function PracticeSession({ sessionId, initialSession, onFinished, onExit }) {
  const [session, setSession] = useState(initialSession || null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(!initialSession);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (initialSession || !sessionId) return;
    let live = true;
    studentApi.getPracticeSession(sessionId).then((data) => {
      if (!live) return;
      setSession(data);
      window.localStorage.setItem("student-active-practice-session", data.id);
      if (data.status !== "in_progress") onFinished?.(data);
    }).catch((reason) => {
      if (!live) return;
      window.localStorage.removeItem("student-active-practice-session");
      setError(reason.message || "练习会话加载失败");
    }).finally(() => live && setLoading(false));
    return () => { live = false; };
  }, [initialSession, onFinished, sessionId]);

  useEffect(() => {
    if (initialSession?.id) window.localStorage.setItem("student-active-practice-session", initialSession.id);
  }, [initialSession?.id]);

  const question = session?.questions?.[activeIndex];
  const storageKey = session && question ? `student-practice-draft:${session.id}:${question.id}` : "student-practice-draft:inactive";
  const autosave = useAnswerAutosave({
    storageKey,
    initialValue: question?.answer,
    save: (answer) => studentApi.savePracticeAnswer(session.id, question.id, answer),
  });
  const answered = useMemo(() => session?.questions?.filter((item, index) => item.answer !== null && item.answer !== undefined || index === activeIndex && autosave.value !== null && autosave.value !== undefined && autosave.value !== "").length || 0, [activeIndex, autosave.value, session?.questions]);

  async function move(nextIndex) {
    await autosave.flush();
    setSession((current) => current ? { ...current, questions: current.questions.map((item, index) => index === activeIndex ? { ...item, answer: autosave.value } : item) } : current);
    setActiveIndex(nextIndex);
  }

  async function submit() {
    if (!window.confirm("确认提交本次随机练习吗？提交后将生成掌握度结果。")) return;
    setSubmitting(true);
    setError("");
    try {
      await autosave.flush();
      const result = await studentApi.submitPracticeSession(session.id);
      window.localStorage.removeItem("student-active-practice-session");
      onFinished?.(result);
    } catch (reason) {
      setError(reason.message || "练习提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <div className="studentAssessmentLoading" aria-label="练习加载中"><span /><span /><span /></div>;
  if (!session || !question) return <div className="studentAssessmentState"><p>{error || "练习中没有可作答题目"}</p><button type="button" onClick={onExit}>返回练习中心</button></div>;

  return <div className="studentSessionLayout">
    <aside className="studentQuestionNavigator"><header><div><span>随机练习</span><strong>{session.chapter || "知识点专项"}</strong></div><button type="button" aria-label="退出练习" title="退出练习" onClick={onExit}><X size={18} /></button></header><div className="studentSessionProgress"><strong>{answered} / {session.questions.length}</strong><span>已作答</span><div><i style={{ width: `${session.questions.length ? answered / session.questions.length * 100 : 0}%` }} /></div></div><nav aria-label="练习题号">{session.questions.map((item, index) => <button key={item.id} type="button" aria-label={`第 ${index + 1} 题`} aria-current={index === activeIndex ? "step" : undefined} className={(item.answer !== null && item.answer !== undefined) || index === activeIndex && autosave.value !== null && autosave.value !== undefined && autosave.value !== "" ? "answered" : ""} onClick={() => move(index)}>{index + 1}</button>)}</nav><p>答案会自动保存，刷新页面可继续作答。</p></aside>

    <main className="studentQuestionStage">
      <header className="studentQuestionTopbar"><div><span>第 {activeIndex + 1} / {session.questions.length} 题</span><strong>{question.questionType} · {question.points || 0} 分</strong></div><span className={`studentSaveState ${autosave.status}`}><CheckCircle2 size={15} />{saveStatusLabel(autosave.status)}</span></header>
      <article className="studentQuestionBody"><div className="studentQuestionMeta"><span>{question.chapter}</span><span>{question.difficulty}</span></div><h2>{question.text}</h2><QuestionAttachments attachments={question.attachments} /><QuestionAnswer question={question} value={autosave.value} onChange={autosave.change} /></article>
      {error && <p className="studentSessionError" role="alert">{error}</p>}
      <footer className="studentQuestionActions"><button type="button" className="studentSecondaryButton" disabled={activeIndex === 0} onClick={() => move(activeIndex - 1)}><ArrowLeft size={16} />上一题</button>{activeIndex < session.questions.length - 1 ? <button type="button" className="studentPrimaryButton" onClick={() => move(activeIndex + 1)}>下一题<ArrowRight size={16} /></button> : <button type="button" className="studentPrimaryButton" disabled={submitting} onClick={submit}><Send size={16} />{submitting ? "正在提交" : "提交练习"}</button>}</footer>
    </main>
  </div>;
}
