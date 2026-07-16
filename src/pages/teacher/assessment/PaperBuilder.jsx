import { ArrowDown, ArrowUp, FileCheck2, Filter, Plus, Save, Search, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { teacherApi } from "../../../api/teacher.js";
import { BlueprintBuilder } from "./BlueprintBuilder.jsx";


function selectedQuestion(source, index, existing = {}) {
  return {
    questionId: source.questionId || source.id,
    text: source.text || existing.text || "题目内容加载中",
    questionType: source.questionType || existing.questionType || "题目",
    difficulty: source.difficulty || existing.difficulty || "基础",
    chapter: source.chapter || existing.chapter || "",
    knowledgePoints: source.knowledgePoints || existing.knowledgePoints || [],
    sectionTitle: source.sectionTitle || existing.sectionTitle || "",
    sequence: index + 1,
    points: Number(source.points ?? existing.points ?? 10),
  };
}


export function PaperBuilder({ subjects = [], initialValue = null, onSaved, onCancel, onPublish }) {
  const [subjectId, setSubjectId] = useState(initialValue?.subjectId || subjects[0]?.id || "");
  const [title, setTitle] = useState(initialValue?.title || "");
  const [description, setDescription] = useState(initialValue?.description || "");
  const [durationMinutes, setDurationMinutes] = useState(initialValue?.durationMinutes || 60);
  const [status, setStatus] = useState(initialValue?.status === "ready" ? "ready" : "draft");
  const [mode, setMode] = useState(initialValue?.assemblyMode || "manual");
  const [questions, setQuestions] = useState([]);
  const [knowledgePoints, setKnowledgePoints] = useState([]);
  const [selected, setSelected] = useState([]);
  const [blueprintRows, setBlueprintRows] = useState(initialValue?.blueprintRows || []);
  const [assemblySeed, setAssemblySeed] = useState(initialValue?.seed ?? null);
  const [preview, setPreview] = useState(initialValue ? { shortages: initialValue.shortages || [] } : null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!subjectId) return;
    let current = true;
    setLoading(true);
    Promise.all([
      teacherApi.questions(`?subjectId=${encodeURIComponent(subjectId)}&status=active&pageSize=100`),
      teacherApi.knowledgePoints(`?subjectId=${encodeURIComponent(subjectId)}&status=active&pageSize=100`),
    ]).then(([questionData, pointData]) => {
      if (!current) return;
      const nextQuestions = questionData.items || [];
      setQuestions(nextQuestions);
      setKnowledgePoints(pointData.items || []);
      if (initialValue?.questions?.length) {
        const byId = new Map(nextQuestions.map((item) => [item.id, item]));
        setSelected(initialValue.questions.map((item, index) => selectedQuestion(item, index, byId.get(item.questionId) || {})));
      }
    }).catch((reason) => current && setError(reason.message || "组卷数据加载失败")).finally(() => current && setLoading(false));
    return () => { current = false; };
  }, [subjectId, initialValue?.id]);

  const filtered = useMemo(() => questions.filter((item) => !selected.some((record) => record.questionId === item.id) && `${item.text}${item.chapter}${item.questionType}`.includes(query.trim())), [questions, selected, query]);
  const totalPoints = selected.reduce((sum, item) => sum + Number(item.points || 0), 0);
  const coverage = new Set(selected.flatMap((item) => item.knowledgePoints?.map((point) => point.id) || []));
  const typeMix = Object.entries(selected.reduce((result, item) => ({ ...result, [item.questionType]: (result[item.questionType] || 0) + 1 }), {}));

  const add = (item) => setSelected((items) => [...items, selectedQuestion(item, items.length)]);
  const remove = (questionId) => setSelected((items) => items.filter((item) => item.questionId !== questionId).map((item, index) => ({ ...item, sequence: index + 1 })));
  const move = (index, offset) => setSelected((items) => {
    const target = index + offset;
    if (target < 0 || target >= items.length) return items;
    const next = [...items];
    [next[index], next[target]] = [next[target], next[index]];
    return next.map((item, itemIndex) => ({ ...item, sequence: itemIndex + 1 }));
  });
  const updateSelected = (questionId, key, value) => setSelected((items) => items.map((item) => item.questionId === questionId ? { ...item, [key]: value } : item));
  const applyBlueprint = (result, rows) => {
    const byId = new Map(questions.map((item) => [item.id, item]));
    setSelected((result.questions || []).map((item, index) => selectedQuestion(item, index, byId.get(item.questionId || item.id) || {})));
    setBlueprintRows(rows);
    setAssemblySeed(result.seed);
    setPreview(result);
  };

  const save = async () => {
    setError("");
    if (!title.trim()) { setError("请输入试卷标题"); return; }
    if (!selected.length) { setError("试卷至少需要一道题"); return; }
    if (preview?.shortages?.length) { setError("请先解决蓝图缺题再保存"); return; }
    const body = {
      subjectId, title: title.trim(), description: description.trim(), durationMinutes: Number(durationMinutes), status,
      assemblyMode: mode, seed: mode === "automatic" ? assemblySeed : null,
      blueprintRows: mode === "automatic" ? blueprintRows : [],
      questions: selected.map((item, index) => ({ questionId: item.questionId, sectionTitle: item.sectionTitle.trim(), sequence: index + 1, points: Number(item.points) })),
    };
    setBusy(true);
    try {
      const saved = initialValue?.id ? await teacherApi.updatePaper(initialValue.id, body) : await teacherApi.createPaper(body);
      onSaved?.(saved);
    } catch (reason) {
      setError(reason.message || "保存试卷失败");
      setBusy(false);
    }
  };

  return <div className="paperBuilder">
    <div className="paperBuilderMeta">
      <label className="paperTitleField"><span>试卷标题</span><input aria-label="试卷标题" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="例如：土力学第二单元测验" /></label>
      <label><span>课程</span><select aria-label="试卷课程" value={subjectId} onChange={(event) => { setSubjectId(event.target.value); setSelected([]); setPreview(null); }}>{subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.title}</option>)}</select></label>
      <label><span>限时</span><input aria-label="考试时长" type="number" min="1" max="1440" value={durationMinutes} onChange={(event) => setDurationMinutes(event.target.value)} /><small>分钟</small></label>
      <label><span>保存状态</span><select aria-label="保存状态" value={status} onChange={(event) => setStatus(event.target.value)}><option value="draft">草稿</option><option value="ready">可发布</option></select></label>
      <label className="paperDescriptionField"><span>试卷说明</span><input aria-label="试卷说明" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="考试范围或作答要求" /></label>
    </div>
    <div className="paperModeTabs" role="tablist" aria-label="组卷方式"><button type="button" role="tab" aria-selected={mode === "manual"} onClick={() => setMode("manual")}>手动选题</button><button type="button" role="tab" aria-selected={mode === "automatic"} onClick={() => setMode("automatic")}>自动组卷</button></div>

    {mode === "automatic" ? <BlueprintBuilder subjectId={subjectId} knowledgePoints={knowledgePoints} initialRows={blueprintRows} onApply={applyBlueprint} /> : <div className="paperQuestionSelector">
      <section className="paperAvailableQuestions"><header><div><Filter size={16} /><strong>课程题库</strong></div><label><Search size={15} /><input aria-label="搜索可选题目" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索题干、章节或题型" /></label></header>
        {loading ? <div className="assessmentLoading"><span /><span /><span /></div> : !filtered.length ? <div className="assessmentState"><p>没有更多可选题目</p></div> : <div className="assessmentTableWrap"><table className="assessmentTable paperCandidateTable"><thead><tr><th>题目</th><th>题型</th><th>难度</th><th>操作</th></tr></thead><tbody>{filtered.map((item) => <tr key={item.id}><td><strong>{item.text}</strong><small>{item.chapter || "未分章"}</small></td><td>{item.questionType}</td><td>{item.difficulty}</td><td><button type="button" className="assessmentIconText" onClick={() => add(item)}><Plus size={14} />加入试卷</button></td></tr>)}</tbody></table></div>}
      </section>
    </div>}

    <section className="paperSelectedQuestions"><header><div><FileCheck2 size={17} /><strong>试卷题目</strong><span>{selected.length} 题 · {totalPoints} 分</span></div></header>
      {!selected.length ? <div className="assessmentState"><p>尚未选择题目</p><span>从课程题库加入题目，或使用自动组卷生成。</span></div> : <div className="assessmentTableWrap"><table className="assessmentTable"><thead><tr><th>顺序</th><th>题目</th><th>大题标题</th><th>分值</th><th>操作</th></tr></thead><tbody>{selected.map((item, index) => <tr key={item.questionId}><td><div className="paperOrderButtons"><button type="button" aria-label={`上移 ${item.text}`} title="上移" disabled={index === 0} onClick={() => move(index, -1)}><ArrowUp size={14} /></button><button type="button" aria-label={`下移 ${item.text}`} title="下移" disabled={index === selected.length - 1} onClick={() => move(index, 1)}><ArrowDown size={14} /></button></div></td><td><strong>{item.text}</strong><small>{item.questionType} · {item.difficulty}</small></td><td><input aria-label={`章节 ${item.text}`} value={item.sectionTitle} onChange={(event) => updateSelected(item.questionId, "sectionTitle", event.target.value)} placeholder="例如：一、选择题" /></td><td><input className="paperPointsInput" aria-label={`分值 ${item.text}`} type="number" min="0.5" step="0.5" value={item.points} onChange={(event) => updateSelected(item.questionId, "points", event.target.value)} /></td><td><button type="button" className="assessmentIconButton danger" aria-label={`移除 ${item.text}`} title="移除题目" onClick={() => remove(item.questionId)}><Trash2 size={15} /></button></td></tr>)}</tbody></table></div>}
    </section>

    <div className="paperSummaryBand"><strong>{totalPoints} 分</strong><span>{selected.length} 道题</span><span>覆盖 {coverage.size} 个知识点</span><span>{typeMix.map(([name, count]) => `${name} ${count}`).join(" · ") || "暂无题型"}</span><span>{preview?.shortages?.length ? `缺题 ${preview.shortages.reduce((sum, item) => sum + item.missing, 0)} 道` : "无缺题"}</span></div>
    {error && <p className="assessmentEditorError" role="alert">{error}</p>}
    <div className="assessmentDrawerActions"><button type="button" onClick={onCancel}>取消</button>{onPublish && <button type="button" disabled={!initialValue?.id || !selected.length || Boolean(preview?.shortages?.length)} onClick={() => onPublish(initialValue)}>发布试卷</button>}<button type="button" className="portalPrimary" disabled={busy} onClick={save}><Save size={15} />{busy ? "正在保存..." : "保存试卷"}</button></div>
  </div>;
}
