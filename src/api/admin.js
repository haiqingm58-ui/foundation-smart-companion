import { request } from "./client.js";

export const adminApi = {
  dashboard: () => request("/admin/dashboard"),
  teachers: (query = "") => request(`/admin/teachers${query}`),
  students: (query = "") => request(`/admin/students${query}`),
  classes: () => request("/admin/classes"),
  createClass: (body) => request("/admin/classes", { method: "POST", body }),
  bindings: () => request("/admin/bindings"),
  createBindings: (body) => request("/admin/bindings/batch", { method: "POST", body }),
  createTeacherWithStudents: (body) => request("/admin/teachers-with-students", { method: "POST", body }),
  logs: (query = "") => request(`/admin/logs${query}`),
};
