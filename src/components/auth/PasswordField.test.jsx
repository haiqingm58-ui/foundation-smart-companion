import { fireEvent, render, screen } from "@testing-library/react";
import { PasswordField } from "./PasswordField.jsx";


test("密码输入框可以显示和隐藏内容", () => {
  render(<PasswordField label="新密码" name="password" />);
  const input = screen.getByLabelText("新密码");
  expect(input).toHaveAttribute("type", "password");
  fireEvent.click(screen.getByRole("button", { name: "显示新密码" }));
  expect(input).toHaveAttribute("type", "text");
  expect(screen.getByRole("button", { name: "隐藏新密码" })).toBeInTheDocument();
});
