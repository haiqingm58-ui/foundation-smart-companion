import { useMemo, useState } from "react";
import {
  BarChart3,
  Bell,
  BookOpen,
  Bot,
  BriefcaseBusiness,
  ChevronDown,
  CircleHelp,
  Clock3,
  Database,
  FileText,
  GraduationCap,
  LayoutDashboard,
  LibraryBig,
  Link2,
  MessageSquareText,
  Network,
  NotebookTabs,
  PenLine,
  Play,
  Search,
  Settings,
  Target,
  Trophy,
  UserRound,
} from "lucide-react";
import foundationSection from "./assets/foundation-section.png";

const navItems = [
  { id: "overview", label: "课程总览", icon: LayoutDashboard },
  { id: "textbook", label: "教材学习", icon: BookOpen },
  { id: "graph", label: "知识图谱", icon: Network },
  { id: "qa", label: "智能问答", icon: MessageSquareText },
  { id: "cases", label: "工程案例", icon: BriefcaseBusiness },
  { id: "resources", label: "关联资料", icon: FileText },
  { id: "practice", label: "练习中心", icon: PenLine },
  { id: "report", label: "学习报告", icon: BarChart3 },
  { id: "admin", label: "后台管理", icon: Settings },
];

const moduleCards = [
  {
    id: "textbook",
    title: "教材学习",
    icon: BookOpen,
    tone: "blue",
    desc: "按章节浏览导读、公式、图表解释",
    meta: "当前：第八章 桩基础",
    action: "进入教材",
  },
  {
    id: "graph",
    title: "知识图谱",
    icon: Network,
    tone: "green",
    desc: "查看章节、知识点、案例、资料关系",
    meta: "286 个知识点",
    action: "打开图谱",
  },
  {
    id: "qa",
    title: "智能问答",
    icon: Bot,
    tone: "purple",
    desc: "教材问答、规范问答、学习辅导",
    meta: "支持引用来源",
    action: "开始提问",
  },
  {
    id: "cases",
    title: "工程案例",
    icon: BriefcaseBusiness,
    tone: "orange",
    desc: "地基失稳、沉降、桩基、基坑案例",
    meta: "52 个案例",
    action: "查看案例",
  },
  {
    id: "resources",
    title: "关联资料",
    icon: LibraryBig,
    tone: "teal",
    desc: "规范、参考教材、课程资料与附件",
    meta: "GB 50007、JGJ 94、参考教材",
    action: "查看资料",
  },
  {
    id: "practice",
    title: "练习中心",
    icon: PenLine,
    tone: "amber",
    desc: "章节练习、错题、智能评分",
    meta: "错题本 18",
    action: "进入练习",
  },
];

const weakPoints = [
  { name: "沉降计算", score: 62, note: "公式适用条件容易混淆" },
  { name: "桩侧阻力", score: 58, note: "荷载传递机制掌握不足" },
  { name: "群桩效应", score: 65, note: "与单桩承载力关联薄弱" },
];

const studentProfile = [
  { label: "姓名", value: "张同学" },
  { label: "学号", value: "20220001" },
  { label: "学院", value: "土木工程学院" },
  { label: "学校", value: "某某大学" },
  { label: "辅导老师", value: "李老师" },
];

const rankInfo = {
  level: "黄金",
  score: 82,
  next: "白金",
  tip: "学习状态很稳，补齐薄弱点就能冲白金。",
};

const chapters = [
  "绪论",
  "土的物理性质",
  "地基中的应力计算",
  "地基变形计算",
  "土的抗剪强度",
  "地基承载力",
  "浅基础",
  "桩基础",
  "地基处理",
  "基坑工程",
];

const resources = [
  { title: "建筑地基基础设计规范", code: "GB 50007", type: "规范", link: "浅基础、承载力、沉降" },
  { title: "建筑桩基技术规范", code: "JGJ 94", type: "规范", link: "桩基础、单桩承载力" },
  { title: "土力学", code: "参考教材", type: "教材", link: "抗剪强度、应力计算" },
  { title: "岩土工程勘察", code: "课程资料", type: "教材", link: "地质勘察、土层识别" },
];

const caseItems = [
  { title: "某高层建筑钻孔灌注桩基础设计案例", tag: "桩基础", status: "推荐" },
  { title: "某住宅楼不均匀沉降分析", tag: "沉降", status: "重点" },
  { title: "软弱地基 CFG 桩处理方案", tag: "地基处理", status: "案例题" },
];

function cx(...classes) {
  return classes.filter(Boolean).join(" ");
}

function Sidebar({ active, onNavigate }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brandMark">
          <GraduationCap size={25} strokeWidth={2.1} />
        </div>
        <div>
          <strong>《基础工程》智慧学伴</strong>
        </div>
      </div>

      <nav className="navList" aria-label="主导航">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              className={cx("navItem", active === item.id && "active")}
              type="button"
              key={item.id}
              onClick={() => onNavigate(item.id)}
            >
              <Icon size={21} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <RankPanel compact />

      <section className="studentCard" aria-label="学生信息">
        <div className="studentAvatar">
          <UserRound size={26} />
        </div>
        <div className="bindingBadge">
          <Link2 size={13} />
          指导老师强绑定
        </div>
        <div className="studentRows">
          {studentProfile.map((item) => (
            <div className="studentRow" key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
        </div>
      </section>
    </aside>
  );
}

function RankPanel({ compact = false }) {
  return (
    <section className={cx("rankPanel", compact && "compact")}>
      <div className="panelTitle slim">
        <span className="titleIcon rank">
          <Trophy size={18} />
        </span>
        <div>
          <h2>学习段位</h2>
          {!compact && <p>根据学习掌握度给一点情绪价值</p>}
        </div>
      </div>
      <div className="rankBadge">
        <span>{rankInfo.level}</span>
        <strong>{rankInfo.score}</strong>
      </div>
      {!compact && (
        <p className="rankTip">
          当前段位：{rankInfo.level}，距离{rankInfo.next}还差一点点。
        </p>
      )}
      <div className="rankLadder" aria-label="学习段位阶梯">
        {["青铜", "白银", "黄金", "白金", "王者"].map((rank) => (
          <span className={cx(rank === rankInfo.level && "active")} key={rank}>
            {rank}
          </span>
        ))}
      </div>
    </section>
  );
}

function Header({ query, setQuery }) {
  return (
    <header className="topbar">
      <label className="searchBox">
        <Search size={20} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="搜索章节、知识点、案例、资料…"
        />
      </label>
      <div className="topActions">
        <button className="iconButton" type="button" aria-label="通知">
          <Bell size={20} />
          <span className="dot" />
        </button>
        <button className="iconButton" type="button" aria-label="帮助">
          <CircleHelp size={20} />
        </button>
        <button className="userChip" type="button">
          <span className="avatar">
            <UserRound size={18} />
          </span>
          <span>张同学</span>
          <ChevronDown size={16} />
        </button>
      </div>
    </header>
  );
}

function Metric({ label, value, suffix }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>
        {value}
        {suffix && <small>{suffix}</small>}
      </strong>
    </div>
  );
}

function Hero({ onNavigate }) {
  return (
    <section className="heroPanel">
      <div className="heroCopy">
        <p className="eyebrow">学习概况</p>
        <h1>课程总览</h1>
        <p className="heroText">系统学习地基基础知识，掌握工程分析与设计方法。</p>
        <div className="heroStats">
          <div className="progressRing" aria-label="学习进度 25%">
            <span>25%</span>
          </div>
          <Metric label="已完成" value="3" suffix=" / 12 章" />
          <Metric label="平均分" value="82" suffix=" 分" />
        </div>
        <div className="heroActions">
          <button className="primaryButton" type="button" onClick={() => onNavigate("textbook")}>
            <Play size={17} fill="currentColor" />
            继续学习第八章
          </button>
          <button className="ghostButton" type="button" onClick={() => onNavigate("report")}>
            <Clock3 size={18} />
            学习记录
          </button>
        </div>
      </div>
      <img className="heroImage" src={foundationSection} alt="桩基础剖面工程示意" />
    </section>
  );
}

function ModuleCard({ card, onNavigate }) {
  const Icon = card.icon;
  return (
    <button className="moduleCard" type="button" onClick={() => onNavigate(card.id)}>
      <span className={cx("moduleIcon", card.tone)}>
        <Icon size={31} />
      </span>
      <span className="moduleBody">
        <strong>{card.title}</strong>
        <span>{card.desc}</span>
        <em>{card.meta}</em>
      </span>
      <span className="moduleAction">
        {card.action}
        <span aria-hidden="true">→</span>
      </span>
    </button>
  );
}

function WeakPanel({ onNavigate }) {
  return (
    <aside className="sideStack" aria-label="薄弱环节">
      <section className="weakPanel">
        <div className="panelTitle">
          <span className="titleIcon warning">
            <Target size={19} />
          </span>
          <div>
            <h2>薄弱环节</h2>
            <p>基于学习数据识别的待强化知识点</p>
          </div>
        </div>
        <div className="weakList">
          {weakPoints.map((item) => (
            <article className="weakItem" key={item.name}>
              <div className="weakTop">
                <strong>{item.name}</strong>
                <span>掌握度 {item.score}%</span>
              </div>
              <p>{item.note}</p>
            </article>
          ))}
        </div>
        <div className="weakActions panelActions">
          <button type="button" onClick={() => onNavigate("textbook")}>
            专项复习
          </button>
          <button type="button" onClick={() => onNavigate("practice")}>
            生成练习
          </button>
        </div>
      </section>

      <section className="chapterPanel">
        <div className="panelTitle slim">
          <span className="titleIcon">
            <NotebookTabs size={18} />
          </span>
          <div>
            <h2>章节快捷入口</h2>
            <p>章节平行浏览，无固定学习顺序</p>
          </div>
        </div>
        <div className="chapterGrid">
          {["绪论", "土的物理性质", "地基承载力", "浅基础", "桩基础", "地基处理", "基坑工程"].map((chapter) => (
            <button
              className={cx("chapterChip", chapter === "桩基础" && "current")}
              type="button"
              key={chapter}
              onClick={() => onNavigate("textbook")}
            >
              {chapter}
            </button>
          ))}
        </div>
      </section>
    </aside>
  );
}

function Overview({ onNavigate }) {
  return (
    <div className="overviewLayout">
      <div className="mainStack">
        <Hero onNavigate={onNavigate} />
        <section className="moduleGrid" aria-label="平台模块入口">
          {moduleCards.map((card) => (
            <ModuleCard card={card} key={card.id} onNavigate={onNavigate} />
          ))}
        </section>
      </div>
      <WeakPanel onNavigate={onNavigate} />
    </div>
  );
}

function TextbookPage({ onNavigate }) {
  const [activeChapter, setActiveChapter] = useState("桩基础");
  return (
    <section className="pagePanel">
      <PageHeader
        label="教材学习"
        title="章节学习工作台"
        desc="每个章节独立进入，按导读、公式、图表、案例和练习组织。"
      />
      <div className="studyLayout">
        <aside className="chapterList">
          {chapters.map((chapter) => (
            <button
              type="button"
              className={cx(activeChapter === chapter && "selected")}
              key={chapter}
              onClick={() => setActiveChapter(chapter)}
            >
              {chapter}
            </button>
          ))}
        </aside>
        <div className="readingPane">
          <div className="tabBar">
            {["章节导读", "重点公式", "图表解释", "案例关联", "章节练习"].map((tab, index) => (
              <button className={cx(index === 1 && "active")} type="button" key={tab}>
                {tab}
              </button>
            ))}
          </div>
          <article className="readingContent">
            <p className="eyebrow">第八章</p>
            <h2>{activeChapter}</h2>
            <p>
              本章重点包括桩基础类型、单桩竖向承载力、桩侧阻力与桩端阻力、群桩效应和桩基沉降计算。
              学习时建议把公式、土层条件和工程案例放在一起理解。
            </p>
            <div className="formulaBox">
              <span>单桩竖向承载力</span>
              <strong>Ra = u Σ qsi li + Ap qpa</strong>
              <button type="button">展开推导</button>
            </div>
            <img className="contentImage" src={foundationSection} alt="桩基础与土层剖面" />
          </article>
        </div>
        <aside className="resourceRail">
          <h3>关联资料</h3>
          <p>JGJ 94 与 GB 50007 可辅助理解本章设计要求。</p>
          <button type="button" onClick={() => onNavigate("resources")}>
            查看资料
          </button>
          <h3>相关案例</h3>
          <p>某高层建筑钻孔灌注桩基础设计案例。</p>
          <button type="button" onClick={() => onNavigate("cases")}>
            查看案例
          </button>
        </aside>
      </div>
    </section>
  );
}

function GraphPage() {
  const nodes = ["桩基础", "桩侧阻力", "桩端阻力", "单桩承载力", "群桩效应", "沉降计算", "JGJ 94", "章节练习"];
  return (
    <section className="pagePanel">
      <PageHeader label="知识图谱" title="章节知识关系" desc="以章节为入口，查看知识点、资料、案例和练习之间的关联。" />
      <div className="graphLayout">
        <div className="graphCanvas">
          <div className="graphCenter">桩基础</div>
          {nodes.slice(1).map((node, index) => (
            <button className={`graphNode node${index + 1}`} type="button" key={node}>
              {node}
            </button>
          ))}
        </div>
        <aside className="inspector">
          <h3>桩侧阻力</h3>
          <p>桩身与周围土体之间相互作用产生的摩阻力，是单桩承载力的重要组成。</p>
          <dl>
            <div>
              <dt>来源</dt>
              <dd>第八章 桩基础</dd>
            </div>
            <div>
              <dt>关联资料</dt>
              <dd>JGJ 94、GB 50007</dd>
            </div>
            <div>
              <dt>易错点</dt>
              <dd>与桩端阻力混淆</dd>
            </div>
          </dl>
        </aside>
      </div>
    </section>
  );
}

function QAPage() {
  const [mode, setMode] = useState("教材问答");
  const modes = ["教材问答", "规范问答", "学习辅导"];
  return (
    <section className="pagePanel">
      <PageHeader label="智能问答" title="教材 AI 助教" desc="围绕教材、关联资料和学习辅导提供带来源的回答。" />
      <div className="teacherNotice">
        <Link2 size={17} />
        当前答疑资料由绑定辅导老师维护，学院与课程资料需由辅导老师添加后开放。
      </div>
      <div className="qaShell">
        <div className="segmented">
          {modes.map((item) => (
            <button className={cx(mode === item && "active")} type="button" key={item} onClick={() => setMode(item)}>
              {item}
            </button>
          ))}
        </div>
        <div className="chatArea">
          <div className="bubble user">桩侧阻力是如何产生的？影响它的主要因素有哪些？</div>
          <div className="bubble assistant">
            <Bot size={20} />
            <div>
              <p>
                桩侧阻力主要来自桩身与周围土体之间的摩擦和黏结作用，受土层性质、桩径、施工工艺、地下水位等因素影响。
              </p>
              <span>引用：《基础工程》第八章 桩基础；JGJ 94</span>
            </div>
          </div>
        </div>
        <label className="askBox">
          <input placeholder={`继续使用${mode}提问…`} />
          <button type="button">发送</button>
        </label>
      </div>
    </section>
  );
}

function CasesPage() {
  return (
    <section className="pagePanel">
      <PageHeader label="工程案例" title="案例库" desc="把工程问题、教材章节、关联资料和思考题串起来。" />
      <div className="caseGrid">
        {caseItems.map((item) => (
          <article className="caseCard" key={item.title}>
            <span>{item.tag}</span>
            <h3>{item.title}</h3>
            <p>工程背景、问题表现、原因分析、涉及知识点与思考题已整理。</p>
            <button type="button">查看详情</button>
          </article>
        ))}
      </div>
    </section>
  );
}

function ResourcesPage() {
  return (
    <section className="pagePanel">
      <PageHeader label="关联资料" title="资料中心" desc="统一管理规范、参考教材、课程资料和相关附件。" />
      <div className="tablePanel">
        {resources.map((item) => (
          <div className="resourceRow" key={item.title}>
            <span className="typePill">{item.type}</span>
            <div>
              <strong>{item.title}</strong>
              <p>{item.link}</p>
            </div>
            <em>{item.code}</em>
            <button type="button">查看</button>
          </div>
        ))}
      </div>
    </section>
  );
}

function PracticePage() {
  return (
    <section className="pagePanel">
      <PageHeader label="练习中心" title="章节练习与智能评分" desc="客观题规则评分，主观题给出扣分点和补充建议。" />
      <div className="practiceLayout">
        <article className="questionCard">
          <span>简答题 · 第八章 桩基础</span>
          <h3>简述浅基础和桩基础的主要区别。</h3>
          <textarea defaultValue="浅基础是将荷载直接传给地基浅部土层；桩基础通过桩将荷载传递到深部持力层，适用于软弱土层或荷载较大的情况。" />
          <button type="button">提交评分</button>
        </article>
        <aside className="scorePanel">
          <strong>72</strong>
          <span>/ 100</span>
          <p>缺少荷载传递机制和适用场景的完整说明。</p>
          <ul>
            <li>补充桩侧阻力与桩端阻力</li>
            <li>说明浅基础适用地基条件</li>
          </ul>
        </aside>
      </div>
    </section>
  );
}

function ReportPage() {
  return (
    <section className="pagePanel">
      <PageHeader label="学习报告" title="学习画像" desc="根据章节学习和练习结果生成复习建议。" />
      <div className="reportRank">
        <Trophy size={24} />
        <div>
          <span>当前学习段位</span>
          <strong>{rankInfo.level}</strong>
          <p>{rankInfo.tip}</p>
        </div>
      </div>
      <div className="reportGrid">
        {[
          ["土的性质", 85],
          ["应力计算", 70],
          ["沉降计算", 62],
          ["承载力", 58],
          ["浅基础", 80],
          ["桩基础", 65],
        ].map(([name, value]) => (
          <div className="abilityRow" key={name}>
            <span>{name}</span>
            <div>
              <i style={{ width: `${value}%` }} />
            </div>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

function AdminPage() {
  return (
    <section className="pagePanel">
      <PageHeader label="后台管理" title="内容管理" desc="用于后续上传教材、资料、案例和题库，目前为展示状态。" />
      <div className="adminGrid">
        {["上传教材", "管理知识点", "维护案例", "导入题库"].map((item) => (
          <button className="adminTile" type="button" key={item}>
            <Database size={24} />
            {item}
          </button>
        ))}
      </div>
    </section>
  );
}

function PageHeader({ label, title, desc }) {
  return (
    <div className="pageHeader">
      <p className="eyebrow">{label}</p>
      <h1>{title}</h1>
      <p>{desc}</p>
    </div>
  );
}

function Page({ active, onNavigate }) {
  switch (active) {
    case "textbook":
      return <TextbookPage onNavigate={onNavigate} />;
    case "graph":
      return <GraphPage />;
    case "qa":
      return <QAPage />;
    case "cases":
      return <CasesPage />;
    case "resources":
      return <ResourcesPage />;
    case "practice":
      return <PracticePage />;
    case "report":
      return <ReportPage />;
    case "admin":
      return <AdminPage />;
    default:
      return <Overview onNavigate={onNavigate} />;
  }
}

export function App() {
  const [active, setActive] = useState("overview");
  const [query, setQuery] = useState("");
  const activeLabel = useMemo(() => navItems.find((item) => item.id === active)?.label ?? "课程总览", [active]);

  return (
    <div className="appShell">
      <Sidebar active={active} onNavigate={setActive} />
      <div className="workspace">
        <Header query={query} setQuery={setQuery} />
        <main className="content">
          <div className="mobilePageLabel">{activeLabel}</div>
          {query.trim() && (
            <div className="searchNotice">
              <Search size={16} />
              正在展示与“{query.trim()}”相关的课程内容入口。
            </div>
          )}
          <Page active={active} onNavigate={setActive} />
        </main>
      </div>
    </div>
  );
}
