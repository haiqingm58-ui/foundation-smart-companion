import { AlertCircle, CheckCircle2, ClipboardCheck, RefreshCw, ShieldAlert, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { teacherApi } from "../../../api/teacher.js";
import { AttachmentPreview } from "./AttachmentPreview.jsx";


function formatDate(value) {
  return value ? new Intl.DateTimeFormat("zh-CN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "-";
}


function answerText(answer) {
  if (answer === null || answer === undefined || answer === "") return "未作答";
  if (Array.isArray(answer)) return answer.join("、");
  if (typeof answer === "object") return JSON.stringify(answer, null, 2);
  return String(answer);
}


export function SubmissionGrading({ notify }) {
  const [status, setStatus] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [grades, setGrades] = useState([]);
  const [finalScore, setFinalScore] = useState(0);
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setData(await teacherApi.submissions(status ? `?status=${status}` : "")); }
    catch (reason) { setError(reason.message || "提交记录加载失败"); }
    finally { setLoading(false); }
  }, [status]);
  useEffect(() => { load(); }, [load]);

  const open = async (item) => {
    setDetailLoading(true); setError("");
    try {
      const result = await teacherApi.submission(item.id);
      const nextGrades = (result.questions || []).map((question) => ({
        questionId: question.questionId || question.id,
        score: question.score ?? 0,
        criteriaScores: question.criteriaScores || {},
        feedback: question.feedback || "",
      }));
      setDetail(result); setGrades(nextGrades);
      setFinalScore(result.score ?? nextGrades.reduce((sum, grade) => sum + Number(grade.score || 0), 0));
      setFeedback(result.feedback || "");
    } catch (reason) {
      notify?.(reason.message || "批改详情加载失败", "error");
    } finally {
      setDetailLoading(false);
    }
  };
  const updateGrade = (questionId, key, value) => setGrades((items) => items.map((item) => item.questionId === questionId ? { ...item, [key]: value } : item));
  const updateCriterion = (questionId, criterion, value) => setGrades((items) => items.map((item) => item.questionId === questionId ? { ...item, criteriaScores: { ...item.criteriaScores, [criterion]: Number(value) } } : item));
  const save = async () => {
    setBusy(true); setError("");
    try {
      await teacherApi.gradeSubmission(detail.id, {
        score: Number(finalScore), feedback: feedback.trim(),
        answers: grades.map((item) => ({ ...item, score: Number(item.score), feedback: item.feedback.trim() })),
      });
      setDetail(null); notify?.("批改结果已保存"); await load();
    } catch (reason) {
      setError(reason.message || "保存批改失败"); setBusy(false);
    }
  };

  return <div className="assessmentWorkspace gradingWorkspace">
    <header className="assessmentPageHead"><div><span>真实提交与人工复核</span><h1>批改与成绩分析</h1><p>查看发布快照、学生答案和评分项，低置信度与计算题由教师复核。</p></div><button type="button" className="assessmentIconButton" aria-label="刷新提交记录" title="刷新" onClick={load}><RefreshCw size={17} /></button></header>
    <div className="assessmentToolbar gradingFilters"><label><span>批改状态</span><select aria-label="批改状态" value={status} onChange={(event) => setStatus(event.target.value)}><option value="">全部状态</option><option value="pending_review">待人工复核</option><option value="submitted">已提交</option><option value="graded">已批改</option></select></label></div>
    <div className="assessmentListFrame"><header><strong>共 {data?.total || 0} 条提交</strong><span>仅显示本人发布范围</span></header>{loading ? <div className="assessmentLoading"><span /><span /><span /></div> : error && !detail ? <div className="assessmentState"><p>{error}</p><button type="button" onClick={load}>重试</button></div> : !data?.items?.length ? <div className="assessmentState"><ClipboardCheck size={24} /><p>暂无待处理提交</p><span>学生提交试卷后会出现在这里。</span></div> : <div className="assessmentTableWrap"><table className="assessmentTable"><thead><tr><th>考试 / 作业</th><th>学生</th><th>提交时间</th><th>得分</th><th>状态</th><th>操作</th></tr></thead><tbody>{data.items.map((item) => <tr key={item.id}><td><strong>{item.assignmentTitle}</strong></td><td><strong>{item.studentName}</strong><small>{item.studentNo}</small></td><td>{formatDate(item.submittedAt)}</td><td>{item.score ?? "-"}</td><td><span className={`assessmentStatus ${item.status}`}>{item.status === "graded" ? "已批改" : "待人工复核"}</span></td><td><button type="button" className="assessmentIconText" disabled={detailLoading} onClick={() => open(item)}>{item.status === "graded" ? "重新批改" : "开始批改"}</button></td></tr>)}</tbody></table></div>}</div>
    {detail && <div className="assessmentDrawerBackdrop"><aside className="assessmentDrawer gradingDrawer" role="dialog" aria-label="批改学生试卷" aria-modal="true"><header><div><span>{detail.studentName} · {detail.studentNo}</span><h2>{detail.assignmentTitle}</h2></div><button type="button" aria-label="关闭" onClick={() => setDetail(null)}><X size={19} /></button></header><div className="assessmentDrawerBody gradingBody">
      <div className="gradingSummary"><span>提交时间 {formatDate(detail.submittedAt)}</span><strong>满分 {detail.totalPoints} 分</strong><span>{detail.questions?.length || 0} 道题</span></div>
      {(detail.questions || []).map((question, index) => { const grade = grades.find((item) => item.questionId === (question.questionId || question.id)) || {}; const questionId = question.questionId || question.id; return <section className="gradingQuestion" key={questionId}><header><span>{question.sectionTitle || `第 ${index + 1} 题`}</span><strong>{question.points} 分</strong></header><h3>{question.text}</h3><AttachmentPreview attachments={question.attachments || []} /><div className="gradingAnswer"><span>学生答案</span><pre>{answerText(question.answer)}</pre></div><div className="gradingSignals">{question.gradingMode === "manual" && <span><ShieldAlert size={14} />教师人工批改</span>}{question.confidence !== null && question.confidence !== undefined && <span className={question.confidence < 0.6 ? "low" : ""}>AI 评分置信度 {Math.round(question.confidence * 100)}%</span>}</div>{question.rubric?.length > 0 && <div className="gradingRubric"><strong>评分项</strong>{question.rubric.map((item, rubricIndex) => { const criterion = item.criterion || `评分项 ${rubricIndex + 1}`; return <label key={`${criterion}-${rubricIndex}`}><span>{criterion}（{item.points ?? 0} 分）</span><input aria-label={`评分项 ${criterion}`} type="number" min="0" max={item.points ?? question.points} step="0.5" value={grade.criteriaScores?.[criterion] ?? ""} onChange={(event) => updateCriterion(questionId, criterion, event.target.value)} /></label>; })}</div>}<div className="gradingQuestionFields"><label><span>题目得分</span><input aria-label={`题目得分 ${question.text}`} type="number" min="0" max={question.points} step="0.5" value={grade.score ?? 0} onChange={(event) => updateGrade(questionId, "score", event.target.value)} /></label><label><span>本题评语</span><input aria-label={`本题评语 ${question.text}`} value={grade.feedback || ""} onChange={(event) => updateGrade(questionId, "feedback", event.target.value)} placeholder="指出得分点或需要改进之处" /></label></div></section>; })}
      <section className="gradingFinal"><div><CheckCircle2 size={19} /><span><strong>最终成绩复核</strong><small>允许教师根据整卷质量调整总分。</small></span></div><label><span>最终总分</span><input aria-label="最终总分" type="number" min="0" max={detail.totalPoints} step="0.5" value={finalScore} onChange={(event) => setFinalScore(event.target.value)} /></label><label className="gradingFeedback"><span>总体评语</span><textarea aria-label="总体评语" rows="4" value={feedback} onChange={(event) => setFeedback(event.target.value)} /></label></section>
      {error && <p className="assessmentEditorError" role="alert"><AlertCircle size={16} />{error}</p>}<div className="assessmentDrawerActions"><button type="button" onClick={() => setDetail(null)}>取消</button><button type="button" className="portalPrimary" disabled={busy} onClick={save}>{busy ? "正在保存..." : "保存批改"}</button></div>
    </div></aside></div>}
  </div>;
}
