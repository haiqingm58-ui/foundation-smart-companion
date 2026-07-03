import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthContext } from "../stores/AuthContext.jsx";
import { RoleGuard } from "./RoleGuard.jsx";


function renderGuard(user, allowedRoles = ["teacher"]) {
  return render(
    <AuthContext.Provider value={{ user, loading: false }}>
      <MemoryRouter initialEntries={["/teacher"]}>
        <Routes>
          <Route element={<RoleGuard allowedRoles={allowedRoles} />}>
            <Route path="/teacher" element={<div>教师页面</div>} />
          </Route>
          <Route path="/login" element={<div>登录页面</div>} />
          <Route path="/student" element={<div>学生首页</div>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}


test("未登录用户访问角色页面时跳转登录", () => {
  renderGuard(null);
  expect(screen.getByText("登录页面")).toBeInTheDocument();
});


test("学生不能通过地址进入教师页面", () => {
  renderGuard({ role: "student" });
  expect(screen.getByText("学生首页")).toBeInTheDocument();
});


test("教师可以进入教师页面", () => {
  renderGuard({ role: "teacher" });
  expect(screen.getByText("教师页面")).toBeInTheDocument();
});
