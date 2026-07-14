import {
  BarChart3, BookOpenCheck, Boxes, ClipboardCheck, FilePlus2, FileText, GraduationCap,
  LayoutDashboard, LibraryBig, Megaphone, Plus, School, Send, Trash2, Upload, Users,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { apiUrl } from "../../api/client.js";
import { teacherApi } from "../../api/teacher.js";
import {
  ConfirmDialog, DataTable, EmptyState, ErrorState, Field, LoadingState, Modal, PageHeading, Panel,
  PortalShell, SearchField, StatGrid, StatusBadge, Toast,
} from "../../components/portal/PortalKit.jsx";
import { useAuth } from "../../stores/AuthContext.jsx";
import { QuestionImportModal } from "./QuestionImportModal.jsx";


const navItems = [
  { key: "dashboard", label: "教学工作台", icon: LayoutDashboard },
  { key: "classes", label: "班级管理", icon: School },
  { key: "students", label: "学生管理", icon: Users },
  { key: "resources", label: "资料与 RAG", icon: LibraryBig },
  { key: "question-bank", label: "题库管理", icon: BookOpenCheck },
  { key: "assignments", label: "作业管理", icon: FileText },
  { key: "grading", label: "作业批改", icon: ClipboardCheck },
  { key: "analytics", label: "学情分析", icon: BarChart3 },
  { key: "notices", label: "通知管理", icon: Megaphone },
];


const loaders = {
  dashboard: teacherApi.dashboard,
  classes: teacherApi.classes,
  students: teacherApi.students,
  resources: teacherApi.resources,
  "question-bank": teacherApi.questions,
  assignments: teacherApi.assignments,
  grading: teacherApi.submissions,
  analytics: teacherApi.analytics,
  notices: teacherApi.notices,
};


function currentView(pathname) {
  const tail = pathname.replace(/^\/teacher\/?/, "").split("/")[0];
  return navItems.some((item) => item.key === tail) ? tail : "dashboard";
}


function formatDate(value) {
  return value ? new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "-";
}


function formatSize(bytes = 0) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}


export default function TeacherApp() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const active = currentView(location.pathname);
  const [cache, setCache] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState(null);

  const load = useCallback(async (key = active, force = false) => {
    if (cache[key] && !force) { setLoading(false); return cache[key]; }
    setLoading(true);
    setError("");
    try {
      const data = await loaders[key]();
      setCache((previous) => ({ ...previous, [key]: data }));
      return data;
    } catch (reason) {
      setError(reason.message || "数据加载失败");
      return null;
    } finally {
      setLoading(false);
    }
  }, [active, cache]);

  useEffect(() => { load(active); }, [active]);

  const go = (key) => navigate(key === "dashboard" ? "/teacher" : `/teacher/${key}`);
  const notify = (message, tone = "success") => setToast({ message, tone });
  const refresh = () => load(active, true);
  const common = { data: cache[active], loading, error, retry: refresh, open: setModal, notify, refresh, cache, setCache };

  return (
    <PortalShell roleLabel="教师工作台" navItems={navItems} active={active} onNavigate={go} user={user} onLogout={logout}>
      {active === "dashboard" && <TeacherDashboard {...common} go={go} />}
      {active === "classes" && <ClassesView {...common} />}
      {active === "students" && <StudentsView {...common} />}
      {active === "resources" && <ResourcesView {...common} />}
      {active === "question-bank" && <QuestionsView {...common} />}
      {active === "assignments" && <AssignmentsView {...common} />}
      {active === "grading" && <GradingView {...common} />}
      {active === "analytics" && <AnalyticsView {...common} />}
      {active === "notices" && <NoticesView {...common} />}
      {modal?.type === "resource" && <ResourceModal close={() => setModal(null)} done={() => { setModal(null); refresh(); notify("资料已上传并进入 RAG 知识库"); }} />}
      {modal?.type === "question" && <QuestionModal item={modal.item} close={() => setModal(null)} done={() => { setModal(null); refresh(); notify("题目已保存"); }} />}
      {modal?.type === "question-import" && <QuestionImportModal close={() => setModal(null)} done={(count) => { setModal(null); refresh(); notify(`已导入 ${count} 道题目`); }} />}
      {modal?.type === "assignment" && <AssignmentModal cache={cache} setCache={setCache} close={() => setModal(null)} done={() => { setModal(null); refresh(); notify("作业已创建"); }} />}
      {modal?.type === "grade" && <GradeModal submission={modal.item} close={() => setModal(null)} done={() => { setModal(null); refresh(); notify("批改结果已保存"); }} />}
      {modal?.type === "notice" && <NoticeModal cache={cache} setCache={setCache} close={() => setModal(null)} done={() => { setModal(null); refresh(); notify("通知已发布"); }} />}
      {modal?.type === "confirm" && <ConfirmDialog {...modal} onClose={() => setModal(null)} />}
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </PortalShell>
  );
}


function ViewState({ loading, error, retry, children }) {
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} retry={retry} />;
  return children;
}


function TeacherDashboard({ data = {}, loading, error, retry, go }) {
  const stats = [
    { label: "管理学生", value: data.studentTotal, note: `${data.classTotal || 0} 个教学班`, icon: Users, tone: "blue" },
    { label: "平均成绩", value: `${data.averageScore || 0} 分`, note: "来自真实练习记录", icon: BarChart3, tone: "green" },
    { label: "知识库资料", value: data.resourceTotal, note: "已完成 RAG 切块", icon: LibraryBig, tone: "teal" },
    { label: "待批改", value: data.pendingGrading, note: `${data.assignmentTotal || 0} 份作业`, icon: ClipboardCheck, tone: "amber" },
  ];
  return <ViewState loading={loading} error={error} retry={retry}><PageHeading eyebrow="课程教学" title="教学工作台" description="管理课程资料、题目、作业与学生学习情况。" /><StatGrid items={stats} /><div className="portalTwoColumn"><Panel title="常用教学操作" description="直接进入高频工作流程"><div className="portalQuickGrid"><button onClick={() => go("resources")}><Upload size={20} /><strong>上传教学资料</strong><span>自动提取并加入 RAG</span></button><button onClick={() => go("question-bank")}><FilePlus2 size={20} /><strong>创建练习题</strong><span>支持客观题与主观题</span></button><button onClick={() => go("assignments")}><Send size={20} /><strong>布置作业</strong><span>选择题目与学生范围</span></button><button onClick={() => go("analytics")}><BarChart3 size={20} /><strong>查看学情</strong><span>成绩、进度与薄弱点</span></button></div></Panel><Panel title="教学概况" description="当前账号的数据范围"><dl className="portalDefinition"><div><dt>题库题目</dt><dd>{data.questionTotal || 0} 道</dd></div><div><dt>已建作业</dt><dd>{data.assignmentTotal || 0} 份</dd></div><div><dt>资料数量</dt><dd>{data.resourceTotal || 0} 份</dd></div><div><dt>学生完成率</dt><dd>{data.completionRate || 0}%</dd></div></dl></Panel></div></ViewState>;
}


function ClassesView({ data, loading, error, retry }) {
  return <ViewState loading={loading} error={error} retry={retry}><PageHeading eyebrow="教学组织" title="班级管理" description="仅显示管理员已绑定给您的班级。" /><Panel title="我的班级" description={`共 ${data?.total || 0} 个班级`}><DataTable rows={data?.items} columns={[{ key: "name", label: "班级" }, { key: "grade", label: "年级" }, { key: "major", label: "专业" }]} empty="暂无已绑定班级" /></Panel></ViewState>;
}


function StudentsView({ data, loading, error, retry }) {
  const [query, setQuery] = useState("");
  const rows = useMemo(() => (data?.items || []).filter((item) => `${item.name}${item.studentNo}${item.className}`.includes(query)), [data, query]);
  return <ViewState loading={loading} error={error} retry={retry}><PageHeading eyebrow="学生学习" title="学生管理" description="查看强绑定范围内学生的真实进度与成绩。" /><Panel title="学生列表" description={`共 ${data?.total || 0} 名学生`} actions={<SearchField value={query} onChange={setQuery} placeholder="搜索姓名、学号或班级" />}><DataTable rows={rows} columns={[{ key: "name", label: "姓名" }, { key: "studentNo", label: "学号" }, { key: "className", label: "班级" }, { key: "progress", label: "学习进度", render: (row) => <span>{row.progress}%</span> }, { key: "averageScore", label: "平均分", render: (row) => <strong>{row.averageScore}</strong> }, { key: "status", label: "状态", render: (row) => <StatusBadge status={row.status} /> }]} empty="没有匹配的学生" /></Panel></ViewState>;
}


function ResourcesView({ data, loading, error, retry, open, notify, refresh }) {
  const remove = (item) => open({ type: "confirm", title: "删除教学资料", message: `确认删除“${item.title}”吗？相关 RAG 切块也会一并删除。`, confirmLabel: "确认删除", danger: true, onConfirm: async () => { await teacherApi.deleteResource(item.id); notify("资料已删除"); refresh(); } });
  return <ViewState loading={loading} error={error} retry={retry}><PageHeading eyebrow="课程知识库" title="资料与 RAG" description="上传的资料会在服务器端提取、切块，并参与学生问答检索。" actions={<button className="portalPrimary" onClick={() => open({ type: "resource" })}><Upload size={17} />上传资料</button>} /><Panel title="我的知识库" description={`已收录 ${data?.total || 0} 份资料`}><DataTable rows={data?.items} columns={[{ key: "title", label: "资料名称", render: (row) => <div className="portalTitleCell"><strong>{row.title}</strong><span>{row.name}</span></div> }, { key: "chapter", label: "关联章节" }, { key: "fileSize", label: "大小", render: (row) => formatSize(row.fileSize) }, { key: "visibility", label: "可见范围", render: (row) => <StatusBadge status={row.visibility} /> }, { key: "rag", label: "知识库状态", render: () => <span className="portalRagBadge"><Boxes size={14} />已进入 RAG 知识库</span> }, { key: "actions", label: "操作", render: (row) => <div className="portalRowActions"><a href={apiUrl(`/teacher/resources/${row.id}/preview`)} target="_blank" rel="noreferrer">预览</a><a href={apiUrl(`/teacher/resources/${row.id}/download`)}>下载</a><button onClick={() => remove(row)} aria-label={`删除 ${row.title}`}><Trash2 size={16} /></button></div> }]} empty="尚未上传教学资料" /></Panel></ViewState>;
}


function QuestionsView({ data, loading, error, retry, open, notify, refresh }) {
  const [query, setQuery] = useState("");
  const rows = (data?.items || []).filter((item) => `${item.text}${item.chapter}${item.knowledgePoint}`.includes(query));
  const remove = (item) => open({ type: "confirm", title: "删除题目", message: "确认删除这道自建题目吗？已被作业引用的题目将由服务器拒绝删除。", confirmLabel: "确认删除", danger: true, onConfirm: async () => { await teacherApi.deleteQuestion(item.id); notify("题目已删除"); refresh(); } });
  return <ViewState loading={loading} error={error} retry={retry}><PageHeading eyebrow="教学内容" title="题库管理" description="教材题目只读，自建题目可编辑和用于作业。" actions={<><button className="portalSecondary" onClick={() => open({ type: "question-import" })}><FilePlus2 size={17} />批量导入</button><button className="portalPrimary" onClick={() => open({ type: "question" })}><Plus size={17} />新建题目</button></>} /><Panel title="课程题库" description={`共 ${data?.total || 0} 道题`} actions={<SearchField value={query} onChange={setQuery} placeholder="搜索题干或知识点" />}><DataTable rows={rows} columns={[{ key: "text", label: "题目", render: (row) => <div className="portalQuestionCell"><strong>{row.text}</strong><span>{row.chapter || "未关联章节"} · {row.knowledgePoint || "未标注知识点"}</span></div> }, { key: "questionType", label: "题型" }, { key: "difficulty", label: "难度" }, { key: "points", label: "分值" }, { key: "source", label: "来源", render: (row) => row.source === "textbook" ? "教材题库" : row.source === "teacher-import" ? "批量导入" : "教师自建" }, { key: "actions", label: "操作", render: (row) => row.source !== "textbook" ? <div className="portalRowActions"><button className="portalTextButton" onClick={() => open({ type: "question", item: row })}>编辑</button><button className="portalIconDanger" onClick={() => remove(row)} aria-label={`删除题目 ${row.text}`}><Trash2 size={16} /></button></div> : "只读" }]} empty="题库中暂无题目" /></Panel></ViewState>;
}


function AssignmentsView({ data, loading, error, retry, open }) {
  return <ViewState loading={loading} error={error} retry={retry}><PageHeading eyebrow="作业流程" title="作业管理" description="从题库选题并发送给强绑定范围内的学生。" actions={<button className="portalPrimary" onClick={() => open({ type: "assignment" })}><Plus size={17} />创建作业</button>} /><Panel title="作业列表" description={`共 ${data?.total || 0} 份作业`}><DataTable rows={data?.items} columns={[{ key: "title", label: "作业名称", render: (row) => <div className="portalTitleCell"><strong>{row.title}</strong><span>{row.description || "无说明"}</span></div> }, { key: "dueAt", label: "截止时间", render: (row) => formatDate(row.dueAt) }, { key: "targetCount", label: "布置人数" }, { key: "submittedCount", label: "已提交" }, { key: "completionRate", label: "完成率", render: (row) => `${row.completionRate || 0}%` }, { key: "averageScore", label: "平均分", render: (row) => row.averageScore ?? "-" }, { key: "status", label: "状态", render: (row) => <StatusBadge status={row.status} /> }]} empty="尚未创建作业" /></Panel></ViewState>;
}


function GradingView({ data, loading, error, retry, open }) {
  return <ViewState loading={loading} error={error} retry={retry}><PageHeading eyebrow="作业流程" title="作业批改" description="只能查看和批改本人发布作业的学生提交。" /><Panel title="学生提交" description={`共 ${data?.total || 0} 条提交记录`}><DataTable rows={data?.items} columns={[{ key: "assignmentTitle", label: "作业" }, { key: "studentName", label: "学生", render: (row) => <div className="portalTitleCell"><strong>{row.studentName}</strong><span>{row.studentNo}</span></div> }, { key: "submittedAt", label: "提交时间", render: (row) => formatDate(row.submittedAt) }, { key: "score", label: "得分", render: (row) => row.score ?? "-" }, { key: "status", label: "状态", render: (row) => <StatusBadge status={row.status} /> }, { key: "actions", label: "操作", render: (row) => <button className="portalTextButton" onClick={() => open({ type: "grade", item: row })}>{row.status === "graded" ? "重新批改" : "开始批改"}</button> }]} empty="暂无学生提交" /></Panel></ViewState>;
}


function AnalyticsView({ data = {}, loading, error, retry }) {
  return <ViewState loading={loading} error={error} retry={retry}><PageHeading eyebrow="数据洞察" title="学情分析" description="统计仅来自当前教师管理范围内学生的真实学习记录。" /><StatGrid items={[{ label: "学生总数", value: data.studentTotal, note: "强绑定学生", icon: Users }, { label: "平均成绩", value: `${data.averageScore || 0} 分`, note: "练习与作业", icon: BarChart3, tone: "green" }, { label: "平均进度", value: `${data.averageProgress || 0}%`, note: "教材学习进度", icon: GraduationCap, tone: "teal" }]} /><Panel title="薄弱知识点" description="根据实际作答记录汇总">{data.weakKnowledgePoints?.length ? <div className="portalTagList">{data.weakKnowledgePoints.map((item) => <span key={item.name || item}>{item.name || item}</span>)}</div> : <EmptyState title="暂无足够的薄弱点数据" description="学生完成更多练习后，系统会在这里给出分析。" />}</Panel></ViewState>;
}


function NoticesView({ data, loading, error, retry, open }) {
  return <ViewState loading={loading} error={error} retry={retry}><PageHeading eyebrow="教学沟通" title="通知管理" description="向全部学生或指定教学班发布课程通知。" actions={<button className="portalPrimary" onClick={() => open({ type: "notice" })}><Megaphone size={17} />发布通知</button>} /><Panel title="已发布通知" description={`共 ${data?.total || 0} 条`}><DataTable rows={data?.items} columns={[{ key: "title", label: "标题", render: (row) => <div className="portalTitleCell"><strong>{row.title}</strong><span>{row.content}</span></div> }, { key: "audience", label: "范围", render: (row) => row.audience === "all" ? "全部学生" : `${row.classScope?.length || 0} 个班级` }, { key: "publishedAt", label: "发布时间", render: (row) => formatDate(row.publishedAt) }]} empty="尚未发布通知" /></Panel></ViewState>;
}


function ResourceModal({ close, done }) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [file, setFile] = useState(null); const [dragging, setDragging] = useState(false);
  const submit = async (event) => { event.preventDefault(); if (!file) { setError("请选择资料文件"); return; } const body = new FormData(event.currentTarget); body.set("file", file); setBusy(true); setError(""); try { await teacherApi.uploadResource(body); done(); } catch (reason) { setError(reason.message); setBusy(false); } };
  return <Modal title="上传教学资料" onClose={close}><form className="portalForm" onSubmit={submit}><label className={`portalDropzone ${dragging ? "dragging" : ""}`} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); setFile(event.dataTransfer.files[0] || null); }}><Upload size={24} /><strong>{file ? file.name : "拖拽文件到此处，或点击选择"}</strong><span>支持 PDF、DOCX、PPTX、XLSX、图片、Markdown 和 TXT，最大 25MB</span><input type="file" name="fileInput" accept=".pdf,.docx,.pptx,.xlsx,.png,.jpg,.jpeg,.webp,.md,.markdown,.txt" onChange={(event) => setFile(event.target.files[0] || null)} /></label><div className="portalFormGrid"><Field label="关联章节"><input name="chapter" placeholder="例如：第3章 桩基础" /></Field><Field label="知识点"><input name="knowledgePoint" placeholder="例如：单桩竖向承载力" /></Field></div><Field label="可见范围"><select name="visibility" defaultValue="class"><option value="class">绑定班级可见</option><option value="private">仅自己可见</option></select></Field>{error && <p className="portalFormError">{error}</p>}<div className="portalFormActions"><button type="button" onClick={close}>取消</button><button className="portalPrimary" disabled={busy}>{busy ? "正在提取并建立索引..." : "上传并建立索引"}</button></div></form></Modal>;
}


function QuestionModal({ close, done, item }) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const submit = async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); setBusy(true); try { const body = { text: form.get("text"), questionType: form.get("questionType"), difficulty: form.get("difficulty"), points: Number(form.get("points")), chapter: form.get("chapter"), knowledgePoint: form.get("knowledgePoint"), correctAnswer: form.get("correctAnswer"), explanation: form.get("explanation"), options: item?.options || [], rubric: item?.rubric || [] }; if (item) await teacherApi.updateQuestion(item.id, body); else await teacherApi.createQuestion(body); done(); } catch (reason) { setError(reason.message); setBusy(false); } };
  return <Modal title={item ? "编辑题目" : "新建题目"} onClose={close} wide><form className="portalForm" onSubmit={submit}><Field label="题干"><textarea name="text" rows="4" defaultValue={item?.text || ""} required /></Field><div className="portalFormGrid"><Field label="题型"><select name="questionType" defaultValue={item?.questionType || "简答题"}><option>简答题</option><option>单项选择题</option><option>多项选择题</option><option>判断题</option><option>填空题</option><option>计算题</option></select></Field><Field label="难度"><select name="difficulty" defaultValue={item?.difficulty || "基础"}><option>基础</option><option>中等</option><option>困难</option></select></Field><Field label="分值"><input name="points" type="number" min="1" defaultValue={item?.points || 10} required /></Field><Field label="章节"><input name="chapter" defaultValue={item?.chapter || ""} placeholder="第3章 桩基础" /></Field></div><Field label="知识点"><input name="knowledgePoint" defaultValue={item?.knowledgePoint || ""} /></Field><Field label="标准答案"><textarea name="correctAnswer" rows="3" defaultValue={typeof item?.correctAnswer === "string" ? item.correctAnswer : ""} /></Field><Field label="答案解析"><textarea name="explanation" rows="3" defaultValue={item?.explanation || ""} /></Field>{error && <p className="portalFormError">{error}</p>}<div className="portalFormActions"><button type="button" onClick={close}>取消</button><button className="portalPrimary" disabled={busy}>保存题目</button></div></form></Modal>;
}


function AssignmentModal({ cache, setCache, close, done }) {
  const [busy, setBusy] = useState(true); const [error, setError] = useState(""); const [students, setStudents] = useState(cache.students?.items || []); const [questions, setQuestions] = useState(cache["question-bank"]?.items || []);
  useEffect(() => { Promise.all([teacherApi.students(), teacherApi.questions()]).then(([studentData, questionData]) => { setStudents(studentData.items); setQuestions(questionData.items); setCache((old) => ({ ...old, students: studentData, "question-bank": questionData })); setBusy(false); }).catch((reason) => { setError(reason.message); setBusy(false); }); }, []);
  const submit = async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); setBusy(true); try { await teacherApi.createAssignment({ title: form.get("title"), description: form.get("description"), dueAt: form.get("dueAt") || null, totalPoints: Number(form.get("totalPoints")), status: "published", allowResubmit: form.get("allowResubmit") === "on", autoGrade: true, studentIds: form.getAll("studentIds"), questionIds: form.getAll("questionIds") }); done(); } catch (reason) { setError(reason.message); setBusy(false); } };
  return <Modal title="创建作业" onClose={close} wide>{busy && !students.length ? <LoadingState /> : <form className="portalForm" onSubmit={submit}><Field label="作业名称"><input name="title" required /></Field><Field label="作业说明"><textarea name="description" rows="2" /></Field><div className="portalFormGrid"><Field label="截止时间"><input name="dueAt" type="datetime-local" /></Field><Field label="总分"><input name="totalPoints" type="number" min="1" defaultValue="100" required /></Field></div><fieldset className="portalChoiceGroup"><legend>选择学生</legend>{students.map((item) => <label key={item.id}><input type="checkbox" name="studentIds" value={item.id} />{item.name} <span>{item.studentNo}</span></label>)}</fieldset><fieldset className="portalChoiceGroup"><legend>选择题目</legend>{questions.map((item) => <label key={item.id}><input type="checkbox" name="questionIds" value={item.id} /><span>{item.text}</span></label>)}</fieldset><label className="portalCheck"><input type="checkbox" name="allowResubmit" />允许学生重新提交</label>{error && <p className="portalFormError">{error}</p>}<div className="portalFormActions"><button type="button" onClick={close}>取消</button><button className="portalPrimary" disabled={busy}>发布作业</button></div></form>}</Modal>;
}


function GradeModal({ submission, close, done }) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const submit = async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); setBusy(true); try { await teacherApi.gradeSubmission(submission.id, { score: Number(form.get("score")), feedback: form.get("feedback") }); done(); } catch (reason) { setError(reason.message); setBusy(false); } };
  return <Modal title={`批改：${submission.assignmentTitle}`} onClose={close}><form className="portalForm" onSubmit={submit}><div className="portalSubject"><strong>{submission.studentName}</strong><span>{submission.studentNo} · {formatDate(submission.submittedAt)}</span></div><Field label="得分"><input name="score" type="number" min="0" step="0.5" defaultValue={submission.score ?? ""} required /></Field><Field label="教师评语"><textarea name="feedback" rows="5" defaultValue={submission.feedback || ""} /></Field>{error && <p className="portalFormError">{error}</p>}<div className="portalFormActions"><button type="button" onClick={close}>取消</button><button className="portalPrimary" disabled={busy}>保存批改</button></div></form></Modal>;
}


function NoticeModal({ cache, setCache, close, done }) {
  const [classes, setClasses] = useState(cache.classes?.items || []); const [busy, setBusy] = useState(!cache.classes); const [error, setError] = useState("");
  useEffect(() => { if (!cache.classes) teacherApi.classes().then((data) => { setClasses(data.items); setCache((old) => ({ ...old, classes: data })); setBusy(false); }).catch((reason) => { setError(reason.message); setBusy(false); }); }, []);
  const submit = async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); setBusy(true); try { await teacherApi.createNotice({ title: form.get("title"), content: form.get("content"), audience: form.get("audience"), classScope: form.getAll("classScope") }); done(); } catch (reason) { setError(reason.message); setBusy(false); } };
  return <Modal title="发布课程通知" onClose={close}><form className="portalForm" onSubmit={submit}><Field label="通知标题"><input name="title" required /></Field><Field label="通知内容"><textarea name="content" rows="5" required /></Field><Field label="发布范围"><select name="audience" defaultValue="all"><option value="all">全部绑定学生</option><option value="class">指定班级</option></select></Field><fieldset className="portalChoiceGroup"><legend>班级范围（选择“指定班级”时必填）</legend>{classes.map((item) => <label key={item.id}><input type="checkbox" name="classScope" value={item.id} />{item.name}</label>)}</fieldset>{error && <p className="portalFormError">{error}</p>}<div className="portalFormActions"><button type="button" onClick={close}>取消</button><button className="portalPrimary" disabled={busy}>发布通知</button></div></form></Modal>;
}
