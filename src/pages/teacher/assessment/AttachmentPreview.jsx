import { FileImage, FunctionSquare, Table2 } from "lucide-react";


function attachmentRows(attachment) {
  if (Array.isArray(attachment.rows)) return attachment.rows;
  if (Array.isArray(attachment.table)) return attachment.table;
  if (Array.isArray(attachment.data)) return attachment.data;
  return [];
}

export function AttachmentPreview({ attachments = [] }) {
  if (!attachments.length) return <p className="assessmentInlineEmpty">暂无图表或公式附件</p>;
  return <div className="assessmentAttachments">
    {attachments.map((attachment, index) => {
      const key = attachment.id || `${attachment.kind || "attachment"}-${index}`;
      if (attachment.kind === "image") {
        return <figure key={key}><div><FileImage size={16} /><span>题图</span></div>{attachment.url || attachment.src ? <img src={attachment.url || attachment.src} alt={attachment.alt || `题目附件 ${index + 1}`} /> : <p>图片资源待补充</p>}</figure>;
      }
      if (attachment.kind === "table") {
        const rows = attachmentRows(attachment);
        return <figure key={key}><div><Table2 size={16} /><span>数据表</span></div><div className="assessmentAttachmentTable"><table><tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{(Array.isArray(row) ? row : [row]).map((cell, cellIndex) => <td key={cellIndex}>{String(cell ?? "")}</td>)}</tr>)}</tbody></table></div></figure>;
      }
      if (attachment.kind === "formula") {
        return <figure key={key}><div><FunctionSquare size={16} /><span>公式</span></div><code>{attachment.latex || attachment.text || attachment.value || "公式待补充"}</code></figure>;
      }
      return <figure key={key}><div><FileImage size={16} /><span>{attachment.label || attachment.kind || "附件"}</span></div><p>{attachment.text || attachment.name || "结构化附件"}</p></figure>;
    })}
  </div>;
}
