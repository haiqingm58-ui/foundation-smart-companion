import { useState } from "react";
import { ClipboardCheck, Dices } from "lucide-react";
import { studentApi } from "../../../api/student.js";
import { AssessmentResult } from "./AssessmentResult.jsx";
import { ExamSession } from "./ExamSession.jsx";
import { MyPapers } from "./MyPapers.jsx";
import { PracticeSession } from "./PracticeSession.jsx";
import { RandomPracticeSetup } from "./RandomPracticeSetup.jsx";
import "./assessment.css";


export function AssessmentHome() {
  const [view, setView] = useState("practice");
  const [practiceSession, setPracticeSession] = useState(() => {
    const id = window.localStorage.getItem("student-active-practice-session");
    return id ? { id, resume: true } : null;
  });
  const [exam, setExam] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function openResult(submissionId) {
    setError("");
    try {
      const data = await studentApi.paperResult(submissionId);
      setResult({ kind: "paper", data });
    } catch (reason) {
      setError(reason.message || "结果加载失败");
    }
  }

  function resetPractice() {
    window.localStorage.removeItem("student-active-practice-session");
    setPracticeSession(null);
    setResult(null);
    setView("practice");
  }

  if (result) return <section className="pagePanel studentAssessmentPage"><AssessmentResult kind={result.kind} result={result.data} onBack={() => { setResult(null); setPracticeSession(null); setExam(null); }} onRetry={result.kind === "practice" ? resetPractice : undefined} /></section>;
  if (practiceSession) return <section className="pagePanel studentAssessmentPage"><PracticeSession sessionId={practiceSession.resume ? practiceSession.id : undefined} initialSession={practiceSession.resume ? undefined : practiceSession} onExit={() => setPracticeSession(null)} onFinished={(data) => setResult({ kind: "practice", data })} /></section>;
  if (exam) return <section className="pagePanel studentAssessmentPage"><ExamSession assignmentId={exam.assignmentId} title={exam.paper?.title} onExit={() => setExam(null)} onFinished={(data) => setResult({ kind: "paper", data })} /></section>;

  return <section className="pagePanel studentAssessmentPage">
    <header className="studentAssessmentPageHead"><div><span>练习中心</span><h1>课程评测与自主练习</h1><p>按课程知识体系随机巩固，或完成老师发布的正式试卷。</p></div><div className="studentAssessmentMode" role="tablist" aria-label="练习中心模块"><button type="button" role="tab" aria-selected={view === "practice"} onClick={() => setView("practice")}><Dices size={17} />随机练习</button><button type="button" role="tab" aria-selected={view === "papers"} onClick={() => setView("papers")}><ClipboardCheck size={17} />我的试卷</button></div></header>
    {error && <p className="studentSessionError" role="alert">{error}</p>}
    {view === "practice" ? <RandomPracticeSetup onStarted={setPracticeSession} /> : <MyPapers onStart={(assignmentId, paper) => setExam({ assignmentId, paper })} onViewResult={openResult} />}
  </section>;
}


export default AssessmentHome;
