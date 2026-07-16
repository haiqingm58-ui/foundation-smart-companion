import { AlertCircle, CalendarClock, CheckCircle2, ShieldCheck, X } from "lucide-react";
import { useMemo, useState } from "react";
import { teacherApi } from "../../../api/teacher.js";


function isoOrNull(value) {
  return value ? new Date(value).toISOString() : null;
}


function createPublicationKey() {
  const token = globalThis.crypto?.randomUUID?.()
    || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `publish-${token}`;
}


export function PublicationDialog({ paper, classes = [], students = [], onClose, onPublished }) {
  const [publicationKey] = useState(createPublicationKey);
  const [classIds, setClassIds] = useState([]);
  const [studentIds, setStudentIds] = useState([]);
  const [startsAt, setStartsAt] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(paper.durationMinutes || 60);
  const [showAnswersMode, setShowAnswersMode] = useState("after_submission");
  const [allowResubmit, setAllowResubmit] = useState(false);
  const [autoGrade, setAutoGrade] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const targetStudents = useMemo(() => new Set([
    ...studentIds,
    ...students.filter((student) => classIds.includes(student.classId)).map((student) => student.id),
  ]), [classIds, studentIds, students]);

  const toggle = (setter) => (id) => setter((items) => items.includes(id) ? items.filter((item) => item !== id) : [...items, id]);
  const submit = async (event) => {
    event.preventDefault(); setError("");
    if (!classIds.length && !studentIds.length) { setError("至少选择一个班级或一名学生"); return; }
    setBusy(true);
    try {
      const result = await teacherApi.publishPaper(paper.id, {
        classIds, studentIds, startsAt: isoOrNull(startsAt), dueAt: isoOrNull(dueAt), durationMinutes: Number(durationMinutes),
        showAnswersMode, allowResubmit, autoGrade, publicationKey,
      });
      onPublished?.(result);
    } catch (reason) {
      setError(reason.message || "发布试卷失败");
      setBusy(false);
    }
  };

  return <div className="assessmentDrawerBackdrop">
    <aside className="assessmentDrawer publicationDrawer" role="dialog" aria-label="发布试卷" aria-modal="true">
      <header><div><span>考试发布</span><h2>{paper.title}</h2></div><button type="button" aria-label="关闭" onClick={onClose}><X size={19} /></button></header>
      <form className="assessmentDrawerBody publicationForm" onSubmit={submit}>
        <div className="publicationSnapshotNotice"><ShieldCheck size={21} /><span><strong>发布后题目、答案、评分规则和附件将生成不可变快照</strong><small>后续修改题库不会改变学生已经收到的试卷。</small></span></div>
        <section><header><div><CheckCircle2 size={17} /><strong>发布范围</strong></div><span>预计覆盖 {targetStudents.size} 名学生</span></header><div className="publicationTargets"><fieldset><legend>绑定班级</legend>{classes.length ? classes.map((item) => <label key={item.id}><input aria-label={`班级 ${item.name}`} type="checkbox" checked={classIds.includes(item.id)} onChange={() => toggle(setClassIds)(item.id)} /><span><strong>{item.name}</strong><small>{item.grade || ""} {item.major || ""}</small></span></label>) : <p>暂无绑定班级</p>}</fieldset><fieldset><legend>单独选择学生</legend>{students.length ? students.map((item) => <label key={item.id}><input aria-label={`学生 ${item.name}`} type="checkbox" checked={studentIds.includes(item.id)} onChange={() => toggle(setStudentIds)(item.id)} /><span><strong>{item.name}</strong><small>{item.studentNo} · {item.className || "未分班"}</small></span></label>) : <p>暂无绑定学生</p>}</fieldset></div></section>
        <section><header><div><CalendarClock size={17} /><strong>时间与作答规则</strong></div></header><div className="publicationSettings"><label><span>开始时间</span><input aria-label="开始时间" type="datetime-local" value={startsAt} onChange={(event) => setStartsAt(event.target.value)} /></label><label><span>截止时间</span><input aria-label="截止时间" type="datetime-local" value={dueAt} onChange={(event) => setDueAt(event.target.value)} /></label><label><span>考试时长</span><input aria-label="发布考试时长" type="number" min="1" max="1440" value={durationMinutes} onChange={(event) => setDurationMinutes(event.target.value)} /></label><label><span>答案公开</span><select aria-label="答案公开方式" value={showAnswersMode} onChange={(event) => setShowAnswersMode(event.target.value)}><option value="never">不公开答案</option><option value="after_submission">提交后公开</option><option value="after_close">考试关闭后公开</option></select></label></div><div className="publicationToggles"><label><input type="checkbox" checked={allowResubmit} onChange={(event) => setAllowResubmit(event.target.checked)} />允许重新作答</label><label><input type="checkbox" checked={autoGrade} onChange={(event) => setAutoGrade(event.target.checked)} />客观题自动判分</label></div></section>
        {error && <p className="assessmentEditorError" role="alert"><AlertCircle size={16} />{error}</p>}
        <div className="assessmentDrawerActions"><button type="button" onClick={onClose}>取消</button><button className="portalPrimary" disabled={busy}>{busy ? "正在发布..." : "确认发布"}</button></div>
      </form>
    </aside>
  </div>;
}
