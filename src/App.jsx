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
      <PageHeader label="知识图谱" title="教材知识图谱工作台" desc="从 Markdown 教材自动抽取章节、概念、公式、表格、图片和原文切块关系。" />
      {summary && (
        <div className="knowledgeStats" aria-label="知识库统计">
          <Metric label="图谱节点" value={summary.graph_nodes} />
          <Metric label="图谱关系" value={summary.graph_edges} />
          <Metric label="教材切块" value={summary.chunks} />
          <Metric label="公式/表格" value={`${summary.formulas}/${summary.tables}`} />
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
  const chunks = useJsonAsset("/knowledge/chunks.json", []);
  const modes = ["教材问答", "规范问答", "学习辅导"];
  const results = useMemo(() => searchChunks(chunks, question, 4), [chunks, question]);
  const answer = results[0]?.text ?? "教材索引加载后，会在这里显示最相关的原文依据。";

  return (
    <section className="pagePanel">
      <PageHeader label="智能问答" title="教材检索问答" desc="已接入《基础工程》Markdown 切块索引，先给出教材原文依据，后续可替换为大模型生成答案。" />
      <div className="teacherNotice">
        <Link2 size={17} />
        当前检索库来自本书 Markdown：{chunks.length ? `${chunks.length} 个教材块已加载` : "正在加载教材索引"}。
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
              <p>{answer}</p>
              <span>
                引用：{results[0]?.heading_path ?? "教材索引"} {results[0] ? `L${results[0].source_line}` : ""}
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
          <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={`继续使用${mode}提问…`} />
          <button type="button">检索</button>
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
