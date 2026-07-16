import { useEffect, useMemo, useState } from "react";
import { BookOpenCheck, Check, Layers3, Play, SlidersHorizontal, Target } from "lucide-react";
import { studentApi } from "../../../api/student.js";


const QUICK_COUNTS = [5, 10, 20];


export function RandomPracticeSetup({ onStarted }) {
  const [catalog, setCatalog] = useState(null);
  const [subjectId, setSubjectId] = useState("");
  const [mode, setMode] = useState("chapter");
  const [chapter, setChapter] = useState("");
  const [knowledgePointIds, setKnowledgePointIds] = useState([]);
  const [questionTypes, setQuestionTypes] = useState([]);
  const [difficulties, setDifficulties] = useState([]);
  const [count, setCount] = useState(5);
  const [customCount, setCustomCount] = useState(false);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  async function load(nextSubjectId = "") {
    setLoading(true);
    setError("");
    try {
      const data = await studentApi.assessmentCatalog(nextSubjectId);
      setCatalog(data);
      const selected = data.selectedSubjectId || nextSubjectId || data.subjects?.[0]?.id || "";
      setSubjectId(selected);
      setChapter(data.chapters?.[0]?.name || "");
      setKnowledgePointIds([]);
      setQuestionTypes([]);
      setDifficulties([]);
    } catch (reason) {
      setError(reason.message || "练习目录加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const selectedSubject = catalog?.subjects?.find((item) => item.id === subjectId);
  const availableCount = useMemo(() => {
    if (!catalog) return 0;
    if (mode === "chapter") return catalog.chapters.find((item) => item.name === chapter)?.questionCount || 0;
    const total = catalog.knowledgePoints
      .filter((item) => knowledgePointIds.includes(item.id))
      .reduce((sum, item) => sum + item.questionCount, 0);
    return Math.min(selectedSubject?.questionCount || total, total);
  }, [catalog, chapter, knowledgePointIds, mode, selectedSubject?.questionCount]);
  const invalidCount = count < 1 || count > availableCount;
  const invalidSelection = mode === "chapter" ? !chapter : knowledgePointIds.length < 1;

  async function selectSubject(nextSubjectId) {
    if (nextSubjectId === subjectId || loading) return;
    setSubjectId(nextSubjectId);
    await load(nextSubjectId);
  }

  function toggle(item, values, setValues, maximum) {
    if (values.includes(item)) setValues(values.filter((value) => value !== item));
    else if (!maximum || values.length < maximum) setValues([...values, item]);
  }

  async function start() {
    if (invalidCount || invalidSelection || starting) return;
    setStarting(true);
    setError("");
    try {
      const session = await studentApi.createPracticeSession({
        subjectId,
        mode,
        chapter: mode === "chapter" ? chapter : null,
        knowledgePointIds: mode === "knowledge_points" ? knowledgePointIds : [],
        questionTypes,
        difficulties,
        count,
      });
      window.localStorage.setItem("student-active-practice-session", session.id);
      onStarted?.(session);
    } catch (reason) {
      setError(reason.message || "随机练习创建失败");
    } finally {
      setStarting(false);
    }
  }

  if (loading && !catalog) return <div className="studentAssessmentLoading" aria-label="练习目录加载中"><span /><span /><span /></div>;
  if (!catalog) return <div className="studentAssessmentState"><p>{error || "练习目录暂不可用"}</p><button type="button" onClick={() => load()}>重试</button></div>;

  return <div className="randomPracticeSetup">
    <header className="studentAssessmentSectionHead"><div><span>自主巩固</span><h2>按章节或知识点生成专属练习</h2><p>随机抽题不会计入课程成绩，只用于掌握度与错题记录。</p></div><div className="studentAvailableBadge"><strong>{selectedSubject?.questionCount || 0}</strong><span>课程可用题目</span></div></header>

    <section className="studentSetupBand" aria-label="选择课程">
      <div className="studentSetupTitle"><BookOpenCheck size={18} /><div><strong>选择课程</strong><span>不同课程的章节、知识点和练习记录相互独立</span></div></div>
      <div className="studentSubjectSegments">{catalog.subjects.map((subject) => <button key={subject.id} type="button" aria-label={subject.title} aria-pressed={subjectId === subject.id} onClick={() => selectSubject(subject.id)}><span>{subject.title}</span><small>{subject.questionCount} 题</small></button>)}</div>
    </section>

    <div className="studentSetupGrid">
      <section className="studentSetupPanel">
        <div className="studentSetupTitle"><Target size={18} /><div><strong>抽题范围</strong><span>选择一个章节，或选择 1 至 3 个知识点</span></div></div>
        <div className="studentModeTabs" role="tablist" aria-label="抽题方式"><button type="button" role="tab" aria-selected={mode === "chapter"} onClick={() => setMode("chapter")}>按章节</button><button type="button" role="tab" aria-selected={mode === "knowledge_points"} onClick={() => setMode("knowledge_points")}>按知识点</button></div>
        {mode === "chapter" ? <><label className="studentSelectField"><span>选择章节</span><select aria-label="选择章节" value={chapter} onChange={(event) => setChapter(event.target.value)}>{catalog.chapters.map((item) => <option key={item.name} value={item.name}>{item.name}（{item.questionCount} 题）</option>)}</select></label><div className="studentCatalogPreview"><span>本课程可选知识点</span><div>{catalog.knowledgePoints.slice(0, 5).map((item) => <small key={item.id}>{item.name}</small>)}</div></div></> : <><div className="studentKnowledgeChoices">{catalog.knowledgePoints.map((item) => <label key={item.id} className={knowledgePointIds.includes(item.id) ? "selected" : ""}><input type="checkbox" aria-label={item.name} checked={knowledgePointIds.includes(item.id)} disabled={!knowledgePointIds.includes(item.id) && knowledgePointIds.length >= 3} onChange={() => toggle(item.id, knowledgePointIds, setKnowledgePointIds, 3)} /><span><strong>{item.name}</strong><small>{item.chapter} · {item.questionCount} 题</small></span>{knowledgePointIds.includes(item.id) && <Check size={15} />}</label>)}</div><p className="studentSelectionCount">已选 {knowledgePointIds.length} / 3 个知识点</p></>}
      </section>

      <section className="studentSetupPanel">
        <div className="studentSetupTitle"><SlidersHorizontal size={18} /><div><strong>题目偏好</strong><span>不选择时包含全部题型与难度</span></div></div>
        <fieldset className="studentFilterChecks"><legend>题型</legend>{catalog.questionTypes.map((item) => <label key={item.name}><input type="checkbox" aria-label={item.name} checked={questionTypes.includes(item.name)} onChange={() => toggle(item.name, questionTypes, setQuestionTypes)} /><span>{item.name}</span><small>{item.questionCount}</small></label>)}</fieldset>
        <fieldset className="studentFilterChecks"><legend>难度</legend>{catalog.difficulties.map((item) => <label key={item.name}><input type="checkbox" aria-label={item.name} checked={difficulties.includes(item.name)} onChange={() => toggle(item.name, difficulties, setDifficulties)} /><span>{item.name}</span><small>{item.questionCount}</small></label>)}</fieldset>
      </section>

      <section className="studentSetupPanel studentCountPanel">
        <div className="studentSetupTitle"><Layers3 size={18} /><div><strong>练习题量</strong><span>短时巩固建议 5 至 10 题</span></div></div>
        <div className="studentCountOptions">{QUICK_COUNTS.map((item) => <button type="button" key={item} aria-label={`${item} 题`} aria-pressed={!customCount && count === item} onClick={() => { setCustomCount(false); setCount(item); }}>{item}<small>题</small></button>)}<button type="button" aria-pressed={customCount} onClick={() => setCustomCount(true)}>自定义</button></div>
        {customCount && <label className="studentCustomCount"><span>自定义题量</span><input aria-label="自定义题量" type="number" min="1" max="100" value={count} onChange={(event) => setCount(Number(event.target.value))} /></label>}
        <div className="studentAvailability"><span>当前范围可用</span><strong>{availableCount} 题</strong></div>
        {invalidCount && <p className="studentSetupError">当前{mode === "chapter" ? "章节" : "知识点范围"}可用 {availableCount} 题，不能抽取 {count} 题</p>}
      </section>
    </div>
    {error && <p className="studentSetupError" role="alert">{error}</p>}
    <footer className="studentSetupFooter"><span>抽题后可随时退出，系统会保留当前会话和已保存答案。</span><button type="button" className="studentPrimaryButton" disabled={invalidCount || invalidSelection || starting} onClick={start}><Play size={17} />{starting ? "正在抽题" : "开始随机练习"}</button></footer>
  </div>;
}
