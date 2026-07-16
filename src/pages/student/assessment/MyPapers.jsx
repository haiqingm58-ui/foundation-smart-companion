import { useEffect, useMemo, useState } from "react";
import { CalendarClock, CheckCircle2, Clock3, FileCheck2, Play, RefreshCw, UserRound } from "lucide-react";
import { studentApi } from "../../../api/student.js";


const FILTERS = [
  { id: "pending", label: "待完成", statuses: ["pending"] },
  { id: "in_progress", label: "进行中", statuses: ["in_progress"] },
  { id: "submitted", label: "已提交", statuses: ["pending_review", "submitted"] },
  { id: "graded", label: "已批改", statuses: ["graded"] },
];


function formatDate(value) {
  if (!value) return "长期有效";
  return new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(value));
}


function remainingText(seconds) {
  if (seconds === null || seconds === undefined) return "不限时";
  if (seconds <= 0) return "已截止";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.ceil(seconds % 3600 / 60);
  return hours ? `剩余 ${hours} 小时 ${minutes} 分` : `剩余 ${minutes} 分钟`;
}


export function MyPapers({ onStart, onViewResult }) {
  const [data, setData] = useState(null);
  const [filter, setFilter] = useState("pending");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError("");
    try { setData(await studentApi.papers()); }
    catch (reason) { setError(reason.message || "试卷加载失败"); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  const counts = useMemo(() => Object.fromEntries(FILTERS.map((item) => [item.id, data?.items?.filter((paper) => item.statuses.includes(paper.status)).length || 0])), [data?.items]);
  const selectedFilter = FILTERS.find((item) => item.id === filter) || FILTERS[0];
  const items = data?.items?.filter((paper) => selectedFilter.statuses.includes(paper.status)) || [];

  return <div className="studentPaperWorkspace">
    <header className="studentAssessmentSectionHead"><div><span>正式评测</span><h2>老师发布的考试与作业</h2><p>正式试卷会计入课程成绩，请在截止时间前完成并交卷。</p></div><button type="button" className="studentIconButton" aria-label="刷新试卷" title="刷新" onClick={load}><RefreshCw size={17} /></button></header>
    <div className="studentPaperTabs" role="tablist" aria-label="试卷状态">{FILTERS.map((item) => <button key={item.id} type="button" role="tab" aria-selected={filter === item.id} onClick={() => setFilter(item.id)}>{item.label} <span>{counts[item.id]}</span></button>)}</div>
    {loading ? <div className="studentAssessmentLoading" aria-label="试卷加载中"><span /><span /><span /></div> : error ? <div className="studentAssessmentState"><p>{error}</p><button type="button" onClick={load}>重试</button></div> : !items.length ? <div className="studentAssessmentState"><FileCheck2 size={25} /><p>当前没有{selectedFilter.label}的试卷</p><span>老师发布新试卷后会自动出现在这里。</span></div> : <div className="studentPaperList">{items.map((paper) => <article key={paper.assignmentId}>
      <div className="studentPaperStatusIcon">{paper.status === "graded" ? <CheckCircle2 size={20} /> : paper.status === "in_progress" ? <Clock3 size={20} /> : <FileCheck2 size={20} />}</div>
      <div className="studentPaperMain"><div><span>{paper.status === "pending" ? "待开始" : paper.status === "in_progress" ? "答题中" : paper.status === "graded" ? "已批改" : "待老师批改"}</span><h3>{paper.title}</h3><p>{paper.description || "请仔细阅读题目并在规定时间内完成。"}</p></div><dl><div><dt><UserRound size={14} />发布教师</dt><dd>{paper.teacherName || "课程教师"}</dd></div><div><dt><FileCheck2 size={14} />试卷规模</dt><dd>{paper.questionCount || 0} 题 · {paper.totalPoints} 分</dd></div><div><dt><CalendarClock size={14} />截止时间</dt><dd>{formatDate(paper.countdown?.dueAt)}</dd></div><div><dt><Clock3 size={14} />作答时间</dt><dd>{remainingText(paper.countdown?.remainingSeconds)}</dd></div></dl></div>
      <div className="studentPaperAction">{paper.status === "graded" ? <><strong>{paper.score} / {paper.totalPoints} 分</strong><button type="button" className="studentSecondaryButton" onClick={() => onViewResult?.(paper.submissionId, paper)}>查看结果</button></> : ["pending_review", "submitted"].includes(paper.status) ? <><strong>已提交</strong><button type="button" className="studentSecondaryButton" onClick={() => onViewResult?.(paper.submissionId, paper)}>查看进度</button></> : <button type="button" className="studentPrimaryButton" onClick={() => onStart?.(paper.assignmentId, paper)}><Play size={16} />{paper.status === "in_progress" ? "继续作答" : "开始作答"}</button>}</div>
    </article>)}</div>}
  </div>;
}
