import {
  Activity, BookUser, Building2, Database, FileClock, GraduationCap, KeyRound, LayoutDashboard,
  Link2, ListChecks, Plus, School, Settings, ShieldCheck, Upload, UserCog, Users,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { adminApi } from "../../api/admin.js";
import { apiUrl } from "../../api/client.js";
import {
  ConfirmDialog, DataTable, EmptyState, ErrorState, Field, LoadingState, Modal, PageHeading, Panel,
  PortalShell, SearchField, StatGrid, StatusBadge, Toast,
} from "../../components/portal/PortalKit.jsx";
import { useAuth } from "../../stores/AuthContext.jsx";


const navItems = [
  { key: "dashboard", label: "平台总览", icon: LayoutDashboard },
  { key: "teachers", label: "教师管理", icon: UserCog },
  { key: "students", label: "学生管理", icon: GraduationCap },
  { key: "classes", label: "班级管理", icon: School },
  { key: "bindings", label: "师生绑定", icon: Link2 },
  { key: "import", label: "数据导入", icon: Upload },
  { key: "accounts", label: "账号安全", icon: ShieldCheck },
  { key: "logs", label: "操作日志", icon: FileClock },
  { key: "settings", label: "平台设置", icon: Settings },
];


const loaders = {
  dashboard: adminApi.dashboard,
  teachers: adminApi.teachers,
  students: adminApi.students,
  classes: adminApi.classes,
  bindings: adminApi.bindings,
  logs: adminApi.logs,
  accounts: async () => {
    const [teachers, students] = await Promise.all([adminApi.teachers(), adminApi.students()]);
    return { items: [...teachers.items, ...students.items], total: teachers.total + students.total };
  },
  import: async () => ({}),
  settings: async () => ({}),
};


function currentView(pathname) {
  const tail = pathname.replace(/^\/admin\/?/, "").split("/")[0];
  return navItems.some((item) => item.key === tail) ? tail : "dashboard";
}


function formatDate(value) {
  return value ? new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "-";
}


export default function AdminApp() {
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
    setLoading(true); setError("");
    try { const data = await loaders[key](); setCache((old) => ({ ...old, [key]: data })); return data; }
    catch (reason) { setError(reason.message || "数据加载失败"); return null; }
    finally { setLoading(false); }
  }, [active, cache]);

  useEffect(() => { load(active); }, [active]);
  const go = (key) => navigate(key === "dashboard" ? "/admin" : `/admin/${key}`);
  const notify = (message, tone = "success") => setToast({ message, tone });
  const refresh = () => load(active, true);
  const common = { data: cache[active], loading, error, retry: refresh, open: setModal, notify, refresh, cache, setCache };

  return (
    <PortalShell roleLabel="系统管理后台" navItems={navItems} active={active} onNavigate={go} user={user} onLogout={logout}>
      {active === "dashboard" && <AdminDashboard {...common} go={go} />}
      {active === "teachers" && <PeopleView {...common} role="teacher" />}
      {active === "students" && <PeopleView {...common} role="student" />}
      {active === "classes" && <ClassesView {...common} />}
      {active === "bindings" && <BindingsView {...common} />}
      {active === "import" && <ImportView {...common} />}
      {active === "accounts" && <AccountsView {...common} />}
      {active === "logs" && <LogsView {...common} />}
      {active === "settings" && <SettingsView {...common} />}
      {modal?.type === "wizard" && <TeacherStudentWizard close={() => setModal(null)} done={(result) => { setModal(null); setCache({}); notify(`创建完成：${result.studentSuccess} 名学生已绑定`); }} />}
      {modal?.type === "class" && <ClassModal close={() => setModal(null)} done={() => { setModal(null); refresh(); notify("班级已创建"); }} />}
      {modal?.type === "binding" && <BindingModal cache={cache} setCache={setCache} close={() => setModal(null)} done={() => { setModal(null); refresh(); notify("师生绑定已保存"); }} />}
      {modal?.type === "password" && <PasswordModal item={modal.item} close={() => setModal(null)} done={() => { setModal(null); notify("密码已重置，原会话已失效"); }} />}
      {modal?.type === "person" && <PersonModal role={modal.role} item={modal.item} cache={cache} close={() => setModal(null)} done={() => { setModal(null); setCache({}); refresh(); notify("人员信息已保存"); }} />}
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


function AdminDashboard({ data = {}, loading, error, retry, go }) {
  return <ViewState loading={loading} error={error} retry={retry}><PageHeading eyebrow="平台治理" title="平台总览" description="查看账号、班级和强绑定关系的实时状态。" /><StatGrid items={[{ label: "指导教师", value: data.teacherTotal, note: "真实教师账号", icon: UserCog }, { label: "学生账号", value: data.studentTotal, note: `${data.boundStudentTotal || 0} 人已绑定`, icon: Users, tone: "green" }, { label: "教学班级", value: data.classTotal, note: "管理员统一维护", icon: School, tone: "teal" }, { label: "待绑定学生", value: data.unboundStudentTotal, note: `${data.disabledAccountTotal || 0} 个停用账号`, icon: Link2, tone: "amber" }]} /><div className="portalTwoColumn"><Panel title="管理快捷入口" description="高频事务在独立模块中完成"><div className="portalQuickGrid"><button onClick={() => go("teachers")}><UserCog size={20} /><strong>新增指导教师</strong><span>同步创建班级与学生</span></button><button onClick={() => go("bindings")}><Link2 size={20} /><strong>维护师生绑定</strong><span>教师数据范围的唯一依据</span></button><button onClick={() => go("import")}><Upload size={20} /><strong>批量导入学生</strong><span>先预检再写入</span></button><button onClick={() => go("logs")}><Activity size={20} /><strong>查看操作日志</strong><span>追踪关键管理操作</span></button></div></Panel><Panel title="权限边界" description="角色权限由后端强制执行"><dl className="portalDefinition"><div><dt>学生端</dt><dd>学习与作答</dd></div><div><dt>教师端</dt><dd>绑定范围教学</dd></div><div><dt>管理员端</dt><dd>账号与组织管理</dd></div><div><dt>认证方式</dt><dd>HttpOnly 会话</dd></div></dl></Panel></div></ViewState>;
}


function PeopleView({ role, data, loading, error, retry, open }) {
  const [query, setQuery] = useState("");
  const isTeacher = role === "teacher";
  const rows = useMemo(() => (data?.items || []).filter((item) => `${item.name}${item.username}${item.number}`.includes(query)), [data, query]);
  const actions = <div className="portalHeadingActions">{isTeacher && <button className="portalSecondary" onClick={() => open({ type: "person", role })}><Plus size={17} />单独新增教师</button>}<button className="portalPrimary" onClick={() => open(isTeacher ? { type: "wizard" } : { type: "person", role })}><Plus size={17} />{isTeacher ? "新增教师并绑定学生" : "新增学生"}</button></div>;
  return <ViewState loading={loading} error={error} retry={retry}><PageHeading eyebrow="组织与账号" title={isTeacher ? "教师管理" : "学生管理"} description={isTeacher ? "教师、班级、学生和绑定关系可通过一个事务向导完整创建。" : "学生账号由管理员创建，并通过绑定关系交由指导教师管理。"} actions={actions} /><Panel title={isTeacher ? "教师账号" : "学生账号"} description={`共 ${data?.total || 0} 个账号`} actions={<SearchField value={query} onChange={setQuery} placeholder="搜索姓名、账号或编号" />}><DataTable rows={rows} columns={[{ key: "name", label: "姓名" }, { key: "username", label: "登录账号" }, { key: "number", label: isTeacher ? "工号" : "学号" }, { key: "college", label: "学院" }, { key: "lastLoginAt", label: "最近登录", render: (row) => formatDate(row.lastLoginAt) }, { key: "status", label: "状态", render: (row) => <StatusBadge status={row.status} /> }, { key: "actions", label: "操作", render: (row) => <button className="portalTextButton" onClick={() => open({ type: "person", role, item: row })}>编辑</button> }]} empty={`暂无${isTeacher ? "教师" : "学生"}账号`} /></Panel></ViewState>;
}


function ClassesView({ data, loading, error, retry, open }) {
  return <ViewState loading={loading} error={error} retry={retry}><PageHeading eyebrow="教学组织" title="班级管理" description="班级由管理员统一维护，教师只能看到与本人绑定的班级。" actions={<button className="portalPrimary" onClick={() => open({ type: "class" })}><Plus size={17} />新建班级</button>} /><Panel title="班级列表" description={`共 ${data?.total || 0} 个班级`}><DataTable rows={data?.items} columns={[{ key: "name", label: "班级名称" }, { key: "grade", label: "年级" }, { key: "major", label: "专业" }, { key: "college", label: "学院" }]} empty="暂无班级" /></Panel></ViewState>;
}


function BindingsView({ data, loading, error, retry, open }) {
  return <ViewState loading={loading} error={error} retry={retry}><PageHeading eyebrow="数据权限" title="师生绑定" description="绑定关系决定教师可以查看、答疑和分析哪些学生的数据。" actions={<button className="portalPrimary" onClick={() => open({ type: "binding" })}><Plus size={17} />新增绑定</button>} /><Panel title="绑定关系列表" description={`共 ${data?.total || 0} 条`}><DataTable rows={data?.items} columns={[{ key: "teacherName", label: "指导老师", render: (row) => row.teacherName || row.teacherId }, { key: "studentName", label: "学生" }, { key: "studentNo", label: "学号" }, { key: "className", label: "班级", render: (row) => row.className || row.classId || "未分班" }, { key: "status", label: "状态", render: (row) => <StatusBadge status={row.status} /> }]} empty="暂无师生绑定关系" /></Panel></ViewState>;
}


function ImportView({ notify }) {
  const [result, setResult] = useState(null); const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [classes, setClasses] = useState([]); const [classId, setClassId] = useState(""); const [password, setPassword] = useState("Student-123");
  useEffect(() => { adminApi.classes().then((data) => setClasses(data.items)).catch((reason) => setError(reason.message)); }, []);
  const submit = async (event) => { event.preventDefault(); setBusy(true); setError(""); try { const data = await adminApi.previewImport(new FormData(event.currentTarget)); setResult(data); notify(`预检完成：${data.valid.length} 条有效记录`); } catch (reason) { setError(reason.message); } finally { setBusy(false); } };
  const commit = async () => { if (!classId || !result?.valid.length) { setError("请选择目标班级并确保存在有效记录"); return; } setBusy(true); setError(""); try { const data = await adminApi.createStudentsBatch({ classId, students: result.valid.map((item) => ({ name: item.name, studentNo: item.studentNo, username: item.username, password })) }); notify(`成功导入 ${data.created} 名学生`); setResult(null); } catch (reason) { setError(reason.message); } finally { setBusy(false); } };
  return <><PageHeading eyebrow="批量管理" title="数据导入" description="名单先在服务器端预检，确认后以单个数据库事务批量写入。" actions={<a className="portalSecondary" href={apiUrl("/admin/import-template")}><Upload size={16} />下载导入模板</a>} /><div className="portalTwoColumn"><Panel title="学生名单预检" description="支持官方 XLSX 模板或 UTF-8 CSV"><form className="portalForm" onSubmit={submit}><Field label="选择名单文件" hint="最大 5MB，公式内容会被安全拦截。"><input type="file" name="file" accept=".xlsx,.csv" required /></Field>{error && <p className="portalFormError">{error}</p>}<button className="portalPrimary" disabled={busy}><Upload size={17} />{busy ? "正在预检..." : "上传并预检"}</button></form></Panel><Panel title="导入规则" description="正式写库前的校验项目"><ul className="portalRuleList"><li>姓名、学号、班级不能为空</li><li>文件内学号不能重复</li><li>禁止 Excel 公式注入</li><li>账号冲突时整批事务回滚</li></ul></Panel></div>{result && <Panel title="预检结果" description={`${result.valid.length} 条有效，${result.errors.length} 条需修正`}><DataTable rows={result.valid.map((item, index) => ({ id: `${item.studentNo}-${index}`, ...item }))} columns={[{ key: "name", label: "姓名" }, { key: "studentNo", label: "学号" }, { key: "className", label: "班级" }, { key: "username", label: "登录账号" }]} empty="没有可导入的有效记录" />{result.errors.length > 0 && <div className="portalImportErrors"><strong>需要修正</strong>{result.errors.map((item) => <p key={`${item.row}-${item.code}`}>第 {item.row} 行：{item.reason}</p>)}</div>}<div className="portalImportCommit"><Field label="写入班级"><select value={classId} onChange={(event) => setClassId(event.target.value)}><option value="">请选择班级</option>{classes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field><Field label="统一初始密码"><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></Field><button className="portalPrimary" type="button" onClick={commit} disabled={busy || Boolean(result.errors.length)}>确认批量导入</button></div></Panel>}</>;
}


function AccountsView({ data, loading, error, retry, open, notify, refresh }) {
  const [query, setQuery] = useState("");
  const rows = (data?.items || []).filter((item) => `${item.name}${item.username}`.includes(query));
  const toggle = (item) => { const status = item.status === "active" ? "disabled" : "active"; open({ type: "confirm", title: `${status === "disabled" ? "停用" : "启用"}账号`, message: `确认${status === "disabled" ? "停用" : "启用"}账号“${item.name}”吗？停用会立即撤销现有会话。`, confirmLabel: status === "disabled" ? "确认停用" : "确认启用", danger: status === "disabled", onConfirm: async () => { await adminApi.updateAccountStatus(item.id, status); notify("账号状态已更新"); refresh(); } }); };
  return <ViewState loading={loading} error={error} retry={retry}><PageHeading eyebrow="安全管理" title="账号安全" description="停用账号或重置密码时，服务器会立即撤销该账号的现有会话。" /><Panel title="账号列表" description={`共 ${data?.total || 0} 个教师与学生账号`} actions={<SearchField value={query} onChange={setQuery} placeholder="搜索账号" />}><DataTable rows={rows} columns={[{ key: "name", label: "姓名" }, { key: "username", label: "账号" }, { key: "number", label: "编号" }, { key: "status", label: "状态", render: (row) => <StatusBadge status={row.status} /> }, { key: "actions", label: "安全操作", render: (row) => <div className="portalRowActions"><button className="portalTextButton" onClick={() => toggle(row)}>{row.status === "active" ? "停用" : "启用"}</button><button className="portalTextButton" onClick={() => open({ type: "password", item: row })}><KeyRound size={14} />重置密码</button></div> }]} empty="暂无账号" /></Panel></ViewState>;
}


function LogsView({ data, loading, error, retry }) {
  return <ViewState loading={loading} error={error} retry={retry}><PageHeading eyebrow="审计追踪" title="操作日志" description="记录账号、班级、绑定、资料、题目和作业的关键管理操作。" /><Panel title="最近操作" description={`共 ${data?.total || 0} 条日志`}><DataTable rows={data?.items} columns={[{ key: "createdAt", label: "时间", render: (row) => formatDate(row.createdAt) }, { key: "action", label: "操作" }, { key: "targetType", label: "对象类型" }, { key: "targetId", label: "对象编号" }, { key: "actorId", label: "操作者" }]} empty="暂无操作日志" /></Panel></ViewState>;
}


function SettingsView() {
  return <><PageHeading eyebrow="系统配置" title="平台设置" description="展示当前平台的关键安全与数据策略。" /><div className="portalSettingsGrid"><Panel title="认证策略"><dl className="portalDefinition"><div><dt>密码哈希</dt><dd>Argon2</dd></div><div><dt>会话</dt><dd>HttpOnly Cookie</dd></div><div><dt>验证码</dt><dd>数据库一次性验证码</dd></div><div><dt>登录保护</dt><dd>失败锁定与限流</dd></div></dl></Panel><Panel title="数据策略"><dl className="portalDefinition"><div><dt>教师范围</dt><dd>强绑定关系</dd></div><div><dt>资料存储</dt><dd>服务器私有目录</dd></div><div><dt>RAG 检索</dt><dd>服务端切块与召回</dd></div><div><dt>审计</dt><dd>关键操作留痕</dd></div></dl></Panel></div></>;
}


function TeacherStudentWizard({ close, done }) {
  const [step, setStep] = useState(1); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const [form, setForm] = useState({ teacherName: "", teacherNo: "", username: "", password: "", className: "", grade: "2024", major: "土木工程", college: "土木工程学院", students: "" });
  const update = (key) => (event) => setForm((old) => ({ ...old, [key]: event.target.value }));
  const parsed = form.students.split("\n").filter((line) => line.trim()).map((line) => { const [name, studentNo, password = "Student-123"] = line.split(/[\t,]/).map((item) => item.trim()); return { name, studentNo, username: studentNo, password, className: form.className }; }).filter((item) => item.name && item.studentNo);
  const submit = async () => { setBusy(true); setError(""); try { const result = await adminApi.createTeacherWithStudents({ teacher: { name: form.teacherName, teacherNo: form.teacherNo, username: form.username, password: form.password, college: form.college, course: "基础工程", status: "active" }, classInfo: { name: form.className, grade: form.grade, major: form.major, college: form.college }, students: parsed }); done(result); } catch (reason) { setError(reason.message); setBusy(false); } };
  return <Modal title="新增教师并绑定学生" onClose={close} wide><div className="portalSteps"><span className={step >= 1 ? "active" : ""}>1. 教师与班级</span><span className={step >= 2 ? "active" : ""}>2. 学生名单</span><span className={step >= 3 ? "active" : ""}>3. 确认创建</span></div>{step === 1 && <div className="portalForm"><div className="portalFormGrid"><Field label="教师姓名"><input value={form.teacherName} onChange={update("teacherName")} required /></Field><Field label="教师工号"><input value={form.teacherNo} onChange={update("teacherNo")} required /></Field><Field label="登录账号"><input value={form.username} onChange={update("username")} required /></Field><Field label="初始密码" hint="至少 8 位，含大小写字母和数字"><input type="password" value={form.password} onChange={update("password")} required /></Field><Field label="班级名称"><input value={form.className} onChange={update("className")} required /></Field><Field label="年级"><input value={form.grade} onChange={update("grade")} /></Field><Field label="专业"><input value={form.major} onChange={update("major")} /></Field><Field label="学院"><input value={form.college} onChange={update("college")} /></Field></div></div>}{step === 2 && <div className="portalForm"><Field label="学生名单" hint="每行：姓名, 学号, 初始密码。密码可省略，默认 Student-123"><textarea rows="10" value={form.students} onChange={update("students")} placeholder={'王同学,20260001,Student-123\n李同学,20260002,Student-123'} /></Field><p className="portalFormNote">已识别 {parsed.length} 名学生。创建时将同时建立账号、学生档案和教师强绑定。</p></div>}{step === 3 && <div className="portalReview"><div><span>指导教师</span><strong>{form.teacherName}（{form.teacherNo}）</strong></div><div><span>教学班级</span><strong>{form.className}</strong></div><div><span>学生数量</span><strong>{parsed.length} 人</strong></div><div><span>事务保障</span><strong>任一冲突则全部回滚</strong></div></div>}{error && <p className="portalFormError">{error}</p>}<div className="portalFormActions"><button type="button" onClick={step === 1 ? close : () => setStep(step - 1)}>{step === 1 ? "取消" : "上一步"}</button>{step < 3 ? <button className="portalPrimary" type="button" disabled={(step === 1 && (!form.teacherName || !form.teacherNo || !form.username || !form.password || !form.className)) || (step === 2 && !parsed.length)} onClick={() => setStep(step + 1)}>下一步</button> : <button className="portalPrimary" type="button" onClick={submit} disabled={busy}>{busy ? "正在创建..." : "确认创建并绑定"}</button>}</div></Modal>;
}


function ClassModal({ close, done }) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const submit = async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); setBusy(true); try { await adminApi.createClass(Object.fromEntries(form)); done(); } catch (reason) { setError(reason.message); setBusy(false); } };
  return <Modal title="新建班级" onClose={close}><form className="portalForm" onSubmit={submit}><Field label="班级名称"><input name="name" required /></Field><div className="portalFormGrid"><Field label="年级"><input name="grade" defaultValue="2024" /></Field><Field label="专业"><input name="major" defaultValue="土木工程" /></Field></div><Field label="学院"><input name="college" defaultValue="土木工程学院" /></Field>{error && <p className="portalFormError">{error}</p>}<div className="portalFormActions"><button type="button" onClick={close}>取消</button><button className="portalPrimary" disabled={busy}>创建班级</button></div></form></Modal>;
}


function BindingModal({ cache, setCache, close, done }) {
  const [teachers, setTeachers] = useState(cache.teachers?.items || []); const [students, setStudents] = useState(cache.students?.items || []); const [classes, setClasses] = useState(cache.classes?.items || []); const [busy, setBusy] = useState(true); const [error, setError] = useState("");
  useEffect(() => { Promise.all([adminApi.teachers(), adminApi.students(), adminApi.classes()]).then(([t, s, c]) => { setTeachers(t.items); setStudents(s.items); setClasses(c.items); setCache((old) => ({ ...old, teachers: t, students: s, classes: c })); setBusy(false); }).catch((reason) => { setError(reason.message); setBusy(false); }); }, []);
  const submit = async (event) => { event.preventDefault(); const form = new FormData(event.currentTarget); setBusy(true); try { await adminApi.createBindings({ teacherId: form.get("teacherId"), studentIds: form.getAll("studentIds"), classId: form.get("classId") || null }); done(); } catch (reason) { setError(reason.message); setBusy(false); } };
  return <Modal title="新增师生绑定" onClose={close} wide>{busy && !teachers.length ? <LoadingState /> : <form className="portalForm" onSubmit={submit}><div className="portalFormGrid"><Field label="指导老师"><select name="teacherId" required><option value="">请选择</option>{teachers.map((item) => <option key={item.id} value={item.profileId || item.id}>{item.name}（{item.number}）</option>)}</select></Field><Field label="班级"><select name="classId"><option value="">不指定班级</option>{classes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field></div><fieldset className="portalChoiceGroup"><legend>选择学生</legend>{students.map((item) => <label key={item.id}><input type="checkbox" name="studentIds" value={item.profileId || item.id} />{item.name} <span>{item.number}</span></label>)}</fieldset>{error && <p className="portalFormError">{error}</p>}<div className="portalFormActions"><button type="button" onClick={close}>取消</button><button className="portalPrimary" disabled={busy}>保存绑定</button></div></form>}</Modal>;
}


function PersonModal({ role, item, cache, close, done }) {
  const isTeacher = role === "teacher";
  const [classes, setClasses] = useState(cache.classes?.items || []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { if (!isTeacher && !cache.classes) adminApi.classes().then((data) => setClasses(data.items)).catch((reason) => setError(reason.message)); }, []);
  const submit = async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true); setError("");
    try {
      if (isTeacher) {
        const base = { name: form.get("name"), college: form.get("college"), course: form.get("course"), phone: form.get("phone") || null, email: form.get("email") || null, status: form.get("status") };
        if (item) await adminApi.updateTeacher(item.profileId, base);
        else await adminApi.createTeacher({ ...base, teacherNo: form.get("number"), username: form.get("username"), password: form.get("password") });
      } else {
        const base = { name: form.get("name"), classId: form.get("classId") || null, college: form.get("college"), status: form.get("status") };
        if (item) await adminApi.updateStudent(item.profileId, base);
        else await adminApi.createStudent({ ...base, studentNo: form.get("number"), username: form.get("username"), password: form.get("password") });
      }
      done();
    } catch (reason) { setError(reason.message); setBusy(false); }
  };
  return <Modal title={`${item ? "编辑" : "新增"}${isTeacher ? "教师" : "学生"}`} onClose={close} wide><form className="portalForm" onSubmit={submit}><div className="portalFormGrid"><Field label="姓名"><input name="name" defaultValue={item?.name || ""} required /></Field><Field label={isTeacher ? "教师工号" : "学号"}><input name="number" defaultValue={item?.number || ""} disabled={Boolean(item)} required /></Field><Field label="登录账号"><input name="username" defaultValue={item?.username || ""} disabled={Boolean(item)} required /></Field>{!item && <Field label="初始密码" hint="至少 8 位，含大小写字母和数字"><input name="password" type="password" required /></Field>}<Field label="学院"><input name="college" defaultValue={item?.college || "土木工程学院"} required /></Field>{isTeacher ? <><Field label="所教课程"><input name="course" defaultValue="基础工程" required /></Field><Field label="手机号"><input name="phone" /></Field><Field label="邮箱"><input name="email" type="email" /></Field></> : <Field label="班级"><select name="classId" defaultValue=""><option value="">未分班</option>{classes.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></Field>}<Field label="账号状态"><select name="status" defaultValue={item?.status || "active"}><option value="active">正常</option><option value="disabled">停用</option></select></Field></div>{error && <p className="portalFormError">{error}</p>}<div className="portalFormActions"><button type="button" onClick={close}>取消</button><button className="portalPrimary" disabled={busy}>{busy ? "正在保存..." : "保存"}</button></div></form></Modal>;
}


function PasswordModal({ item, close, done }) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const submit = async (event) => { event.preventDefault(); const password = new FormData(event.currentTarget).get("password"); setBusy(true); try { await adminApi.resetPassword(item.id, password); done(); } catch (reason) { setError(reason.message); setBusy(false); } };
  return <Modal title={`重置密码：${item.name}`} onClose={close}><form className="portalForm" onSubmit={submit}><Field label="新密码" hint="至少 8 位，必须包含大写字母、小写字母和数字。"><input type="password" name="password" minLength="8" required /></Field><p className="portalFormNote">保存后该账号的全部现有会话将失效，并在下次登录时要求修改密码。</p>{error && <p className="portalFormError">{error}</p>}<div className="portalFormActions"><button type="button" onClick={close}>取消</button><button className="portalPrimary" disabled={busy}><KeyRound size={16} />确认重置</button></div></form></Modal>;
}
