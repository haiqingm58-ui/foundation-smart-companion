import { AlertTriangle, BarChart3, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { teacherApi } from "../../../api/teacher.js";


const TYPES = ["单项选择题", "多项选择题", "判断题", "填空题", "简答题", "计算题"];
const DIFFICULTIES = ["基础", "中等", "困难"];


function emptyRow() {
  return { chapterId: "", knowledgePointId: "", questionType: "单项选择题", difficulty: "基础", count: 5, pointsEach: 5, sectionTitle: "一、选择题" };
}


function toApiRow(row) {
  return {
    chapterIds: row.chapterId ? [row.chapterId] : [],
    knowledgePointIds: row.knowledgePointId ? [row.knowledgePointId] : [],
    questionTypes: row.questionType ? [row.questionType] : [],
    difficulties: row.difficulty ? [row.difficulty] : [],
    count: Number(row.count),
    pointsEach: Number(row.pointsEach),
    sectionTitle: row.sectionTitle.trim(),
  };
}


export function BlueprintBuilder({ subjectId, knowledgePoints = [], initialRows = [], onApply }) {
  const [rows, setRows] = useState(() => initialRows.length ? initialRows.map((row) => ({
    chapterId: row.chapterIds?.[0] || "", knowledgePointId: row.knowledgePointIds?.[0] || "",
    questionType: row.questionTypes?.[0] || "", difficulty: row.difficulties?.[0] || "",
    count: row.count, pointsEach: row.pointsEach, sectionTitle: row.sectionTitle || "",
  })) : [emptyRow()]);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const chapters = useMemo(() => [...new Set(knowledgePoints.map((point) => point.chapter).filter(Boolean))], [knowledgePoints]);

  const update = (index, key, value) => {
    setRows((items) => items.map((row, rowIndex) => rowIndex === index ? { ...row, [key]: value } : row));
    setPreview(null);
  };
  const remove = (index) => { setRows((items) => items.filter((_, rowIndex) => rowIndex !== index)); setPreview(null); };
  const generate = async () => {
    setBusy(true); setError(""); setPreview(null);
    try {
      const seed = Date.now() % 2147483647;
      const result = await teacherApi.generatePaperPreview({ subjectId, seed, rows: rows.map(toApiRow) });
      setPreview({ ...result, seed });
    } catch (reason) {
      setError(reason.message || "自动组卷预览失败");
    } finally {
      setBusy(false);
    }
  };
  const coverageCount = Object.keys(preview?.coverage || {}).length;
  const apiRows = rows.map(toApiRow);

  return <div className="blueprintBuilder">
    <div className="blueprintRows">
      {rows.map((row, index) => <section key={index} className="blueprintRow" aria-label={`蓝图条件第 ${index + 1} 行`}>
        <header><strong>第 {index + 1} 组</strong><button type="button" aria-label={`删除第 ${index + 1} 组`} title="删除条件组" disabled={rows.length === 1} onClick={() => remove(index)}><Trash2 size={15} /></button></header>
        <label><span>章节</span><select aria-label={`第 ${index + 1} 行章节`} value={row.chapterId} onChange={(event) => update(index, "chapterId", event.target.value)}><option value="">不限章节</option>{chapters.map((chapter) => <option key={chapter}>{chapter}</option>)}</select></label>
        <label><span>知识点</span><select aria-label={`第 ${index + 1} 行知识点`} value={row.knowledgePointId} onChange={(event) => update(index, "knowledgePointId", event.target.value)}><option value="">不限知识点</option>{knowledgePoints.map((point) => <option key={point.id} value={point.id}>{point.name}</option>)}</select></label>
        <label><span>题型</span><select aria-label={`第 ${index + 1} 行题型`} value={row.questionType} onChange={(event) => update(index, "questionType", event.target.value)}>{TYPES.map((type) => <option key={type}>{type}</option>)}</select></label>
        <label><span>难度</span><select aria-label={`第 ${index + 1} 行难度`} value={row.difficulty} onChange={(event) => update(index, "difficulty", event.target.value)}>{DIFFICULTIES.map((difficulty) => <option key={difficulty}>{difficulty}</option>)}</select></label>
        <label><span>题量</span><input aria-label={`第 ${index + 1} 行题量`} type="number" min="1" max="100" value={row.count} onChange={(event) => update(index, "count", event.target.value)} /></label>
        <label><span>每题分值</span><input aria-label={`第 ${index + 1} 行每题分值`} type="number" min="0.5" step="0.5" value={row.pointsEach} onChange={(event) => update(index, "pointsEach", event.target.value)} /></label>
        <label className="blueprintSectionField"><span>大题标题</span><input aria-label={`第 ${index + 1} 行大题标题`} value={row.sectionTitle} onChange={(event) => update(index, "sectionTitle", event.target.value)} /></label>
      </section>)}
    </div>
    <div className="blueprintActions"><button type="button" className="assessmentIconText" onClick={() => { setRows((items) => [...items, emptyRow()]); setPreview(null); }}><Plus size={15} />添加条件组</button><button type="button" className="portalPrimary" disabled={busy || !subjectId} onClick={generate}><RefreshCw size={15} />{busy ? "正在生成..." : "生成预览"}</button></div>
    {error && <p className="assessmentEditorError" role="alert">{error}</p>}
    {preview && <div className="blueprintPreview">
      <div className="paperSummaryBand"><div><BarChart3 size={17} /><span>生成 {preview.questions?.length || 0} 题</span></div><strong>覆盖 {coverageCount} 个知识点</strong><span>重复风险 {preview.duplicateRisk ?? 0}</span><span>{Object.entries(preview.typeDistribution || {}).map(([name, count]) => `${name} ${count}`).join(" · ") || "暂无题型分布"}</span><span>{Object.entries(preview.difficultyDistribution || {}).map(([name, count]) => `${name} ${count}`).join(" · ") || "暂无难度分布"}</span></div>
      {preview.shortages?.length > 0 && <div className="blueprintShortages" role="alert"><div><AlertTriangle size={18} /><strong>蓝图条件存在缺题</strong></div>{preview.shortages.map((item) => <p key={item.row}>第 {item.row} 组还缺 {item.missing} 题（需要 {item.requested} 题，当前 {item.available} 题）</p>)}<small>系统未放宽任何章节、知识点、题型或难度条件</small></div>}
      <button type="button" className="portalPrimary" disabled={!preview.questions?.length || Boolean(preview.shortages?.length)} onClick={() => onApply(preview, apiRows)}>使用本次组卷结果</button>
    </div>}
  </div>;
}
