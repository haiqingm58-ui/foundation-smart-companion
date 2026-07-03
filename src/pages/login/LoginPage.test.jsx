import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { AuthContext } from "../../stores/AuthContext.jsx";
import LoginPage from "./LoginPage.jsx";


vi.mock("../../api/auth.js", () => ({
  authApi: {
    captcha: vi.fn(async () => ({ captchaId: "captcha-1", image: "data:image/png;base64,AAA", expiresIn: 120 })),
  },
}));


function renderLogin(login = vi.fn(async () => ({ role: "student" }))) {
  return render(
    <AuthContext.Provider value={{ user: null, loading: false, login, logout: vi.fn(), refresh: vi.fn() }}>
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}


test("登录页展示院徽、三种 Emoji 角色和后端验证码", async () => {
  renderLogin();
  expect(screen.getByAltText("湖南大学土木工程学院院徽")).toBeInTheDocument();
  expect(screen.getByText("🧑‍🎓")).toBeInTheDocument();
  expect(screen.getByText("🧑‍🏫")).toBeInTheDocument();
  expect(screen.getByText("🛡️")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByAltText("图片验证码")).toHaveAttribute("src", "data:image/png;base64,AAA"));
});


test("空表单显示中文校验信息", async () => {
  renderLogin();
  await waitFor(() => expect(screen.getByAltText("图片验证码")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: "登录平台" }));
  expect(await screen.findByText("请输入登录账号")).toBeInTheDocument();
});


test("密码显示按钮和完整登录提交可用", async () => {
  const login = vi.fn(async () => ({ role: "student" }));
  renderLogin(login);
  fireEvent.change(screen.getByLabelText("登录账号"), { target: { value: "student" } });
  fireEvent.change(screen.getByLabelText("登录密码"), { target: { value: "Student-123" } });
  fireEvent.click(screen.getByRole("button", { name: "显示密码" }));
  expect(screen.getByLabelText("登录密码")).toHaveAttribute("type", "text");
  await waitFor(() => expect(screen.getByAltText("图片验证码")).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText("验证码"), { target: { value: "ABCD" } });
  fireEvent.click(screen.getByRole("button", { name: "登录平台" }));
  await waitFor(() => expect(login).toHaveBeenCalledWith({ username: "student", password: "Student-123", role: "student", captchaId: "captcha-1", captchaCode: "ABCD" }));
});
