import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

const distDir = path.resolve("dist");
const basePath = "/foundation-smart-companion";
const canonicalOrigin = "https://haiqingm58-ui.github.io";

const routes = [
  {
    path: "/",
    title: "《基础工程》智慧学伴",
    description: "面向土木工程基础工程课程的教材学习、知识图谱、RAG 智能问答、关联规范资料、题库练习和学习报告平台。",
    keywords: "基础工程,智慧学伴,土木工程,地基基础,知识图谱,RAG,智能问答,题库练习",
    heading: "《基础工程》智慧学伴",
    points: ["课程总览", "教材学习", "知识图谱", "智能问答", "关联资料", "练习中心", "学习报告"],
  },
  {
    path: "/textbook",
    title: "教材学习 - 《基础工程》智慧学伴",
    description: "按章节浏览《基础工程》教材内容，查看公式、图表解释、案例关联和章节练习。",
    keywords: "基础工程教材,浅基础,桩基础,基坑工程,地基处理",
    heading: "教材学习",
    points: ["章节导读", "重点公式", "图表解释", "案例关联", "章节练习"],
  },
  {
    path: "/graph",
    title: "知识图谱 - 《基础工程》智慧学伴",
    description: "以可交互知识图谱浏览基础工程章节、概念、关系和教材原文依据。",
    keywords: "基础工程知识图谱,地基基础概念,教材关系图谱",
    heading: "知识图谱",
    points: ["节点搜索", "关系过滤", "节点展开", "教材依据"],
  },
  {
    path: "/qa",
    title: "RAG 智能问答 - 《基础工程》智慧学伴",
    description: "基于教材切块、教师上传知识库和大模型生成的基础工程课程问答系统。",
    keywords: "RAG问答,基础工程智能问答,教材问答,规范问答",
    heading: "RAG 智能问答",
    points: ["教材问答", "规范问答", "学习辅导", "来源引用"],
  },
  {
    path: "/cases",
    title: "工程案例 - 《基础工程》智慧学伴",
    description: "围绕浅基础、桩基础、基坑工程、地基处理等主题的工程案例学习入口。",
    keywords: "基础工程案例,桩基础案例,基坑工程案例,地基处理案例",
    heading: "工程案例",
    points: ["工程背景", "地质条件", "处理措施", "经验启示"],
  },
  {
    path: "/resources",
    title: "关联资料 - 《基础工程》智慧学伴",
    description: "整理基础工程课程相关规范、规程、参考教材和拓展资料，可查看标准编号、版本和关联章节。",
    keywords: "基础工程规范,GB 50007,JGJ 94,JGJ 120,关联资料",
    heading: "关联资料",
    points: ["标准规范", "参考教材", "课程讲义", "论文与拓展阅读"],
  },
  {
    path: "/practice",
    title: "练习中心 - 《基础工程》智慧学伴",
    description: "覆盖《基础工程》全书思考题和习题，支持按章节、题型、难度和关键词练习。",
    keywords: "基础工程习题,基础工程题库,思考题,章节练习",
    heading: "练习中心",
    points: ["全书题库", "Rubric 评分", "错题反馈", "教师复核"],
  },
  {
    path: "/report",
    title: "学习报告 - 《基础工程》智慧学伴",
    description: "根据练习记录生成学习进度、掌握度、薄弱知识点和学习段位反馈。",
    keywords: "学习报告,基础工程学习进度,知识点掌握度,学习段位",
    heading: "学习报告",
    points: ["学习进度", "平均分", "薄弱环节", "学习段位"],
  },
];

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function routeUrl(routePath) {
  const suffix = routePath === "/" ? "/" : `${routePath.replace(/\/$/, "")}/`;
  return `${canonicalOrigin}${basePath}${suffix}`;
}

function upsert(html, regex, replacement) {
  if (regex.test(html)) {
    return html.replace(regex, replacement);
  }
  return html.replace("</head>", `    ${replacement}\n  </head>`);
}

function routeJsonLd(route) {
  return {
    "@context": "https://schema.org",
    "@type": "Course",
    name: route.title.replace(" - 《基础工程》智慧学伴", ""),
    description: route.description,
    inLanguage: "zh-CN",
    url: routeUrl(route.path),
    provider: {
      "@type": "Organization",
      name: "Foundation Smart Companion",
    },
    hasCourseInstance: {
      "@type": "CourseInstance",
      courseMode: "online",
      courseWorkload: "P1D",
    },
  };
}

function noscriptContent(route) {
  const items = route.points.map((point) => `<li>${escapeHtml(point)}</li>`).join("");
  return `<noscript>
      <main>
        <h1>${escapeHtml(route.heading)}</h1>
        <p>${escapeHtml(route.description)}</p>
        <ul>${items}</ul>
      </main>
    </noscript>`;
}

function renderRoute(template, route) {
  const url = routeUrl(route.path);
  let html = template;
  html = html.replace(/<title>[\s\S]*?<\/title>/i, `<title>${escapeHtml(route.title)}</title>`);
  html = upsert(html, /<meta\s+name="description"\s+content="[^"]*"\s*\/?>/i, `<meta name="description" content="${escapeHtml(route.description)}" />`);
  html = upsert(html, /<meta\s+name="keywords"\s+content="[^"]*"\s*\/?>/i, `<meta name="keywords" content="${escapeHtml(route.keywords)}" />`);
  html = upsert(html, /<link\s+rel="canonical"\s+href="[^"]*"\s*\/?>/i, `<link rel="canonical" href="${url}" />`);
  html = upsert(html, /<meta\s+property="og:title"\s+content="[^"]*"\s*\/?>/i, `<meta property="og:title" content="${escapeHtml(route.title)}" />`);
  html = upsert(
    html,
    /<meta\s+property="og:description"\s+content="[^"]*"\s*\/?>/i,
    `<meta property="og:description" content="${escapeHtml(route.description)}" />`,
  );
  html = upsert(html, /<meta\s+property="og:url"\s+content="[^"]*"\s*\/?>/i, `<meta property="og:url" content="${url}" />`);
  html = html.replace(
    /<script\s+id="seo-structured-data"\s+type="application\/ld\+json">[\s\S]*?<\/script>/i,
    `<script id="seo-structured-data" type="application/ld+json">${JSON.stringify(routeJsonLd(route))}</script>`,
  );
  html = html.replace(/<noscript>[\s\S]*?<\/noscript>/i, noscriptContent(route));
  return html;
}

async function writeRoute(template, route) {
  const html = renderRoute(template, route);
  if (route.path === "/") {
    await writeFile(path.join(distDir, "index.html"), html);
    await writeFile(path.join(distDir, "404.html"), html);
    return;
  }
  const routeDir = path.join(distDir, route.path.replace(/^\//, ""));
  await mkdir(routeDir, { recursive: true });
  await writeFile(path.join(routeDir, "index.html"), html);
}

function buildSitemap() {
  const today = new Date().toISOString().slice(0, 10);
  const urls = routes
    .map(
      (route) => `  <url>
    <loc>${routeUrl(route.path)}</loc>
    <lastmod>${today}</lastmod>
    <changefreq>weekly</changefreq>
  </url>`,
    )
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;
}

const template = await readFile(path.join(distDir, "index.html"), "utf8");
await Promise.all(routes.map((route) => writeRoute(template, route)));
await writeFile(path.join(distDir, "sitemap.xml"), buildSitemap());
await writeFile(
  path.join(distDir, "robots.txt"),
  `User-agent: *
Allow: /
Sitemap: ${routeUrl("/")}sitemap.xml
`,
);

console.log(`Prerendered ${routes.length} routes with SEO metadata.`);
