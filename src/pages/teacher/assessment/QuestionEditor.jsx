import { AlertCircle, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { AttachmentPreview } from "./AttachmentPreview.jsx";
import { KnowledgePointPicker } from "./KnowledgePointPicker.jsx";


const QUESTION_TYPES = ["单项选择题", "多项选择题", "判断题", "填空题", "简答题", "计算题"];
const OPTION_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");


function initialOptions(item) {
  if (item?.options?.length) return item.options.map((option) => ({ ...option }));
  return OPTION_LABELS.slice(0, 4).map((label) => ({ label, text: "" }));
}

function initialAnswer(item, questionType) {
  if (questionType === "多项选择题") return Array.isArray(item?.correctAnswer) ? item.correctAnswer : [];
  if (questionType === "填空题") return Array.isArray(item?.correctAnswer) ? item.correctAnswer.join("\n") : "";
  if (questionType === "判断题") return item?.correctAnswer === false ? "false" : "true";
  return typeof item?.correctAnswer === "string" ? item.correctAnswer : "A";
}


function buildInitial(item, subjects) {
  const questionType = item?.questionType || "单项选择题";
  return {
    subjectId: item?.subjectId || subjects[0]?.id || "",
    chapter: item?.chapter || "",
    text: item?.text || "",
    questionType,
    difficulty: item?.difficulty || "基础",
    points: item?.points ?? 10,
    knowledgePointIds: item?.knowledgePoints?.map((point) => point.id) || [],
    options: initialOptions(item),
    answer: initialAnswer(item, questionType),
    explanation: item?.explanation || "",
    answerWordLimit: item?.answerWordLimit ?? 200,
  };
}


export function QuestionEditor({ initialValue, subjects = [], knowledgePoints = [], onSave, onCancel }) {
  const [draft, setDraft] = useState(() => buildInitial(initialValue, subjects));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const availablePoints = useMemo(
    () => knowledgePoints.filter((point) => point.subjectId === draft.subjectId && point.status !== "inactive"),
    [knowledgePoints, draft.subjectId],
  );

  useEffect(() => {
    if (!draft.subjectId && subjects[0]?.id) setDraft((value) => ({ ...value, subjectId: subjects[0].id }));
  }, [subjects, draft.subjectId]);

  const update = (key) => (event) => setDraft((value) => ({ ...value, [key]: event.target.value }));
  const updateOption = (index, text) => setDraft((value) => ({
    ...value,
    options: value.options.map((option, optionIndex) => optionIndex === index ? { ...option, text } : option),
  }));

  const changeType = (event) => {
    const questionType = event.target.value;
    setError("");
    setDraft((value) => ({
      ...value,
      questionType,
      options: questionType.includes("选择题") ? (value.options.length >= 2 ? value.options : initialOptions()) : [],
      answer: questionType === "多项选择题" ? [] : questionType === "填空题" ? "" : questionType === "判断题" ? "true" : questionType.includes("选择题") ? "A" : "",
      answerWordLimit: questionType === "简答题" ? (value.answerWordLimit || 200) : value.answerWordLimit,
    }));
  };

  const addOption = () => setDraft((value) => ({
    ...value,
    options: [...value.options, { label: OPTION_LABELS[value.options.length] || `${value.options.length + 1}`, text: "" }],
  }));

  const removeOption = (index) => setDraft((value) => {
    const options = value.options.filter((_, optionIndex) => optionIndex !== index).map((option, optionIndex) => ({ ...option, label: OPTION_LABELS[optionIndex] || `${optionIndex + 1}` }));
    const labels = new Set(options.map((option) => option.label));
    const answer = Array.isArray(value.answer) ? value.answer.filter((label) => labels.has(label)) : labels.has(value.answer) ? value.answer : options[0]?.label || "";
    return { ...value, options, answer };
  });

  const toggleMultipleAnswer = (label) => setDraft((value) => ({
    ...value,
    answer: value.answer.includes(label) ? value.answer.filter((item) => item !== label) : [...value.answer, label],
  }));

  const validateAndBuild = () => {
    if (draft.text.trim().length < 2) throw new Error("请输入完整题干");
    if (!draft.subjectId) throw new Error("请选择课程");
    if (draft.knowledgePointIds.length < 1 || draft.knowledgePointIds.length > 3) throw new Error("每道题必须关联 1 至 3 个知识点");
    const payload = {
      text: draft.text.trim(),
      questionType: draft.questionType,
      difficulty: draft.difficulty,
      points: Number(draft.points),
      chapter: draft.chapter.trim() || null,
      correctAnswer: null,
      explanation: draft.explanation.trim(),
      options: [],
      rubric: initialValue?.rubric || [],
      attachments: initialValue?.attachments || [],
      gradingMode: ["简答题", "计算题"].includes(draft.questionType) ? "manual" : "auto",
      answerWordLimit: draft.questionType === "简答题" ? Number(draft.answerWordLimit) : undefined,
      subjectId: draft.subjectId,
      knowledgePointIds: draft.knowledgePointIds,
    };
    if (draft.questionType.includes("选择题")) {
      payload.options = draft.options.filter((option) => option.text.trim()).map((option) => ({ label: option.label, text: option.text.trim() }));
      if (payload.options.length < 2) throw new Error("选择题至少需要两个有效选项");
      const validLabels = new Set(payload.options.map((option) => option.label));
      if (draft.questionType === "单项选择题") {
        if (!validLabels.has(draft.answer)) throw new Error("请选择一个有效的正确答案");
        payload.correctAnswer = draft.answer;
      } else {
        payload.correctAnswer = draft.answer.filter((label) => validLabels.has(label));
        if (!payload.correctAnswer.length) throw new Error("多项选择题至少选择一个正确答案");
      }
    } else if (draft.questionType === "判断题") {
      payload.correctAnswer = draft.answer === "true";
    } else if (draft.questionType === "填空题") {
      payload.correctAnswer = [...new Set(draft.answer.split(/\n|,|，/).map((item) => item.trim()).filter(Boolean))];
      if (!payload.correctAnswer.length) throw new Error("填空题至少需要一个可接受答案");
    } else if (draft.questionType === "简答题") {
      if (payload.answerWordLimit < 20 || payload.answerWordLimit > 2000) throw new Error("简答题字数限制必须在 20 至 2000 之间");
    }
    return payload;
  };

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    let payload;
    try {
      payload = validateAndBuild();
    } catch (reason) {
      setError(reason.message);
      return;
    }
    setBusy(true);
    try {
      await onSave(payload);
    } catch (reason) {
      setError(reason.message || "保存题目失败");
      setBusy(false);
    }
  };

  return <form className="assessmentEditor" onSubmit={submit}>
    <div className="assessmentEditorGrid">
      <label><span>课程</span><select aria-label="课程" value={draft.subjectId} onChange={(event) => setDraft((value) => ({ ...value, subjectId: event.target.value, knowledgePointIds: [] }))}>{subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.title}</option>)}</select></label>
      <label><span>章节</span><input aria-label="章节" value={draft.chapter} onChange={update("chapter")} placeholder="例如：第二章 土的渗透性" /></label>
      <label><span>题型</span><select aria-label="题型" value={draft.questionType} onChange={changeType}>{QUESTION_TYPES.map((type) => <option key={type}>{type}</option>)}</select></label>
      <label><span>难度</span><select aria-label="难度" value={draft.difficulty} onChange={update("difficulty")}><option>基础</option><option>中等</option><option>困难</option></select></label>
      <label><span>分值</span><input aria-label="分值" type="number" min="0.5" step="0.5" value={draft.points} onChange={update("points")} /></label>
    </div>
    <label className="assessmentFullField"><span>题干</span><textarea aria-label="题干" rows="5" value={draft.text} onChange={update("text")} placeholder="输入清晰、完整的题目内容" /></label>

    <section className="assessmentEditorSection" aria-labelledby="knowledge-point-editor-title">
      <div className="assessmentSectionTitle"><div><h3 id="knowledge-point-editor-title">关联知识点</h3><p>一题可关联 1–3 个知识点，用于随机练习、组卷和掌握度分析。</p></div></div>
      <KnowledgePointPicker points={availablePoints} selected={draft.knowledgePointIds} onChange={(knowledgePointIds) => setDraft((value) => ({ ...value, knowledgePointIds }))} />
    </section>

    {draft.questionType.includes("选择题") && <section className="assessmentEditorSection">
      <div className="assessmentSectionTitle"><div><h3>选项设置</h3><p>{draft.questionType === "多项选择题" ? "可选择多个正确答案" : "请选择一个正确答案"}</p></div><button type="button" className="assessmentIconText" onClick={addOption}><Plus size={15} />添加选项</button></div>
      <div className="assessmentChoiceEditor">{draft.options.map((option, index) => <div key={option.label}>
        <label className="assessmentCorrectChoice">
          <input aria-label={`${option.label} 为正确答案`} type={draft.questionType === "多项选择题" ? "checkbox" : "radio"} name="correctOption" checked={draft.questionType === "多项选择题" ? draft.answer.includes(option.label) : draft.answer === option.label} onChange={() => draft.questionType === "多项选择题" ? toggleMultipleAnswer(option.label) : setDraft((value) => ({ ...value, answer: option.label }))} />
          <span>{option.label}</span>
        </label>
        <input aria-label={`选项 ${option.label}`} value={option.text} onChange={(event) => updateOption(index, event.target.value)} placeholder={`选项 ${option.label} 内容`} />
        <button type="button" aria-label={`删除选项 ${option.label}`} title="删除选项" onClick={() => removeOption(index)} disabled={draft.options.length <= 2}><Trash2 size={15} /></button>
      </div>)}</div>
    </section>}

    {draft.questionType === "判断题" && <section className="assessmentEditorSection"><h3>标准答案</h3><div className="assessmentSegmented"><label><input type="radio" name="booleanAnswer" checked={draft.answer === "true"} onChange={() => setDraft((value) => ({ ...value, answer: "true" }))} />正确</label><label><input type="radio" name="booleanAnswer" checked={draft.answer === "false"} onChange={() => setDraft((value) => ({ ...value, answer: "false" }))} />错误</label></div></section>}

    {draft.questionType === "填空题" && <section className="assessmentEditorSection"><label className="assessmentFullField"><span>可接受答案</span><textarea aria-label="可接受答案" rows="4" value={draft.answer} onChange={update("answer")} placeholder="每行填写一个同义答案" /></label></section>}

    {draft.questionType === "简答题" && <section className="assessmentEditorSection"><div className="assessmentManualNotice"><ShieldCheck size={17} /><span><strong>教师人工批改</strong>主观题提交后进入教师批改队列。</span></div><label className="assessmentLimitField"><span>字数限制</span><input aria-label="字数限制" type="number" min="20" max="2000" value={draft.answerWordLimit} onChange={update("answerWordLimit")} /><small>20–2000 字</small></label></section>}

    {draft.questionType === "计算题" && <section className="assessmentEditorSection"><div className="assessmentManualNotice"><ShieldCheck size={17} /><span><strong>教师人工批改</strong>计算步骤、公式和单位由教师复核评分。</span></div></section>}

    <section className="assessmentEditorSection"><label className="assessmentFullField"><span>答案解析</span><textarea aria-label="答案解析" rows="4" value={draft.explanation} onChange={update("explanation")} placeholder="填写解题依据、易错点或评分说明" /></label></section>
    {initialValue?.attachments?.length > 0 && <section className="assessmentEditorSection"><h3>题目附件</h3><AttachmentPreview attachments={initialValue.attachments} /></section>}
    {error && <p className="assessmentEditorError" role="alert"><AlertCircle size={16} />{error}</p>}
    <div className="assessmentDrawerActions"><button type="button" onClick={onCancel}>取消</button><button className="portalPrimary" disabled={busy}>{busy ? "正在保存..." : "保存题目"}</button></div>
  </form>;
}
