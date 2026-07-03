import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { AuthContext } from "../../stores/AuthContext.jsx";
import AdminApp from "./AdminApp.jsx";


vi.mock("../../api/admin.js", () => ({
  adminApi: {
    dashboard: vi.fn(async () => ({ teacherTotal: 3, studentTotal: 42, classTotal: 2, boundStudentTotal: 38, unboundStudentTotal: 4, disabledAccountTotal: 1 })),
    teachers: vi.fn(async () => ({ items: [{ id: "t1", name: "张老师", username: "teacher-zhang", number: "T001", college: "土木工程学院", status: "active" }], total: 1 })),
    students: vi.fn(async () => ({ items: [], total: 0 })),
    classes: vi.fn(async () => ({ items: [{ id: "c1", name: "土木2401班", grade: "2024", major: "土木工程", college: "土木工程学院" }], total: 1 })),
    bindings: vi.fn(async () => ({ items: [], total: 0 })),
    logs: vi.fn(async () => ({ items: [], total: 0 })),
    createClass: vi.fn(), createBindings: vi.fn(), createTeacherWithStudents: vi.fn(), updateAccountStatus: vi.fn(), resetPassword: vi.fn(), previewImport: vi.fn(),
  },
}));


function renderAdmin() {
  return render(
    <AuthContext.Provider value={{ user: { name: "系统管理员", role: "admin", college: "土木工程学院" }, logout: vi.fn() }}>
      <MemoryRouter initialEntries={["/admin"]}><AdminApp /></MemoryRouter>
    </AuthContext.Provider>,
  );
}


test("管理后台展示平台统计和完整导航", async () => {
  renderAdmin();
  expect(await screen.findByRole("heading", { name: "平台总览" })).toBeInTheDocument();
  expect(screen.getByText("42")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /^师生绑定$/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /^操作日志$/ })).toBeInTheDocument();
});


test("管理员可进入教师管理并打开创建向导", async () => {
  renderAdmin();
  await screen.findByRole("heading", { name: "平台总览" });
  fireEvent.click(screen.getByRole("button", { name: /教师管理/ }));
  expect(await screen.findByText("张老师")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "新增教师并绑定学生" }));
  expect(screen.getByRole("dialog", { name: "新增教师并绑定学生" })).toBeInTheDocument();
  expect(screen.getByText("1. 教师与班级")).toBeInTheDocument();
});
