import { FileImage, FunctionSquare, Table2 } from "lucide-react";


function normalizedValue(question, value) {
  if (question.questionType === "多项选择题") return Array.isArray(value) ? value : [];
  if (question.questionType === "判断题") return typeof value === "boolean" ? value : null;
  return value ?? "";
}


export function QuestionAttachments({ attachments = [] }) {
  if (!attachments.length) return null;
  return <div className="studentQuestionAttachments">
    {attachments.map((attachment, index) => {
      const key = attachment.id || `${attachment.kind || "attachment"}-${index}`;
      if (attachment.kind === "image") {
        return <figure key={key}><figcaption><FileImage size={15} />题图</figcaption><img src={attachment.src || attachment.url} alt={attachment.alt || attachment.altText || `题目附件 ${index + 1}`} /></figure>;
      }
      if (attachment.kind === "table") {
        const rows = attachment.rows || attachment.table || [];
        return <figure key={key}><figcaption><Table2 size={15} />数据表</figcaption><div className="studentAttachmentTable"><table><tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{(Array.isArray(row) ? row : [row]).map((cell, cellIndex) => <td key={cellIndex}>{String(cell ?? "")}</td>)}</tr>)}</tbody></table></div></figure>;
      }
      if (attachment.kind === "formula") {
        return <figure key={key}><figcaption><FunctionSquare size={15} />公式</figcaption><code>{attachment.latex || attachment.text || ""}</code></figure>;
      }
      return null;
    })}
  </div>;
}


export function QuestionAnswer({ question, value, onChange, disabled = false }) {
  const current = normalizedValue(question, value);
  if (question.questionType === "单项选择题") {
    return <fieldset className="studentAnswerOptions" disabled={disabled}><legend>请选择一个答案</legend>{(question.options || []).map((option) => <label key={option.label}><input type="radio" name={`answer-${question.id}`} aria-label={`${option.label}. ${option.text}`} checked={current === option.label} onChange={() => onChange(option.label)} /><span className="studentOptionLabel">{option.label}</span><span>{option.text}</span></label>)}</fieldset>;
  }
  if (question.questionType === "多项选择题") {
    return <fieldset className="studentAnswerOptions" disabled={disabled}><legend>请选择所有正确答案</legend>{(question.options || []).map((option) => <label key={option.label}><input type="checkbox" aria-label={`${option.label}. ${option.text}`} checked={current.includes(option.label)} onChange={() => onChange(current.includes(option.label) ? current.filter((item) => item !== option.label) : [...current, option.label])} /><span className="studentOptionLabel">{option.label}</span><span>{option.text}</span></label>)}</fieldset>;
  }
  if (question.questionType === "判断题") {
    return <fieldset className="studentAnswerOptions studentBooleanOptions" disabled={disabled}><legend>请选择判断结果</legend><label><input type="radio" name={`answer-${question.id}`} aria-label="正确" checked={current === true} onChange={() => onChange(true)} /><span>正确</span></label><label><input type="radio" name={`answer-${question.id}`} aria-label="错误" checked={current === false} onChange={() => onChange(false)} /><span>错误</span></label></fieldset>;
  }
  if (question.questionType === "填空题") {
    return <label className="studentTextAnswer"><span>填写答案</span><input aria-label={question.text} disabled={disabled} value={current} onChange={(event) => onChange(event.target.value)} placeholder="请输入答案" /></label>;
  }
  const limit = question.answerWordLimit || 2000;
  return <label className="studentTextAnswer"><span>{question.questionType === "计算题" ? "写出计算步骤与结果" : "作答内容"}</span><textarea aria-label={question.text} disabled={disabled} maxLength={limit} value={current} onChange={(event) => onChange(event.target.value)} placeholder={question.questionType === "计算题" ? "请写明公式、代入过程、单位和结果" : "请按要点作答"} /><small>{String(current).length} / {limit} 字</small></label>;
}
