import { Copy, FileCheck2, FilePlus2, Pencil, RefreshCw, Send, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { teacherApi } from "../../../api/teacher.js";
import { ExportMenu } from "./ExportMenu.jsx";
import { PaperBuilder } from "./PaperBuilder.jsx";
import { PublicationDialog } from "./PublicationDialog.jsx";


function statusLabel(status) {
  return ({ draft: "草稿", ready: "可发布", published: "已发布", archived: "已归档", closed: "已关闭" })[status] || status;
}


function formatDate(value) {
  return value ? new Intl.DateTimeFormat("zh-CN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "-";
}


export function PaperList({ subjects = [], defaultTab = "papers", notify }) {
  const [tab, setTab] = useState(defaultTab);
  const [papers, setPapers] = useState(null);
  const [assignments, setAssignments] = useState(null);
  const [classes, setClasses] = useState([]);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editor, setEditor] = useState(null);
  const [publication, setPublication] = useState(null);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [paperData, assignmentData, classData, studentData] = await Promise.all([
        teacherApi.papers(), teacherApi.assignments(), teacherApi.classes(), teacherApi.students("?pageSize=100"),
      ]);
      setPapers(paperData); setAssignments(assignmentData); setClasses(classData.items || []); setStudents(studentData.items || []);
    } catch (reason) {
      setError(reason.message || "试卷数据加载失败");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const edit = async (paper) => {
    try { setEditor(await teacherApi.paper(paper.id)); } catch (reason) { notify?.(reason.message || "试卷加载失败", "error"); }
  };
  const copy = async (paper) => {
    try { await teacherApi.copyPaper(paper.id); notify?.("试卷副本已创建"); await load(); } catch (reason) { notify?.(reason.message || "复制试卷失败", "error"); }
  };
  const remove = async (paper) => {
    if (!window.confirm(`确认删除“${paper.title}”吗？`)) return;
    try { await teacherApi.deletePaper(paper.id); notify?.("试卷已删除"); await load(); } catch (reason) { notify?.(reason.message || "删除试卷失败", "error"); }
  };

  if (editor) return <div className="assessmentDrawerBackdrop"><aside className="assessmentDrawer assessmentPaperDrawer" role="dialog" aria-label={editor.id ? "编辑试卷" : "新建试卷"} aria-modal="true"><header><div><span>组卷中心</span><h2>{editor.id ? editor.title : "新建试卷"}</h2></div><button type="button" aria-label="关闭" onClick={() => setEditor(null)}><X size={19} /></button></header><div className="assessmentDrawerBody"><PaperBuilder subjects={subjects} initialValue={editor.id ? editor : null} onCancel={() => setEditor(null)} onSaved={async () => { setEditor(null); notify?.("试卷已保存"); await load(); }} onPublish={(paper) => { setEditor(null); setPublication(paper); }} /></div></aside></div>;

  return <div className="assessmentWorkspace paperListWorkspace">
    <header className="assessmentPageHead"><div><span>可复用试卷与发布记录</span><h1>{tab === "papers" ? "组卷中心" : "考试与作业"}</h1><p>{tab === "papers" ? "手动选题或按蓝图自动组卷，保存为可复用版本。" : "查看已经发布给绑定学生的考试与作业。"}</p></div><div className="assessmentHeadActions"><button type="button" className="assessmentIconButton" aria-label="刷新试卷" title="刷新" onClick={load}><RefreshCw size={17} /></button>{tab === "papers" && <button type="button" className="portalPrimary" onClick={() => setEditor({})}><FilePlus2 size={16} />新建试卷</button>}</div></header>
    <div className="paperModeTabs paperListTabs" role="tablist" aria-label="试卷工作区"><button type="button" role="tab" aria-selected={tab === "papers"} onClick={() => setTab("papers")}>可复用试卷</button><button type="button" role="tab" aria-selected={tab === "exams"} onClick={() => setTab("exams")}>已发布考试</button></div>
    {loading ? <div className="assessmentLoading"><span /><span /><span /></div> : error ? <div className="assessmentState"><p>{error}</p><button type="button" onClick={load}>重试</button></div> : tab === "papers" ? <div className="assessmentListFrame"><header><strong>共 {papers?.total || 0} 份试卷</strong><span>发布前可继续修改或复制新版本</span></header>{!papers?.items?.length ? <div className="assessmentState"><FileCheck2 size={24} /><p>还没有可复用试卷</p><span>点击“新建试卷”开始组卷。</span></div> : <div className="assessmentTableWrap"><table className="assessmentTable paperListTable"><thead><tr><th>试卷</th><th>题量 / 总分</th><th>时长</th><th>状态</th><th>更新时间</th><th>操作</th></tr></thead><tbody>{papers.items.map((paper) => <tr key={paper.id}><td><strong>{paper.title}</strong><small>{paper.assemblyMode === "automatic" ? "自动组卷" : "手动组卷"} · <span>v{paper.version}</span></small></td><td>{paper.questionCount} 题 / {paper.totalPoints} 分</td><td>{paper.durationMinutes || "-"} 分钟</td><td><span className={`assessmentStatus ${paper.status}`}>{statusLabel(paper.status)}</span></td><td>{formatDate(paper.updatedAt)}</td><td><div className="assessmentRowActions"><button type="button" aria-label={`编辑试卷 ${paper.title}`} title="编辑" onClick={() => edit(paper)}><Pencil size={15} /></button><button type="button" aria-label={`复制试卷 ${paper.title}`} title="复制" onClick={() => copy(paper)}><Copy size={15} /></button><button type="button" aria-label={`发布试卷 ${paper.title}`} title="发布" disabled={!paper.questionCount || Boolean(paper.shortages?.length)} onClick={() => setPublication(paper)}><Send size={15} /></button><ExportMenu paperId={paper.id} label="导出" /><button type="button" className="danger" aria-label={`删除试卷 ${paper.title}`} title="删除" onClick={() => remove(paper)}><Trash2 size={15} /></button></div></td></tr>)}</tbody></table></div>}</div> : <div className="assessmentListFrame"><header><strong>共 {assignments?.total || 0} 场考试或作业</strong><span>数据来自真实发布和提交记录</span></header>{!assignments?.items?.length ? <div className="assessmentState"><p>尚未发布考试</p><span>在可复用试卷中选择“发布”。</span></div> : <div className="assessmentTableWrap"><table className="assessmentTable"><thead><tr><th>考试 / 作业</th><th>发布人数</th><th>已提交</th><th>完成率</th><th>平均分</th><th>截止时间</th><th>状态</th></tr></thead><tbody>{assignments.items.map((item) => <tr key={item.id}><td><strong>{item.title}</strong><small>{item.description || "无说明"}</small></td><td>{item.targetCount}</td><td>{item.submittedCount}</td><td>{item.completionRate}%</td><td>{item.averageScore ?? "-"}</td><td>{formatDate(item.dueAt)}</td><td><span className={`assessmentStatus ${item.status}`}>{statusLabel(item.status)}</span></td></tr>)}</tbody></table></div>}</div>}
    {publication && <PublicationDialog paper={publication} classes={classes} students={students} onClose={() => setPublication(null)} onPublished={async (result) => { setPublication(null); notify?.(`已发布给 ${result.targetCount} 名学生`); setTab("exams"); await load(); }} />}
  </div>;
}
