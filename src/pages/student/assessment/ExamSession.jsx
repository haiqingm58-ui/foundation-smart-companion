import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, ArrowLeft, ArrowRight, CheckCircle2, Clock3, Send, X } from "lucide-react";
import { studentApi } from "../../../api/student.js";
import { QuestionAnswer, QuestionAttachments } from "./QuestionAnswer.jsx";
import { saveStatusLabel, useAnswerAutosave } from "./useAnswerAutosave.js";


function timerText(seconds) {
  if (seconds === null || seconds === undefined) return "不限时";
  const safe = Math.max(0, seconds);
  const hours = String(Math.floor(safe / 3600)).padStart(2, "0");
  const minutes = String(Math.floor(safe % 3600 / 60)).padStart(2, "0");
  const remaining = String(safe % 60).padStart(2, "0");
  return `${hours}:${minutes}:${remaining}`;
}


export function ExamSession({ assignmentId, title = "正式试卷", initialSubmission, onFinished, onExit }) {
  const [submission, setSubmission] = useState(initialSubmission || null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [remainingSeconds, setRemainingSeconds] = useState(initialSubmission?.countdown?.remainingSeconds ?? null);
  const [loading, setLoading] = useState(!initialSubmission);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const autoSubmittedRef = useRef(false);

  useEffect(() => {
    if (initialSubmission) return;
    let live = true;
    studentApi.startPaper(assignmentId).then((data) => {
      if (!live) return;
      setSubmission(data);
      setRemainingSeconds(data.countdown?.remainingSeconds ?? null);
      window.localStorage.setItem(`student-active-submission:${assignmentId}`, data.submissionId);
    }).catch((reason) => live && setError(reason.message || "试卷启动失败")).finally(() => live && setLoading(false));
    return () => { live = false; };
  }, [assignmentId, initialSubmission]);

  useEffect(() => {
    if (remainingSeconds === null || remainingSeconds <= 0) return undefined;
    const timer = window.setInterval(() => setRemainingSeconds((current) => current === null ? null : Math.max(0, current - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [remainingSeconds === null]);

  const question = submission?.questions?.[activeIndex];
  const storageKey = submission && question ? `student-paper-draft:${submission.submissionId}:${question.id}` : "student-paper-draft:inactive";
  const autosave = useAnswerAutosave({
    storageKey,
    initialValue: question?.answer,
    save: (answer) => studentApi.saveSubmissionAnswer(submission.submissionId, question.id, answer),
  });
  const answered = useMemo(() => submission?.questions?.filter((item, index) => item.answer !== null && item.answer !== undefined || index === activeIndex && autosave.value !== null && autosave.value !== undefined && autosave.value !== "").length || 0, [activeIndex, autosave.value, submission?.questions]);

  async function move(nextIndex) {
    await autosave.flush();
    setSubmission((current) => current ? { ...current, questions: current.questions.map((item, index) => index === activeIndex ? { ...item, answer: autosave.value } : item) } : current);
    setActiveIndex(nextIndex);
  }

  async function submit(force = false) {
    if (!force && !window.confirm(`确认交卷吗？当前已作答 ${answered} / ${submission.questions.length} 题，交卷后不能修改。`)) return;
    setSubmitting(true);
    setError("");
    try {
      const saved = await autosave.flush();
      if (!saved) {
        setError("当前答案尚未保存，请联网后重试交卷。");
        return;
      }
      const summary = await studentApi.submitPaper(submission.submissionId);
      const result = await studentApi.paperResult(summary.submissionId);
      window.localStorage.removeItem(`student-active-submission:${assignmentId}`);
      onFinished?.(result);
    } catch (reason) {
      setError(reason.message || "交卷失败");
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    if (remainingSeconds !== 0 || !submission || autoSubmittedRef.current) return;
    autoSubmittedRef.current = true;
    submit(true);
  }, [remainingSeconds, submission]);

  if (loading) return <div className="studentAssessmentLoading" aria-label="正式试卷加载中"><span /><span /><span /></div>;
  if (!submission || !question) return <div className="studentAssessmentState"><p>{error || "试卷中没有可作答题目"}</p><button type="button" onClick={onExit}>返回我的试卷</button></div>;

  return <div className="studentSessionLayout studentExamLayout">
    <aside className="studentQuestionNavigator"><header><div><span>正式试卷</span><strong>{title}</strong></div><button type="button" aria-label="退出试卷" title="暂时退出" onClick={onExit}><X size={18} /></button></header><div className={`studentExamTimer ${remainingSeconds !== null && remainingSeconds <= 300 ? "urgent" : ""}`}><Clock3 size={18} /><div><span>剩余时间</span><strong>{timerText(remainingSeconds)}</strong></div></div><div className="studentSessionProgress"><strong>{answered} / {submission.questions.length}</strong><span>已作答</span><div><i style={{ width: `${submission.questions.length ? answered / submission.questions.length * 100 : 0}%` }} /></div></div><nav aria-label="试卷题号">{submission.questions.map((item, index) => <button key={item.id} type="button" aria-label={`第 ${index + 1} 题`} aria-current={index === activeIndex ? "step" : undefined} className={(item.answer !== null && item.answer !== undefined) || index === activeIndex && autosave.value !== null && autosave.value !== undefined && autosave.value !== "" ? "answered" : ""} onClick={() => move(index)}>{index + 1}</button>)}</nav><div className="studentExamNotice"><AlertTriangle size={15} /><span>倒计时由服务器计算。刷新或重新进入不会重置时间。</span></div></aside>

    <main className="studentQuestionStage"><header className="studentQuestionTopbar"><div><span>第 {activeIndex + 1} / {submission.questions.length} 题</span><strong>{question.questionType} · {question.points || 0} 分</strong></div><span className={`studentSaveState ${autosave.status}`}><CheckCircle2 size={15} />{saveStatusLabel(autosave.status)}</span></header><article className="studentQuestionBody"><div className="studentQuestionMeta"><span>{question.sectionTitle || question.chapter}</span><span>{question.difficulty}</span></div><h2>{question.text}</h2><QuestionAttachments attachments={question.attachments} /><QuestionAnswer question={question} value={autosave.value} onChange={autosave.change} /></article>{error && <p className="studentSessionError" role="alert">{error}</p>}<footer className="studentQuestionActions"><button type="button" className="studentSecondaryButton" disabled={activeIndex === 0} onClick={() => move(activeIndex - 1)}><ArrowLeft size={16} />上一题</button><div>{activeIndex < submission.questions.length - 1 && <button type="button" className="studentSecondaryButton" onClick={() => move(activeIndex + 1)}>下一题<ArrowRight size={16} /></button>}<button type="button" className="studentPrimaryButton" disabled={submitting} onClick={() => submit(false)}><Send size={16} />{submitting ? "正在交卷" : "交卷"}</button></div></footer></main>
  </div>;
}
