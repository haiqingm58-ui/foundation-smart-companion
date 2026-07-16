import { Download, FileText } from "lucide-react";
import { useState } from "react";
import { teacherApi } from "../../../api/teacher.js";


const VARIANTS = [
  { id: "questions", label: "试题" },
  { id: "answer-sheet", label: "答题卡" },
  { id: "answers", label: "参考答案" },
];


export function ExportMenu({ paperId, label = "导出试卷" }) {
  const [open, setOpen] = useState(false);
  return <div className="paperExportMenu">
    <button type="button" className="assessmentIconText" aria-expanded={open} onClick={() => setOpen((value) => !value)}><Download size={15} />{label}</button>
    {open && <div className="paperExportPopover" role="menu" aria-label="试卷导出格式">
      {VARIANTS.flatMap((variant) => ["docx", "pdf"].map((format) => <a key={`${variant.id}-${format}`} role="menuitem" aria-label={`${format === "docx" ? "Word" : "PDF"} ${variant.label}`} href={teacherApi.paperExportUrl(paperId, format, variant.id)} download>
        <FileText size={15} /><span><strong>{format === "docx" ? "Word" : "PDF"} {variant.label}</strong><small>{variant.id === "answers" ? "含参考答案和解析" : variant.id === "answer-sheet" ? "仅供学生作答" : "不包含答案"}</small></span>
      </a>))}
    </div>}
  </div>;
}
