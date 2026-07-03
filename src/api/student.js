import { request } from "./client.js";

export const studentApi = {
  dashboard: () => request("/student/dashboard"),
  report: () => request("/student/report"),
  exercises: (query = "") => request(`/student/exercises${query}`),
  saveProgress: (chapterId, body) => request(`/student/progress/${chapterId}`, { method: "PUT", body }),
  submitAttempt: (questionId, answer) => request(`/student/exercises/${questionId}/attempts`, { method: "POST", body: { answer } }),
};
