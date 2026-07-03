import { RefreshCw } from "lucide-react";


export function CaptchaInput({ value, onChange, captcha, loading, onRefresh, error }) {
  return (
    <div className="captchaField">
      <label htmlFor="captcha-code">验证码</label>
      <div className="captchaRow">
        <input id="captcha-code" value={value} onChange={(event) => onChange(event.target.value.toUpperCase())} autoComplete="off" maxLength={8} aria-invalid={Boolean(error)} />
        <button className="captchaImageButton" type="button" onClick={onRefresh} disabled={loading} aria-label="换一张验证码">
          {captcha?.image ? <img src={captcha.image} alt="图片验证码" /> : <span>加载中</span>}
        </button>
        <button className="captchaRefresh" type="button" onClick={onRefresh} disabled={loading} title="换一张" aria-label="刷新验证码"><RefreshCw size={17} /></button>
      </div>
      {error && <span className="fieldError">{error}</span>}
    </div>
  );
}
