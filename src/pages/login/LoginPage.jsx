import { useCallback, useEffect, useState } from "react";
import { Eye, EyeOff, LoaderCircle, LockKeyhole, LogIn, UserRound } from "lucide-react";
import { Navigate, useNavigate } from "react-router-dom";
import { authApi } from "../../api/auth.js";
import { CaptchaInput } from "../../components/auth/CaptchaInput.jsx";
import { LoginCarousel } from "../../components/auth/LoginCarousel.jsx";
import { RoleSelector } from "../../components/auth/RoleSelector.jsx";
import { useAuth } from "../../stores/AuthContext.jsx";
import "./LoginPage.css";


export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [role, setRole] = useState("student");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [captchaCode, setCaptchaCode] = useState("");
  const [captcha, setCaptcha] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [captchaLoading, setCaptchaLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState("");

  const refreshCaptcha = useCallback(async () => {
    setCaptchaLoading(true);
    setCaptchaCode("");
    try {
      setCaptcha(await authApi.captcha());
      setServerError("");
      return true;
    } catch (error) {
      setCaptcha(null);
      setServerError(error.message || "验证码加载失败，请重试");
      return false;
    } finally {
      setCaptchaLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshCaptcha();
  }, [refreshCaptcha]);

  if (user) return <Navigate to={`/${user.role}`} replace />;

  function validate() {
    const next = {};
    if (!username.trim()) next.username = "请输入登录账号";
    if (!password) next.password = "请输入登录密码";
    if (!captchaCode.trim()) next.captcha = "请输入验证码";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function onSubmit(event) {
    event.preventDefault();
    if (!validate() || !captcha?.captchaId) return;
    setLoading(true);
    setServerError("");
    try {
      const loggedInUser = await login({ username: username.trim(), password, role, captchaId: captcha.captchaId, captchaCode });
      navigate(`/${loggedInUser.role}`, { replace: true });
    } catch (error) {
      const message = error.code === "INVALID_CREDENTIALS"
        ? "验证码已通过，但账号或密码错误。已自动刷新验证码，请核对账号后重试。"
        : error.message || "登录失败，请稍后重试";
      const refreshed = await refreshCaptcha();
      if (refreshed) setServerError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="authPage">
      <header className="authBrand">
        <div className="collegeLogo"><img src={`${import.meta.env.BASE_URL}college-logo.jpg`} alt="湖南大学土木工程学院院徽" /></div>
        <h1>《基础工程》智慧学伴</h1>
        <p>面向土木工程基础工程课程的智能学习与教学管理平台</p>
      </header>

      <div className="authColumns">
        <LoginCarousel />
        <section className="loginCard" aria-labelledby="login-title">
          <div className="loginHeading">
            <span>欢迎回来</span>
            <h2 id="login-title">登录教学平台</h2>
            <p>请选择身份并使用学校分配的账号登录</p>
          </div>
          <RoleSelector value={role} onChange={(next) => { setRole(next); setServerError(""); }} />
          <form className="formalLoginForm" onSubmit={onSubmit} noValidate>
            <div className="loginField">
              <label htmlFor="login-username">登录账号</label>
              <div className="inputWithIcon"><UserRound size={18} /><input id="login-username" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" aria-invalid={Boolean(errors.username)} /></div>
              {errors.username && <span className="fieldError">{errors.username}</span>}
            </div>
            <div className="loginField">
              <label htmlFor="login-password">登录密码</label>
              <div className="inputWithIcon"><LockKeyhole size={18} /><input id="login-password" type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" aria-invalid={Boolean(errors.password)} /><button type="button" aria-label={showPassword ? "隐藏密码" : "显示密码"} onClick={() => setShowPassword((value) => !value)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>
              {errors.password && <span className="fieldError">{errors.password}</span>}
            </div>
            <CaptchaInput value={captchaCode} onChange={setCaptchaCode} captcha={captcha} loading={captchaLoading} onRefresh={refreshCaptcha} error={errors.captcha} />
            {serverError && <div className="loginServerError" role="alert">{serverError}</div>}
            <button className="loginSubmit" type="submit" disabled={loading || captchaLoading || !captcha}>
              {loading ? <LoaderCircle className="spin" size={19} /> : <LogIn size={19} />}
              {loading ? "正在登录" : "登录平台"}
            </button>
            <button className="loginReset" type="button" onClick={() => { setUsername(""); setPassword(""); setCaptchaCode(""); setErrors({}); setServerError(""); }}>重置</button>
          </form>
          <p className="authPrivacy">登录即表示你同意学校对课程学习数据进行教学用途处理。</p>
        </section>
      </div>
      <footer className="authCopyright">All Rights Reserved @2026</footer>
    </main>
  );
}
