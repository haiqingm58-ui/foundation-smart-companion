import { request } from "./client.js";

export const teacherApi = {
  dashboard: () => request("/teacher/dashboard"),
  students: (query = "") => request(`/teacher/students${query}`),
  resources: () => request("/teacher/resources"),
  uploadResource: (body) => request("/teacher/resources", { method: "POST", body }),
  questions: (query = "") => request(`/teacher/questions${query}`),
  createQuestion: (body) => request("/teacher/questions", { method: "POST", body }),
  updateQuestion: (id, body) => request(`/teacher/questions/${id}`, { method: "PUT", body }),
  deleteQuestion: (id) => request(`/teacher/questions/${id}`, { method: "DELETE" }),
  assignments: () => request("/teacher/assignments"),
  createAssignment: (body) => request("/teacher/assignments", { method: "POST", body }),
  analytics: () => request("/teacher/analytics"),
};
