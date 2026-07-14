import { useEffect, useMemo, useRef, useState } from "react";
import {
  BarChart3,
  Bell,
  BookOpen,
  Bot,
  BrainCircuit,
  BriefcaseBusiness,
  ChevronDown,
  CheckCircle2,
  CircleHelp,
  ClipboardList,
  Clock3,
  Database,
  FileText,
  FileUp,
  Focus,
  GraduationCap,
  LayoutDashboard,
  LibraryBig,
  Link2,
  ListFilter,
  LockKeyhole,
  LocateFixed,
  LogIn,
  LogOut,
  MessageSquareText,
  MousePointer2,
  Network,
  NotebookTabs,
  PenLine,
  Play,
  RefreshCcw,
  RotateCcw,
  Search,
  Settings,
  ShieldCheck,
  Target,
  Trophy,
  UploadCloud,
  UserPlus,
  UserRound,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import foundationSection from "./assets/foundation-section-compact.png";

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

const demoUsers = [
  {
    id: "student-zhang",
    role: "student",
    roleLabel: "学生",
    name: "张同学",
    username: "student",
    password: "123456",
    studentNo: "20220001",
    college: "土木工程学院",
    school: "某某大学",
    mentor: "李老师",
  },
  {
    id: "teacher-li",
    role: "teacher",
    roleLabel: "指导老师",
    name: "李老师",
    username: "teacher",
    password: "123456",
    studentNo: "T-001",
    college: "土木工程学院",
    school: "某某大学",
    mentor: "课程负责人",
  },
  {
    id: "admin-root",
    role: "admin",
    roleLabel: "管理员",
    name: "管理员",
    username: "admin",
    password: "123456",
    studentNo: "ADMIN",
    college: "教务与资源中心",
    school: "某某大学",
    mentor: "平台运维",
  },
];

const roleFeatures = {
  student: ["教材学习", "RAG 问答", "题库练习", "学习报告"],
  teacher: ["知识库上传", "题库导入", "答疑配置", "学生绑定"],
  admin: ["全局后台", "内容审核", "数据维护", "权限管理"],
};

const defaultCourseManifest = {
  courseId: "foundation-engineering",
  title: "基础工程",
  platformTitle: "《基础工程》智慧学伴",
  totalChapters: 7,
  currentChapterId: "chapter-03",
  progress: {
    completedChapters: 3,
    averageScore: 82,
  },
  chapters: [
    { id: "chapter-01", number: 1, title: "绪论", slug: "introduction" },
    { id: "chapter-02", number: 2, title: "浅基础", slug: "shallow-foundation" },
    { id: "chapter-03", number: 3, title: "桩基础", slug: "pile-foundation" },
    { id: "chapter-04", number: 4, title: "沉井基础", slug: "open-caisson-foundation" },
    { id: "chapter-05", number: 5, title: "基坑工程", slug: "excavation-engineering" },
    { id: "chapter-06", number: 6, title: "地基处理", slug: "ground-treatment" },
    { id: "chapter-07", number: 7, title: "区域性地基", slug: "regional-ground" },
  ],
  preKnowledge: ["土的物理性质", "地基中的应力计算", "地基变形计算", "土的抗剪强度", "地基承载力"],
};

const moduleCards = [
  {
    id: "textbook",
    title: "教材学习",
    icon: BookOpen,
    tone: "blue",
    desc: "按章节浏览导读、公式、图表解释",
    action: "进入教材",
  },
  {
    id: "graph",
    title: "知识图谱",
    icon: Network,
    tone: "green",
    desc: "查看章节、知识点、案例、资料关系",
    action: "打开图谱",
  },
  {
    id: "qa",
    title: "智能问答",
    icon: Bot,
    tone: "purple",
    desc: "教材问答、规范问答、学习辅导",
    action: "开始提问",
  },
  {
    id: "cases",
    title: "工程案例",
    icon: BriefcaseBusiness,
    tone: "orange",
    desc: "地基失稳、沉降、桩基、基坑案例",
    action: "查看案例",
  },
  {
    id: "resources",
    title: "关联资料",
    icon: LibraryBig,
    tone: "teal",
    desc: "规范、参考教材、课程资料与附件",
    action: "查看资料",
  },
  {
    id: "practice",
    title: "练习中心",
    icon: PenLine,
    tone: "amber",
    desc: "章节练习、错题、智能评分",
    action: "进入练习",
  },
];

const weakPoints = [
  { name: "沉降计算", score: 62, note: "公式适用条件容易混淆" },
  { name: "桩侧阻力", score: 58, note: "荷载传递机制掌握不足" },
  { name: "群桩效应", score: 65, note: "与单桩承载力关联薄弱" },
];

const rankInfo = {
  level: "黄金",
  score: 82,
  next: "白金",
  tip: "学习状态很稳，补齐薄弱点就能冲白金。",
};

const chapterStudyContent = {
  绪论: {
    label: "第1章",
    intro: "本专题先建立地基、基础、上部结构共同工作的设计视角，理解承载力、变形和稳定三类控制目标。",
    formulaName: "地基基础设计控制",
    formula: "pk <= fa，s <= [s]",
    derivation:
      "基础设计通常同时满足承载力极限状态和正常使用状态。平均基底压力 pk 由上部荷载与基础自重折算到基底面积得到，需不超过修正后的地基承载力 fa；沉降 s 由土层压缩变形累加得到，需控制在允许值 [s] 内。",
    diagram: "用一张荷载传递示意图理解上部结构、基础和地基之间的作用路径。",
    caseText: "可关联不均匀沉降或承载力不足案例，观察设计控制条件如何同时发挥作用。",
  },
  土的物理性质: {
    label: "学习专题 02",
    intro: "本专题关注含水率、孔隙比、饱和度和重度等指标，它们是后续承载力、沉降和抗剪分析的基础。",
    formulaName: "三相指标换算",
    formula: "e = Gs(1 + w)γw / γ - 1",
    derivation:
      "由三相图出发，土粒体积 Vs 与孔隙体积 Vv 之比定义为孔隙比 e。含水率 w 反映水质量与土粒质量的比值，Gsγw 表示土粒单位体积重度，结合总重度 γ 可把质量关系转化为体积关系，从而得到孔隙比换算式。",
    diagram: "图表重点应展示土的三相组成，以及 w、e、Sr、γ 之间的换算路径。",
    caseText: "可关联填土、软土或地下水位变化案例，理解物理指标对工程判断的影响。",
  },
  地基中的应力计算: {
    label: "学习专题 03",
    intro: "本专题把基础底面荷载转化为地基内部附加应力，是沉降计算和下卧层验算的前置步骤。",
    formulaName: "附加应力计算",
    formula: "σz = α p0",
    derivation:
      "在弹性半空间假定下，基底附加压力 p0 向地基内部扩散，某深度处竖向附加应力可写成影响系数 α 与 p0 的乘积。α 由基础形状、计算点位置和深宽比查表或计算得到。",
    diagram: "图表重点应展示基底压力向下扩散、等应力线和计算点位置。",
    caseText: "可关联软弱下卧层验算案例，比较不同深度处附加应力衰减规律。",
  },
  地基变形计算: {
    label: "学习专题 04",
    intro: "本专题围绕地基沉降、沉降差和倾斜控制，理解分层总和法的计算逻辑。",
    formulaName: "分层总和法",
    formula: "s = ψs Σ Δsi",
    derivation:
      "把压缩层范围内土体按性质和应力变化分层，每层沉降 Δsi 由该层附加应力、压缩模量和厚度确定，再按层累加。经验修正系数 ψs 用来修正计算沉降与实测沉降之间的差异。",
    diagram: "图表重点应展示压缩层分层、各层附加应力和沉降累加关系。",
    caseText: "可关联住宅楼不均匀沉降案例，观察沉降差如何影响结构使用。",
  },
  土的抗剪强度: {
    label: "学习专题 05",
    intro: "本专题解释土体破坏时的抗剪强度来源，为边坡、基坑、承载力和桩侧阻力分析打基础。",
    formulaName: "库仑抗剪强度",
    formula: "τf = c + σ tan φ",
    derivation:
      "土的抗剪强度由黏聚力 c 和摩擦强度两部分组成。法向应力 σ 增大时，颗粒间摩擦作用增强，摩擦项可表示为 σ tan φ；当剪应力达到 τf 时土体进入破坏状态。",
    diagram: "图表重点应展示莫尔圆与强度包线的相切关系。",
    caseText: "可关联基坑稳定、边坡滑动和桩侧摩阻力案例，理解强度参数的工程意义。",
  },
  地基承载力: {
    label: "学习专题 06",
    intro: "本专题关注地基在荷载作用下的承载能力，核心是承载力特征值修正和基底压力验算。",
    formulaName: "承载力特征值修正",
    formula: "fa = fak + ηbγ(b - 3) + ηdγm(d - 0.5)",
    derivation:
      "地基承载力特征值 fak 来自载荷试验、经验或规范表值。基础宽度 b 和埋深 d 会改变地基受力与约束条件，因此通过宽度修正项和埋深修正项得到设计采用的 fa。",
    diagram: "图表重点应展示基础宽度、埋深、持力层和基底压力之间的关系。",
    caseText: "可关联承载力不足或软弱下卧层案例，比较修正前后验算结果。",
  },
  浅基础: {
    label: "第2章",
    intro: "本专题学习独立基础、条形基础、筏形基础等浅基础形式，重点掌握基底压力和基础尺寸确定。",
    formulaName: "基底平均压力验算",
    formula: "pk = (Fk + Gk) / A <= fa",
    derivation:
      "上部结构传来的竖向荷载 Fk 与基础及覆土自重 Gk 共同作用在基底面积 A 上，得到平均基底压力 pk。只要 pk 不超过修正后的承载力 fa，平均压力验算满足要求。",
    diagram: "图表重点应展示基础底面积、荷载合力位置和基底压力分布。",
    caseText: "可关联浅基础尺寸初选案例，比较独立基础和筏形基础的适用条件。",
  },
  桩基础: {
    label: "第3章",
    intro: "本专题重点包括桩基础类型、单桩竖向承载力、桩侧阻力与桩端阻力、群桩效应和桩基沉降计算。",
    formulaName: "单桩竖向承载力",
    formula: "Ra = u Σ qsi li + Ap qpa",
    derivation:
      "桩侧阻力按桩周长 u、各土层侧阻力特征值 qsi 与分层厚度 li 累加；桩端阻力按桩端面积 Ap 与端阻力 qpa 计算，两部分共同形成单桩竖向承载力。",
    diagram: "图表重点应展示桩侧阻力、桩端阻力、持力层和荷载传递路径。",
    caseText: "可关联钻孔灌注桩、高层建筑桩基和负摩阻力案例。",
  },
  沉井基础: {
    label: "第4章",
    intro: "本章关注沉井基础的构造、下沉施工、刃脚受力、封底和沉井稳定验算，适合与桥梁、水工和深基础施工场景结合学习。",
    formulaName: "沉井下沉验算",
    formula: "G - Ff - Rb > 0",
    derivation:
      "沉井能否顺利下沉，取决于自重 G 是否足以克服井壁侧面摩阻力 Ff 和刃脚、底部阻力 Rb。若剩余下沉力不足，需要采取加载、减阻或调整施工工艺等措施。",
    diagram: "图表重点应展示沉井井壁、刃脚、土层摩阻力和下沉力之间的关系。",
    caseText: "可关联桥梁沉井基础或地下构筑物施工案例，分析下沉偏斜、突沉和封底控制。",
  },
  地基处理: {
    label: "第6章",
    intro: "本专题比较换填、强夯、排水固结、复合地基等处理方法，关注处理前后承载力和变形改善。",
    formulaName: "复合地基承载力",
    formula: "fspk = m fp + β(1 - m) fsk",
    derivation:
      "复合地基由增强体和桩间土共同承担荷载。面积置换率 m 表示增强体分担面积比例，fp 表示增强体承载力贡献，β(1 - m)fsk 表示桩间土折减后的承载力贡献，两者叠加得到 fspk。",
    diagram: "图表重点应展示增强体、桩间土、褥垫层和荷载分担关系。",
    caseText: "可关联 CFG 桩或软弱地基处理方案，比较处理前后指标变化。",
  },
  基坑工程: {
    label: "第5章",
    intro: "本专题关注支护结构、土压力、降水和基坑稳定，理解施工过程对周边环境的影响。",
    formulaName: "主动土压力合力",
    formula: "Ea = 1/2 Ka γ H²",
    derivation:
      "当墙后填土达到主动极限平衡状态时，水平土压力沿深度近似线性增大，底部压力为 KaγH。三角形压力图的面积即主动土压力合力，因此 Ea = 1/2 KaγH²。",
    diagram: "图表重点应展示土压力三角形分布、支护结构受力和开挖深度 H。",
    caseText: "可关联基坑变形、支护失稳和降水引起周边沉降案例。",
  },
  区域性地基: {
    label: "第7章",
    intro: "本章关注湿陷性黄土、膨胀土、盐渍土、冻土和山区地基等区域性工程问题，重点是识别特殊土性并选择相应处理措施。",
    formulaName: "自由膨胀率",
    formula: "δef = (V - V0) / V0 × 100%",
    derivation:
      "膨胀土自由膨胀率由膨胀稳定后的体积 V 与原始体积 V0 的相对增量计算。该指标用于判断膨胀潜势，并为地基处理和基础设计提供依据。",
    diagram: "图表重点应展示特殊土分布、变形机理和工程处置路径。",
    caseText: "可关联湿陷性黄土或膨胀土地基案例，比较不同区域性地基的识别指标。",
  },
};

const resources = [
  {
    title: "建筑地基基础设计规范",
    code: "GB 50007-2011",
    shortCode: "GB 50007",
    type: "国家标准",
    level: "基础主规范",
    version: "2011版",
    source: "教材参考文献[1]，中国建筑科学研究院，2012",
    organization: "中国建筑科学研究院",
    publisher: "中国建筑工业出版社",
    publishedYear: "2012",
    link: "浅基础、承载力、沉降、软弱下卧层",
    relatedChapters: ["绪论", "浅基础", "地基处理", "区域性地基"],
    keyTopics: ["地基承载力特征值", "基础埋置深度", "地基变形验算", "软弱下卧层", "不均匀沉降"],
    clauses: ["地基基础设计等级与设计原则", "承载力特征值及宽度、埋深修正", "沉降、倾斜和差异沉降控制", "浅基础构造和验算"],
    useCases: ["浅基础尺寸初选", "承载力修正计算", "沉降验算和课堂例题引用"],
    status: "教材引用版本；正式教学前由指导老师确认最新版",
  },
  {
    title: "建筑桩基技术规范",
    code: "JGJ 94-2008",
    shortCode: "JGJ 94",
    type: "行业规范",
    level: "桩基主规范",
    version: "2008版",
    source: "教材参考文献[6]，住房和城乡建设部，2008",
    organization: "中华人民共和国住房和城乡建设部",
    publisher: "中国建筑工业出版社",
    publishedYear: "2008",
    link: "桩基础、单桩承载力、群桩效应",
    relatedChapters: ["桩基础"],
    keyTopics: ["桩型选择", "单桩竖向承载力", "负摩阻力", "水平承载力", "群桩基础", "承台设计"],
    clauses: ["桩基设计等级和基本规定", "单桩竖向承载力确定方法", "桩侧负摩阻力和中性点", "群桩承载力与沉降验算"],
    useCases: ["桩基础方案比选", "单桩承载力例题", "群桩效应和承台验算"],
    status: "教材引用版本；课堂条文摘录由指导老师维护",
  },
  {
    title: "建筑基坑支护技术规程",
    code: "JGJ 120-2012",
    shortCode: "JGJ 120",
    type: "行业规程",
    level: "基坑支护",
    version: "2012版",
    source: "教材参考文献[7]，中国建筑科学研究院，2012",
    organization: "中国建筑科学研究院",
    publisher: "中国建筑工业出版社",
    publishedYear: "2012",
    link: "基坑支护、土压力、降水与监测",
    relatedChapters: ["基坑工程"],
    keyTopics: ["支护结构选型", "土压力计算", "整体稳定", "抗隆起", "地下水控制"],
    clauses: ["基坑支护设计原则", "排桩、地下连续墙和土钉墙设计", "稳定性验算", "地下水控制要求"],
    useCases: ["基坑支护方案判断", "土压力计算题", "支挡结构稳定验算"],
    status: "教材引用版本；用于基坑工程章节",
  },
  {
    title: "建筑地基处理技术规范",
    code: "JGJ 79-2012",
    shortCode: "JGJ 79",
    type: "行业规范",
    level: "地基处理",
    version: "2012版",
    source: "教材参考文献[9]，住房和城乡建设部，2013",
    organization: "中华人民共和国住房和城乡建设部",
    publisher: "中国建筑工业出版社",
    publishedYear: "2013",
    link: "换填、强夯、复合地基、预压法",
    relatedChapters: ["地基处理"],
    keyTopics: ["换填垫层", "强夯法", "排水固结", "复合地基", "注浆法", "处理效果检验"],
    clauses: ["常用地基处理方法适用范围", "垫层厚度和承载力验算", "复合地基承载力与变形", "施工质量检验"],
    useCases: ["软土地基处理方案比选", "复合地基计算", "处理后承载力评价"],
    status: "教材引用版本；用于处理方案比选",
  },
  {
    title: "湿陷性黄土地区建筑标准",
    code: "GB 50025-2018",
    shortCode: "GB 50025",
    type: "国家标准",
    level: "特殊土",
    version: "2018版",
    source: "教材参考文献[11]，住房和城乡建设部，2019",
    organization: "中华人民共和国住房和城乡建设部",
    publisher: "中国建筑工业出版社",
    publishedYear: "2019",
    link: "湿陷类型、湿陷等级、区域性地基",
    relatedChapters: ["区域性地基"],
    keyTopics: ["自重湿陷性", "非自重湿陷性", "湿陷等级", "地基处理措施"],
    clauses: ["湿陷性黄土场地评价", "湿陷等级划分", "地基处理和基础措施", "检验与施工控制"],
    useCases: ["湿陷等级判别题", "黄土地基处理方案", "区域性地基复习"],
    status: "教材引用版本；用于特殊土地基判别",
  },
  {
    title: "公路桥涵地基与基础设计规范",
    code: "JTG 3363-2019",
    shortCode: "JTG 3363",
    type: "行业规范",
    level: "桥涵基础",
    version: "2019版",
    source: "教材参考文献[2]，中交公路规划设计院有限公司，2020",
    organization: "中交公路规划设计院有限公司",
    publisher: "人民交通出版社",
    publishedYear: "2020",
    link: "桥梁沉井、深基础、承载与稳定",
    relatedChapters: ["浅基础", "桩基础", "沉井基础"],
    keyTopics: ["桥涵地基承载力", "扩大基础", "桩基础", "沉井基础", "冲刷影响"],
    clauses: ["桥涵基础设计原则", "地基承载力取值与修正", "沉井基础构造与稳定", "桥梁桩基础验算"],
    useCases: ["桥梁基础拓展题", "沉井基础案例", "公路桥涵地基承载力计算"],
    status: "教材引用版本；用于桥梁沉井拓展",
  },
  {
    title: "岩土工程勘察规范",
    code: "GB 50021-2001（2009年版）",
    shortCode: "GB 50021",
    type: "国家标准",
    level: "勘察资料",
    version: "2009年版",
    source: "教材参考文献[3]，建设综合勘察研究设计院，2009",
    organization: "建设综合勘察研究设计院",
    publisher: "中国建筑工业出版社",
    publishedYear: "2009",
    link: "勘察等级、岩土参数、原位测试、场地评价",
    relatedChapters: ["绪论", "浅基础", "桩基础", "区域性地基"],
    keyTopics: ["勘察分级", "岩土参数", "原位测试", "地下水", "不良地质作用"],
    clauses: ["勘察阶段与工作量", "土工试验和原位测试", "地基土参数建议值", "勘察报告内容"],
    useCases: ["读懂勘察报告", "参数取值依据", "工程案例地质条件整理"],
    status: "教材引用版本；用于连接勘察资料和设计计算",
  },
  {
    title: "混凝土结构设计规范",
    code: "GB 50010-2010（2015年版）",
    shortCode: "GB 50010",
    type: "国家标准",
    level: "结构设计",
    version: "2015年版",
    source: "教材参考文献[4]，中国建筑科学研究院，2016",
    organization: "中国建筑科学研究院",
    publisher: "中国建筑工业出版社",
    publishedYear: "2016",
    link: "基础结构配筋、承台、筏板、扩展基础",
    relatedChapters: ["浅基础", "桩基础", "沉井基础"],
    keyTopics: ["受弯承载力", "受冲切承载力", "剪切验算", "构造配筋", "裂缝控制"],
    clauses: ["混凝土构件承载力设计", "基础板和承台配筋", "冲切与剪切验算", "耐久性和构造要求"],
    useCases: ["扩展基础结构设计", "桩承台配筋", "筏形基础结构验算"],
    status: "教材引用版本；用于基础构件结构计算",
  },
  {
    title: "建筑基坑工程监测技术标准",
    code: "GB 50497-2020",
    shortCode: "GB 50497",
    type: "国家标准",
    level: "基坑监测",
    version: "2020版",
    source: "教材参考文献[8]，中国建筑科学研究院，2020",
    organization: "中国建筑科学研究院",
    publisher: "中国计划出版社",
    publishedYear: "2020",
    link: "监测项目、报警值、巡视、信息反馈",
    relatedChapters: ["基坑工程"],
    keyTopics: ["支护结构位移", "周边沉降", "地下水位", "监测频率", "报警控制"],
    clauses: ["监测等级和监测项目", "监测点布置", "监测频率与报警", "信息反馈和应急处置"],
    useCases: ["基坑案例复盘", "监测方案识读", "变形控制讨论"],
    status: "教材引用版本；与基坑支护规程配套使用",
  },
  {
    title: "膨胀土地区建筑技术规范",
    code: "GB 50112-2013",
    shortCode: "GB 50112",
    type: "国家标准",
    level: "特殊土",
    version: "2013版",
    source: "教材参考文献[10]，住房和城乡建设部，2013",
    organization: "中华人民共和国住房和城乡建设部",
    publisher: "中国建筑工业出版社",
    publishedYear: "2013",
    link: "膨胀潜势、胀缩等级、基础与地基处理",
    relatedChapters: ["区域性地基"],
    keyTopics: ["自由膨胀率", "膨胀潜势", "胀缩等级", "防水保湿", "地基处理"],
    clauses: ["膨胀土地基评价", "地基胀缩等级", "基础措施和处理措施", "施工与维护要求"],
    useCases: ["自由膨胀率习题", "膨胀土危害机理", "特殊土地基处置"],
    status: "教材引用版本；用于膨胀土地基专题",
  },
  {
    title: "冻土地区建筑地基基础设计规范",
    code: "JGJ 118-2011",
    shortCode: "JGJ 118",
    type: "行业规范",
    level: "特殊土",
    version: "2011版",
    source: "教材参考文献[12]，住房和城乡建设部，2012",
    organization: "中华人民共和国住房和城乡建设部",
    publisher: "中国建筑工业出版社",
    publishedYear: "2012",
    link: "多年冻土、季节冻土、冻胀融沉、基础措施",
    relatedChapters: ["区域性地基"],
    keyTopics: ["冻胀性", "融沉性", "多年冻土", "季节冻土", "保温隔热措施"],
    clauses: ["冻土地基分类", "冻胀融沉评价", "基础埋深和防冻措施", "施工与维护"],
    useCases: ["冻土地基概念辨析", "区域性地基对比", "基础防冻措施讨论"],
    status: "教材引用版本；用于冻土地基专题",
  },
  {
    title: "建筑抗震设计规范",
    code: "GB 50011-2010（2016年版）",
    shortCode: "GB 50011",
    type: "国家标准",
    level: "抗震与场地",
    version: "2016年版",
    source: "教材参考文献[13]，住房和城乡建设部，2016",
    organization: "中华人民共和国住房和城乡建设部",
    publisher: "中国建筑工业出版社",
    publishedYear: "2016",
    link: "场地类别、液化判别、抗震设防、地基基础抗震",
    relatedChapters: ["绪论", "区域性地基"],
    keyTopics: ["场地类别", "地震烈度", "液化判别", "抗震设防", "地基基础措施"],
    clauses: ["抗震设防基本要求", "场地和地基评价", "液化土判别与处理", "地基基础抗震构造"],
    useCases: ["地震区地基章节", "场地类别复习", "液化处理案例"],
    status: "教材引用版本；用于地震区地基拓展",
  },
  {
    title: "动力机器基础设计标准",
    code: "GB 50040-2020",
    shortCode: "GB 50040",
    type: "国家标准",
    level: "动力基础",
    version: "2020版",
    source: "教材参考文献[14]，住房和城乡建设部，2020",
    organization: "中华人民共和国住房和城乡建设部",
    publisher: "中国计划出版社",
    publishedYear: "2020",
    link: "动力机器基础、振动响应、动荷载、地基承载力折减",
    relatedChapters: ["区域性地基"],
    keyTopics: ["动力折减系数", "基础振动响应", "容许振幅", "动力荷载", "地基土类别"],
    clauses: ["动力机器基础设计要求", "地基承载力动力折减", "振动位移、速度、加速度控制", "基础构造和隔振"],
    useCases: ["动力机器基础专题", "第7章动力基础公式", "振动控制讨论"],
    status: "教材引用版本；用于动力机器基础拓展",
  },
  {
    title: "建筑工程容许振动标准",
    code: "GB 50868-2013",
    shortCode: "GB 50868",
    type: "国家标准",
    level: "振动控制",
    version: "2013版",
    source: "教材第7章动力基础正文提及",
    organization: "住房和城乡建设主管部门",
    publisher: "教材正文未列出版社",
    publishedYear: "2013",
    link: "容许振动、振动速度、振动加速度、设备影响",
    relatedChapters: ["区域性地基"],
    keyTopics: ["容许振动值", "振动速度", "振动加速度", "精密设备保护", "邻近建筑影响"],
    clauses: ["建筑工程振动评价指标", "不同使用对象容许限值", "振动控制和评估方法"],
    useCases: ["动力机器基础振动控制", "邻近建筑影响判断", "第7章拓展资料"],
    status: "教材正文提及；详细版本由指导老师确认",
  },
  {
    title: "岩溶地区建筑地基基础技术标准",
    code: "GB/T 51238-2018",
    shortCode: "GB/T 51238",
    type: "国家标准",
    level: "特殊地基",
    version: "2018版",
    source: "教材参考文献[15]，住房和城乡建设部，2018",
    organization: "中华人民共和国住房和城乡建设部",
    publisher: "中国计划出版社",
    publishedYear: "2018",
    link: "岩溶地基、土洞、溶洞、山区地基",
    relatedChapters: ["区域性地基"],
    keyTopics: ["岩溶发育", "土洞", "溶洞稳定", "地基处理", "山区地基"],
    clauses: ["岩溶场地勘察评价", "地基稳定性分析", "处理措施与基础选型", "施工监测"],
    useCases: ["山区地基案例", "岩溶地基危害机理", "特殊地基处理方案"],
    status: "教材引用版本；用于山区和岩溶地基拓展",
  },
  {
    title: "土力学",
    code: "参考教材",
    shortCode: "土力学",
    type: "教材",
    level: "前置知识",
    version: "课程前置知识",
    source: "课程前置知识库",
    organization: "任课教师指定",
    publisher: "按授课教材为准",
    publishedYear: "课堂指定",
    link: "抗剪强度、应力计算、变形计算",
    relatedChapters: ["绪论", "浅基础", "基坑工程"],
    keyTopics: ["土的物理性质", "地基应力", "压缩变形", "抗剪强度", "土压力"],
    clauses: ["土体指标换算", "附加应力计算", "沉降计算基本方法", "库仑土压力理论"],
    useCases: ["薄弱点复习", "基础工程计算前置", "章节学习补课"],
    status: "前置知识复习；由指导老师指定版本",
  },
];

const caseItems = [
  {
    title: "某住宅楼不均匀沉降分析",
    tag: "沉降",
    status: "重点",
    relatedChapters: ["绪论", "浅基础"],
    problem: "建筑使用期出现沉降差，需追溯地基、基础和上部结构共同作用。",
    lesson: "把承载力验算和变形控制一起看，不能只看基础强度。",
  },
  {
    title: "独立基础尺寸初选与软弱下卧层验算",
    tag: "浅基础",
    status: "案例题",
    relatedChapters: ["浅基础"],
    problem: "柱下独立基础基底压力满足要求，但下卧软弱土层仍需复核。",
    lesson: "浅基础设计要同步检查基底压力、偏心、沉降和软弱下卧层。",
  },
  {
    title: "某高层建筑钻孔灌注桩基础设计案例",
    tag: "桩基础",
    status: "推荐",
    relatedChapters: ["桩基础"],
    problem: "高层建筑荷载大，需比较桩侧阻力、桩端阻力和群桩效应。",
    lesson: "桩基础不是单看单桩承载力，还要关注沉降、负摩阻力和承台作用。",
  },
  {
    title: "跨江桥梁沉井下沉偏斜处理",
    tag: "沉井基础",
    status: "施工案例",
    relatedChapters: ["沉井基础"],
    problem: "沉井下沉过程中发生偏斜，需要调整取土、加载和纠偏工艺。",
    lesson: "沉井施工要把下沉力、侧摩阻、刃脚阻力和封底安全联系起来。",
  },
  {
    title: "深基坑支护变形监测与险情处置",
    tag: "基坑工程",
    status: "监测案例",
    relatedChapters: ["基坑工程"],
    problem: "开挖后围护结构水平位移和周边沉降增大，需要动态调整支护。",
    lesson: "基坑工程必须把土压力、支护刚度、降水和监测预警一起管理。",
  },
  {
    title: "软弱地基 CFG 桩处理方案",
    tag: "地基处理",
    status: "案例题",
    relatedChapters: ["地基处理"],
    problem: "软弱地基承载力和沉降均不满足要求，需要复合地基处理。",
    lesson: "复合地基设计要同时看增强体、桩间土和褥垫层的协同作用。",
  },
  {
    title: "湿陷性黄土地基处理与等级判别",
    tag: "区域性地基",
    status: "专题案例",
    relatedChapters: ["区域性地基"],
    problem: "场地黄土遇水湿陷，需确定湿陷类型、湿陷等级和处理措施。",
    lesson: "区域性地基先识别特殊土性，再选择基础形式和地基处理方法。",
  },
];

const relationLabels = {
  introduces: "导入",
  transfers_load_to: "传荷",
  is_a: "属于",
  contains: "包含",
  has_mechanism: "作用机理",
  checks: "验算",
  improves: "改良",
  special_case: "特殊地基",
  展开: "展开",
};

const graphTypeOptions = ["全部", "章节", "知识点", "展开"];

const graphFocusNames = ["桩基础", "桩侧阻力", "承载力", "沉降计算", "基坑工程", "地基处理"];

const graphWeakNames = new Set(weakPoints.map((item) => item.name));

const graphExpansionMap = {
  "第3章 桩基础": ["单桩竖向荷载传递", "摩擦型桩", "端承型桩", "负摩阻力", "群桩效应", "桩基沉降"],
  桩基础: ["单桩竖向荷载传递", "摩擦型桩", "端承型桩", "负摩阻力", "群桩效应", "桩基沉降"],
  桩侧阻力: ["桩土相对位移", "桩侧摩阻力", "荷载传递", "应变软化"],
  桩端阻力: ["桩端持力层", "端承型桩", "桩端沉降", "极限阻力"],
  浅基础: ["无筋扩展基础", "扩展基础", "条形基础", "筏形基础", "箱形基础", "基础埋深"],
  深基础: ["桩基础", "沉井基础", "地下连续墙", "墩基"],
  地基: ["天然地基", "人工地基", "持力层", "下卧层", "软弱下卧层"],
  基础: ["浅基础", "深基础", "承台", "筏板", "箱形基础"],
  承载力: ["地基承载力特征值", "极限承载力", "承载力验算", "原位测试"],
  沉降计算: ["分层总和法", "压缩模量", "沉降差", "局部倾斜"],
  基坑工程: ["支护结构", "土压力", "降水", "基坑稳定性", "环境影响"],
  地基处理: ["换填垫层法", "强夯法", "复合地基", "排水固结", "深层搅拌"],
  区域性地基: ["湿陷性黄土", "膨胀土", "盐渍土", "冻土", "山区地基"],
};

function cx(...classes) {
  return classes.filter(Boolean).join(" ");
}

function useJsonAssetState(path, fallback, options = {}) {
  const { enabled = true } = options;
  const fallbackRef = useRef(fallback);
  const [state, setState] = useState(() => ({
    data: fallback,
    status: enabled ? "loading" : "idle",
    error: null,
  }));

  useEffect(() => {
    fallbackRef.current = fallback;
  }, [fallback]);

  useEffect(() => {
    let alive = true;
    if (!enabled) {
      setState({ data: fallbackRef.current, status: "idle", error: null });
      return () => {
        alive = false;
      };
    }
    const cleanPath = path.replace(/^\/+/, "");
    const assetUrl = `${import.meta.env.BASE_URL || "/"}${cleanPath}`;
    setState((current) => ({
      data: current.data ?? fallbackRef.current,
      status: "loading",
      error: null,
    }));
    fetch(assetUrl)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to load ${path}`);
        }
        return response.json();
      })
      .then((nextData) => {
        if (alive) {
          setState({ data: nextData, status: "success", error: null });
        }
      })
      .catch((error) => {
        if (alive) {
          setState({ data: fallbackRef.current, status: "error", error });
        }
      });
    return () => {
      alive = false;
    };
  }, [enabled, path]);

  return state;
}

function useJsonAsset(path, fallback, options) {
  return useJsonAssetState(path, fallback, options).data;
}

const puterScriptId = "puter-ai-script";
let puterLoadPromise = null;

function ensurePuterLoaded() {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("FREE_AI_UNAVAILABLE"));
  }
  if (typeof window.puter?.ai?.chat === "function") {
    return Promise.resolve();
  }
  if (!puterLoadPromise) {
    puterLoadPromise = new Promise((resolve, reject) => {
      const existingScript = document.getElementById(puterScriptId);
      const script = existingScript ?? document.createElement("script");
      let timeoutId = null;
      const cleanup = () => {
        window.clearTimeout(timeoutId);
        script.removeEventListener("load", handleLoad);
        script.removeEventListener("error", handleError);
      };
      const handleLoad = () => {
        cleanup();
        if (typeof window.puter?.ai?.chat === "function") {
          resolve();
        } else {
          reject(new Error("FREE_AI_UNAVAILABLE"));
        }
      };
      const handleError = () => {
        cleanup();
        reject(new Error("FREE_AI_UNAVAILABLE"));
      };
      script.id = puterScriptId;
      script.src = "https://js.puter.com/v2/";
      script.async = true;
      script.addEventListener("load", handleLoad);
      script.addEventListener("error", handleError);
      timeoutId = window.setTimeout(() => {
        cleanup();
        reject(new Error("FREE_AI_TIMEOUT"));
      }, 12000);
      if (!existingScript) {
        document.body.appendChild(script);
      }
    }).catch((error) => {
      puterLoadPromise = null;
      throw error;
    });
  }
  return puterLoadPromise;
}

function courseChapters(courseManifest) {
  return courseManifest?.chapters?.length ? courseManifest.chapters : defaultCourseManifest.chapters;
}

function chapterTitles(courseManifest) {
  return courseChapters(courseManifest).map((chapter) => chapter.title);
}

function currentCourseChapter(courseManifest) {
  const chapters = courseChapters(courseManifest);
  return chapters.find((chapter) => chapter.id === courseManifest?.currentChapterId) ?? chapters[0];
}

function chapterNumberLabel(courseManifest, title) {
  const chapter = courseChapters(courseManifest).find((item) => item.title === title);
  return chapter ? `第${chapter.number}章` : "前置知识";
}

function progressPercent(courseManifest) {
  const total = courseManifest?.totalChapters ?? courseChapters(courseManifest).length;
  const completed = courseManifest?.progress?.completedChapters ?? 0;
  if (!total) {
    return 0;
  }
  return Math.round((completed / total) * 100);
}

const learningAttemptsKey = "foundation-smart-companion:learning-attempts";
const authSessionKey = "foundation-smart-companion:auth-session";
const ragDocumentsKey = "foundation-smart-companion:rag-documents";
const customExercisesKey = "foundation-smart-companion:custom-exercises";
const qaConfigKey = "foundation-smart-companion:qa-config";

const defaultQaConfig = {
  teacherInstruction: "回答时优先引用教材原文，涉及规范条文时提示学生以指导老师确认版本为准。",
  answerStyle: "先给结论，再列关键依据，最后给复习建议。",
  reviewRule: "低置信度答案和计算题高分答案建议教师复核。",
};

function readStoredJson(key, fallback) {
  if (typeof window === "undefined") {
    return fallback;
  }
  try {
    const value = window.localStorage.getItem(key);
    if (!value) {
      return fallback;
    }
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

function usePersistentState(key, fallback) {
  const [value, setValue] = useState(() => readStoredJson(key, fallback));

  useEffect(() => {
    window.localStorage.setItem(key, JSON.stringify(value));
  }, [key, value]);

  return [value, setValue];
}

function csrfCookie() {
  return document.cookie
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith("foundation_csrf="))
    ?.split("=")
    .slice(1)
    .join("=") ?? "";
}

async function apiRequest(path, { method = "GET", body, headers = {} } = {}) {
  const requestHeaders = { ...headers };
  const options = { method, headers: requestHeaders, credentials: "include" };
  if (!["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase())) {
    const csrf = csrfCookie();
    if (csrf) requestHeaders["X-CSRF-Token"] = decodeURIComponent(csrf);
  }
  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
    requestHeaders["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const base = import.meta.env.DEV ? "/api" : `${appBasePath()}/api`;
  const response = await fetch(`${base}${path}`, options);
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.detail || data.message || `API ${response.status}`);
  }
  return data.success === true ? data.data : data;
}

function canManageContent(user) {
  return ["teacher", "admin"].includes(user?.role);
}

function profileRowsForUser(user) {
  const profile = user ?? demoUsers[0];
  return [
    { label: "姓名", value: profile.name },
    { label: profile.role === "student" ? "学号" : "工号", value: profile.studentNo },
    { label: "学院", value: profile.college },
    { label: "学校", value: profile.school },
    { label: "辅导老师", value: profile.mentor },
  ];
}

function cleanUploadedText(text = "") {
  return text
    .replace(/\r/g, "")
    .replace(/\\n/g, "\n")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{4,}/g, "\n\n\n")
    .trim();
}

function normalizeDocumentTitle(name = "补充资料") {
  return name.replace(/\.(md|markdown|txt|json)$/i, "").slice(0, 42) || "补充资料";
}

function makeRagDocument({ title, text, sourceType = "teacher-upload" }) {
  const clean = cleanUploadedText(text);
  if (!clean) {
    return null;
  }
  return {
    id: `doc-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    title: normalizeDocumentTitle(title),
    text: clean.slice(0, 180000),
    sourceType,
    uploadedAt: new Date().toISOString(),
  };
}

function extractDocumentText(rawText) {
  const clean = cleanUploadedText(rawText);
  if (!clean) {
    return "";
  }
  try {
    const parsed = JSON.parse(clean);
    if (Array.isArray(parsed)) {
      return parsed.map((item) => item.text ?? item.content ?? item.title ?? "").join("\n\n");
    }
    if (Array.isArray(parsed.chunks)) {
      return parsed.chunks.map((item) => item.text ?? item.content ?? "").join("\n\n");
    }
    if (Array.isArray(parsed.items)) {
      return parsed.items.map((item) => item.text ?? item.content ?? item.title ?? "").join("\n\n");
    }
    return parsed.text ?? parsed.content ?? clean;
  } catch {
    return clean;
  }
}

function chunkTextForRag(document) {
  if (!document?.text) {
    return [];
  }
  const lines = cleanUploadedText(document.text).split("\n");
  const chunks = [];
  let heading = document.title;
  let buffer = [];
  let startLine = 1;

  function flush(endLine) {
    const text = cleanUploadedText(buffer.join("\n"));
    if (text.length < 18) {
      buffer = [];
      startLine = endLine + 1;
      return;
    }
    chunks.push({
      id: `upload:${document.id}:${chunks.length + 1}`,
      kind: "teacher-upload",
      sourceType: document.sourceType,
      documentTitle: document.title,
      text,
      source_line: startLine,
      end_line: endLine,
      heading_path: `${document.title}${heading && heading !== document.title ? ` > ${heading}` : ""}`,
    });
    buffer = [];
    startLine = endLine + 1;
  }

  lines.forEach((line, index) => {
    const lineNumber = index + 1;
    const headingMatch = line.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      flush(lineNumber - 1);
      heading = headingMatch[2].trim().slice(0, 80);
      startLine = lineNumber + 1;
      return;
    }
    buffer.push(line);
    if (buffer.join("\n").length >= 620 || (line.trim() === "" && buffer.join("\n").length >= 360)) {
      flush(lineNumber);
    }
  });
  flush(lines.length);
  return chunks;
}

function buildLocalRagChunks(documents) {
  return (documents ?? []).flatMap((document) => chunkTextForRag(document));
}

function mergeExerciseBank(baseBank, customExercises) {
  const baseExercises = baseBank?.exercises ?? [];
  const mergedMap = new Map();
  [...(customExercises ?? []), ...baseExercises].forEach((exercise) => {
    if (exercise?.id && !mergedMap.has(exercise.id)) {
      mergedMap.set(exercise.id, exercise);
    }
  });
  const exercises = Array.from(mergedMap.values());
  const chapters = Array.from(new Set(exercises.map((item) => item.chapter).filter(Boolean)));
  return {
    summary: {
      ...(baseBank?.summary ?? {}),
      total: exercises.length,
      thinking: exercises.filter((item) => item.type === "思考题").length,
      exercise: exercises.filter((item) => item.type === "习题").length,
      chapters,
    },
    exercises,
  };
}

function normalizeImportedExercise(item, index) {
  if (!item || typeof item !== "object") {
    return null;
  }
  const text = String(item.text ?? item.title ?? item.question ?? "").trim();
  if (!text) {
    return null;
  }
  return {
    id: item.id ?? `custom-exercise-${Date.now()}-${index}`,
    number: item.number ?? `导入-${index + 1}`,
    chapter: item.chapter ?? "第3章 桩基础",
    chapterNo: item.chapterNo ?? null,
    type: item.type ?? "思考题",
    kind: item.kind ?? "教师导入",
    difficulty: item.difficulty ?? "基础",
    text,
    tags: Array.isArray(item.tags) ? item.tags : ["教师导入"],
    answer: item.answer ?? null,
    attachments: Array.isArray(item.attachments) ? item.attachments : [],
    sourceLine: item.sourceLine ?? "teacher-import",
  };
}

function parseExerciseImport(rawText) {
  const parsed = JSON.parse(rawText);
  const list = Array.isArray(parsed) ? parsed : parsed.exercises ?? parsed.items ?? [];
  if (!Array.isArray(list)) {
    return [];
  }
  return list.map((item, index) => normalizeImportedExercise(item, index)).filter(Boolean);
}

function readLearningAttempts() {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    const parsed = JSON.parse(window.localStorage.getItem(learningAttemptsKey) ?? "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function latestAttempts(attempts) {
  const latest = new Map();
  attempts.forEach((attempt) => {
    if (!attempt?.questionId || latest.has(attempt.questionId)) {
      return;
    }
    latest.set(attempt.questionId, attempt);
  });
  return Array.from(latest.values());
}

function average(values, fallback = 0) {
  const numeric = values.filter((value) => Number.isFinite(value));
  if (!numeric.length) {
    return fallback;
  }
  return Math.round(numeric.reduce((sum, value) => sum + value, 0) / numeric.length);
}

function rankFromScore(score) {
  if (score >= 95) {
    return { level: "王者", score, next: "满级", tip: "已经是高掌握度状态，适合挑战综合设计题。" };
  }
  if (score >= 85) {
    return { level: "白金", score, next: "王者", tip: "表现很稳，继续补齐低分评分点就能冲王者。" };
  }
  if (score >= 75) {
    return { level: "黄金", score, next: "白金", tip: "学习状态很稳，补齐薄弱点就能冲白金。" };
  }
  if (score >= 60) {
    return { level: "白银", score, next: "黄金", tip: "基础已经起步，优先把低分章节刷到 75 分。" };
  }
  return { level: "青铜", score, next: "白银", tip: "先完成一轮基础题，把核心概念搭起来。" };
}

function attemptChapterTitle(attempt) {
  return normalizeChapterName(attempt?.chapter ?? "");
}

function buildWeakPointsFromAttempts(attempts) {
  const conceptMap = new Map();
  attempts.forEach((attempt) => {
    (attempt.missingConcepts ?? []).slice(0, 4).forEach((concept) => {
      const current = conceptMap.get(concept) ?? { name: concept, scores: [], count: 0 };
      current.scores.push(attempt.score);
      current.count += 1;
      conceptMap.set(concept, current);
    });
    (attempt.criteria ?? []).forEach((criterion) => {
      const mastery = criterion.weight ? Math.round((criterion.score / criterion.weight) * 100) : attempt.score;
      (criterion.missing ?? []).slice(0, 3).forEach((concept) => {
        const current = conceptMap.get(concept) ?? { name: concept, scores: [], count: 0 };
        current.scores.push(Math.min(attempt.score, mastery));
        current.count += 1;
        conceptMap.set(concept, current);
      });
    });
  });

  return Array.from(conceptMap.values())
    .map((item) => ({
      name: item.name,
      score: Math.max(25, Math.min(92, average(item.scores, 65))),
      note: `${item.count} 次作答暴露该知识点，可回到相关章节复习`,
    }))
    .sort((a, b) => a.score - b.score || b.note.localeCompare(a.note, "zh-Hans-CN"))
    .slice(0, 3);
}

function buildLearningStats({ courseManifest, exerciseBank, attempts }) {
  const chapters = courseChapters(courseManifest);
  const totalQuestions = exerciseBank?.summary?.total ?? exerciseBank?.exercises?.length ?? 0;
  const latest = latestAttempts(attempts);
  const hasAttempts = latest.length > 0;
  const fallbackAverage = courseManifest?.progress?.averageScore ?? rankInfo.score;
  const averageScore = hasAttempts ? average(latest.map((attempt) => attempt.score), fallbackAverage) : fallbackAverage;
  const chapterFallbacks = [88, 80, 65, 72, 70, 76, 68];
  const chapterStats = chapters.map((chapter, index) => {
    const chapterAttempts = latest.filter((attempt) => attemptChapterTitle(attempt) === chapter.title);
    const chapterScore = chapterAttempts.length ? average(chapterAttempts.map((attempt) => attempt.score), 0) : chapterFallbacks[index] ?? 70;
    return {
      id: chapter.id,
      title: chapter.title,
      score: chapterScore,
      attempts: chapterAttempts.length,
      isActual: chapterAttempts.length > 0,
    };
  });
  const completedChapters = hasAttempts
    ? chapterStats.filter((chapter) => chapter.attempts > 0).length
    : (courseManifest?.progress?.completedChapters ?? 0);
  const percent = hasAttempts && totalQuestions ? Math.round((latest.length / totalQuestions) * 100) : progressPercent(courseManifest);
  const weakPointsFromAttempts = hasAttempts ? buildWeakPointsFromAttempts(latest) : [];
  const mergedWeakPoints = [
    ...weakPointsFromAttempts,
    ...weakPoints.filter((item) => !weakPointsFromAttempts.some((candidate) => candidate.name === item.name)),
  ].slice(0, 3);

  return {
    hasAttempts,
    attempts,
    latestAttempts: latest,
    totalQuestions,
    attemptedQuestions: latest.length,
    completedChapters,
    progressPercent: Math.min(100, percent),
    averageScore,
    rank: rankFromScore(averageScore),
    chapterStats,
    weakPoints: hasAttempts ? mergedWeakPoints : weakPoints,
    recentAttempts: attempts.slice(0, 5),
  };
}

function moduleMeta(cardId, { courseManifest, graphSummary, exerciseBank }) {
  const totalChapters = courseManifest?.totalChapters ?? courseChapters(courseManifest).length;
  const currentChapter = currentCourseChapter(courseManifest);
  const exerciseTotal = exerciseBank?.summary?.total ?? exerciseBank?.exercises?.length ?? 0;
  const resourceCount = resources.length;
  const caseCount = caseItems.length;

  switch (cardId) {
    case "textbook":
      return `${totalChapters} 章教材 · 当前：第${currentChapter.number}章 ${currentChapter.title}`;
    case "graph":
      return graphSummary ? `完整 ${graphSummary.graph_nodes} 节点 · 当前演示 19 节点` : "完整知识库 + 当前演示子图";
    case "qa":
      return graphSummary ? `${graphSummary.chunks} 个教材切块` : "支持引用来源";
    case "cases":
      return `${caseCount} 个示例案例`;
    case "resources":
      return `${resourceCount} 条关联资料`;
    case "practice":
      return `${exerciseTotal || 79} 道教材题`;
    default:
      return "";
  }
}

function relatedResourcesForChapter(chapterTitle) {
  return resources.filter((item) => {
    const related = item.relatedChapters ?? [];
    const searchable = [item.link, item.level, item.status, ...(item.keyTopics ?? []), ...(item.clauses ?? [])].join(" ");
    return related.includes(chapterTitle) || searchable.includes(chapterTitle);
  });
}

function relatedCasesForChapter(chapterTitle) {
  return caseItems.filter((item) => {
    const related = item.relatedChapters ?? [];
    return related.includes(chapterTitle) || item.tag === chapterTitle;
  });
}

function appBasePath() {
  const base = import.meta.env.BASE_URL || "/";
  if (base === "./") {
    return "";
  }
  return base.endsWith("/") ? base.slice(0, -1) : base;
}

function stripAppBase(pathname) {
  const base = appBasePath();
  if (base && pathname.startsWith(base)) {
    return pathname.slice(base.length) || "/";
  }
  return pathname || "/";
}

function chapterFromRouteSegment(courseManifest, segment) {
  const decoded = decodeURIComponent(segment ?? "");
  return courseChapters(courseManifest).find((chapter) => {
    const numberSlug = `chapter-${String(chapter.number).padStart(2, "0")}`;
    return chapter.slug === decoded || numberSlug === decoded || chapter.title === decoded || `第${chapter.number}章${chapter.title}` === decoded;
  });
}

function routeFromLocation(courseManifest) {
  if (typeof window === "undefined") {
    return { page: "overview" };
  }
  const path = stripAppBase(window.location.pathname);
  const rawSegments = path.split("/").filter(Boolean).map((segment) => decodeURIComponent(segment));
  const segments = rawSegments[0] === "student" ? rawSegments.slice(1) : rawSegments;
  const params = new URLSearchParams(window.location.search);
  const [page = "overview", detail] = segments;

  switch (page) {
    case "textbook": {
      const chapter = chapterFromRouteSegment(courseManifest, detail) ?? currentCourseChapter(courseManifest);
      return { page: "textbook", chapter: chapter.title };
    }
    case "graph":
      return { page: "graph", node: params.get("node") ?? "" };
    case "qa":
      return { page: "qa", mode: params.get("mode") ?? "" };
    case "cases":
      return { page: "cases", caseTitle: detail ?? params.get("case") ?? "" };
    case "resources":
      return { page: "resources", resourceTitle: detail ?? params.get("resource") ?? "" };
    case "practice":
      return { page: "practice", exerciseId: detail ?? params.get("exercise") ?? "", chapter: params.get("chapter") ?? "" };
    case "report":
    case "admin":
    case "overview":
      return { page };
    default:
      return { page: "overview" };
  }
}

function routeToUrl(page, options = {}, courseManifest = defaultCourseManifest) {
  const base = appBasePath();
  const params = new URLSearchParams();
  let path = "/";

  if (page === "textbook") {
    const chapter = courseChapters(courseManifest).find((item) => item.title === options.chapter) ?? currentCourseChapter(courseManifest);
    path = `/textbook/${chapter.slug}`;
  } else if (page === "graph") {
    path = "/graph";
    if (options.node) {
      params.set("node", options.node);
    }
  } else if (page === "qa") {
    path = "/qa";
    if (options.mode) {
      params.set("mode", options.mode);
    }
  } else if (page === "cases") {
    path = options.caseTitle ? `/cases/${encodeURIComponent(options.caseTitle)}` : "/cases";
  } else if (page === "resources") {
    path = options.resourceTitle ? `/resources/${encodeURIComponent(options.resourceTitle)}` : "/resources";
  } else if (page === "practice") {
    path = options.exerciseId ? `/practice/${encodeURIComponent(options.exerciseId)}` : "/practice";
    if (options.chapter) {
      params.set("chapter", options.chapter);
    }
  } else if (["report", "admin"].includes(page)) {
    path = `/${page}`;
  }

  const query = params.toString();
  const studentPath = path === "/" ? "/student" : `/student${path}`;
  return `${base}${studentPath}${query ? `?${query}` : ""}`;
}

const pageSeo = {
  overview: {
    title: "《基础工程》智慧学伴",
    description: "面向土木工程基础工程课程的教材学习、知识图谱、RAG 智能问答、关联规范资料、题库练习和学习报告平台。",
  },
  textbook: {
    title: "教材学习 - 《基础工程》智慧学伴",
    description: "按章节浏览《基础工程》教材内容，查看公式、图表解释、案例关联和章节练习。",
  },
  graph: {
    title: "知识图谱 - 《基础工程》智慧学伴",
    description: "以可交互知识图谱浏览基础工程章节、概念、关系和教材原文依据。",
  },
  qa: {
    title: "RAG 智能问答 - 《基础工程》智慧学伴",
    description: "基于教材切块、教师上传知识库和大模型生成的基础工程课程问答系统。",
  },
  cases: {
    title: "工程案例 - 《基础工程》智慧学伴",
    description: "围绕浅基础、桩基础、基坑工程、地基处理等主题的工程案例学习入口。",
  },
  resources: {
    title: "关联资料 - 《基础工程》智慧学伴",
    description: "整理基础工程课程相关规范、规程、参考教材和拓展资料，可查看标准编号、版本和关联章节。",
  },
  practice: {
    title: "练习中心 - 《基础工程》智慧学伴",
    description: "覆盖《基础工程》全书思考题和习题，支持按章节、题型、难度和关键词练习。",
  },
  report: {
    title: "学习报告 - 《基础工程》智慧学伴",
    description: "根据练习记录生成学习进度、掌握度、薄弱知识点和学习段位反馈。",
  },
  admin: {
    title: "后台管理 - 《基础工程》智慧学伴",
    description: "指导老师维护 RAG 知识库、题库、答疑口径和学生绑定关系。",
  },
};

function routeSeo(page, details = {}) {
  const base = pageSeo[page] ?? pageSeo.overview;
  if (page === "textbook" && details.chapter) {
    return {
      title: `${details.chapter} - 教材学习 - 《基础工程》智慧学伴`,
      description: `学习《基础工程》${details.chapter}，查看重点公式、图表解释、案例关联和章节练习。`,
    };
  }
  if (page === "graph" && details.node) {
    return {
      title: `${details.node} - 知识图谱 - 《基础工程》智慧学伴`,
      description: `在基础工程知识图谱中查看“${details.node}”的关联概念、关系和教材依据。`,
    };
  }
  if (page === "cases" && details.caseTitle) {
    return {
      title: `${details.caseTitle} - 工程案例 - 《基础工程》智慧学伴`,
      description: `查看基础工程案例“${details.caseTitle}”的工程背景、原因分析、处理措施和相关章节。`,
    };
  }
  if (page === "resources" && details.resourceTitle) {
    return {
      title: `${details.resourceTitle} - 关联资料 - 《基础工程》智慧学伴`,
      description: `查看关联资料“${details.resourceTitle}”的规范编号、版本信息、关键条款和课程章节关系。`,
    };
  }
  return base;
}

function setDocumentMeta(selector, attributes) {
  if (typeof document === "undefined") {
    return;
  }
  let element = document.querySelector(selector);
  if (!element) {
    element = selector.startsWith("link") ? document.createElement("link") : document.createElement("meta");
    if (selector.includes('rel="canonical"')) {
      element.setAttribute("rel", "canonical");
    }
    if (selector.includes('name="description"')) {
      element.setAttribute("name", "description");
    }
    if (selector.includes('property="og:title"')) {
      element.setAttribute("property", "og:title");
    }
    if (selector.includes('property="og:description"')) {
      element.setAttribute("property", "og:description");
    }
    if (selector.includes('property="og:url"')) {
      element.setAttribute("property", "og:url");
    }
    document.head.appendChild(element);
  }
  Object.entries(attributes).forEach(([name, value]) => {
    element.setAttribute(name, value);
  });
}

function keywordTerms(text) {
  const compact = text.replace(/\s+/g, "");
  const terms = new Set();
  for (let index = 0; index < compact.length; index += 1) {
    for (let size = 2; size <= 6; size += 1) {
      const term = compact.slice(index, index + size);
      if (term.length === size && !/^[的是了和与及或在有为对中下上其要能可]+$/.test(term)) {
        terms.add(term);
      }
    }
  }
  return Array.from(terms).sort((a, b) => b.length - a.length);
}

function searchChunks(chunks, query, limit = 4) {
  const terms = keywordTerms(query);
  if (!terms.length) {
    return [];
  }
  const anchorTerms = ["桩侧阻力", "桩端阻力", "摩阻力", "浅基础", "深基础", "地基", "基础", "沉降", "承载力", "基坑", "土压力"].filter((term) =>
    query.includes(term),
  );
  return chunks
    .map((chunk) => {
      const haystack = `${chunk.heading_path}\n${chunk.text}`;
      const score = terms.reduce((total, term) => total + (haystack.includes(term) ? term.length : 0), 0);
      const anchorHits = anchorTerms.filter((term) => haystack.includes(term)).length;
      const anchor = anchorTerms.length ? (anchorHits ? anchorHits * 26 : -50) : 0;
      const lengthBonus = chunk.text.length > 80 ? 4 : 0;
      return { ...chunk, score: score + anchor + lengthBonus };
    })
    .filter((chunk) => chunk.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

function compactText(text = "", limit = 260) {
  const clean = text.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  return clean.length > limit ? `${clean.slice(0, limit)}...` : clean;
}

function buildAiPrompt(question, mode, results, qaConfig = defaultQaConfig) {
  const context = results.length
    ? results
        .map((item, index) => {
          const title = item.heading_path || item.documentTitle || item.title || "教材资料";
          const line = item.source_line ? ` L${item.source_line}` : "";
          return `${index + 1}. ${title}${line}: ${compactText(item.text ?? "", 360)}`;
        })
        .join("\n")
    : "暂无教材检索片段。";
  return [
    "你是《基础工程》课程的智慧学伴。请只基于给定教材片段回答，必要时说明还需要查教材。",
    `问答模式：${mode}`,
    `指导老师要求：${qaConfig.teacherInstruction}`,
    `回答风格：${qaConfig.answerStyle}`,
    `学生问题：${question}`,
    "教材片段：",
    context,
    "请用中文回答，结构简洁，包含：直接回答、关键概念、复习提醒。不要编造规范条文编号。",
  ].join("\n");
}

function buildLocalRagAnswer(question, mode, results, qaConfig = defaultQaConfig) {
  if (!results.length) {
    return "暂时没有检索到足够相关的教材或教师上传资料。可以换一个更具体的关键词，例如“桩侧阻力”“地基承载力修正”或“主动土压力”。";
  }
  const top = results[0];
  const concepts = keywordTerms(question)
    .filter((term) => top.text.includes(term) || top.heading_path.includes(term))
    .slice(0, 5);
  const modeLead =
    mode === "规范问答"
      ? "按规范问答的口径，先定位到与问题相关的教材和关联资料片段；正式条文编号仍建议由指导老师确认最新版本。"
      : mode === "学习辅导"
        ? "按学习辅导的口径，可以先抓住教材中的关键说法，再回到练习题里验证掌握度。"
        : "按教材问答的口径，当前最相关的依据如下。";
  const support = results
    .slice(0, 3)
    .map((item, index) => `${index + 1}. ${compactText(item.text, 150)}（${item.heading_path || item.documentTitle || "教材资料"}）`)
    .join("\n");
  return [
    modeLead,
    "",
    `直接回答：${compactText(top.text, 260)}`,
    concepts.length ? `关键概念：${concepts.join("、")}` : "关键概念：建议结合检索片段中的术语继续追问。",
    `复习提醒：${qaConfig.answerStyle}`,
    "",
    `引用依据：\n${support}`,
  ].join("\n");
}

function normalizeAiResponse(response) {
  if (typeof response === "string") {
    return response;
  }
  if (response?.message?.content) {
    return Array.isArray(response.message.content)
      ? response.message.content.map((item) => item.text ?? "").join("")
      : response.message.content;
  }
  if (response?.text) {
    return response.text;
  }
  return JSON.stringify(response);
}

async function callFreeAi(prompt) {
  await ensurePuterLoaded();
  const response = await Promise.race([
    window.puter.ai.chat(prompt),
    new Promise((_, reject) => {
      window.setTimeout(() => reject(new Error("FREE_AI_TIMEOUT")), 12000);
    }),
  ]);
  const text = normalizeAiResponse(response).trim();
  if (!text) {
    throw new Error("FREE_AI_EMPTY");
  }
  return text;
}

function displayChapter(chapter = "") {
  return chapter.replace(/^第(\d+)章\s*/, "第$1章 ");
}

function normalizeChapterName(chapter = "") {
  return chapter.replace(/^第\d+章\s*/, "").replace(/\s+/g, "");
}

function matchExerciseChapter(exerciseChapters, chapterName) {
  if (!chapterName) {
    return "全部";
  }
  const cleanChapter = chapterName.replace(/\s+/g, "");
  const direct = exerciseChapters.find((chapter) => chapter.replace(/\s+/g, "") === cleanChapter);
  if (direct) {
    return direct;
  }
  const simpleName = normalizeChapterName(chapterName);
  return (
    exerciseChapters.find((chapter) => {
      const candidate = chapter.replace(/\s+/g, "");
      const candidateName = normalizeChapterName(chapter);
      return candidate.includes(cleanChapter) || candidateName.includes(simpleName) || simpleName.includes(candidateName);
    }) ?? "全部"
  );
}

function exerciseSearchText(exercise) {
  return [exercise.number, exercise.chapter, exercise.type, exercise.kind, exercise.difficulty, exercise.text, ...(exercise.tags ?? [])]
    .join(" ")
    .toLowerCase();
}

const scoringAliases = {
  岩土体: ["岩土", "土体", "土层", "天然土层"],
  承受荷载: ["承受", "荷载", "承载"],
  结构构件: ["构件", "结构", "基础结构"],
  传递荷载: ["传递", "上部荷载", "上部结构"],
  工程意义: ["工程意义", "实际意义", "工程作用", "影响"],
  设计要求: ["设计要求", "安全", "经济", "正常使用"],
  适用条件: ["适用条件", "适用范围", "条件"],
  题给数据: ["已知", "题给", "数据", "表", "取值"],
  附表数据: ["表", "附表", "数据", "取土深度"],
  代入过程: ["代入", "带入", "=", "＝", "×", "/", "÷"],
  计算步骤: ["计算", "求得", "可得", "步骤", "代入"],
  数值结果: ["结果", "数值", "得", "="],
  单位: ["单位", "kN", "kPa", "m", "mm", "%", "mL", "㎡"],
  结论: ["结论", "因此", "所以", "判定", "属于"],
  等级: ["等级", "级", "判定"],
  类型: ["类型", "类", "判定"],
  类: ["类型", "类", "判定"],
  首先: ["首先", "第一", "一是", "从"],
  因此: ["因此", "所以", "可知", "综上"],
};

function countOccurrences(text, term) {
  if (!term) {
    return 0;
  }
  return text.split(term).length - 1;
}

function answerHasConcept(answer, concept) {
  if (!concept) {
    return false;
  }
  if (answer.includes(concept)) {
    return true;
  }
  if (concept === "数值结果") {
    return /\d+(\.\d+)?/.test(answer);
  }
  if (concept === "单位") {
    return /(kN|kPa|mm|mL|m²|m2|㎡|%|米|厘米|吨|级|类)/i.test(answer);
  }
  if (["题给数据", "附表数据"].includes(concept)) {
    return /\d+(\.\d+)?/.test(answer) && /已知|题给|表|数据|取|测得|原始|增大/.test(answer);
  }
  if (concept === "代入过程") {
    return /\d+(\.\d+)?/.test(answer) && /代入|带入|=|＝|×|÷|\/|\*/.test(answer);
  }
  if (concept === "计算步骤") {
    return /\d+(\.\d+)?/.test(answer) && /计算|求得|可得|得|步骤|代入|判定/.test(answer);
  }
  return (scoringAliases[concept] ?? []).some((alias) => answer.includes(alias));
}

function fallbackRubric(exercise) {
  const tags = exercise?.tags?.length ? exercise.tags : ["教材概念"];
  if (exercise?.type === "习题") {
    return [
      { criterion: "选用正确公式或判别方法", weight: 25, requiredConcepts: tags },
      { criterion: "整理题给条件并完整代入", weight: 25, requiredConcepts: ["题给数据", "代入过程", "计算步骤"] },
      { criterion: "给出数值结果、单位或等级判定", weight: 30, requiredConcepts: ["数值结果", "单位", "结论"] },
      { criterion: "说明验算过程和工程结论", weight: 20, requiredConcepts: ["验算", "因此", "结论"] },
    ];
  }
  return [
    { criterion: "说明核心概念或定义", weight: 30, requiredConcepts: tags },
    { criterion: "解释作用机理或适用条件", weight: 30, requiredConcepts: ["适用条件", "设计要求"] },
    { criterion: "指出工程意义、区别或设计要求", weight: 25, requiredConcepts: [...tags.slice(0, 2), "工程意义"] },
    { criterion: "表达准确、层次清楚", weight: 15, requiredConcepts: ["首先", "因此"] },
  ];
}

function scoreCriterion(answer, criterion) {
  const required = criterion.requiredConcepts ?? [];
  const matched = required.filter((concept) => answerHasConcept(answer, concept));
  const ratio = required.length ? matched.length / required.length : 0;
  const partial = required.length && matched.length ? 0.25 : 0;
  const score = Math.round(criterion.weight * Math.min(1, ratio + partial));
  return {
    ...criterion,
    matched,
    missing: required.filter((concept) => !matched.includes(concept)),
    score: Math.min(criterion.weight, score),
  };
}

function detectKeywordStuffing(answer, concepts) {
  const clean = answer.replace(/\s+/g, "");
  const repeated = concepts
    .map((concept) => ({ concept, count: countOccurrences(clean, concept) }))
    .filter((item) => item.concept.length >= 2 && item.count >= 4);
  const hasReasoning = /因为|因此|所以|首先|其次|定义|区别|公式|代入|计算|验算|结论|适用|影响|导致/.test(answer);
  const uniqueRatio = clean ? new Set(clean).size / clean.length : 1;
  return {
    isStuffing: (repeated.length > 0 && !hasReasoning) || (clean.length > 24 && uniqueRatio < 0.22),
    repeated,
  };
}

function clampScore(value) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function scoreExerciseAnswer(answer, exercise) {
  const clean = answer.trim();
  const rubric = exercise?.rubric?.length ? exercise.rubric : fallbackRubric(exercise);
  const expectedConcepts = exercise?.expectedConcepts?.length ? exercise.expectedConcepts : exercise?.tags ?? [];
  if (!clean) {
    return {
      score: 0,
      summary: "还没有作答，先写出思路或计算步骤再提交。",
      feedback: ["建议先列出关键词、公式或判断依据。"],
      criteria: rubric.map((criterion) => ({ ...criterion, matched: [], missing: criterion.requiredConcepts ?? [], score: 0 })),
      issues: [],
      misconceptionsHit: [],
      confidence: 0,
      needsTeacherReview: false,
      hits: [],
      missing: expectedConcepts.slice(0, 4),
    };
  }

  const criteria = rubric.map((criterion) => scoreCriterion(clean, criterion));
  const totalRaw = criteria.reduce((sum, criterion) => sum + criterion.score, 0);
  const totalRequired = criteria.reduce((sum, criterion) => sum + (criterion.requiredConcepts?.length ?? 0), 0);
  const totalMatched = criteria.reduce((sum, criterion) => sum + criterion.matched.length, 0);
  const misconceptionsHit = (exercise?.misconceptions ?? []).filter((item) => clean.includes(item));
  const stuffing = detectKeywordStuffing(clean, expectedConcepts);
  const issues = [];

  if (misconceptionsHit.length) {
    issues.push(`疑似概念误区：${misconceptionsHit.join("；")}`);
  }
  if (stuffing.isStuffing) {
    issues.push("疑似关键词堆砌，建议补充因果说明、公式来源或判断依据。");
  }
  if (exercise?.requiresNumericAnswer && !/\d+(\.\d+)?/.test(clean)) {
    issues.push("计算题缺少明确数值结果。");
  }
  if (exercise?.requiresNumericAnswer && !/(kN|kPa|mm|mL|m²|m2|㎡|%|米|厘米|吨|级|类)/i.test(clean)) {
    issues.push("计算题建议写明单位、类型或等级判定。");
  }

  const penalty =
    misconceptionsHit.length * 16 +
    (stuffing.isStuffing ? 14 : 0) +
    (exercise?.requiresNumericAnswer && !/\d+(\.\d+)?/.test(clean) ? 12 : 0) +
    (exercise?.requiresNumericAnswer && !/(kN|kPa|mm|mL|m²|m2|㎡|%|米|厘米|吨|级|类)/i.test(clean) ? 8 : 0);
  const score = clampScore(totalRaw - penalty);
  const coverage = totalRequired ? totalMatched / totalRequired : 0;
  const lengthAdequacy = Math.min(1, clean.length / (exercise?.requiresNumericAnswer ? 160 : 110));
  const issuePenalty = Math.min(0.45, issues.length * 0.12);
  const confidence = Math.max(0.05, Math.min(0.98, coverage * 0.72 + lengthAdequacy * 0.2 + (issues.length ? 0 : 0.08) - issuePenalty));
  const reviewThreshold = exercise?.teacherReviewBelowConfidence ?? (exercise?.requiresNumericAnswer ? 0.68 : 0.55);
  const needsTeacherReview = confidence < reviewThreshold || (exercise?.requiresNumericAnswer && score >= 80);
  const hits = expectedConcepts.filter((concept) => answerHasConcept(clean, concept));
  const missing = expectedConcepts.filter((concept) => !answerHasConcept(clean, concept)).slice(0, 5);
  const weakestCriterion = [...criteria].sort((a, b) => a.score / a.weight - b.score / b.weight)[0];
  const feedback = [
    hits.length ? `已覆盖：${hits.slice(0, 5).join("、")}` : "答案里还缺少本题核心概念。",
    missing.length ? `建议补充：${missing.join("、")}` : "核心概念覆盖较完整，注意把结论和条件对应起来。",
    weakestCriterion?.missing?.length
      ? `薄弱评分点：${weakestCriterion.criterion}，可补充 ${weakestCriterion.missing.slice(0, 3).join("、")}。`
      : "分项评分点覆盖较均衡。",
  ];

  return {
    score,
    summary:
      score >= 85
        ? "掌握较好，答案已覆盖主要评分点。"
        : score >= 70
          ? "基本掌握，但还可以补足关键条件或计算细节。"
          : "建议回到教材对应章节复习后再答一次。",
    feedback,
    criteria,
    issues,
    misconceptionsHit,
    confidence,
    needsTeacherReview,
    hits,
    missing,
  };
}

function resultMatches(query, ...values) {
  const cleanQuery = query.trim().toLowerCase();
  if (!cleanQuery) {
    return false;
  }
  return values
    .filter(Boolean)
    .join(" ")
    .toLowerCase()
    .includes(cleanQuery);
}

function chapterTitleFromText(text, courseManifest) {
  const cleanText = text ?? "";
  return courseChapters(courseManifest).find((chapter) => cleanText.includes(chapter.title))?.title ?? currentCourseChapter(courseManifest).title;
}

function buildGlobalSearchResults({ query, courseManifest, chunks, graph, exerciseBank }) {
  const cleanQuery = query.trim();
  if (!cleanQuery) {
    return [];
  }

  const chapterResults = courseChapters(courseManifest)
    .filter((chapter) => resultMatches(cleanQuery, chapter.title, chapter.slug, `第${chapter.number}章`))
    .slice(0, 4)
    .map((chapter) => ({
      id: `chapter:${chapter.id}`,
      group: "教材章节",
      title: `第${chapter.number}章 ${chapter.title}`,
      desc: chapterStudyContent[chapter.title]?.intro ?? "进入章节学习工作台。",
      action: { page: "textbook", chapter: chapter.title },
    }));

  const textbookResults = searchChunks(chunks, cleanQuery, 4).map((chunk) => ({
    id: `chunk:${chunk.id}`,
    group: "教材原文",
    title: chunk.heading_path || "教材正文",
    desc: compactText(chunk.text, 112),
    meta: `来源行 ${chunk.source_line}`,
    action: { page: "textbook", chapter: chapterTitleFromText(chunk.heading_path, courseManifest) },
  }));

  const graphResults = (graph.nodes ?? [])
    .filter((node) => resultMatches(cleanQuery, node.name, node.definition, graphNodeType(node)))
    .slice(0, 5)
    .map((node) => ({
      id: `graph:${node.id}`,
      group: "知识图谱",
      title: node.name,
      desc: node.definition ?? `${graphNodeType(node)}节点`,
      meta: graphNodeType(node),
      action: { page: "graph", node: node.name },
    }));

  const caseResults = caseItems
    .filter((item) => resultMatches(cleanQuery, item.title, item.tag, item.status, item.problem, item.lesson, ...(item.relatedChapters ?? [])))
    .map((item) => ({
      id: `case:${item.title}`,
      group: "工程案例",
      title: item.title,
      desc: item.problem,
      meta: item.status,
      action: { page: "cases", caseTitle: item.title },
    }));

  const resourceResults = resources
    .filter((item) =>
      resultMatches(
        cleanQuery,
        item.title,
        item.code,
        item.shortCode,
        item.type,
        item.level,
        item.version,
        item.link,
        item.status,
        item.source,
        item.organization,
        item.publisher,
        ...(item.relatedChapters ?? []),
        ...(item.keyTopics ?? []),
        ...(item.clauses ?? []),
        ...(item.useCases ?? []),
      ),
    )
    .map((item) => ({
      id: `resource:${item.title}`,
      group: "关联资料",
      title: item.title,
      desc: `${item.link}；重点：${(item.keyTopics ?? []).slice(0, 3).join("、")}`,
      meta: `${item.type} · ${item.code}`,
      action: { page: "resources", resourceTitle: item.title },
    }));

  const exerciseResults = (exerciseBank.exercises ?? [])
    .filter((exercise) => resultMatches(cleanQuery, exercise.number, exercise.chapter, exercise.type, exercise.kind, exercise.text, ...(exercise.tags ?? [])))
    .slice(0, 6)
    .map((exercise) => ({
      id: `exercise:${exercise.id}`,
      group: "练习题",
      title: `${exercise.number} ${exercise.text}`,
      desc: `${displayChapter(exercise.chapter)} · ${exercise.type} · ${exercise.difficulty}`,
      meta: exercise.tags?.slice(0, 3).join("、"),
      action: { page: "practice", chapter: normalizeChapterName(exercise.chapter), exerciseId: exercise.id },
    }));

  return [
    { group: "教材章节", items: chapterResults },
    { group: "教材原文", items: textbookResults },
    { group: "知识图谱", items: graphResults },
    { group: "工程案例", items: caseResults },
    { group: "关联资料", items: resourceResults },
    { group: "练习题", items: exerciseResults },
  ].filter((section) => section.items.length);
}

function graphNodeType(node) {
  if (node?.expandedFrom) {
    return "展开";
  }
  return node?.label === "Chapter" ? "章节" : "知识点";
}

function relationText(relation) {
  return relationLabels[relation] ?? relation;
}

function splitNodeName(name) {
  if (!name) {
    return [];
  }
  if (name.length <= 5) {
    return [name];
  }
  return [name.slice(0, 5), name.slice(5, 10)];
}

function edgePath(source, target, index) {
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const length = Math.hypot(dx, dy) || 1;
  const bend = ((index % 3) - 1) * 16 + 20;
  const labelX = (source.x + target.x) / 2 - (dy / length) * bend;
  const labelY = (source.y + target.y) / 2 + (dx / length) * bend;

  return {
    d: `M ${source.x} ${source.y} Q ${labelX} ${labelY} ${target.x} ${target.y}`,
    labelX,
    labelY,
  };
}

function createLayout(nodes, width = 920, height = 560) {
  const centerX = width / 2;
  const centerY = height / 2 + 6;
  const layout = {};
  const chapters = nodes.filter((node) => graphNodeType(node) === "章节");
  const expanded = nodes.filter((node) => graphNodeType(node) === "展开");
  const concepts = nodes.filter((node) => graphNodeType(node) === "知识点");
  const anchor = concepts.find((node) => node.name === "桩基础") ?? concepts.find((node) => node.name === "基础") ?? concepts[0] ?? nodes[0];

  if (anchor) {
    layout[anchor.id] = { x: centerX, y: centerY };
  }

  chapters.forEach((node, index) => {
    const angle = -Math.PI / 2 + (index / Math.max(1, chapters.length - 1)) * Math.PI;
    layout[node.id] = {
      x: centerX - 305 + Math.cos(angle) * 76,
      y: centerY + Math.sin(angle) * 212,
    };
  });

  concepts
    .filter((node) => node.id !== anchor?.id)
    .forEach((node, index, list) => {
      const angle = -Math.PI / 2 + (index / Math.max(1, list.length)) * Math.PI * 2;
      const weakOffset = graphWeakNames.has(node.name) ? 34 : 0;
      layout[node.id] = {
        x: centerX + Math.cos(angle) * (205 + weakOffset),
        y: centerY + Math.sin(angle) * 146,
      };
    });

  const byId = new Map(nodes.map((node) => [node.id, node]));
  expanded.forEach((node, index) => {
    const parentPosition = layout[node.expandedFrom] ?? { x: centerX, y: centerY };
    const siblingCount = expanded.filter((item) => item.expandedFrom === node.expandedFrom).length;
    const siblingIndex = expanded.filter((item) => item.expandedFrom === node.expandedFrom).findIndex((item) => item.id === node.id);
    const angle = -Math.PI / 2 + (siblingIndex / Math.max(1, siblingCount - 1)) * Math.PI;
    const parent = byId.get(node.expandedFrom);
    const side = parent?.label === "Chapter" ? 1 : parentPosition.x < centerX ? 1 : -1;
    layout[node.id] = {
      x: parentPosition.x + Math.cos(angle) * 86 + side * 96,
      y: parentPosition.y + Math.sin(angle) * 96,
    };
    if (index % 2 === 1) {
      layout[node.id].y += 16;
    }
  });

  return layout;
}

function expansionNodeId(parentId, name) {
  return `expanded:${parentId}:${name}`;
}

function DynamicKnowledgeGraph({ nodes, edges, selectedId, onSelect, onExpand }) {
  const svgWidth = 920;
  const svgHeight = 560;
  const [positions, setPositions] = useState({});
  const [view, setView] = useState({ x: 0, y: 0, zoom: 1 });
  const [drag, setDrag] = useState(null);
  const nodeKey = useMemo(() => nodes.map((node) => node.id).join("|"), [nodes]);
  const selectedNode = nodes.find((node) => node.id === selectedId);

  useEffect(() => {
    setPositions(createLayout(nodes, svgWidth, svgHeight));
  }, [nodeKey]);

  const visibleEdges = edges.filter((edge) => positions[edge.source] && positions[edge.target]);
  const relatedIds = useMemo(() => {
    const ids = new Set();
    visibleEdges.forEach((edge) => {
      if (edge.source === selectedId) {
        ids.add(edge.target);
      }
      if (edge.target === selectedId) {
        ids.add(edge.source);
      }
    });
    return ids;
  }, [visibleEdges, selectedId]);

  function pointFromEvent(event) {
    const rect = event.currentTarget.closest("svg").getBoundingClientRect();
    return {
      x: (event.clientX - rect.left - view.x) / view.zoom,
      y: (event.clientY - rect.top - view.y) / view.zoom,
    };
  }

  function runLayout() {
    const baseLayout = createLayout(nodes, svgWidth, svgHeight);
    const degree = edges.reduce((map, edge) => {
      map[edge.source] = (map[edge.source] ?? 0) + 1;
      map[edge.target] = (map[edge.target] ?? 0) + 1;
      return map;
    }, {});
    setPositions((current) => {
      const next = { ...current };
      nodes.forEach((node, index) => {
        const base = baseLayout[node.id];
        const pulse = Math.min(34, 10 + (degree[node.id] ?? 1) * 5);
        next[node.id] = {
          x: base.x + Math.cos(index * 1.7) * pulse,
          y: base.y + Math.sin(index * 1.3) * pulse,
        };
      });
      return next;
    });
  }

  function zoomBy(delta) {
    setView((current) => ({
      ...current,
      zoom: Math.min(1.7, Math.max(0.62, current.zoom + delta)),
    }));
  }

  function resetGraph() {
    setPositions(createLayout(nodes, svgWidth, svgHeight));
    setView({ x: 0, y: 0, zoom: 1 });
  }

  function focusSelected() {
    if (!selectedId || !positions[selectedId]) {
      return;
    }
    const nodePosition = positions[selectedId];
    setView({
      x: svgWidth / 2 - nodePosition.x * 1.16,
      y: svgHeight / 2 - nodePosition.y * 1.16,
      zoom: 1.16,
    });
  }

  return (
    <div className="dynamicGraph">
      <div className="graphToolbar">
        <div className="graphCanvasTitle">
          <span className="titleIcon green">
            <Network size={18} />
          </span>
          <div>
            <strong>关系画布</strong>
            <p>{nodes.length} 个节点 / {visibleEdges.length} 条关系</p>
          </div>
        </div>
        <div className="graphToolbarActions">
          <button type="button" title="自动布局" onClick={runLayout}>
            <RefreshCcw size={16} />
            自动布局
          </button>
          <button type="button" title="聚焦当前节点" disabled={!selectedNode} onClick={focusSelected}>
            <LocateFixed size={16} />
            聚焦
          </button>
          <button type="button" title="放大" onClick={() => zoomBy(0.12)}>
            <ZoomIn size={16} />
          </button>
          <button type="button" title="缩小" onClick={() => zoomBy(-0.12)}>
            <ZoomOut size={16} />
          </button>
          <button type="button" title="复位" onClick={resetGraph}>
            <RotateCcw size={16} />
          </button>
        </div>
      </div>
      <div className="graphGuideBar">
        <span>
          <MousePointer2 size={15} />
          {selectedNode?.name ?? "未选中"}
        </span>
        <span>
          <Focus size={15} />
          邻接 {relatedIds.size}
        </span>
        <span>
          <ListFilter size={15} />
          {Math.round(view.zoom * 100)}%
        </span>
      </div>
      <svg
        className="graphSvg"
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        role="img"
        aria-label="基础工程知识图谱"
        onWheel={(event) => {
          event.preventDefault();
          zoomBy(event.deltaY > 0 ? -0.08 : 0.08);
        }}
        onPointerDown={(event) => {
          if (event.target === event.currentTarget) {
            setDrag({ type: "pan", startX: event.clientX, startY: event.clientY, origin: view });
          }
        }}
        onPointerMove={(event) => {
          if (!drag) {
            return;
          }
          if (drag.type === "node") {
            const point = pointFromEvent(event);
            setPositions((current) => ({ ...current, [drag.id]: point }));
          } else {
            setView({
              ...drag.origin,
              x: drag.origin.x + event.clientX - drag.startX,
              y: drag.origin.y + event.clientY - drag.startY,
            });
          }
        }}
        onPointerUp={() => setDrag(null)}
        onPointerLeave={() => setDrag(null)}
      >
        <defs>
          <marker id="graphArrow" markerHeight="8" markerWidth="8" orient="auto" refX="7" refY="4">
            <path d="M 0 0 L 8 4 L 0 8 z" />
          </marker>
        </defs>
        <g transform={`translate(${view.x} ${view.y}) scale(${view.zoom})`}>
          {visibleEdges.map((edge, index) => {
            const source = positions[edge.source];
            const target = positions[edge.target];
            const active = selectedId === edge.source || selectedId === edge.target;
            const dimmed = selectedId && !active;
            const path = edgePath(source, target, index);
            return (
              <g className={cx("graphLink", active && "active", dimmed && "dimmed")} key={`${edge.source}-${edge.target}-${edge.relation}`}>
                <path d={path.d} markerEnd="url(#graphArrow)" />
                <text x={path.labelX} y={path.labelY}>
                  {relationText(edge.relation)}
                </text>
              </g>
            );
          })}
          {nodes.map((node) => {
            const position = positions[node.id] ?? { x: svgWidth / 2, y: svgHeight / 2 };
            const active = selectedId === node.id;
            const related = relatedIds.has(node.id);
            const nodeType = graphNodeType(node);
            const dimmed = selectedId && !active && !related;
            const radius = nodeType === "章节" ? 31 : nodeType === "展开" ? 27 : graphWeakNames.has(node.name) ? 40 : 36;
            return (
              <g
                className={cx(
                  "graphSvgNode",
                  nodeType === "章节" && "chapter",
                  nodeType === "展开" && "expanded",
                  graphWeakNames.has(node.name) && "weak",
                  active && "active",
                  related && "related",
                  dimmed && "dimmed",
                )}
                key={node.id}
                transform={`translate(${position.x} ${position.y})`}
                onPointerDown={(event) => {
                  event.stopPropagation();
                  onSelect(node.id);
                  event.currentTarget.setPointerCapture?.(event.pointerId);
                  setDrag({ type: "node", id: node.id });
                }}
                onDoubleClick={(event) => {
                  event.stopPropagation();
                  onExpand(node.id);
                }}
              >
                <title>{node.name}</title>
                <circle r={radius} />
                <text>
                  {splitNodeName(node.name).map((line, lineIndex, lines) => (
                    <tspan x="0" y={(lineIndex - (lines.length - 1) / 2) * 15} key={`${node.id}-${line}`}>
                      {line}
                    </tspan>
                  ))}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}

function LoginPage({ onLogin }) {
  const [selectedRole, setSelectedRole] = useState("student");
  const selectedUser = demoUsers.find((user) => user.role === selectedRole) ?? demoUsers[0];
  const [username, setUsername] = useState(selectedUser.username);
  const [password, setPassword] = useState(selectedUser.password);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("idle");

  useEffect(() => {
    setUsername(selectedUser.username);
    setPassword(selectedUser.password);
    setError("");
  }, [selectedUser.password, selectedUser.username]);

  async function submitLogin(event) {
    event.preventDefault();
    const matched = demoUsers.find((user) => user.username === username.trim() && user.password === password.trim());
    setStatus("loading");
    setError("");
    const result = await onLogin({ username: username.trim(), password: password.trim(), fallbackUser: matched });
    if (!result?.ok) {
      setStatus("error");
      setError(result?.message || "账号或密码不匹配。");
      return;
    }
    setStatus(result.offline ? "offline" : "success");
  }

  return (
    <main className="loginPage">
      <section className="loginPanel">
        <div className="loginBrand">
          <span>
            <GraduationCap size={28} />
          </span>
          <div>
            <p>Foundation Engineering</p>
            <h1>《基础工程》智慧学伴</h1>
          </div>
        </div>
        <p className="loginLead">学生学习、指导老师维护知识库和题库、管理员管理内容，一套入口完成强绑定。</p>
        <div className="loginRoleGrid">
          {demoUsers.map((user) => (
            <button className={cx(selectedRole === user.role && "active")} type="button" key={user.id} onClick={() => setSelectedRole(user.role)}>
              {user.role === "student" ? <UserRound size={20} /> : user.role === "teacher" ? <ShieldCheck size={20} /> : <LockKeyhole size={20} />}
              <strong>{user.roleLabel}</strong>
              <span>{user.username} / 123456</span>
            </button>
          ))}
        </div>
        <form className="loginForm" onSubmit={submitLogin}>
          <label>
            <span>账号</span>
            <input value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label>
            <span>密码</span>
            <input value={password} type="password" onChange={(event) => setPassword(event.target.value)} />
          </label>
          {error && <p className="loginError">{error}</p>}
          {status === "offline" && <p className="loginHint">后端暂未连接，已进入本机演示模式。</p>}
          <button type="submit" disabled={status === "loading"}>
            <LogIn size={18} />
            {status === "loading" ? "登录中" : "登录平台"}
          </button>
        </form>
      </section>
      <aside className="loginAside">
        <div className="loginAsideHeader">
          <BrainCircuit size={24} />
          <div>
            <strong>本次新增能力</strong>
            <p>登录、后台、RAG 上传、问答和题库联动</p>
          </div>
        </div>
        <div className="loginFeatureList">
          {(roleFeatures[selectedRole] ?? []).map((feature) => (
            <span key={feature}>
              <CheckCircle2 size={16} />
              {feature}
            </span>
          ))}
        </div>
        <div className="loginBinding">
          <Link2 size={18} />
          <p>学院、学校、题库和答疑由指导老师维护，学生端只展示绑定后的课程内容。</p>
        </div>
      </aside>
    </main>
  );
}

function Sidebar({ active, onNavigate, learningStats, currentUser }) {
  const visibleNavItems = navItems.filter((item) => item.id !== "admin" || canManageContent(currentUser));
  const profileRows = profileRowsForUser(currentUser);

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
        {visibleNavItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              className={cx("navItem", active === item.id && "active")}
              type="button"
              aria-label={item.label}
              title={item.label}
              key={item.id}
              onClick={() => onNavigate(item.id)}
            >
              <Icon size={21} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <RankPanel compact rank={learningStats.rank} />

      <section className="studentCard" aria-label="学生信息">
        <div className="studentAvatar">
          <UserRound size={26} />
        </div>
        <div className="bindingBadge">
          <Link2 size={13} />
          指导老师强绑定
        </div>
        <div className="studentRows">
          {profileRows.map((item) => (
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

function RankPanel({ compact = false, rank = rankInfo }) {
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
        <span>{rank.level}</span>
        <strong>{rank.score}</strong>
      </div>
      {!compact && (
        <p className="rankTip">
          当前段位：{rank.level}，距离{rank.next}还差一点点。
        </p>
      )}
      <div className="rankLadder" aria-label="学习段位阶梯">
        {["青铜", "白银", "黄金", "白金", "王者"].map((level) => (
          <span className={cx(level === rank.level && "active")} key={level}>
            {level}
          </span>
        ))}
      </div>
    </section>
  );
}

function Header({ query, setQuery, onNavigate, currentUser, onLogout }) {
  const [openPanel, setOpenPanel] = useState("");
  const isManager = canManageContent(currentUser);

  function togglePanel(panel) {
    setOpenPanel((current) => (current === panel ? "" : panel));
  }

  function jumpTo(page) {
    onNavigate(page);
    setOpenPanel("");
  }

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
        <button className={cx("iconButton", openPanel === "notice" && "active")} type="button" aria-label="通知" onClick={() => togglePanel("notice")}>
          <Bell size={20} />
          <span className="dot" />
        </button>
        <button className={cx("iconButton", openPanel === "help" && "active")} type="button" aria-label="帮助" onClick={() => togglePanel("help")}>
          <CircleHelp size={20} />
        </button>
        <button className={cx("userChip", openPanel === "user" && "active")} type="button" onClick={() => togglePanel("user")}>
          <span className="avatar">
            <UserRound size={18} />
          </span>
          <span>{currentUser?.name ?? "未登录"}</span>
          <ChevronDown size={16} />
        </button>
        {openPanel && (
          <div className="topPopover" role="dialog" aria-label="快捷面板">
            {openPanel === "notice" && (
              <>
                <strong>学习提醒</strong>
                <p>沉降计算和桩侧阻力本周建议复习，已生成 8 道强化题。</p>
                <button type="button" onClick={() => jumpTo("practice")}>
                  去练习中心
                </button>
              </>
            )}
            {openPanel === "help" && (
              <>
                <strong>学习助手</strong>
                <p>可以围绕教材原文、规范条文、章节练习继续提问。</p>
                <button type="button" onClick={() => jumpTo("qa")}>
                  打开智能问答
                </button>
              </>
            )}
            {openPanel === "user" && (
              <>
                <strong>{currentUser?.name ?? "未登录"}</strong>
                <p>
                  {currentUser?.college ?? "土木工程学院"} · {currentUser?.roleLabel ?? "学生"} · 指导老师
                  {currentUser?.mentor ?? "李老师"}已绑定
                </p>
                <div className="popoverActions">
                  <button type="button" onClick={() => jumpTo("report")}>
                    学习报告
                  </button>
                  {isManager && (
                    <button type="button" onClick={() => jumpTo("admin")}>
                      后台管理
                    </button>
                  )}
                  <button type="button" onClick={onLogout}>
                    <LogOut size={15} />
                    退出
                  </button>
                </div>
              </>
            )}
          </div>
        )}
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

function Hero({ onNavigate, courseManifest, learningStats }) {
  const currentChapter = currentCourseChapter(courseManifest);
  const completedChapters = learningStats.completedChapters;
  const totalChapters = courseManifest?.totalChapters ?? courseChapters(courseManifest).length;
  const percent = learningStats.progressPercent;
  const averageScore = learningStats.averageScore;

  return (
    <section className="heroPanel">
      <div className="heroCopy">
        <p className="eyebrow">学习概况</p>
        <h1>课程总览</h1>
        <p className="heroText">系统学习地基基础知识，掌握工程分析与设计方法。</p>
        <div className="heroStats">
          <div className="progressRing" style={{ "--progress": `${percent}%` }} aria-label={`学习进度 ${percent}%`}>
            <span>{percent}%</span>
          </div>
          <Metric label={learningStats.hasAttempts ? "已练习" : "已完成"} value={completedChapters} suffix={` / ${totalChapters} 章`} />
          <Metric label="平均分" value={averageScore} suffix=" 分" />
        </div>
        <div className="heroActions">
          <button className="primaryButton" type="button" onClick={() => onNavigate("textbook", { chapter: currentChapter.title })}>
            <Play size={17} fill="currentColor" />
            继续学习{currentChapter.title}
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

function WeakPanel({ onNavigate, courseManifest, learningStats }) {
  const currentChapter = currentCourseChapter(courseManifest);
  const quickChapters = courseChapters(courseManifest);
  const panelWeakPoints = learningStats.weakPoints ?? weakPoints;

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
          {panelWeakPoints.map((item) => (
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
          <button type="button" onClick={() => onNavigate("textbook", { chapter: currentChapter.title })}>
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
          {quickChapters.map((chapter) => (
            <button
              className={cx("chapterChip", chapter.id === currentChapter.id && "current")}
              type="button"
              key={chapter.id}
              onClick={() => onNavigate("textbook", { chapter: chapter.title })}
            >
              {chapter.title}
            </button>
          ))}
        </div>
      </section>
    </aside>
  );
}

function Overview({ onNavigate, courseManifest, learningStats, exerciseBank: mergedExerciseBank }) {
  const graphSummary = useJsonAsset("/knowledge/build_summary.json", null);
  const cards = moduleCards.map((card) => ({
    ...card,
    meta: moduleMeta(card.id, { courseManifest, graphSummary, exerciseBank: mergedExerciseBank }),
  }));

  return (
    <div className="overviewLayout">
      <div className="mainStack">
        <Hero onNavigate={onNavigate} courseManifest={courseManifest} learningStats={learningStats} />
        <section className="moduleGrid" aria-label="平台模块入口">
          {cards.map((card) => (
            <ModuleCard card={card} key={card.id} onNavigate={onNavigate} />
          ))}
        </section>
      </div>
      <WeakPanel onNavigate={onNavigate} courseManifest={courseManifest} learningStats={learningStats} />
    </div>
  );
}

function TextbookPage({ onNavigate, initialChapter, courseManifest }) {
  const tabs = ["章节导读", "重点公式", "图表解释", "案例关联", "章节练习"];
  const courseChapterTitles = chapterTitles(courseManifest);
  const manifestChapter = currentCourseChapter(courseManifest);
  const initialTitle = courseChapterTitles.includes(initialChapter) ? initialChapter : manifestChapter.title;
  const [activeChapter, setActiveChapter] = useState(initialTitle);
  const [activeTab, setActiveTab] = useState("重点公式");
  const [showDerivation, setShowDerivation] = useState(false);
  const activeContent = chapterStudyContent[activeChapter] ?? chapterStudyContent.桩基础;
  const chapterResources = relatedResourcesForChapter(activeChapter);
  const chapterCases = relatedCasesForChapter(activeChapter);
  const tabCopy = {
    章节导读: "先把章节目标、核心概念和适用场景串起来，再进入公式和案例。",
    重点公式: `本专题核心公式是“${activeContent.formulaName}”，重点看适用条件、参数含义和计算边界。`,
    图表解释: activeContent.diagram,
    案例关联: activeContent.caseText,
    章节练习: "围绕本章薄弱点生成练习，完成后回到学习报告查看掌握度变化。",
  };

  useEffect(() => {
    const nextChapter = courseChapterTitles.includes(initialChapter) ? initialChapter : manifestChapter.title;
    setActiveChapter(nextChapter);
  }, [courseChapterTitles.join("|"), initialChapter, manifestChapter.title]);

  useEffect(() => {
    setShowDerivation(false);
  }, [activeChapter]);

  return (
    <section className="pagePanel">
      <PageHeader
        label="教材学习"
        title="章节学习工作台"
        desc="每个章节独立进入，按导读、公式、图表、案例和练习组织。"
      />
      <div className="studyLayout">
        <aside className="chapterList">
          {courseChapters(courseManifest).map((chapter) => (
            <button
              type="button"
              aria-label={`第${chapter.number}章 ${chapter.title}`}
              className={cx(activeChapter === chapter.title && "selected")}
              key={chapter.id}
              onClick={() => setActiveChapter(chapter.title)}
            >
              <span>{chapter.number}</span>
              {chapter.title}
            </button>
          ))}
        </aside>
        <div className="readingPane">
          <div className="tabBar">
            {tabs.map((tab) => (
              <button className={cx(activeTab === tab && "active")} type="button" key={tab} onClick={() => setActiveTab(tab)}>
                {tab}
              </button>
            ))}
          </div>
          <article className="readingContent">
            <p className="eyebrow">{chapterNumberLabel(courseManifest, activeChapter)}</p>
            <h2>{activeChapter}</h2>
            <p>{activeContent.intro} 学习时建议把公式、土层条件和工程案例放在一起理解。</p>
            <div className="learningHint">
              <strong>{activeTab}</strong>
              <span>{tabCopy[activeTab]}</span>
            </div>
            <div className="formulaBox">
              <span>{activeContent.formulaName}</span>
              <strong>{activeContent.formula}</strong>
              <button type="button" onClick={() => setShowDerivation((value) => !value)}>
                {showDerivation ? "收起推导" : "展开推导"}
              </button>
            </div>
            {showDerivation && (
              <div className="derivationBox">
                <strong>推导说明</strong>
                <p>{activeContent.derivation}</p>
              </div>
            )}
            {activeTab === "章节练习" && (
              <button className="inlineActionButton" type="button" onClick={() => onNavigate("practice", { chapter: activeChapter })}>
                进入本章练习
              </button>
            )}
            <img className="contentImage" src={foundationSection} alt="桩基础与土层剖面" />
          </article>
        </div>
        <aside className="resourceRail">
          <h3>关联资料</h3>
          <div className="railList">
            {chapterResources.map((item) => (
              <button
                className="railMiniCard"
                type="button"
                key={item.title}
                onClick={() => onNavigate("resources", { resourceTitle: item.title })}
              >
                <span>{item.type}</span>
                <strong>{item.code}</strong>
                <em>{item.link}</em>
              </button>
            ))}
          </div>
          <h3>相关案例</h3>
          <div className="railList">
            {chapterCases.map((item) => (
              <button className="railMiniCard case" type="button" key={item.title} onClick={() => onNavigate("cases", { caseTitle: item.title })}>
                <span>{item.status}</span>
                <strong>{item.tag}</strong>
                <em>{item.title}</em>
              </button>
            ))}
          </div>
        </aside>
      </div>
    </section>
  );
}

function GraphPage({ initialNode }) {
  const summaryState = useJsonAssetState("/knowledge/build_summary.json", null);
  const summary = summaryState.data;
  const graphState = useJsonAssetState("/knowledge/graph_preview.json", { nodes: [], edges: [] });
  const graph = graphState.data;
  const chunkState = useJsonAssetState("/knowledge/chunks.json", []);
  const chunks = chunkState.data;
  const centerNode = graph.nodes.find((node) => node.name === "第3章 桩基础") ?? graph.nodes.find((node) => node.label === "Chapter");
  const [expandedIds, setExpandedIds] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [nodeQuery, setNodeQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("全部");
  const [relationFilter, setRelationFilter] = useState("全部");

  const graphNodes = useMemo(() => {
    const chapterNodes = graph.nodes.filter((node) => node.label === "Chapter").slice(0, 7);
    const conceptNodes = graph.nodes.filter((node) => node.label === "Concept").slice(0, 12);
    const baseNodes = [...chapterNodes, ...conceptNodes];
    const existingIds = new Set(baseNodes.map((node) => node.id));
    const byId = new Map(baseNodes.map((node) => [node.id, node]));
    const expandedNodes = [];

    expandedIds.forEach((id) => {
      const parent = byId.get(id);
      const children = graphExpansionMap[parent?.name] ?? [];
      children.forEach((name) => {
        const childId = expansionNodeId(id, name);
        if (!existingIds.has(childId)) {
          existingIds.add(childId);
          expandedNodes.push({
            id: childId,
            label: "Concept",
            name,
            definition: `“${name}”是从“${parent.name}”展开出的关联知识点，可继续作为教材检索和图谱浏览入口。`,
            expandedFrom: id,
          });
        }
      });
    });

    return [...baseNodes, ...expandedNodes];
  }, [graph, expandedIds]);
  const graphNodeIds = useMemo(() => new Set(graphNodes.map((node) => node.id)), [graphNodes]);
  const graphEdges = useMemo(() => {
    const baseEdges = graph.edges.filter((edge) => graphNodeIds.has(edge.source) && graphNodeIds.has(edge.target));
    const expandedEdges = [];
    const byId = new Map(graphNodes.map((node) => [node.id, node]));

    expandedIds.forEach((id) => {
      const parent = byId.get(id);
      const children = graphExpansionMap[parent?.name] ?? [];
      children.forEach((name) => {
        const childId = expansionNodeId(id, name);
        if (graphNodeIds.has(childId)) {
          expandedEdges.push({ source: id, target: childId, relation: "展开" });
        }
      });
    });

    return [...baseEdges, ...expandedEdges];
  }, [graph.edges, graphNodeIds, graphNodes, expandedIds]);

  const relationOptions = useMemo(() => ["全部", ...Array.from(new Set(graphEdges.map((edge) => edge.relation)))], [graphEdges]);
  const degreeById = useMemo(
    () =>
      graphEdges.reduce((map, edge) => {
        map[edge.source] = (map[edge.source] ?? 0) + 1;
        map[edge.target] = (map[edge.target] ?? 0) + 1;
        return map;
      }, {}),
    [graphEdges],
  );
  const filteredGraph = useMemo(() => {
    const query = nodeQuery.trim().toLowerCase();
    const typeMatches = (node) => typeFilter === "全部" || graphNodeType(node) === typeFilter;
    const relationMatches = (edge) => relationFilter === "全部" || edge.relation === relationFilter;
    const matchedIds = new Set();

    graphNodes.forEach((node) => {
      const haystack = `${node.name}${node.definition ?? ""}${graphNodeType(node)}`.toLowerCase();
      if (!query || haystack.includes(query)) {
        matchedIds.add(node.id);
      }
    });

    const contextIds = new Set(matchedIds);
    if (query) {
      graphEdges.forEach((edge) => {
        if (matchedIds.has(edge.source) || matchedIds.has(edge.target)) {
          contextIds.add(edge.source);
          contextIds.add(edge.target);
        }
      });
    }

    let visibleIds = new Set(
      graphNodes.filter((node) => typeMatches(node) && (!query || contextIds.has(node.id))).map((node) => node.id),
    );

    if (relationFilter !== "全部") {
      const relationIds = new Set();
      graphEdges.filter(relationMatches).forEach((edge) => {
        relationIds.add(edge.source);
        relationIds.add(edge.target);
      });
      visibleIds = new Set(Array.from(visibleIds).filter((id) => relationIds.has(id)));
    }

    return {
      nodes: graphNodes.filter((node) => visibleIds.has(node.id)),
      edges: graphEdges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target) && relationMatches(edge)),
      matchedIds,
    };
  }, [graphEdges, graphNodes, nodeQuery, relationFilter, typeFilter]);
  const previewNodes = filteredGraph.nodes.filter((node) => node.label === "Concept");
  const selected =
    filteredGraph.nodes.find((node) => node.id === selectedId) ??
    previewNodes.find((node) => node.name === "桩侧阻力") ??
    filteredGraph.nodes[0] ??
    centerNode ??
    graphNodes[0];
  const selectedChildren = graphExpansionMap[selected?.name] ?? [];
  const isExpanded = selected ? expandedIds.includes(selected.id) : false;
  const canExpand = selectedChildren.length > 0;
  const selectedRelations = useMemo(() => {
    if (!selected) {
      return [];
    }
    const byId = new Map(graphNodes.map((node) => [node.id, node]));
    return graphEdges
      .filter((edge) => edge.source === selected.id || edge.target === selected.id)
      .map((edge) => {
        const neighborId = edge.source === selected.id ? edge.target : edge.source;
        return {
          ...edge,
          neighbor: byId.get(neighborId)?.name ?? "未知节点",
          direction: edge.source === selected.id ? "→" : "←",
        };
      });
  }, [graphEdges, graphNodes, selected]);
  const sourceSnippets = useMemo(() => searchChunks(chunks, selected?.name ?? "", 3), [chunks, selected?.name]);
  const isGraphLoading = graphState.status === "loading" && !graph.nodes.length;

  useEffect(() => {
    if (!initialNode) {
      return;
    }
    const target = graphNodes.find((node) => node.name === initialNode);
    if (target) {
      setNodeQuery("");
      setTypeFilter("全部");
      setRelationFilter("全部");
      setSelectedId(target.id);
    }
  }, [graphNodes, initialNode]);

  function expandSelected(id = selected?.id) {
    if (!id || expandedIds.includes(id)) {
      return;
    }
    const node = graphNodes.find((item) => item.id === id);
    if (!graphExpansionMap[node?.name]?.length) {
      return;
    }
    setExpandedIds((items) => [...items, id]);
  }

  function focusNodeByName(name) {
    const node = graphNodes.find((item) => item.name === name);
    if (!node) {
      return;
    }
    setNodeQuery("");
    setTypeFilter("全部");
    setRelationFilter("全部");
    setSelectedId(node.id);
  }

  function resetFilters() {
    setNodeQuery("");
    setTypeFilter("全部");
    setRelationFilter("全部");
  }

  return (
    <section className="pagePanel">
      <PageHeader label="知识图谱" title="教材知识图谱工作台" desc="完整知识库来自教材抽取，当前画布展示可交互演示子图。" />
      {(summaryState.status === "loading" || isGraphLoading || (chunkState.status === "loading" && !chunks.length)) && (
        <LoadingSkeleton title="正在加载图谱子图和教材索引" rows={3} />
      )}
      {summary && (
        <div className="knowledgeStats" aria-label="知识库统计">
          <Metric label="完整节点" value={summary.graph_nodes} />
          <Metric label="完整关系" value={summary.graph_edges} />
          <Metric label="当前子图" value={`${graph.nodes.length}/${graph.edges.length}`} />
          <Metric label="教材切块" value={summary.chunks} />
        </div>
      )}
      <div className="graphWorkbench">
        <aside className="graphControlRail" aria-label="知识图谱控制">
          <section className="graphRailBlock">
            <div className="railHeading">
              <h3>图谱导航</h3>
              <button type="button" title="清空筛选" onClick={resetFilters}>
                <RotateCcw size={15} />
              </button>
            </div>
            <label className="graphSearchBox">
              <Search size={17} />
              <input value={nodeQuery} onChange={(event) => setNodeQuery(event.target.value)} placeholder="搜索节点" />
            </label>
            <div className="graphRailStats">
              <div>
                <strong>{filteredGraph.nodes.length}</strong>
                <span>当前节点</span>
              </div>
              <div>
                <strong>{filteredGraph.edges.length}</strong>
                <span>当前关系</span>
              </div>
            </div>
          </section>

          <section className="graphRailBlock">
            <h3>节点类型</h3>
            <div className="chipGrid">
              {graphTypeOptions.map((type) => (
                <button className={cx(typeFilter === type && "active")} type="button" key={type} onClick={() => setTypeFilter(type)}>
                  {type}
                </button>
              ))}
            </div>
          </section>

          <section className="graphRailBlock">
            <h3>关系类型</h3>
            <div className="relationChips">
              {relationOptions.map((relation) => (
                <button
                  className={cx(relationFilter === relation && "active")}
                  type="button"
                  key={relation}
                  onClick={() => setRelationFilter(relation)}
                >
                  {relation === "全部" ? relation : relationText(relation)}
                </button>
              ))}
            </div>
          </section>

          <section className="graphRailBlock">
            <h3>快速聚焦</h3>
            <div className="quickNodeList">
              {graphFocusNames.map((name) => {
                const node = graphNodes.find((item) => item.name === name);
                return (
                  <button className={cx(selected?.name === name && "active")} type="button" key={name} disabled={!node} onClick={() => focusNodeByName(name)}>
                    <span>{name}</span>
                    <small>{node ? `${degreeById[node.id] ?? 0} 关系` : "未接入"}</small>
                  </button>
                );
              })}
            </div>
          </section>
        </aside>

        <DynamicKnowledgeGraph
          nodes={filteredGraph.nodes}
          edges={filteredGraph.edges}
          selectedId={selected?.id}
          onSelect={setSelectedId}
          onExpand={expandSelected}
        />
        <aside className="inspector graphInspector">
          <div className="inspectorKicker">
            <span>{selected ? graphNodeType(selected) : "节点"}</span>
            <small>{selectedRelations.length} 条关系</small>
          </div>
          <h3>{selected?.name ?? "教材实体"}</h3>
          <p>{selected?.definition ?? "该实体来自教材章节、定义句或原文切块，可与章节、公式、图片和表格建立来源关系。"}</p>
          <div className="inspectorActions">
            <button type="button" disabled={!canExpand || isExpanded} onClick={() => expandSelected()}>
              {isExpanded ? "已展开" : canExpand ? "展开节点" : "暂无下级"}
            </button>
          </div>
          <dl>
            <div>
              <dt>来源节点</dt>
              <dd>{centerNode?.name ?? "《基础工程》"}</dd>
            </div>
            <div>
              <dt>连接关系</dt>
              <dd>{selectedRelations.length ? selectedRelations.slice(0, 3).map((item) => `${relationText(item.relation)} ${item.neighbor}`).join("、") : "暂无直接关系"}</dd>
            </div>
            <div>
              <dt>可展开关系</dt>
              <dd>{selectedChildren.length ? selectedChildren.join("、") : "当前节点无预置下级关系"}</dd>
            </div>
            <div>
              <dt>教材索引</dt>
              <dd>{summary ? `${summary.sections} 个标题，${summary.images} 个图片引用` : "正在读取"}</dd>
            </div>
          </dl>
          <div className="sourceSnippetList">
            <h4>教材依据</h4>
            {sourceSnippets.length ? (
              sourceSnippets.map((snippet) => {
                const text = snippet.text.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
                return (
                  <article key={snippet.id}>
                    <strong>{snippet.heading_path || "教材正文"}</strong>
                    <p>{text.length > 112 ? `${text.slice(0, 112)}...` : text}</p>
                  </article>
                );
              })
            ) : (
              <p className="emptySnippet">正在匹配教材原文</p>
            )}
          </div>
        </aside>
      </div>
    </section>
  );
}

function QAPage({ ragChunks = [], qaConfig = defaultQaConfig, apiToken, backendStatus = "offline" }) {
  const [mode, setMode] = useState("教材问答");
  const [question, setQuestion] = useState("桩侧阻力是如何产生的？影响它的主要因素有哪些？");
  const [draftQuestion, setDraftQuestion] = useState(question);
  const [searchCount, setSearchCount] = useState(1);
  const [aiAnswer, setAiAnswer] = useState("");
  const [serverSources, setServerSources] = useState([]);
  const [aiStatus, setAiStatus] = useState("idle");
  const [aiError, setAiError] = useState("");
  const baseChunks = [];
  const chunks = useMemo(() => [...ragChunks], [ragChunks]);
  const modes = ["教材问答", "规范问答", "学习辅导"];
  const localResults = useMemo(() => searchChunks(chunks, question, 4), [chunks, question]);
  const results = serverSources.length ? serverSources : localResults;
  const answer = buildLocalRagAnswer(question, mode, results, qaConfig);
  const isCorpusLoading = false;

  useEffect(() => {
    setAiAnswer("");
    setServerSources([]);
    setAiStatus("idle");
    setAiError("");
  }, [mode, question]);

  async function askServer(nextQuestion, useLlm) {
    if (!apiToken) {
      throw new Error("NO_SERVER_TOKEN");
    }
    const data = await apiRequest("/qa", {
      method: "POST",
      token: apiToken,
      body: { question: nextQuestion, mode, useLlm },
    });
    setServerSources(data.sources ?? []);
    setAiAnswer(data.answer ?? "");
    return data;
  }

  async function runSearch() {
    const nextQuestion = draftQuestion.trim() || "桩侧阻力是如何产生的？";
    setQuestion(nextQuestion);
    setDraftQuestion(nextQuestion);
    setSearchCount((count) => count + 1);
    setAiStatus("loading");
    setAiError("");
    try {
      const data = await askServer(nextQuestion, false);
      setAiStatus("success");
      setAiError(data.usedLlm ? "服务端大模型生成" : "服务端 RAG 检索回答");
    } catch {
      setServerSources([]);
      setAiAnswer("");
      setAiStatus("idle");
      setAiError(apiToken ? "服务端暂不可用，已使用本地教材索引检索。" : "");
    }
  }

  async function generateAiAnswer() {
    const nextQuestion = draftQuestion.trim() || "桩侧阻力是如何产生的？";
    const nextResults = searchChunks(chunks, nextQuestion, 4);
    setQuestion(nextQuestion);
    setDraftQuestion(nextQuestion);
    setSearchCount((count) => count + 1);
    setAiStatus("loading");
    setAiError("");
    try {
      const data = await askServer(nextQuestion, true);
      setAiStatus("success");
      if (data.usedLlm) {
        setAiError("服务端大模型生成 · 已结合 RAG 检索片段");
        return;
      }
      try {
        const responseText = await callFreeAi(buildAiPrompt(nextQuestion, mode, data.sources?.length ? data.sources : nextResults, qaConfig));
        setAiAnswer(responseText);
        setAiError("浏览器端免费 AI 生成 · 已结合服务器 RAG 片段");
      } catch {
        setAiError("免费 AI 需首次授权或暂不可用，已返回服务器 RAG 检索答案");
      }
    } catch {
      try {
        const responseText = await callFreeAi(buildAiPrompt(nextQuestion, mode, nextResults, qaConfig));
        setAiAnswer(responseText);
        setAiStatus("success");
        setAiError("浏览器端免费 AI 生成 · 服务端暂不可用");
      } catch {
        setAiAnswer("");
        setAiStatus("error");
        setAiError("大模型暂时没有返回，已保留本地教材检索结果。");
      }
    }
  }

  return (
    <section className="pagePanel">
      <PageHeader label="智能问答" title="RAG 检索问答" desc="已接入《基础工程》教材切块和教师上传知识库，先检索引用，再生成回答。" />
      <div className="teacherNotice">
        <Link2 size={17} />
        当前模式：{mode} · {backendStatus === "online" ? "服务器 RAG 已连接，教材切块在私有知识库中检索" : "服务器暂未连接"}
      </div>
      {isCorpusLoading && <LoadingSkeleton title="正在准备 RAG 教材索引" rows={3} />}
      <div className="qaShell">
        <div className="segmented">
          {modes.map((item) => (
            <button className={cx(mode === item && "active")} type="button" key={item} onClick={() => setMode(item)}>
              {item}
            </button>
          ))}
        </div>
        <div className="chatArea">
          <div className="bubble user">{question}</div>
          <div className="bubble assistant">
            <Bot size={20} />
            <div>
              <p>{aiAnswer || answer}</p>
              <span>
                {aiStatus === "success"
                  ? aiError || "已结合 RAG 检索片段生成"
                  : aiStatus === "loading"
                    ? "正在请求服务端问答..."
                    : aiError || `引用：${results[0]?.heading_path ?? "教材索引"} ${results[0] ? `L${results[0].source_line}` : ""}`}
              </span>
            </div>
          </div>
          <div className="ragFlow" aria-label="RAG 流程">
            {["提问", "检索教材/上传库", "抽取引用", "生成回答"].map((step, index) => (
              <span key={step}>
                <em>{index + 1}</em>
                {step}
              </span>
            ))}
          </div>
          <div className="sourceList">
            {results.map((item) => (
              <article className="sourceItem" key={item.id}>
                <strong>{item.heading_path}</strong>
                <p>{item.text.replace(/\s+/g, " ").slice(0, 150)}</p>
                <span>
                  来源行 {item.source_line} · {item.kind}
                  {item.documentTitle ? ` · ${item.documentTitle}` : ""}
                </span>
              </article>
            ))}
          </div>
        </div>
        <label className="askBox">
          <input
            value={draftQuestion}
            onChange={(event) => setDraftQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                runSearch();
              }
            }}
            placeholder={`继续使用${mode}提问…`}
          />
          <button type="button" onClick={runSearch}>
            检索{searchCount > 1 ? ` ${searchCount - 1}` : ""}
          </button>
          <button className="secondaryAskButton" type="button" onClick={generateAiAnswer} disabled={aiStatus === "loading"}>
            {aiStatus === "loading" ? "生成中" : "AI生成"}
          </button>
        </label>
      </div>
    </section>
  );
}

function CasesPage({ initialCaseTitle }) {
  const [selectedCase, setSelectedCase] = useState(caseItems[0]);

  useEffect(() => {
    const nextCase = caseItems.find((item) => item.title === initialCaseTitle);
    if (nextCase) {
      setSelectedCase(nextCase);
    }
  }, [initialCaseTitle]);

  return (
    <section className="pagePanel">
      <PageHeader label="工程案例" title="案例库" desc="把工程问题、教材章节、关联资料和思考题串起来。" />
      <div className="caseGrid">
        {caseItems.map((item) => (
          <article className={cx("caseCard", selectedCase.title === item.title && "active")} key={item.title}>
            <span>{item.tag}</span>
            <h3>{item.title}</h3>
            <p>{item.problem}</p>
            <button type="button" onClick={() => setSelectedCase(item)}>
              {selectedCase.title === item.title ? "正在查看" : "查看详情"}
            </button>
          </article>
        ))}
      </div>
      <section className="detailPanel">
        <strong>{selectedCase.title}</strong>
        <p>{selectedCase.problem}</p>
        <p>{selectedCase.lesson}</p>
        <div className="detailTags">
          <span>{selectedCase.status}</span>
          <span>{selectedCase.tag}</span>
          {(selectedCase.relatedChapters ?? []).map((chapter) => (
            <span key={chapter}>{chapter}</span>
          ))}
        </div>
      </section>
    </section>
  );
}

function ResourcesPage({ initialResourceTitle }) {
  const [selectedResource, setSelectedResource] = useState(resources[0]);
  const [typeFilter, setTypeFilter] = useState("全部");
  const [resourceQuery, setResourceQuery] = useState("");
  const detailRef = useRef(null);
  const resourceTypes = useMemo(() => ["全部", ...Array.from(new Set(resources.map((item) => item.type)))], []);
  const standardCount = resources.filter((item) => item.type.includes("标准") || item.type.includes("规范") || item.type.includes("规程")).length;
  const filteredResources = useMemo(() => {
    const cleanQuery = resourceQuery.trim();
    return resources.filter((item) => {
      const typeMatched = typeFilter === "全部" || item.type === typeFilter;
      const queryMatched =
        !cleanQuery ||
        resultMatches(
          cleanQuery,
          item.title,
          item.code,
          item.shortCode,
          item.type,
          item.level,
          item.link,
          item.source,
          item.status,
          ...(item.relatedChapters ?? []),
          ...(item.keyTopics ?? []),
          ...(item.clauses ?? []),
          ...(item.useCases ?? []),
        );
      return typeMatched && queryMatched;
    });
  }, [resourceQuery, typeFilter]);

  useEffect(() => {
    const nextResource = resources.find((item) => item.title === initialResourceTitle);
    if (nextResource) {
      setSelectedResource(nextResource);
    }
  }, [initialResourceTitle]);

  useEffect(() => {
    if (!filteredResources.length) {
      return;
    }
    if (!filteredResources.some((item) => item.title === selectedResource.title)) {
      setSelectedResource(filteredResources[0]);
    }
  }, [filteredResources, selectedResource.title]);

  function openResourceDetail(item, shouldScroll = false) {
    setSelectedResource(item);
    window.requestAnimationFrame(() => {
      const detail = detailRef.current;
      if (!detail) {
        return;
      }
      const narrowScreen = window.matchMedia?.("(max-width: 980px)")?.matches;
      detail.focus({ preventScroll: true });
      if (shouldScroll || narrowScreen) {
        detail.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  }

  return (
    <section className="pagePanel">
      <PageHeader label="关联资料" title="规范资料库" desc="按教材参考文献和正文提及的规范整理，帮助学生从章节直接定位到设计依据、适用范围和重点条文方向。" />
      <div className="resourceSummary">
        <article>
          <strong>{resources.length}</strong>
          <span>条资料</span>
        </article>
        <article>
          <strong>{standardCount}</strong>
          <span>规范/标准/规程</span>
        </article>
        <article>
          <strong>7</strong>
          <span>章课程关联</span>
        </article>
        <p>页面展示的是课程引用版本，不替代正式规范查新；教师可在后台继续上传条文摘录和课堂讲义。</p>
      </div>

      <div className="resourceControls">
        <div className="segmented resourceTypeFilter">
          {resourceTypes.map((type) => (
            <button className={cx(typeFilter === type && "active")} type="button" key={type} onClick={() => setTypeFilter(type)}>
              {type}
            </button>
          ))}
        </div>
        <label className="resourceSearch">
          <Search size={17} />
          <input value={resourceQuery} onChange={(event) => setResourceQuery(event.target.value)} placeholder="搜索规范编号、章节、关键词…" />
        </label>
      </div>

      <div className="resourceLibrary">
        <div className="tablePanel resourceList">
          {filteredResources.map((item) => (
            <article
              className={cx("resourceRow", selectedResource.title === item.title && "active")}
              key={item.title}
              onClick={() => openResourceDetail(item)}
            >
              <span className="typePill">{item.type}</span>
              <div>
                <strong>{item.title}</strong>
                <p>{item.link}</p>
                <small>{(item.keyTopics ?? []).slice(0, 4).join(" · ")}</small>
              </div>
              <em>{item.code}</em>
              <button
                className="resourceDetailButton"
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  openResourceDetail(item, true);
                }}
              >
                <FileText size={15} />
                {selectedResource.title === item.title ? "正在查看" : "查看详情"}
              </button>
            </article>
          ))}
          {!filteredResources.length && <p className="emptySearch">没有匹配的规范资料。</p>}
        </div>

        <section className="resourceDetail" ref={detailRef} tabIndex={-1} aria-label={`${selectedResource.title} 详情`}>
          <div className="resourceDetailHeader">
            <span className="typePill">{selectedResource.type}</span>
            <h2>{selectedResource.title}</h2>
            <strong>{selectedResource.code}</strong>
            <p>{selectedResource.status}</p>
          </div>

          <div className="resourceMetaGrid">
            <div>
              <span>资料层级</span>
              <strong>{selectedResource.level}</strong>
            </div>
            <div>
              <span>引用版本</span>
              <strong>{selectedResource.version}</strong>
            </div>
            <div>
              <span>编制/发布单位</span>
              <strong>{selectedResource.organization}</strong>
            </div>
            <div>
              <span>出版社/年份</span>
              <strong>
                {selectedResource.publisher} · {selectedResource.publishedYear}
              </strong>
            </div>
          </div>

          <div className="resourceSection">
            <h3>课程用途</h3>
            <p>{selectedResource.link}</p>
            <div className="detailTags">
              {(selectedResource.relatedChapters ?? []).map((chapter) => (
                <span key={chapter}>{chapter}</span>
              ))}
            </div>
          </div>

          <div className="resourceSection">
            <h3>重点条文方向</h3>
            <ul className="resourceBulletList">
              {(selectedResource.clauses ?? []).map((clause) => (
                <li key={clause}>{clause}</li>
              ))}
            </ul>
          </div>

          <div className="resourceSection twoColumn">
            <div>
              <h3>关键词</h3>
              <div className="detailTags">
                {(selectedResource.keyTopics ?? []).map((topic) => (
                  <span key={topic}>{topic}</span>
                ))}
              </div>
            </div>
            <div>
              <h3>适用场景</h3>
              <ul className="resourceBulletList compactList">
                {(selectedResource.useCases ?? []).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="resourceSource">
            <span>来源</span>
            <p>{selectedResource.source}</p>
          </div>
        </section>
      </div>
    </section>
  );
}

function PracticePage({ initialChapter, initialExerciseId, onRecordAttempt, exerciseBank: providedExerciseBank, customExercises = [] }) {
  const loadedExerciseState = useJsonAssetState("/knowledge/exercises.json", { summary: { total: 0, thinking: 0, exercise: 0, chapters: [] }, exercises: [] });
  const exerciseBank = useMemo(
    () => providedExerciseBank ?? mergeExerciseBank(loadedExerciseState.data, customExercises),
    [customExercises, loadedExerciseState.data, providedExerciseBank],
  );
  const rubricState = useJsonAssetState("/knowledge/exercise_rubrics.json", { items: {} });
  const rubricBank = rubricState.data;
  const exercises = exerciseBank.exercises ?? [];
  const summary = exerciseBank.summary ?? {};
  const exerciseChapters = useMemo(() => {
    if (summary.chapters?.length) {
      return summary.chapters;
    }
    return Array.from(new Set(exercises.map((item) => item.chapter).filter(Boolean)));
  }, [exercises, summary.chapters]);
  const [chapterFilter, setChapterFilter] = useState("全部");
  const [typeFilter, setTypeFilter] = useState("全部");
  const [difficultyFilter, setDifficultyFilter] = useState("全部");
  const [keyword, setKeyword] = useState("");
  const [selectedExerciseId, setSelectedExerciseId] = useState("");
  const [answer, setAnswer] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const chapterKey = exerciseChapters.join("|");

  useEffect(() => {
    const matchedChapter = matchExerciseChapter(exerciseChapters, initialChapter);
    if (matchedChapter !== "全部") {
      setChapterFilter(matchedChapter);
    }
  }, [chapterKey, initialChapter]);

  useEffect(() => {
    if (!initialExerciseId || !exercises.length) {
      return;
    }
    const targetExercise = exercises.find((exercise) => exercise.id === initialExerciseId);
    if (!targetExercise) {
      return;
    }
    setChapterFilter(targetExercise.chapter);
    setTypeFilter("全部");
    setDifficultyFilter("全部");
    setKeyword("");
    setSelectedExerciseId(targetExercise.id);
    setAnswer("");
    setSubmitted(false);
  }, [exercises, initialExerciseId]);

  const filteredExercises = useMemo(() => {
    const cleanKeyword = keyword.trim().toLowerCase();
    return exercises.filter((exercise) => {
      const matchesChapter = chapterFilter === "全部" || exercise.chapter === chapterFilter;
      const matchesType = typeFilter === "全部" || exercise.type === typeFilter;
      const matchesDifficulty = difficultyFilter === "全部" || exercise.difficulty === difficultyFilter;
      const matchesKeyword = !cleanKeyword || exerciseSearchText(exercise).includes(cleanKeyword);
      return matchesChapter && matchesType && matchesDifficulty && matchesKeyword;
    });
  }, [chapterFilter, difficultyFilter, exercises, keyword, typeFilter]);

  useEffect(() => {
    if (!filteredExercises.length) {
      setSelectedExerciseId("");
      return;
    }
    if (!filteredExercises.some((exercise) => exercise.id === selectedExerciseId)) {
      setSelectedExerciseId(filteredExercises[0].id);
      setAnswer("");
      setSubmitted(false);
    }
  }, [filteredExercises, selectedExerciseId]);

  const selectedExercise = filteredExercises.find((exercise) => exercise.id === selectedExerciseId) ?? filteredExercises[0];
  const selectedRubric = selectedExercise ? rubricBank.items?.[selectedExercise.id] : null;
  const selectedExerciseWithRubric = selectedExercise
    ? {
        ...selectedExercise,
        rubric: selectedRubric?.rubric,
        misconceptions: selectedRubric?.misconceptions,
        expectedConcepts: selectedRubric?.expectedConcepts,
        requiresNumericAnswer: selectedRubric?.requiresNumericAnswer,
        teacherReviewBelowConfidence: selectedRubric?.teacherReviewBelowConfidence,
      }
    : null;
  const selectedIndex = selectedExercise ? filteredExercises.findIndex((exercise) => exercise.id === selectedExercise.id) : -1;
  const scoreResult = submitted && selectedExerciseWithRubric ? scoreExerciseAnswer(answer, selectedExerciseWithRubric) : null;
  const isExerciseLoading = loadedExerciseState.status === "loading" && !providedExerciseBank && !exercises.length;

  function selectExercise(exercise) {
    setSelectedExerciseId(exercise.id);
    setAnswer("");
    setSubmitted(false);
  }

  function moveExercise(offset) {
    if (!filteredExercises.length) {
      return;
    }
    const currentIndex = Math.max(0, selectedIndex);
    const nextIndex = (currentIndex + offset + filteredExercises.length) % filteredExercises.length;
    selectExercise(filteredExercises[nextIndex]);
  }

  function submitCurrentAnswer() {
    if (!selectedExerciseWithRubric) {
      return;
    }
    const result = scoreExerciseAnswer(answer, selectedExerciseWithRubric);
    setSubmitted(true);
    if (!answer.trim()) {
      return;
    }
    onRecordAttempt?.({
      questionId: selectedExercise.id,
      number: selectedExercise.number,
      chapter: selectedExercise.chapter,
      chapterNo: selectedExercise.chapterNo,
      type: selectedExercise.type,
      kind: selectedExercise.kind,
      difficulty: selectedExercise.difficulty,
      text: selectedExercise.text,
      sourceLine: selectedExercise.sourceLine,
      answerPreview: answer.trim().slice(0, 160),
      score: result.score,
      confidence: result.confidence,
      needsTeacherReview: result.needsTeacherReview,
      missingConcepts: result.missing,
      matchedConcepts: result.hits,
      issues: result.issues,
      criteria: result.criteria.map((criterion) => ({
        criterion: criterion.criterion,
        score: criterion.score,
        weight: criterion.weight,
        matched: criterion.matched,
        missing: criterion.missing,
      })),
      submittedAt: new Date().toISOString(),
    });
  }

  return (
    <section className="pagePanel">
      <PageHeader
        label="练习中心"
        title="全书练习题库"
        desc={`已导入本书 ${summary.total || exercises.length} 道思考题和习题，可按章节、题型和关键词练习。`}
      />
      {(isExerciseLoading || (rubricState.status === "loading" && !Object.keys(rubricBank.items ?? {}).length)) && (
        <LoadingSkeleton title="正在加载教材题库和评分 Rubric" rows={4} />
      )}
      <div className="practiceSummary" aria-label="题库统计">
        <article>
          <strong>{summary.total || exercises.length}</strong>
          <span>全部题目</span>
        </article>
        <article>
          <strong>{summary.thinking ?? exercises.filter((item) => item.type === "思考题").length}</strong>
          <span>思考题</span>
        </article>
        <article>
          <strong>{summary.exercise ?? exercises.filter((item) => item.type === "习题").length}</strong>
          <span>习题</span>
        </article>
        <article>
          <strong>{exerciseChapters.length}</strong>
          <span>覆盖章节</span>
        </article>
      </div>
      <div className="practiceLayout">
        <aside className="exerciseLibrary">
          <div className="libraryHeader">
            <strong>题库筛选</strong>
            <span>{filteredExercises.length} 道</span>
          </div>
          <label className="exerciseSearch">
            <Search size={17} />
            <input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="搜索题号、概念或关键词" />
          </label>
          <div className="filterBlock">
            <span>章节</span>
            <div className="exerciseChapterGrid">
              {["全部", ...exerciseChapters].map((chapter) => (
                <button className={cx(chapterFilter === chapter && "active")} type="button" key={chapter} onClick={() => setChapterFilter(chapter)}>
                  {chapter === "全部" ? "全部" : displayChapter(chapter)}
                </button>
              ))}
            </div>
          </div>
          <div className="filterBlock compact">
            <span>类型</span>
            <div className="pillGroup">
              {["全部", "思考题", "习题"].map((type) => (
                <button className={cx(typeFilter === type && "active")} type="button" key={type} onClick={() => setTypeFilter(type)}>
                  {type}
                </button>
              ))}
            </div>
          </div>
          <div className="filterBlock compact">
            <span>难度</span>
            <div className="pillGroup">
              {["全部", "基础", "困难"].map((difficulty) => (
                <button
                  className={cx(difficultyFilter === difficulty && "active")}
                  type="button"
                  key={difficulty}
                  onClick={() => setDifficultyFilter(difficulty)}
                >
                  {difficulty}
                </button>
              ))}
            </div>
          </div>
          <div className="exerciseList" aria-label="练习题列表">
            {filteredExercises.length ? (
              filteredExercises.map((exercise) => (
                <button
                  className={cx("exerciseItem", selectedExercise?.id === exercise.id && "active")}
                  type="button"
                  key={exercise.id}
                  onClick={() => selectExercise(exercise)}
                >
                  <span>
                    {exercise.number} · {exercise.type}
                  </span>
                  <strong>{exercise.text}</strong>
                  <em>
                    {displayChapter(exercise.chapter)} · {exercise.difficulty}
                  </em>
                </button>
              ))
            ) : (
              <p className="emptyExercise">没有匹配题目，换个筛选条件试试。</p>
            )}
          </div>
        </aside>
        <article className="questionCard exerciseDetail">
          {selectedExercise ? (
            <>
              <div className="exerciseMeta">
                <span>{displayChapter(selectedExercise.chapter)}</span>
                <span>{selectedExercise.type}</span>
                <span>{selectedExercise.kind}</span>
                <span>{selectedExercise.difficulty}</span>
              </div>
              <h3>
                {selectedExercise.number} {selectedExercise.text}
              </h3>
              {selectedExercise.attachments?.length ? (
                <div className="attachmentList">
                  <strong>题目附件</strong>
                  {selectedExercise.attachments.map((attachment, index) =>
                    attachment.type === "image" ? (
                      <figure key={`${attachment.caption}-${index}`}>
                        <img src={`${import.meta.env.BASE_URL || "/"}knowledge/${attachment.path}`} alt={attachment.caption || "习题附图"} />
                        <figcaption>{attachment.caption || "习题附图"}</figcaption>
                      </figure>
                    ) : (
                      <div className="tableAttachment" key={`table-${index}`} dangerouslySetInnerHTML={{ __html: attachment.html }} />
                    ),
                  )}
                </div>
              ) : null}
              <div className="exerciseTags">
                {(selectedExercise.tags?.length ? selectedExercise.tags : ["教材原题"]).map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
              <label className="answerBox">
                <span>我的作答</span>
                <textarea
                  value={answer}
                  onChange={(event) => {
                    setAnswer(event.target.value);
                    setSubmitted(false);
                  }}
                  placeholder={selectedExercise.type === "习题" ? "写出计算过程、采用公式、代入数据和结论。" : "写出你的理解，可用关键词和条目组织答案。"}
                />
              </label>
              <div className="exerciseActions">
                <button className="secondaryAction" type="button" onClick={() => moveExercise(-1)}>
                  上一题
                </button>
                <button className="secondaryAction" type="button" onClick={() => moveExercise(1)}>
                  下一题
                </button>
                <button type="button" onClick={submitCurrentAnswer}>
                  {submitted ? "重新评分" : "提交评分"}
                </button>
              </div>
            </>
          ) : (
            <p className="emptyExercise">题库正在加载。</p>
          )}
        </article>
        <aside className={cx("scorePanel", submitted && "submitted")}>
          <div className="scoreHeader">
            <span>智能评分</span>
            <strong>{scoreResult ? scoreResult.score : "--"}</strong>
            <em>/ 100</em>
          </div>
          <p>{scoreResult ? scoreResult.summary : "提交后显示规则评分、关键词覆盖和复习建议。"}</p>
          {scoreResult && (
            <>
              <div className="criterionList" aria-label="评分点明细">
                {scoreResult.criteria.map((criterion) => (
                  <div className="criterionRow" key={criterion.criterion}>
                    <div>
                      <strong>{criterion.criterion}</strong>
                      <span>
                        {criterion.score} / {criterion.weight}
                      </span>
                    </div>
                    <div className="criterionMeter" aria-hidden="true">
                      <i style={{ width: `${Math.round((criterion.score / criterion.weight) * 100)}%` }} />
                    </div>
                    <p>
                      {criterion.matched.length ? `已命中：${criterion.matched.join("、")}` : "暂未命中本项关键点"}
                      {criterion.missing.length ? `；待补充：${criterion.missing.slice(0, 3).join("、")}` : ""}
                    </p>
                  </div>
                ))}
              </div>
              <ul>
                {scoreResult.feedback.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              {scoreResult.issues.length ? (
                <div className="qualityWarnings" role="status" aria-live="polite">
                  <strong>质量提醒</strong>
                  {scoreResult.issues.map((issue) => (
                    <span key={issue}>{issue}</span>
                  ))}
                </div>
              ) : null}
              <div className={cx("confidenceBadge", scoreResult.needsTeacherReview && "review")}>
                <span>评分置信度 {Math.round(scoreResult.confidence * 100)}%</span>
                <strong>{scoreResult.needsTeacherReview ? "建议教师复核" : "可作为自测参考"}</strong>
              </div>
            </>
          )}
          {selectedExercise && (
            <div className="sourceTrace">
              <span>教材来源</span>
              <strong>
                {displayChapter(selectedExercise.chapter)} · L{selectedExercise.sourceLine}
              </strong>
            </div>
          )}
          <button
            className="clearAnswerButton"
            type="button"
            onClick={() => {
              setAnswer("");
              setSubmitted(false);
            }}
          >
            清空作答
          </button>
        </aside>
      </div>
    </section>
  );
}

function ReportPage({ learningStats }) {
  const reportValues = learningStats.chapterStats;

  return (
    <section className="pagePanel">
      <PageHeader label="学习报告" title="学习画像" desc="根据章节学习和练习结果生成复习建议。" />
      <p className="reportDataNote">
        数据口径：已作答章节按本机最近一次练习评分计算，未作答章节暂显示课程基线，后续接入教师后台后可统一同步到班级数据库。
      </p>
      <div className="reportRank">
        <Trophy size={24} />
        <div>
          <span>当前学习段位</span>
          <strong>
            {learningStats.rank.level} · {learningStats.averageScore} 分
          </strong>
          <p>{learningStats.rank.tip}</p>
        </div>
      </div>
      <div className="reportSummaryGrid">
        <article>
          <strong>{learningStats.attemptedQuestions}</strong>
          <span>已练习题目</span>
        </article>
        <article>
          <strong>{learningStats.completedChapters}</strong>
          <span>覆盖章节</span>
        </article>
        <article>
          <strong>{learningStats.progressPercent}%</strong>
          <span>题库进度</span>
        </article>
      </div>
      <div className="reportGrid">
        {reportValues.map((chapter) => (
          <div className={cx("abilityRow", chapter.isActual && "actual")} key={chapter.title}>
            <span>{chapter.title}</span>
            <div>
              <i style={{ width: `${chapter.score}%` }} />
            </div>
            <strong>{chapter.score}</strong>
            <em>{chapter.isActual ? `${chapter.attempts} 题` : "基线"}</em>
          </div>
        ))}
      </div>
      <section className="recentAttempts">
        <div className="panelTitle slim">
          <span className="titleIcon">
            <Clock3 size={18} />
          </span>
          <div>
            <h2>最近作答</h2>
            <p>{learningStats.hasAttempts ? "刷新页面后仍会保留在本机" : "还没有本地作答记录"}</p>
          </div>
        </div>
        {learningStats.recentAttempts.length ? (
          <div className="attemptList">
            {learningStats.recentAttempts.map((attempt) => (
              <article className="attemptItem" key={`${attempt.questionId}-${attempt.submittedAt}`}>
                <div>
                  <strong>
                    {attempt.number} · {displayChapter(attempt.chapter)}
                  </strong>
                  <span>{attempt.text}</span>
                </div>
                <em>{attempt.score} 分</em>
              </article>
            ))}
          </div>
        ) : (
          <p className="emptyExercise">去练习中心提交一次评分后，这里会自动生成学习记录。</p>
        )}
      </section>
    </section>
  );
}

function AdminPage({
  courseManifest,
  currentUser,
  apiToken,
  backendStatus = "offline",
  onRefreshData,
  baseExerciseBank,
  ragDocuments,
  setRagDocuments,
  ragChunks,
  customExercises,
  setCustomExercises,
  qaConfig,
  setQaConfig,
}) {
  const [activeTool, setActiveTool] = useState("RAG知识库");
  const [pasteTitle, setPasteTitle] = useState("课堂补充资料");
  const [pasteText, setPasteText] = useState("");
  const [uploadStatus, setUploadStatus] = useState("");
  const [exerciseJson, setExerciseJson] = useState(
    JSON.stringify(
      [
        {
          number: "T-1",
          chapter: "第3章 桩基础",
          type: "思考题",
          kind: "教师导入",
          difficulty: "基础",
          text: "什么是桩基础负摩阻力？它通常在什么条件下产生？",
          tags: ["桩基础", "负摩阻力", "桩侧阻力"],
        },
      ],
      null,
      2,
    ),
  );
  const [exerciseStatus, setExerciseStatus] = useState("");
  const safeQaConfig = { ...defaultQaConfig, ...(qaConfig ?? {}) };
  const loadedExerciseState = useJsonAssetState("/knowledge/exercises.json", { summary: null, exercises: [] });
  const managedExerciseBank = useMemo(
    () => baseExerciseBank ?? mergeExerciseBank(loadedExerciseState.data, customExercises),
    [baseExerciseBank, customExercises, loadedExerciseState.data],
  );
  const mergedTotal = managedExerciseBank?.summary?.total ?? managedExerciseBank?.exercises?.length ?? 0;
  const baseTotal = Math.max(0, mergedTotal - customExercises.length);
  const toolItems = [
    { id: "RAG知识库", icon: UploadCloud, desc: "上传 Markdown、TXT 或 JSON，生成本地检索切块" },
    { id: "题库管理", icon: ClipboardList, desc: "导入教师题目，自动进入练习中心" },
    { id: "答疑配置", icon: BrainCircuit, desc: "维护问答口径、教师提示词和复核规则" },
    { id: "班级绑定", icon: UserPlus, desc: "维护学生、学院、学校和指导老师绑定关系" },
  ];

  async function handleKnowledgeFiles(event) {
    const files = Array.from(event.target.files ?? []);
    if (!files.length) {
      return;
    }
    if (apiToken) {
      try {
        for (const file of files) {
          const formData = new FormData();
          formData.append("file", file);
          await apiRequest("/documents/upload", { method: "POST", token: apiToken, body: formData });
        }
        setUploadStatus(`已上传 ${files.length} 个知识库文件到服务器 RAG。`);
        await onRefreshData?.();
        event.target.value = "";
        return;
      } catch {
        setUploadStatus("服务器上传失败，已切换为本机演示导入。");
      }
    }
    const nextDocuments = [];
    for (const file of files) {
      const raw = await file.text();
      const text = extractDocumentText(raw);
      const document = makeRagDocument({ title: file.name, text, sourceType: "file-upload" });
      if (document) {
        nextDocuments.push(document);
      }
    }
    if (nextDocuments.length) {
      setRagDocuments((current) => [...nextDocuments, ...(current ?? [])].slice(0, 40));
      setUploadStatus(`已导入 ${nextDocuments.length} 个知识库文件，并生成可检索切块。`);
    } else {
      setUploadStatus("没有读到有效文本，请检查文件内容。");
    }
    event.target.value = "";
  }

  async function addPastedDocument() {
    if (apiToken) {
      try {
        await apiRequest("/documents", {
          method: "POST",
          token: apiToken,
          body: { title: pasteTitle, text: pasteText, sourceType: "teacher-paste" },
        });
        setPasteText("");
        setUploadStatus("已把粘贴内容写入服务器 RAG 知识库。");
        await onRefreshData?.();
        return;
      } catch {
        setUploadStatus("服务器写入失败，已切换为本机演示导入。");
      }
    }
    const document = makeRagDocument({ title: pasteTitle, text: pasteText, sourceType: "teacher-paste" });
    if (!document) {
      setUploadStatus("请先粘贴 Markdown 或文本内容。");
      return;
    }
    setRagDocuments((current) => [document, ...(current ?? [])].slice(0, 40));
    setPasteText("");
    setUploadStatus("已把粘贴内容加入 RAG 知识库。");
  }

  async function removeDocument(id) {
    if (apiToken) {
      try {
        await apiRequest(`/documents/${encodeURIComponent(id)}`, { method: "DELETE", token: apiToken });
        await onRefreshData?.();
        return;
      } catch {
        setUploadStatus("服务器删除失败，请稍后重试。");
      }
    }
    setRagDocuments((current) => (current ?? []).filter((document) => document.id !== id));
  }

  async function importExercises() {
    try {
      const imported = parseExerciseImport(exerciseJson);
      if (!imported.length) {
        setExerciseStatus("没有识别到有效题目，请使用 JSON 数组或 { exercises: [...] }。");
        return;
      }
      if (apiToken) {
        await apiRequest("/exercises/import", { method: "POST", token: apiToken, body: { exercises: imported } });
        setExerciseStatus(`已导入 ${imported.length} 道题到服务器题库，练习中心会立即显示。`);
        await onRefreshData?.();
        return;
      }
      setCustomExercises((current) => {
        const next = new Map();
        [...imported, ...(current ?? [])].forEach((exercise) => next.set(exercise.id, exercise));
        return Array.from(next.values()).slice(0, 300);
      });
      setExerciseStatus(`已导入 ${imported.length} 道题，练习中心会立即显示。`);
    } catch {
      setExerciseStatus("JSON 格式不正确，检查逗号、引号和数组结构。");
    }
  }

  async function removeCustomExercise(id) {
    if (apiToken) {
      try {
        await apiRequest(`/exercises/${encodeURIComponent(id)}`, { method: "DELETE", token: apiToken });
        await onRefreshData?.();
        return;
      } catch {
        setExerciseStatus("服务器删除失败，请稍后重试。");
      }
    }
    setCustomExercises((current) => (current ?? []).filter((exercise) => exercise.id !== id));
  }

  async function updateQaConfig(key, value) {
    const nextConfig = { ...(qaConfig ?? defaultQaConfig), [key]: value };
    setQaConfig(nextConfig);
    if (!apiToken) {
      return;
    }
    try {
      const saved = await apiRequest("/qa-config", { method: "PUT", token: apiToken, body: nextConfig });
      setQaConfig(saved);
    } catch {
      setUploadStatus("答疑配置暂未同步到服务器，已先保存在本机。");
    }
  }

  return (
    <section className="pagePanel">
      <PageHeader label="后台管理" title="教师内容管理台" desc="指导老师维护知识库、题库、答疑口径和学生绑定，学生端自动读取这些内容。" />
      <div className="adminHero">
        <div>
          <ShieldCheck size={22} />
          <span>{currentUser?.roleLabel}</span>
          <strong>{currentUser?.name}</strong>
        </div>
        <p>
          {backendStatus === "online" ? "服务器已连接" : "本机演示模式"} · 当前课程共 {courseManifest?.totalChapters ?? 7} 章，教材题库 {baseTotal}{" "}
          道，教师导入题 {customExercises.length} 道，上传知识库 {ragDocuments.length} 份。
        </p>
      </div>
      {loadedExerciseState.status === "loading" && !baseExerciseBank && <LoadingSkeleton title="正在加载教材基础题库" rows={2} />}
      <div className="adminGrid">
        {toolItems.map((item) => {
          const Icon = item.icon;
          return (
          <button className={cx("adminTile", activeTool === item.id && "active")} type="button" key={item.id} onClick={() => setActiveTool(item.id)}>
            <Icon size={24} />
            <strong>{item.id}</strong>
            <span>{item.desc}</span>
          </button>
          );
        })}
      </div>
      {activeTool === "RAG知识库" && (
        <div className="adminWorkbench">
          <section className="adminPanel wide">
            <div className="adminPanelTitle">
              <div>
                <strong>知识库上传</strong>
                <p>支持 `.md`、`.txt`、`.json`，上传后自动清洗并切成 RAG 检索块。</p>
              </div>
              <span>{ragChunks.length} 个上传切块</span>
            </div>
            <label className="uploadDrop">
              <input type="file" multiple accept=".md,.markdown,.txt,.json" onChange={handleKnowledgeFiles} />
              <UploadCloud size={28} />
              <strong>选择知识库文件</strong>
              <span>课堂讲义、规范摘录、答疑记录都可以上传</span>
            </label>
            <div className="pasteBox">
              <input value={pasteTitle} onChange={(event) => setPasteTitle(event.target.value)} placeholder="资料标题" />
              <textarea value={pasteText} onChange={(event) => setPasteText(event.target.value)} placeholder="也可以直接粘贴 Markdown / 文本内容" />
              <button type="button" onClick={addPastedDocument}>
                <FileUp size={17} />
                加入知识库
              </button>
            </div>
            {uploadStatus && <p className="adminStatus">{uploadStatus}</p>}
          </section>
          <aside className="adminPanel">
            <div className="adminPanelTitle">
              <div>
                <strong>RAG 流程</strong>
                <p>本地演示版先用关键词检索，生产版可换成向量库。</p>
              </div>
            </div>
            <div className="ragPipeline">
              {["上传资料", "切块清洗", "建立索引", "问答引用"].map((step, index) => (
                <span key={step}>
                  <em>{index + 1}</em>
                  {step}
                </span>
              ))}
            </div>
          </aside>
          <section className="adminPanel full">
            <div className="adminPanelTitle">
              <div>
                <strong>已上传资料</strong>
                <p>这些内容会进入智能问答的检索范围。</p>
              </div>
              {ragDocuments.length ? (
                <button type="button" onClick={() => setRagDocuments([])}>
                  清空上传库
                </button>
              ) : null}
            </div>
            <div className="documentList">
              {ragDocuments.length ? (
                ragDocuments.map((document) => (
                  <article key={document.id}>
                    <Database size={18} />
                    <div>
                      <strong>{document.title}</strong>
                      <p>
                        {chunkTextForRag(document).length} 个切块 · {Math.round(document.text.length / 100) / 10}k 字 ·{" "}
                        {new Date(document.uploadedAt).toLocaleString("zh-CN")}
                      </p>
                    </div>
                    <button type="button" onClick={() => removeDocument(document.id)}>
                      删除
                    </button>
                  </article>
                ))
              ) : (
                <p className="emptyExercise">还没有教师上传资料。可先上传本书 Markdown 或课堂讲义进行演示。</p>
              )}
            </div>
          </section>
        </div>
      )}
      {activeTool === "题库管理" && (
        <div className="adminWorkbench">
          <section className="adminPanel wide">
            <div className="adminPanelTitle">
              <div>
                <strong>题库导入</strong>
                <p>导入 JSON 后会合并到练习中心；没有 Rubric 的题会使用通用评分规则。</p>
              </div>
              <span>{mergedTotal} 道可练习</span>
            </div>
            <textarea className="jsonImportBox" value={exerciseJson} onChange={(event) => setExerciseJson(event.target.value)} />
            <div className="adminButtonRow">
              <button type="button" onClick={importExercises}>
                导入题目
              </button>
              <button type="button" onClick={() => setCustomExercises([])}>
                清空导入题
              </button>
            </div>
            {exerciseStatus && <p className="adminStatus">{exerciseStatus}</p>}
          </section>
          <aside className="adminPanel">
            <div className="adminMetricStack">
              <article>
                <strong>{baseTotal}</strong>
                <span>教材原题</span>
              </article>
              <article>
                <strong>{customExercises.length}</strong>
                <span>教师导入</span>
              </article>
              <article>
                <strong>{managedExerciseBank?.summary?.chapters?.length ?? 7}</strong>
                <span>覆盖章节</span>
              </article>
            </div>
          </aside>
          <section className="adminPanel full">
            <div className="adminPanelTitle">
              <div>
                <strong>教师导入题</strong>
                <p>点击删除只会移除本机导入题，不影响教材题库。</p>
              </div>
            </div>
            <div className="documentList compact">
              {customExercises.length ? (
                customExercises.map((exercise) => (
                  <article key={exercise.id}>
                    <ClipboardList size={18} />
                    <div>
                      <strong>
                        {exercise.number} · {exercise.type}
                      </strong>
                      <p>{exercise.text}</p>
                    </div>
                    <button type="button" onClick={() => removeCustomExercise(exercise.id)}>
                      删除
                    </button>
                  </article>
                ))
              ) : (
                <p className="emptyExercise">暂未导入教师自定义题，练习中心当前使用教材原题。</p>
              )}
            </div>
          </section>
        </div>
      )}
      {activeTool === "答疑配置" && (
        <div className="adminWorkbench single">
          <section className="adminPanel full">
            <div className="adminPanelTitle">
              <div>
                <strong>问答系统配置</strong>
                <p>这些设置会进入智能问答 Prompt，指导老师可统一课程答疑口径。</p>
              </div>
            </div>
            <div className="configGrid">
              <label>
                <span>指导老师要求</span>
                <textarea value={safeQaConfig.teacherInstruction} onChange={(event) => updateQaConfig("teacherInstruction", event.target.value)} />
              </label>
              <label>
                <span>回答风格</span>
                <textarea value={safeQaConfig.answerStyle} onChange={(event) => updateQaConfig("answerStyle", event.target.value)} />
              </label>
              <label>
                <span>复核规则</span>
                <textarea value={safeQaConfig.reviewRule} onChange={(event) => updateQaConfig("reviewRule", event.target.value)} />
              </label>
            </div>
          </section>
        </div>
      )}
      {activeTool === "班级绑定" && (
        <div className="adminWorkbench single">
          <section className="adminPanel full">
            <div className="adminPanelTitle">
              <div>
                <strong>学生强绑定</strong>
                <p>学院、学校、指导老师、答疑资料都由指导老师或管理员维护，学生端只读。</p>
              </div>
            </div>
            <div className="bindingTable">
              {demoUsers
                .filter((user) => user.role === "student")
                .map((user) => (
                  <article key={user.id}>
                    <UserRound size={20} />
                    <div>
                      <strong>{user.name}</strong>
                      <span>{user.studentNo}</span>
                    </div>
                    <p>{user.college}</p>
                    <p>{user.school}</p>
                    <em>辅导老师：{user.mentor}</em>
                  </article>
                ))}
            </div>
          </section>
        </div>
      )}
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

function LoadingSkeleton({ title = "正在加载课程数据", rows = 3 }) {
  return (
    <div className="loadingSkeleton" aria-live="polite">
      <div>
        <span className="skeletonLine title" />
        <strong>{title}</strong>
      </div>
      {Array.from({ length: rows }).map((_, index) => (
        <span className={cx("skeletonLine", index % 2 === 0 && "wide")} key={index} />
      ))}
    </div>
  );
}

function GlobalSearchPanel({ query, courseManifest, onNavigate, onClear, ragChunks = [], exerciseBank: providedExerciseBank, customExercises = [] }) {
  const baseChunkState = useJsonAssetState("/knowledge/chunks.json", []);
  const baseChunks = baseChunkState.data;
  const chunks = useMemo(() => [...ragChunks, ...baseChunks], [baseChunks, ragChunks]);
  const graphState = useJsonAssetState("/knowledge/graph_preview.json", { nodes: [], edges: [] });
  const graph = graphState.data;
  const loadedExerciseState = useJsonAssetState("/knowledge/exercises.json", { summary: null, exercises: [] });
  const exerciseBank = useMemo(
    () => providedExerciseBank ?? mergeExerciseBank(loadedExerciseState.data, customExercises),
    [customExercises, loadedExerciseState.data, providedExerciseBank],
  );
  const resultGroups = useMemo(
    () => buildGlobalSearchResults({ query, courseManifest, chunks, graph, exerciseBank }),
    [chunks, courseManifest, exerciseBank, graph, query],
  );
  const totalResults = resultGroups.reduce((total, group) => total + group.items.length, 0);
  const isSearchingAssets =
    [baseChunkState.status, graphState.status, loadedExerciseState.status].includes("loading") &&
    !chunks.length &&
    !graph.nodes.length &&
    !exerciseBank.exercises?.length;

  function openResult(action) {
    onNavigate(action.page, action);
    onClear();
  }

  function highlighted(text) {
    const value = text ?? "";
    const keyword = query.trim();
    if (!keyword) {
      return value;
    }
    const index = value.toLowerCase().indexOf(keyword.toLowerCase());
    if (index < 0) {
      return value;
    }
    return (
      <>
        {value.slice(0, index)}
        <mark>{value.slice(index, index + keyword.length)}</mark>
        {value.slice(index + keyword.length)}
      </>
    );
  }

  return (
    <section className="globalSearchPanel" aria-live="polite">
      <div className="globalSearchHeader">
        <div>
          <span>全局搜索</span>
          <strong>“{query.trim()}”</strong>
        </div>
        <button type="button" onClick={onClear}>
          清空
        </button>
      </div>
      {isSearchingAssets ? (
        <LoadingSkeleton title="正在检索教材、图谱和题库" rows={4} />
      ) : totalResults ? (
        <div className="globalSearchGroups">
          {resultGroups.map((group) => (
            <section className="globalSearchGroup" key={group.group}>
              <h3>{group.group}</h3>
              <div className="globalSearchItems">
                {group.items.map((item) => (
                  <button type="button" key={item.id} onClick={() => openResult(item.action)}>
                    <span>{highlighted(item.title)}</span>
                    <p>{highlighted(item.desc)}</p>
                    <div className="searchResultFooter">
                      {item.meta && <em>{highlighted(item.meta)}</em>}
                      <strong>进入 →</strong>
                    </div>
                  </button>
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <p className="emptySearchResult">暂时没有匹配内容，可以换一个章节名、知识点或题号试试。</p>
      )}
    </section>
  );
}

function Page({
  active,
  onNavigate,
  activeChapter,
  activeGraphNode,
  activeCaseTitle,
  activeResourceTitle,
  activeExerciseId,
  courseManifest,
  learningStats,
  onRecordAttempt,
  currentUser,
  exerciseBank,
  ragDocuments,
  setRagDocuments,
  ragChunks,
  customExercises,
  setCustomExercises,
  qaConfig,
  setQaConfig,
  apiToken,
  backendStatus,
  onRefreshData,
}) {
  const fullExerciseBank = exerciseBank?._preview ? undefined : exerciseBank;

  switch (active) {
    case "textbook":
      return <TextbookPage onNavigate={onNavigate} initialChapter={activeChapter} courseManifest={courseManifest} />;
    case "graph":
      return <GraphPage initialNode={activeGraphNode} />;
    case "qa":
      return <QAPage ragChunks={ragChunks} qaConfig={qaConfig} apiToken={apiToken} backendStatus={backendStatus} />;
    case "cases":
      return <CasesPage initialCaseTitle={activeCaseTitle} />;
    case "resources":
      return <ResourcesPage initialResourceTitle={activeResourceTitle} />;
    case "practice":
      return (
        <PracticePage
          initialChapter={activeChapter}
          initialExerciseId={activeExerciseId}
          onRecordAttempt={onRecordAttempt}
          exerciseBank={fullExerciseBank}
          customExercises={customExercises}
        />
      );
    case "report":
      return <ReportPage learningStats={learningStats} />;
    case "admin":
      return canManageContent(currentUser) ? (
        <AdminPage
          courseManifest={courseManifest}
          currentUser={currentUser}
          apiToken={apiToken}
          backendStatus={backendStatus}
          onRefreshData={onRefreshData}
          baseExerciseBank={fullExerciseBank}
          ragDocuments={ragDocuments}
          setRagDocuments={setRagDocuments}
          ragChunks={ragChunks}
          customExercises={customExercises}
          setCustomExercises={setCustomExercises}
          qaConfig={qaConfig}
          setQaConfig={setQaConfig}
        />
      ) : (
        <section className="pagePanel">
          <PageHeader label="后台管理" title="需要指导老师权限" desc="后台用于维护学院、答疑知识库和题库。请使用指导老师或管理员账号登录。" />
        </section>
      );
    default:
      return <Overview onNavigate={onNavigate} courseManifest={courseManifest} learningStats={learningStats} exerciseBank={exerciseBank} />;
  }
}

export function StudentExperience({ currentUser, onLogout }) {
  const courseManifest = useJsonAsset("/course-manifest.json", defaultCourseManifest);
  const [ragDocuments, setRagDocuments] = usePersistentState(ragDocumentsKey, []);
  const [customExercises, setCustomExercises] = usePersistentState(customExercisesKey, []);
  const [qaConfig, setQaConfig] = usePersistentState(qaConfigKey, defaultQaConfig);
  const [serverExerciseBank, setServerExerciseBank] = useState(null);
  const [backendStatus, setBackendStatus] = useState("checking");
  const [learningAttempts, setLearningAttempts] = useState(readLearningAttempts);
  const ragChunks = useMemo(() => buildLocalRagChunks(ragDocuments), [ragDocuments]);
  const previewExerciseBank = useMemo(() => {
    const chapters = courseChapters(courseManifest).map((chapter) => `第${chapter.number}章 ${chapter.title}`);
    return {
      _preview: true,
      summary: {
        total: customExercises.length || 79,
        thinking: 0,
        exercise: 0,
        chapters,
      },
      exercises: customExercises,
    };
  }, [courseManifest, customExercises]);
  const exerciseBank = useMemo(() => serverExerciseBank ?? previewExerciseBank, [previewExerciseBank, serverExerciseBank]);
  const initialRoute = routeFromLocation(defaultCourseManifest);
  const [active, setActive] = useState(initialRoute.page);
  const [query, setQuery] = useState("");
  const [activeChapter, setActiveChapter] = useState(initialRoute.chapter ?? currentCourseChapter(defaultCourseManifest).title);
  const [activeGraphNode, setActiveGraphNode] = useState(initialRoute.node ?? "");
  const [activeCaseTitle, setActiveCaseTitle] = useState(initialRoute.caseTitle ?? "");
  const [activeResourceTitle, setActiveResourceTitle] = useState(initialRoute.resourceTitle ?? "");
  const [activeExerciseId, setActiveExerciseId] = useState(initialRoute.exerciseId ?? "");
  const activeLabel = useMemo(() => navItems.find((item) => item.id === active)?.label ?? "课程总览", [active]);
  const activeRouteOptions = useMemo(
    () => ({
      chapter: activeChapter,
      node: activeGraphNode,
      caseTitle: activeCaseTitle,
      resourceTitle: activeResourceTitle,
      exerciseId: activeExerciseId,
    }),
    [activeCaseTitle, activeChapter, activeExerciseId, activeGraphNode, activeResourceTitle],
  );
  const learningStats = useMemo(
    () => buildLearningStats({ courseManifest, exerciseBank, attempts: learningAttempts }),
    [courseManifest, exerciseBank, learningAttempts],
  );

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const seo = routeSeo(active, activeRouteOptions);
    const canonical = `${window.location.origin}${routeToUrl(active, activeRouteOptions, courseManifest)}`;
    document.title = seo.title;
    setDocumentMeta('meta[name="description"]', { content: seo.description });
    setDocumentMeta('meta[property="og:title"]', { content: seo.title });
    setDocumentMeta('meta[property="og:description"]', { content: seo.description });
    setDocumentMeta('meta[property="og:url"]', { content: canonical });
    setDocumentMeta('link[rel="canonical"]', { href: canonical });
  }, [active, activeRouteOptions, courseManifest]);

  useEffect(() => {
    window.localStorage.setItem(learningAttemptsKey, JSON.stringify(learningAttempts));
  }, [learningAttempts]);

  async function refreshServerData() {
    try {
      await apiRequest("/student/dashboard");
      setBackendStatus("online");
      return true;
    } catch {
      setBackendStatus("offline");
      return false;
    }
  }

  useEffect(() => {
    refreshServerData();
  }, [currentUser?.id]);

  function applyRoute(route) {
    if (route.chapter) {
      setActiveChapter(route.chapter);
    }
    setActiveGraphNode(route.node ?? "");
    setActiveCaseTitle(route.caseTitle ?? "");
    setActiveResourceTitle(route.resourceTitle ?? "");
    setActiveExerciseId(route.exerciseId ?? "");
    setActive(route.page);
  }

  useEffect(() => {
    applyRoute(routeFromLocation(courseManifest));
  }, [courseManifest]);

  useEffect(() => {
    function handlePopState() {
      applyRoute(routeFromLocation(courseManifest));
    }
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [courseManifest]);

  function handleNavigate(page, options = {}) {
    if (page === "admin" && !canManageContent(currentUser)) {
      page = "overview";
    }
    const routeOptions = { ...options };
    if (page === "textbook" && !routeOptions.chapter) {
      routeOptions.chapter = activeChapter;
    }
    const route = { page, ...routeOptions };
    applyRoute(route);
    window.history.pushState({ route }, "", routeToUrl(page, routeOptions, courseManifest));
  }

  function handleRecordAttempt(attempt) {
    apiRequest(`/student/exercises/${encodeURIComponent(attempt.questionId)}/attempts`, {
      method: "POST",
      body: { answer: attempt.answerPreview },
    }).catch(() => {});
    setLearningAttempts((current) => {
      const attemptNumber = current.filter((item) => item.questionId === attempt.questionId).length + 1;
      return [{ ...attempt, attemptNumber }, ...current].slice(0, 300);
    });
  }

  async function handleLogout() {
    setServerExerciseBank(null);
    setBackendStatus("offline");
    setQuery("");
    setActive("overview");
    await onLogout?.();
  }

  if (!currentUser) {
    return <LoadingSkeleton title="正在恢复学生信息" />;
  }

  return (
    <div className="appShell">
      <Sidebar active={active} onNavigate={handleNavigate} learningStats={learningStats} currentUser={currentUser} />
      <div className="workspace">
        <Header query={query} setQuery={setQuery} onNavigate={handleNavigate} currentUser={currentUser} onLogout={handleLogout} />
        <main className="content">
          <div className="mobilePageLabel">{activeLabel}</div>
          {query.trim() && (
            <GlobalSearchPanel
              query={query}
              courseManifest={courseManifest}
              onNavigate={handleNavigate}
              onClear={() => setQuery("")}
              ragChunks={ragChunks}
              exerciseBank={exerciseBank?._preview ? undefined : exerciseBank}
              customExercises={customExercises}
            />
          )}
          <div className="routeSurface" key={active}>
            <Page
              active={active}
              onNavigate={handleNavigate}
              activeChapter={activeChapter}
              activeGraphNode={activeGraphNode}
              activeCaseTitle={activeCaseTitle}
              activeResourceTitle={activeResourceTitle}
              activeExerciseId={activeExerciseId}
              courseManifest={courseManifest}
              learningStats={learningStats}
              onRecordAttempt={handleRecordAttempt}
              currentUser={currentUser}
              exerciseBank={exerciseBank}
              ragDocuments={ragDocuments}
              setRagDocuments={setRagDocuments}
              ragChunks={ragChunks}
              customExercises={customExercises}
              setCustomExercises={setCustomExercises}
              qaConfig={qaConfig}
              setQaConfig={setQaConfig}
              apiToken="cookie-session"
              backendStatus={backendStatus}
              onRefreshData={() => refreshServerData()}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
