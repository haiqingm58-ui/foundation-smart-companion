import { AlertCircle, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { teacherApi } from "../../../api/teacher.js";
import { KnowledgePointLibrary } from "./KnowledgePointLibrary.jsx";
import { PaperList } from "./PaperList.jsx";
import { QuestionBank } from "./QuestionBank.jsx";
import { SubmissionGrading } from "./SubmissionGrading.jsx";
import "./assessment.css";


export function TeacherAssessmentShell({ view, onOpenImport, notify }) {
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const result = await teacherApi.subjects();
      setSubjects(result.items || []);
    } catch (reason) {
      setError(reason.message || "课程目录加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="assessmentBootSkeleton" aria-label="教师题库工作台加载中"><span /><span /><span /></div>;
  if (error) return <div className="assessmentBootError"><AlertCircle size={22} /><h1>题库工作台暂时无法加载</h1><p>{error}</p><button type="button" onClick={load}><RefreshCw size={16} />重试</button></div>;
  if (!subjects.length) return <div className="assessmentBootError"><h1>尚未配置课程</h1><p>请联系管理员先启用课程目录。</p></div>;

  if (view === "knowledge-points") return <KnowledgePointLibrary subjects={subjects} notify={notify} />;
  if (view === "question-bank") return <QuestionBank subjects={subjects} onOpenImport={onOpenImport} notify={notify} />;
  if (view === "papers" || view === "exams") return <PaperList subjects={subjects} defaultTab={view} notify={notify} />;
  return <SubmissionGrading notify={notify} />;
}
