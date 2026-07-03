import { request } from "./client.js";

export const teacherApi = {
  dashboard: () => request("/teacher/dashboard"),
  classes: () => request("/teacher/classes"),
  students: (query = "") => request(`/teacher/students${query}`),
  resources: () => request("/teacher/resources"),
  uploadResource: (body) => request("/teacher/resources", { method: "POST", body }),
  deleteResource: (id) => request(`/teacher/resources/${id}`, { method: "DELETE" }),
  questions: (query = "") => request(`/teacher/questions${query}`),
  createQuestion: (body) => request("/teacher/questions", { method: "POST", body }),
  updateQuestion: (id, body) => request(`/teacher/questions/${id}`, { method: "PUT", body }),
  deleteQuestion: (id) => request(`/teacher/questions/${id}`, { method: "DELETE" }),
  assignments: () => request("/teacher/assignments"),
  createAssignment: (body) => request("/teacher/assignments", { method: "POST", body }),
  submissions: (query = "") => request(`/teacher/submissions${query}`),
  gradeSubmission: (id, body) => request(`/teacher/submissions/${id}/grade`, { method: "PUT", body }),
  analytics: () => request("/teacher/analytics"),
  notices: () => request("/teacher/notices"),
  createNotice: (body) => request("/teacher/notices", { method: "POST", body }),
};
