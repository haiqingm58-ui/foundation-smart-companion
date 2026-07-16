import { BookCopy, BookOpenCheck, Copy, FileCheck2, FilePlus2, Filter, Pencil, Plus, RefreshCw, Search, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { teacherApi } from "../../../api/teacher.js";
import { AttachmentPreview } from "./AttachmentPreview.jsx";
import { QuestionEditor } from "./QuestionEditor.jsx";


function queryString(values) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => { if (value) params.set(key, value); });
  return `?${params.toString()}`;
}

function sourceLabel(source) {
  return ({ textbook: "教材共享", imported: "共享 DOCX", "soil-mechanics-bank": "土力学共享题库", "teacher-import": "批量导入", "teacher-copy": "教师副本", teacher: "教师自建" })[source] || "课程题库";
}


function QuestionDrawer({ title, onClose, children }) {
  return <div className="assessmentDrawerBackdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <aside className="assessmentDrawer assessmentQuestionDrawer" role="dialog" aria-label={title} aria-modal="true">
      <header><div><span>题目编辑器</span><h2>{title}</h2></div><button type="button" onClick={onClose} aria-label="关闭"><X size={19} /></button></header>
      <div className="assessmentDrawerBody">{children}</div>
    </aside>
  </div>;
}


export function QuestionBank({ subjects = [], onOpenImport, notify }) {
  const [subjectId, setSubjectId] = useState(subjects[0]?.id || "");
  const [chapter, setChapter] = useState("");
  const [questionType, setQuestionType] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [source, setSource] = useState("");
  const [keyword, setKeyword] = useState("");
  const [data, setData] = useState(null);
  const [points, setPoints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editor, setEditor] = useState(null);
  const [preview, setPreview] = useState(null);

  useEffect(() => { if (!subjectId && subjects[0]?.id) setSubjectId(subjects[0].id); }, [subjects, subjectId]);

  const load = useCallback(async () => {
    if (!subjectId) { setLoading(false); return; }
    setLoading(true); setError("");
    try {
      const [questionData, pointData] = await Promise.all([
        teacherApi.questions(queryString({ subjectId, chapter, questionType, difficulty, source, search: keyword.trim(), pageSize: "100" })),
        teacherApi.knowledgePoints(queryString({ subjectId, status: "active", pageSize: "100" })),
      ]);
      setData(questionData);
      setPoints(pointData.items || []);
    } catch (reason) {
      setError(reason.message || "题库加载失败");
    } finally {
      setLoading(false);
    }
  }, [subjectId, chapter, questionType, difficulty, source, keyword]);

  useEffect(() => { load(); }, [load]);
  const selectedSubject = subjects.find((subject) => subject.id === subjectId) || subjects[0];
  const chapters = useMemo(() => [...new Set(points.map((point) => point.chapter).filter(Boolean))], [points]);
  const sharedCount = (data?.items || []).filter((item) => ["imported", "textbook", "soil-mechanics-bank"].includes(item.source)).length;
  const attachmentCount = (data?.items || []).reduce((sum, item) => sum + (item.attachments?.length || 0), 0);

  const save = async (payload) => {
    if (editor?.id) await teacherApi.updateQuestion(editor.id, payload);
    else await teacherApi.createQuestion(payload);
    setEditor(null);
    notify?.(editor?.id ? "题目已更新" : "题目已创建");
    await load();
  };

  const copy = async (item) => {
    try {
      const copied = await teacherApi.copyQuestion(item.id);
      notify?.("题目副本已创建，待复核");
      setEditor(copied);
      await load();
    } catch (reason) {
      notify?.(reason.message || "复制题目失败", "error");
    }
  };

  const remove = async (item) => {
    if (!window.confirm("确认删除这道教师自建题吗？")) return;
    try { await teacherApi.deleteQuestion(item.id); notify?.("题目已删除"); load(); } catch (reason) { notify?.(reason.message || "删除题目失败", "error"); }
  };

  return <div className="assessmentWorkspace">
    <header className="assessmentPageHead"><div><span>结构化课程题库</span><h1>题库管理</h1><p>按课程、章节和知识点组织题目，教师自建题可编辑，共享题需复制后修改。</p></div><div className="assessmentHeadActions"><button className="portalSecondary" type="button" onClick={onOpenImport}><FilePlus2 size={16} />批量导入</button><button className="portalPrimary" type="button" onClick={() => setEditor({})}><Plus size={16} />新建题目</button></div></header>
    <div className="assessmentCorpusStrip" aria-label="共享题库入库状态">
      <div><FileCheck2 size={19} /><span><strong>共享 DOCX 题库</strong><small>服务器统一解析，学生端不暴露源文件路径</small></span></div>
      <dl><div><dt>当前课程</dt><dd>{selectedSubject?.title || "-"}</dd></div><div><dt>当前共享题</dt><dd>{sharedCount} 道</dd></div><div><dt>图表公式附件</dt><dd>{attachmentCount} 项</dd></div><div><dt>入库状态</dt><dd className="ready">结构化可用</dd></div></dl>
    </div>
    <div className="assessmentToolbar assessmentQuestionFilters">
      <span className="assessmentFilterIcon"><Filter size={16} /></span>
      <label><span>课程</span><select value={subjectId} onChange={(event) => { setSubjectId(event.target.value); setChapter(""); }}><option value="">请选择课程</option>{subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.title}</option>)}</select></label>
      <label><span>章节</span><select value={chapter} onChange={(event) => setChapter(event.target.value)}><option value="">全部章节</option>{chapters.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label><span>题型</span><select value={questionType} onChange={(event) => setQuestionType(event.target.value)}><option value="">全部题型</option><option>单项选择题</option><option>多项选择题</option><option>判断题</option><option>填空题</option><option>简答题</option><option>计算题</option></select></label>
      <label><span>难度</span><select value={difficulty} onChange={(event) => setDifficulty(event.target.value)}><option value="">全部难度</option><option>基础</option><option>中等</option><option>困难</option></select></label>
      <label><span>来源</span><select value={source} onChange={(event) => setSource(event.target.value)}><option value="">全部来源</option><option value="soil-mechanics-bank">土力学共享题库</option><option value="imported">共享 DOCX</option><option value="textbook">教材共享</option><option value="teacher">教师自建</option><option value="teacher-copy">教师副本</option><option value="teacher-import">批量导入</option></select></label>
      <label className="assessmentSearch"><Search size={15} /><span className="srOnly">搜索题目</span><input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="搜索题干" /></label>
      <button className="assessmentIconButton" type="button" onClick={load} aria-label="刷新题库" title="刷新"><RefreshCw size={17} /></button>
    </div>
    <div className="assessmentListFrame">
      <header><strong>共 {data?.total ?? 0} 道题</strong><span>{points.length} 个可用知识点</span></header>
      {loading ? <div className="assessmentLoading" aria-label="题库加载中"><span /><span /><span /></div> : error ? <div className="assessmentState"><p>{error}</p><button type="button" onClick={load}>重试</button></div> : !data?.items?.length ? <div className="assessmentState"><BookOpenCheck size={24} /><p>当前筛选下暂无题目</p><span>可调整筛选、新建题目或批量导入。</span></div> : <div className="assessmentTableWrap"><table className="assessmentTable assessmentQuestionTable"><thead><tr><th>题目</th><th>题型</th><th>难度</th><th>分值</th><th>来源</th><th>操作</th></tr></thead><tbody>{data.items.map((item) => <tr key={item.id}><td><button type="button" className="assessmentQuestionTitle" onClick={() => setPreview(item)}><strong>{item.text}</strong><small>{item.chapter || "未分章"} · {item.knowledgePoints?.map((point) => point.name).join("、") || "未关联知识点"}</small></button></td><td>{item.questionType}</td><td><span className={`assessmentDifficulty ${item.difficulty}`}>{item.difficulty}</span></td><td>{item.points}</td><td><span className={`assessmentSource ${item.editable ? "owned" : "shared"}`}>{sourceLabel(item.source)}</span></td><td><div className="assessmentRowActions">{item.editable ? <><button type="button" onClick={() => setEditor(item)} aria-label="编辑" title="编辑题目"><Pencil size={15} /></button><button type="button" className="danger" onClick={() => remove(item)} aria-label={`删除题目 ${item.text}`} title="删除"><Trash2 size={15} /></button></> : <button type="button" className="assessmentCopyButton" onClick={() => copy(item)}><Copy size={14} />复制到我的题库</button>}</div></td></tr>)}</tbody></table></div>}
    </div>
    {editor && <QuestionDrawer title={editor.id ? "编辑题目" : "新建题目"} onClose={() => setEditor(null)}><QuestionEditor key={editor.id || "new"} initialValue={editor.id ? editor : null} subjects={subjects} knowledgePoints={points} onSave={save} onCancel={() => setEditor(null)} /></QuestionDrawer>}
    {preview && <QuestionDrawer title="题目详情" onClose={() => setPreview(null)}><div className="assessmentQuestionPreview"><span className="assessmentSource shared">{sourceLabel(preview.source)}</span><h3>{preview.text}</h3><dl><div><dt>章节</dt><dd>{preview.chapter || "未分章"}</dd></div><div><dt>题型</dt><dd>{preview.questionType}</dd></div><div><dt>知识点</dt><dd>{preview.knowledgePoints?.map((point) => point.name).join("、") || "未关联"}</dd></div><div><dt>批改方式</dt><dd>{preview.gradingMode === "manual" ? "教师人工批改" : "系统自动判分"}</dd></div></dl>{preview.options?.length > 0 && <ol>{preview.options.map((option) => <li key={option.label}><strong>{option.label}.</strong> {option.text}</li>)}</ol>}<AttachmentPreview attachments={preview.attachments || []} />{!preview.editable && <button className="portalPrimary" type="button" onClick={() => { const item = preview; setPreview(null); copy(item); }}><BookCopy size={16} />复制后编辑</button>}</div></QuestionDrawer>}
  </div>;
}
