import { request } from "./client.js";

export const authApi = {
  captcha: () => request("/auth/captcha"),
  login: (body) => request("/auth/login", { method: "POST", body }),
  me: () => request("/auth/me"),
  logout: () => request("/auth/logout", { method: "POST" }),
  changePassword: (body) => request("/auth/change-password", { method: "POST", body }),
};
