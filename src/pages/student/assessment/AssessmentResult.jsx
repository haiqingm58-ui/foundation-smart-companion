import { ArrowLeft, CheckCircle2, Clock3, EyeOff, MessageSquareText, RotateCcw, Trophy } from "lucide-react";


function scoreText(result) {
  if (result.score === null || result.score === undefined) return "待批改";
  return `${Number(result.score).toLocaleString()} / ${Number(result.maxScore || 0).toLocaleString()}`;
}


function answerText(answer) {
  if (Array.isArray(answer)) return answer.join("、");
  if (typeof answer === "boolean") return answer ? "正确" : "错误";
  return answer === null || answer === undefined || answer === "" ? "未作答" : String(answer);
}


export function AssessmentResult({ kind = "paper", result, onBack, onRetry }) {
  if (!result) return null;
  const pending = result.status === "pending_review";
  const showAnswers = kind === "practice" || Boolean(result.showAnswers);
  return <div className="studentAssessmentResult">
    <header className="studentResultHero">
      <div className={`studentResultIcon ${pending ? "pending" : "graded"}`}>{pending ? <Clock3 size={26} /> : <Trophy size={27} />}</div>
      <div><span>{kind === "practice" ? "随机练习结果" : "正式试卷结果"}</span><h2>{pending ? "等待老师批改" : "本次作答已完成"}</h2><p>{kind === "practice" ? "本次随机练习只更新知识点掌握度，不计入课程成绩" : pending ? "客观题结果已保存，主观题由老师完成复核后计入成绩。" : "成绩与教师反馈已同步到学习记录。"}</p></div>
      <div className="studentResultScore"><strong>{scoreText(result)}</strong><span>{pending ? "当前已评部分" : "得分"}</span></div>
    </header>

    {!showAnswers && <div className="studentAnswerPrivacy"><EyeOff size={18} /><div><strong>答案暂未公开</strong><span>是否公开答案由老师发布试卷时设置。</span></div></div>}

    {kind === "paper" && result.feedback && <section className="studentTeacherFeedback" aria-label="教师总评"><MessageSquareText size={20} /><div><strong>教师总评</strong><p>{result.feedback}</p></div></section>}

    <section className="studentResultQuestions"><header><strong>逐题情况</strong><span>{result.questions?.length || 0} 题</span></header>{(result.questions || []).map((question, index) => <article key={question.id || question.questionId || index}>
      <div className="studentResultQuestionHead"><span>{index + 1}</span><div><strong>{question.text}</strong><small>{question.questionType} · {question.points || question.maxScore || 0} 分</small></div><em>{question.status === "pending_review" || question.score === null ? "待批改" : `${question.score ?? 0} 分`}</em></div>
      <dl><div><dt>我的答案</dt><dd>{answerText(question.answer)}</dd></div>{showAnswers && question.correctAnswer !== undefined && <div><dt>正确答案</dt><dd>{answerText(question.correctAnswer)}</dd></div>}{question.feedback && <div><dt>反馈</dt><dd>{question.feedback}</dd></div>}{showAnswers && question.explanation && <div><dt>解析</dt><dd>{question.explanation}</dd></div>}</dl>
    </article>)}</section>

    <footer className="studentResultActions"><button type="button" className="studentSecondaryButton" onClick={onBack}><ArrowLeft size={16} />返回</button>{kind === "practice" && onRetry && <button type="button" className="studentPrimaryButton" onClick={onRetry}><RotateCcw size={16} />再练一组</button>}{!pending && <span><CheckCircle2 size={16} />结果已保存</span>}</footer>
  </div>;
}
