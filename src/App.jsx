import { useEffect, useMemo, useState } from "react";
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
  Focus,
  GraduationCap,
  LayoutDashboard,
  LibraryBig,
  Link2,
  ListFilter,
  LocateFixed,
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
  Target,
  Trophy,
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

function useJsonAsset(path, fallback) {
  const [data, setData] = useState(fallback);

  useEffect(() => {
    let alive = true;
    const cleanPath = path.replace(/^\/+/, "");
    const assetUrl = `${import.meta.env.BASE_URL || "/"}${cleanPath}`;
    fetch(assetUrl)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to load ${path}`);
        }
        return response.json();
      })
      .then((nextData) => {
        if (alive) {
          setData(nextData);
        }
      })
      .catch(() => {
        if (alive) {
          setData(fallback);
        }
      });
    return () => {
      alive = false;
    };
  }, [path]);

  return data;
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

function buildAiPrompt(question, mode, results) {
  const context = results.length
    ? results
        .map((item, index) => `${index + 1}. ${item.heading_path} L${item.source_line}: ${compactText(item.text, 360)}`)
        .join("\n")
    : "暂无教材检索片段。";
  return [
    "你是《基础工程》课程的智慧学伴。请只基于给定教材片段回答，必要时说明还需要查教材。",
    `问答模式：${mode}`,
    `学生问题：${question}`,
    "教材片段：",
    context,
    "请用中文回答，结构简洁，包含：直接回答、关键概念、复习提醒。不要编造规范条文编号。",
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
  if (typeof window === "undefined" || typeof window.puter?.ai?.chat !== "function") {
    throw new Error("FREE_AI_UNAVAILABLE");
  }
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
    .filter((item) => resultMatches(cleanQuery, item.title, item.tag, item.status))
    .map((item) => ({
      id: `case:${item.title}`,
      group: "工程案例",
      title: item.title,
      desc: `案例类型：${item.tag}`,
      meta: item.status,
      action: { page: "cases", caseTitle: item.title },
    }));

  const resourceResults = resources
    .filter((item) => resultMatches(cleanQuery, item.title, item.code, item.type, item.link))
    .map((item) => ({
      id: `resource:${item.title}`,
      group: "关联资料",
      title: item.title,
      desc: item.link,
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

function Header({ query, setQuery, onNavigate }) {
  const [openPanel, setOpenPanel] = useState("");

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
          <span>张同学</span>
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
                <strong>张同学</strong>
                <p>土木工程学院 · 指导老师李老师已绑定</p>
                <div className="popoverActions">
                  <button type="button" onClick={() => jumpTo("report")}>
                    学习报告
                  </button>
                  <button type="button" onClick={() => jumpTo("admin")}>
                    后台管理
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

function Hero({ onNavigate, courseManifest }) {
  const currentChapter = currentCourseChapter(courseManifest);
  const completedChapters = courseManifest?.progress?.completedChapters ?? 0;
  const totalChapters = courseManifest?.totalChapters ?? courseChapters(courseManifest).length;
  const percent = progressPercent(courseManifest);
  const averageScore = courseManifest?.progress?.averageScore ?? rankInfo.score;

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
          <Metric label="已完成" value={completedChapters} suffix={` / ${totalChapters} 章`} />
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

function WeakPanel({ onNavigate, courseManifest }) {
  const currentChapter = currentCourseChapter(courseManifest);
  const quickChapters = courseChapters(courseManifest);

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

function Overview({ onNavigate, courseManifest }) {
  const graphSummary = useJsonAsset("/knowledge/build_summary.json", null);
  const exerciseBank = useJsonAsset("/knowledge/exercises.json", { summary: null, exercises: [] });
  const cards = moduleCards.map((card) => ({
    ...card,
    meta: moduleMeta(card.id, { courseManifest, graphSummary, exerciseBank }),
  }));

  return (
    <div className="overviewLayout">
      <div className="mainStack">
        <Hero onNavigate={onNavigate} courseManifest={courseManifest} />
        <section className="moduleGrid" aria-label="平台模块入口">
          {cards.map((card) => (
            <ModuleCard card={card} key={card.id} onNavigate={onNavigate} />
          ))}
        </section>
      </div>
      <WeakPanel onNavigate={onNavigate} courseManifest={courseManifest} />
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
          <p>{activeContent.caseText}</p>
          <button type="button" onClick={() => onNavigate("resources")}>
            查看资料
          </button>
          <h3>相关案例</h3>
          <p>{activeContent.diagram}</p>
          <button type="button" onClick={() => onNavigate("cases")}>
            查看案例
          </button>
        </aside>
      </div>
    </section>
  );
}

function GraphPage({ initialNode }) {
  const summary = useJsonAsset("/knowledge/build_summary.json", null);
  const graph = useJsonAsset("/knowledge/graph_preview.json", { nodes: [], edges: [] });
  const chunks = useJsonAsset("/knowledge/chunks.json", []);
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

function QAPage() {
  const [mode, setMode] = useState("教材问答");
  const [question, setQuestion] = useState("桩侧阻力是如何产生的？影响它的主要因素有哪些？");
  const [draftQuestion, setDraftQuestion] = useState(question);
  const [searchCount, setSearchCount] = useState(1);
  const [aiAnswer, setAiAnswer] = useState("");
  const [aiStatus, setAiStatus] = useState("idle");
  const [aiError, setAiError] = useState("");
  const chunks = useJsonAsset("/knowledge/chunks.json", []);
  const modes = ["教材问答", "规范问答", "学习辅导"];
  const results = useMemo(() => searchChunks(chunks, question, 4), [chunks, question]);
  const answer = results[0]?.text ?? "教材索引加载后，会在这里显示最相关的原文依据。";

  useEffect(() => {
    setAiAnswer("");
    setAiStatus("idle");
    setAiError("");
  }, [mode, question]);

  function runSearch() {
    const nextQuestion = draftQuestion.trim() || "桩侧阻力是如何产生的？";
    setQuestion(nextQuestion);
    setDraftQuestion(nextQuestion);
    setSearchCount((count) => count + 1);
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
      const responseText = await callFreeAi(buildAiPrompt(nextQuestion, mode, nextResults));
      setAiAnswer(responseText);
      setAiStatus("success");
    } catch {
      setAiAnswer("");
      setAiStatus("error");
      setAiError("免费 API 暂时没有返回，已保留本地教材检索结果。");
    }
  }

  return (
    <section className="pagePanel">
      <PageHeader label="智能问答" title="教材检索问答" desc="已接入《基础工程》Markdown 切块索引，并可调用免费浏览器端 AI 生成答案。" />
      <div className="teacherNotice">
        <Link2 size={17} />
        当前模式：{mode} · 检索库来自本书 Markdown：{chunks.length ? `${chunks.length} 个教材块已加载` : "正在加载教材索引"}。
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
          <div className="bubble user">{question}</div>
          <div className="bubble assistant">
            <Bot size={20} />
            <div>
              <p>{aiAnswer || answer}</p>
              <span>
                {aiStatus === "success"
                  ? "Puter.js 免费 AI 生成 · 已结合教材检索片段"
                  : aiStatus === "loading"
                    ? "正在调用免费 AI 生成答案..."
                    : aiError || `引用：${results[0]?.heading_path ?? "教材索引"} ${results[0] ? `L${results[0].source_line}` : ""}`}
              </span>
            </div>
          </div>
          <div className="sourceList">
            {results.map((item) => (
              <article className="sourceItem" key={item.id}>
                <strong>{item.heading_path}</strong>
                <p>{item.text.replace(/\s+/g, " ").slice(0, 150)}</p>
                <span>来源行 {item.source_line} · {item.kind}</span>
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
            <p>工程背景、问题表现、原因分析、涉及知识点与思考题已整理。</p>
            <button type="button" onClick={() => setSelectedCase(item)}>
              {selectedCase.title === item.title ? "正在查看" : "查看详情"}
            </button>
          </article>
        ))}
      </div>
      <section className="detailPanel">
        <strong>{selectedCase.title}</strong>
        <p>
          当前案例已关联“{selectedCase.tag}”知识点，可用于课堂讨论、章节复习和练习题生成。建议先定位工程问题，再回到教材查看设计计算依据。
        </p>
        <div className="detailTags">
          <span>{selectedCase.status}</span>
          <span>{selectedCase.tag}</span>
          <span>已关联教材</span>
        </div>
      </section>
    </section>
  );
}

function ResourcesPage({ initialResourceTitle }) {
  const [selectedResource, setSelectedResource] = useState(resources[0]);

  useEffect(() => {
    const nextResource = resources.find((item) => item.title === initialResourceTitle);
    if (nextResource) {
      setSelectedResource(nextResource);
    }
  }, [initialResourceTitle]);

  return (
    <section className="pagePanel">
      <PageHeader label="关联资料" title="资料中心" desc="统一管理规范、参考教材、课程资料和相关附件。" />
      <div className="tablePanel">
        {resources.map((item) => (
          <div className={cx("resourceRow", selectedResource.title === item.title && "active")} key={item.title}>
            <span className="typePill">{item.type}</span>
            <div>
              <strong>{item.title}</strong>
              <p>{item.link}</p>
            </div>
            <em>{item.code}</em>
            <button type="button" onClick={() => setSelectedResource(item)}>
              {selectedResource.title === item.title ? "已查看" : "查看"}
            </button>
          </div>
        ))}
      </div>
      <section className="detailPanel compact">
        <strong>{selectedResource.title}</strong>
        <p>
          已定位到 {selectedResource.code}：重点用于“{selectedResource.link}”。后续可由指导老师补充正式附件、讲义和规范摘录。
        </p>
      </section>
    </section>
  );
}

function PracticePage({ initialChapter, initialExerciseId }) {
  const exerciseBank = useJsonAsset("/knowledge/exercises.json", { summary: { total: 0, thinking: 0, exercise: 0, chapters: [] }, exercises: [] });
  const rubricBank = useJsonAsset("/knowledge/exercise_rubrics.json", { items: {} });
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

  return (
    <section className="pagePanel">
      <PageHeader
        label="练习中心"
        title="全书练习题库"
        desc={`已导入本书 ${summary.total || exercises.length} 道思考题和习题，可按章节、题型和关键词练习。`}
      />
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
              {["全部", "基础", "提高"].map((difficulty) => (
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
                <button type="button" onClick={() => setSubmitted(true)}>
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

function ReportPage({ courseManifest }) {
  const reportValues = courseChapters(courseManifest).map((chapter, index) => {
    const demoValues = [88, 80, 65, 72, 70, 76, 68];
    return [chapter.title, demoValues[index] ?? 70];
  });

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
        {reportValues.map(([name, value]) => (
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
  const [activeTool, setActiveTool] = useState("上传教材");

  return (
    <section className="pagePanel">
      <PageHeader label="后台管理" title="内容管理" desc="用于后续上传教材、资料、案例和题库，目前为展示状态。" />
      <div className="adminGrid">
        {["上传教材", "管理知识点", "维护案例", "导入题库"].map((item) => (
          <button className={cx("adminTile", activeTool === item && "active")} type="button" key={item} onClick={() => setActiveTool(item)}>
            <Database size={24} />
            {item}
          </button>
        ))}
      </div>
      <section className="detailPanel compact">
        <strong>{activeTool}</strong>
        <p>该入口已可选中展示。生产版本中，这里将由指导老师维护课程资料、答疑内容、案例和题库。</p>
      </section>
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

function GlobalSearchPanel({ query, courseManifest, onNavigate, onClear }) {
  const chunks = useJsonAsset("/knowledge/chunks.json", []);
  const graph = useJsonAsset("/knowledge/graph_preview.json", { nodes: [], edges: [] });
  const exerciseBank = useJsonAsset("/knowledge/exercises.json", { summary: null, exercises: [] });
  const resultGroups = useMemo(
    () => buildGlobalSearchResults({ query, courseManifest, chunks, graph, exerciseBank }),
    [chunks, courseManifest, exerciseBank, graph, query],
  );
  const totalResults = resultGroups.reduce((total, group) => total + group.items.length, 0);

  function openResult(action) {
    onNavigate(action.page, action);
    onClear();
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
      {totalResults ? (
        <div className="globalSearchGroups">
          {resultGroups.map((group) => (
            <section className="globalSearchGroup" key={group.group}>
              <h3>{group.group}</h3>
              <div className="globalSearchItems">
                {group.items.map((item) => (
                  <button type="button" key={item.id} onClick={() => openResult(item.action)}>
                    <span>{item.title}</span>
                    <p>{item.desc}</p>
                    {item.meta && <em>{item.meta}</em>}
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

function Page({ active, onNavigate, activeChapter, activeGraphNode, activeCaseTitle, activeResourceTitle, activeExerciseId, courseManifest }) {
  switch (active) {
    case "textbook":
      return <TextbookPage onNavigate={onNavigate} initialChapter={activeChapter} courseManifest={courseManifest} />;
    case "graph":
      return <GraphPage initialNode={activeGraphNode} />;
    case "qa":
      return <QAPage />;
    case "cases":
      return <CasesPage initialCaseTitle={activeCaseTitle} />;
    case "resources":
      return <ResourcesPage initialResourceTitle={activeResourceTitle} />;
    case "practice":
      return <PracticePage initialChapter={activeChapter} initialExerciseId={activeExerciseId} />;
    case "report":
      return <ReportPage courseManifest={courseManifest} />;
    case "admin":
      return <AdminPage />;
    default:
      return <Overview onNavigate={onNavigate} courseManifest={courseManifest} />;
  }
}

export function App() {
  const courseManifest = useJsonAsset("/course-manifest.json", defaultCourseManifest);
  const [active, setActive] = useState("overview");
  const [query, setQuery] = useState("");
  const [activeChapter, setActiveChapter] = useState(currentCourseChapter(defaultCourseManifest).title);
  const [activeGraphNode, setActiveGraphNode] = useState("");
  const [activeCaseTitle, setActiveCaseTitle] = useState("");
  const [activeResourceTitle, setActiveResourceTitle] = useState("");
  const [activeExerciseId, setActiveExerciseId] = useState("");
  const activeLabel = useMemo(() => navItems.find((item) => item.id === active)?.label ?? "课程总览", [active]);

  function handleNavigate(page, options = {}) {
    if (options.chapter) {
      setActiveChapter(options.chapter);
    }
    setActiveGraphNode(options.node ?? "");
    setActiveCaseTitle(options.caseTitle ?? "");
    setActiveResourceTitle(options.resourceTitle ?? "");
    setActiveExerciseId(options.exerciseId ?? "");
    setActive(page);
  }

  return (
    <div className="appShell">
      <Sidebar active={active} onNavigate={handleNavigate} />
      <div className="workspace">
        <Header query={query} setQuery={setQuery} onNavigate={handleNavigate} />
        <main className="content">
          <div className="mobilePageLabel">{activeLabel}</div>
          {query.trim() && (
            <GlobalSearchPanel query={query} courseManifest={courseManifest} onNavigate={handleNavigate} onClear={() => setQuery("")} />
          )}
          <Page
            active={active}
            onNavigate={handleNavigate}
            activeChapter={activeChapter}
            activeGraphNode={activeGraphNode}
            activeCaseTitle={activeCaseTitle}
            activeResourceTitle={activeResourceTitle}
            activeExerciseId={activeExerciseId}
            courseManifest={courseManifest}
          />
        </main>
      </div>
    </div>
  );
}
