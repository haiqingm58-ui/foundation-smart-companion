import { KeyRound } from "lucide-react";
import { useState } from "react";
import { authApi } from "../../api/auth.js";
import { useAuth } from "../../stores/AuthContext.jsx";


export function PasswordChangeGate({ children }) {
  const { user, refresh } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (!user?.mustChangePassword) return children;

  const submit = async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const currentPassword = form.get("currentPassword");
    const newPassword = form.get("newPassword");
    if (newPassword !== form.get("confirmPassword")) {
      setError("两次输入的新密码不一致");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await authApi.changePassword({ currentPassword, newPassword });
      await refresh();
    } catch (reason) {
      setError(reason.message || "密码修改失败");
      setBusy(false);
    }
  };

  return (
    <main className="passwordGate">
      <section aria-labelledby="password-gate-title">
        <img src={`${import.meta.env.BASE_URL}college-logo.jpg`} alt="湖南大学土木工程学院院徽" />
        <span><KeyRound size={18} />账号安全</span>
        <h1 id="password-gate-title">首次登录，请修改密码</h1>
        <p>新密码至少 8 位，并包含大写字母、小写字母和数字。修改完成后才能进入平台。</p>
        <form onSubmit={submit}>
          <label><span>当前密码</span><input type="password" name="currentPassword" required /></label>
          <label><span>新密码</span><input type="password" name="newPassword" minLength="8" required /></label>
          <label><span>确认新密码</span><input type="password" name="confirmPassword" minLength="8" required /></label>
          {error && <p className="portalFormError" role="alert">{error}</p>}
          <button type="submit" disabled={busy}>{busy ? "正在保存..." : "修改密码并进入平台"}</button>
        </form>
      </section>
    </main>
  );
}
