import { ArrowRightLeft, BookOpenCheck, Pencil, Plus, RefreshCw, Search, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { teacherApi } from "../../../api/teacher.js";


function queryString(values) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => { if (value) params.set(key, value); });
  return `?${params.toString()}`;
}

function Drawer({ title, onClose, children }) {
  return <div className="assessmentDrawerBackdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <aside className="assessmentDrawer" role="dialog" aria-label={title} aria-modal="true">
      <header><div><span>教师题库工作台</span><h2>{title}</h2></div><button type="button" onClick={onClose} aria-label="关闭"><X size={19} /></button></header>
      <div className="assessmentDrawerBody">{children}</div>
    </aside>
  </div>;
}


function PointForm({ point, subjects, points, onClose, onDone, notify }) {
  const [subjectId, setSubjectId] = useState(point?.subjectId || subjects[0]?.id || "");
  const [chapter, setChapter] = useState(point?.chapter || "");
  const [name, setName] = useState(point?.name || "");
  const [description, setDescription] = useState(point?.description || "");
  const [status, setStatus] = useState(point?.status || "active");
  const [mergeTarget, setMergeTarget] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const mergeTargets = points.filter((item) => item.editable && item.subjectId === subjectId && item.id !== point?.id);

  const submit = async (event) => {
    event.preventDefault();
    if (!chapter.trim() || !name.trim()) { setError("章节和知识点名称不能为空"); return; }
    setBusy(true); setError("");
    try {
      const body = { subjectId, chapter: chapter.trim(), name: name.trim(), description: description.trim(), status };
      if (point) await teacherApi.updateKnowledgePoint(point.id, body);
      else await teacherApi.createKnowledgePoint(body);
      onDone();
    } catch (reason) {
      setError(reason.message || "知识点保存失败"); setBusy(false);
    }
  };

  const merge = async () => {
    if (!mergeTarget) { setError("请选择合并目标"); return; }
    setBusy(true); setError("");
    try {
      await teacherApi.mergeKnowledgePoint(point.id, mergeTarget);
      notify?.("知识点及题目关联已合并");
      onDone();
    } catch (reason) {
      setError(reason.message || "知识点合并失败"); setBusy(false);
    }
  };

  return <form className="assessmentEditor" onSubmit={submit}>
    <label className="assessmentFullField"><span>课程</span><select value={subjectId} onChange={(event) => setSubjectId(event.target.value)} disabled={Boolean(point)}>{subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.title}</option>)}</select></label>
    <label className="assessmentFullField"><span>章节</span><input value={chapter} onChange={(event) => setChapter(event.target.value)} placeholder="例如：第二章 土的渗透性" /></label>
    <label className="assessmentFullField"><span>知识点名称</span><input value={name} onChange={(event) => setName(event.target.value)} /></label>
    <label className="assessmentFullField"><span>说明</span><textarea rows="5" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="用于教师辨识边界、易错点和出题范围" /></label>
    <label className="assessmentFullField"><span>状态</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="active">启用</option><option value="inactive">停用</option></select></label>
    {point && mergeTargets.length > 0 && <section className="assessmentMergeBox"><div><ArrowRightLeft size={17} /><span><strong>合并重复知识点</strong><small>关联题目会迁移到目标知识点，原知识点随后删除。</small></span></div><select aria-label="合并目标" value={mergeTarget} onChange={(event) => setMergeTarget(event.target.value)}><option value="">选择目标知识点</option>{mergeTargets.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button type="button" onClick={merge} disabled={busy || !mergeTarget}>执行合并</button></section>}
    {error && <p className="assessmentEditorError" role="alert">{error}</p>}
    <div className="assessmentDrawerActions"><button type="button" onClick={onClose}>取消</button><button className="portalPrimary" disabled={busy}>{busy ? "正在保存..." : "保存知识点"}</button></div>
  </form>;
}


export function KnowledgePointLibrary({ subjects = [], notify }) {
  const [subjectId, setSubjectId] = useState(subjects[0]?.id || "");
  const [chapter, setChapter] = useState("");
  const [status, setStatus] = useState("");
  const [query, setQuery] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editor, setEditor] = useState(null);
  const [related, setRelated] = useState(null);
  const [relatedLoading, setRelatedLoading] = useState(false);

  useEffect(() => { if (!subjectId && subjects[0]?.id) setSubjectId(subjects[0].id); }, [subjects, subjectId]);

  const load = useCallback(async () => {
    if (!subjectId) { setLoading(false); return; }
    setLoading(true); setError("");
    try {
      setData(await teacherApi.knowledgePoints(queryString({ subjectId, chapter, status, pageSize: "100" })));
    } catch (reason) {
      setError(reason.message || "知识点加载失败");
    } finally {
      setLoading(false);
    }
  }, [subjectId, chapter, status]);

  useEffect(() => { load(); }, [load]);
  const selectedSubject = subjects.find((subject) => subject.id === subjectId) || subjects[0];
  const chapters = useMemo(() => [...new Set((data?.items || []).map((point) => point.chapter).filter(Boolean))], [data]);
  const rows = useMemo(() => (data?.items || []).filter((point) => `${point.name}${point.chapter}${point.description || ""}`.includes(query.trim())), [data, query]);

  const showRelated = async (point) => {
    setRelated({ point, items: [], total: 0, error: "" });
    setRelatedLoading(true);
    try {
      const result = await teacherApi.questions(queryString({ subjectId: point.subjectId, knowledgePointId: point.id, pageSize: "100" }));
      setRelated({ point, ...result, error: "" });
    } catch (reason) {
      setRelated({ point, items: [], total: 0, error: reason.message || "关联题目加载失败" });
    } finally {
      setRelatedLoading(false);
    }
  };

  const remove = async (point) => {
    if (!window.confirm(`确认删除知识点“${point.name}”吗？`)) return;
    try { await teacherApi.deleteKnowledgePoint(point.id); notify?.("知识点已删除"); load(); } catch (reason) { notify?.(reason.message || "删除失败", "error"); }
  };

  return <div className="assessmentWorkspace">
    <header className="assessmentPageHead"><div><span>有限知识点体系</span><h1>知识点库</h1><p>维护课程知识点边界，查看每个知识点关联的题目数量。</p></div><button className="portalPrimary" type="button" onClick={() => setEditor({})}><Plus size={16} />新增知识点</button></header>
    <div className="assessmentSubjectStrip" aria-label="课程知识点统计"><div><BookOpenCheck size={18} /><span><strong>{selectedSubject?.title || "课程"}</strong><small>课程已定义 {selectedSubject?.knowledgePointCount || 0} 个</small></span></div><div><span>当前结果</span><strong>{data?.total ?? 0}</strong></div><div><span>启用</span><strong>{data?.statusCounts?.active ?? 0}</strong></div><div><span>停用</span><strong>{data?.statusCounts?.inactive ?? 0}</strong></div></div>
    <div className="assessmentToolbar">
      <label><span>课程</span><select value={subjectId} onChange={(event) => { setSubjectId(event.target.value); setChapter(""); }}><option value="">请选择课程</option>{subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.title}</option>)}</select></label>
      <label><span>章节</span><select value={chapter} onChange={(event) => setChapter(event.target.value)}><option value="">全部章节</option>{chapters.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label><span>状态</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">全部状态</option><option value="active">启用</option><option value="inactive">停用</option></select></label>
      <label className="assessmentSearch"><Search size={15} /><span className="srOnly">搜索知识点</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索名称、章节或说明" /></label>
      <button className="assessmentIconButton" type="button" onClick={load} aria-label="刷新知识点" title="刷新"><RefreshCw size={17} /></button>
    </div>
    <div className="assessmentListFrame">
      <header><strong>共 {data?.total ?? 0} 个知识点</strong><span>点击关联题数可查看题目</span></header>
      {loading ? <div className="assessmentLoading" aria-label="知识点加载中"><span /><span /><span /></div> : error ? <div className="assessmentState"><p>{error}</p><button type="button" onClick={load}>重试</button></div> : !rows.length ? <div className="assessmentState"><p>当前筛选下暂无知识点</p><span>可清除筛选或新增知识点。</span></div> : <div className="assessmentTableWrap"><table className="assessmentTable"><thead><tr><th>知识点</th><th>章节</th><th>关联题目</th><th>状态</th><th>权限</th><th>操作</th></tr></thead><tbody>{rows.map((point) => <tr key={point.id}><td><strong>{point.name}</strong><small>{point.description || "暂无说明"}</small></td><td>{point.chapter}</td><td><button className="assessmentLinkButton" type="button" onClick={() => showRelated(point)} aria-label={`查看 ${point.questionCount} 道关联题`}>{point.questionCount} 道</button></td><td><span className={`assessmentStatus ${point.status}`}>{point.status === "active" ? "启用" : "停用"}</span></td><td>{point.editable ? "教师自建" : "课程共享"}</td><td><div className="assessmentRowActions">{point.editable ? <><button type="button" onClick={() => setEditor(point)} aria-label={`编辑 ${point.name}`} title="编辑"><Pencil size={15} /></button><button type="button" className="danger" onClick={() => remove(point)} aria-label={`删除 ${point.name}`} title="删除"><Trash2 size={15} /></button></> : <span>只读</span>}</div></td></tr>)}</tbody></table></div>}
    </div>
    {editor && <Drawer title={editor.id ? "编辑知识点" : "新增知识点"} onClose={() => setEditor(null)}><PointForm point={editor.id ? editor : null} subjects={subjects} points={data?.items || []} notify={notify} onClose={() => setEditor(null)} onDone={() => { setEditor(null); notify?.(editor.id ? "知识点已更新" : "知识点已创建"); load(); }} /></Drawer>}
    {related && <Drawer title={`${related.point.name}关联题目`} onClose={() => setRelated(null)}>{relatedLoading ? <div className="assessmentLoading"><span /><span /><span /></div> : related.error ? <div className="assessmentState"><p>{related.error}</p></div> : related.items?.length ? <div className="assessmentRelatedList">{related.items.map((question) => <article key={question.id}><div><strong>{question.text}</strong><span>{question.questionType} · {question.difficulty}</span></div></article>)}</div> : <div className="assessmentState"><p>暂无关联题目</p><span>编辑题目时可关联这个知识点。</span></div>}</Drawer>}
  </div>;
}
