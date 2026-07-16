import { AlertTriangle, ArrowLeft, BookOpenCheck, CheckCircle2, Download, FileSpreadsheet, Upload } from "lucide-react";
import { useMemo, useState } from "react";
import { teacherApi } from "../../api/teacher.js";
import { DataTable, Modal } from "../../components/portal/PortalKit.jsx";


function distribution(rows, key) {
  return Object.entries(rows.reduce((result, row) => {
    const label = row[key] || "未分类";
    result[label] = (result[label] || 0) + 1;
    return result;
  }, {}));
}


export function QuestionImportModal({ close, done }) {
  const [stage, setStage] = useState(1);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const chapterDistribution = useMemo(() => distribution(preview?.rows || [], "chapter"), [preview]);
  const typeDistribution = useMemo(() => distribution(preview?.rows || [], "questionType"), [preview]);

  const chooseFile = (nextFile) => {
    setFile(nextFile || null);
    setPreview(null);
    setStage(1);
    setError("");
  };

  const previewFile = async (event) => {
    event.preventDefault();
    if (!file) { setError("请选择 XLSX 或 CSV 题库文件"); return; }
    setBusy(true); setError("");
    try {
      const body = new FormData();
      body.set("file", file);
      setPreview(await teacherApi.previewQuestionImport(body));
      setStage(2);
    } catch (reason) {
      setError(reason.message || "题库文件预检失败");
    } finally {
      setBusy(false);
    }
  };

  const commit = async () => {
    setBusy(true); setError("");
    try {
      const result = await teacherApi.importQuestions(preview.rows);
      done(result.created);
    } catch (reason) {
      setError(reason.message || "题库导入失败");
      setBusy(false);
    }
  };

  return (
    <Modal title="批量导入题库" onClose={busy ? () => {} : close} wide>
      <div className="portalSteps questionImportSteps">
        <span className={stage >= 1 ? "active" : ""}>1. 准备文件</span>
        <span className={stage >= 2 ? "active" : ""}>2. 数据预检</span>
        <span className={stage >= 3 ? "active" : ""}>3. 确认入库</span>
      </div>

      {stage === 1 && <form className="portalForm" onSubmit={previewFile}>
        <div className="questionImportModes" aria-label="题库入库方式">
          <section className="active"><FileSpreadsheet size={19} /><span><strong>批量表格导入教师自建题</strong><small>使用 XLSX 或 CSV，系统先预检再写入</small></span></section>
          <section><BookOpenCheck size={19} /><span><strong>共享 DOCX 题库由服务器统一入库</strong><small>无需重复上传原始文档</small></span></section>
        </div>
        <div className="questionImportIntro">
          <div><FileSpreadsheet size={21} /><span><strong>使用官方模板整理题目</strong><small>支持 XLSX 和 UTF-8 CSV，文件最大 5MB</small></span></div>
          <a className="portalSecondary" href={teacherApi.questionImportTemplateUrl()} download><Download size={16} />下载题库模板</a>
        </div>
        <label className={`portalDropzone ${dragging ? "dragging" : ""}`} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files[0]); }}>
          <Upload size={26} />
          <strong>{file ? file.name : "拖拽题库文件到此处，或点击选择"}</strong>
          <span>系统会先检查题型、答案、重复题干与公式内容，不会直接写入题库</span>
          <input aria-label="选择题库文件" type="file" accept=".xlsx,.csv" onChange={(event) => chooseFile(event.target.files[0])} />
        </label>
        {error && <p className="portalFormError" role="alert">{error}</p>}
        <div className="portalFormActions"><button type="button" onClick={close}>取消</button><button className="portalPrimary" disabled={busy || !file}>{busy ? "正在预检..." : "上传并预检"}</button></div>
      </form>}

      {stage === 2 && preview && <div className="portalForm">
        <div className="questionImportSummary" aria-label="题库预检统计">
          <div><span>文件题目</span><strong>{preview.summary.total}</strong></div>
          <div className="valid"><span>可导入</span><strong>{preview.summary.valid}</strong></div>
          <div className={preview.summary.errors ? "invalid" : "valid"}><span>需修正</span><strong>{preview.summary.errors}</strong></div>
        </div>
        <DataTable rows={(preview.rows || []).map((row, index) => ({ ...row, id: `preview-${index}` }))} columns={[
          { key: "text", label: "题干" }, { key: "questionType", label: "题型" },
          { key: "chapter", label: "章节" }, { key: "difficulty", label: "难度" }, { key: "points", label: "分值" },
        ]} empty="没有可导入的题目" />
        {preview.errors?.length > 0 && <div className="questionImportErrors" role="alert"><div><AlertTriangle size={18} /><strong>请修正以下内容后重新上传</strong></div>{preview.errors.map((item, index) => <p key={`${item.row}-${item.code}-${index}`}>第 {item.row} 行 · {item.field}：{item.reason}</p>)}</div>}
        {error && <p className="portalFormError" role="alert">{error}</p>}
        <div className="portalFormActions"><button type="button" onClick={() => setStage(1)}><ArrowLeft size={15} />重新选择</button><button className="portalPrimary" type="button" onClick={() => setStage(3)} disabled={busy || Boolean(preview.errors?.length) || !preview.rows?.length}>下一步：确认导入</button></div>
      </div>}

      {stage === 3 && preview && <div className="portalForm">
        <div className="questionImportConfirm"><CheckCircle2 size={28} /><div><strong>准备导入 {preview.rows.length} 道题</strong><p>确认后将一次性写入您的自建题库，任一题目冲突都会整批回滚。</p></div></div>
        <div className="portalTwoColumn questionImportDistribution">
          <section><h3>章节分布</h3>{chapterDistribution.map(([label, count]) => <p key={label}><span>{label}</span><strong>{count} 道</strong></p>)}</section>
          <section><h3>题型分布</h3>{typeDistribution.map(([label, count]) => <p key={label}><span>{label}</span><strong>{count} 道</strong></p>)}</section>
        </div>
        {error && <p className="portalFormError" role="alert">{error}</p>}
        <div className="portalFormActions"><button type="button" onClick={() => setStage(2)}><ArrowLeft size={15} />返回预检</button><button className="portalPrimary" type="button" onClick={commit} disabled={busy}>{busy ? "正在入库..." : "确认入库"}</button></div>
      </div>}
    </Modal>
  );
}
