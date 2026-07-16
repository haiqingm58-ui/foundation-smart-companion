import { request } from "./client.js";

export const studentApi = {
  dashboard: () => request("/student/dashboard"),
  report: () => request("/student/report"),
  assessmentCatalog: (subjectId = "") => request(`/student/assessment-catalog${subjectId ? `?subjectId=${encodeURIComponent(subjectId)}` : ""}`),
  exercises: (query = "") => request(`/student/exercises${query}`),
  saveProgress: (chapterId, body) => request(`/student/progress/${chapterId}`, { method: "PUT", body }),
  submitAttempt: (questionId, answer) => request(`/student/exercises/${questionId}/attempts`, { method: "POST", body: { answer } }),
  createPracticeSession: (body) => request("/student/practice-sessions", { method: "POST", body }),
  getPracticeSession: (sessionId) => request(`/student/practice-sessions/${sessionId}`),
  savePracticeAnswer: (sessionId, questionId, answer) => request(`/student/practice-sessions/${sessionId}/answers/${questionId}`, { method: "PUT", body: { answer } }),
  submitPracticeSession: (sessionId) => request(`/student/practice-sessions/${sessionId}/submit`, { method: "POST" }),
  papers: () => request("/student/papers"),
  startPaper: (assignmentId) => request(`/student/assignments/${assignmentId}/start`, { method: "POST" }),
  saveSubmissionAnswer: (submissionId, questionId, answer) => request(`/student/submissions/${submissionId}/answers/${questionId}`, { method: "PUT", body: { answer } }),
  submitPaper: (submissionId) => request(`/student/submissions/${submissionId}/submit`, { method: "POST" }),
  paperResult: (submissionId) => request(`/student/submissions/${submissionId}/result`),
};
