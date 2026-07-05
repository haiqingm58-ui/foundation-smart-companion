import { request } from "./client.js";

export const adminApi = {
  dashboard: () => request("/admin/dashboard"),
  teachers: (query = "") => request(`/admin/teachers${query}`),
  createTeacher: (body) => request("/admin/teachers", { method: "POST", body }),
  updateTeacher: (id, body) => request(`/admin/teachers/${id}`, { method: "PUT", body }),
  students: (query = "") => request(`/admin/students${query}`),
  createStudent: (body) => request("/admin/students", { method: "POST", body }),
  updateStudent: (id, body) => request(`/admin/students/${id}`, { method: "PUT", body }),
  createStudentsBatch: (body) => request("/admin/students/batch", { method: "POST", body }),
  classes: () => request("/admin/classes"),
  createClass: (body) => request("/admin/classes", { method: "POST", body }),
  bindings: () => request("/admin/bindings"),
  createBindings: (body) => request("/admin/bindings/batch", { method: "POST", body }),
  createTeacherWithStudents: (body) => request("/admin/teachers-with-students", { method: "POST", body }),
  previewImport: (body) => request("/admin/import/preview", { method: "POST", body }),
  updateAccountStatus: (id, status) => request(`/admin/accounts/${id}/status`, { method: "PATCH", body: { status } }),
  resetPassword: (id, password) => request(`/admin/accounts/${id}/reset-password`, { method: "POST", body: { password } }),
  logs: (query = "") => request(`/admin/logs${query}`),
};
