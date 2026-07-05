import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";


export function PasswordField({ label, hint, className = "", ...inputProps }) {
  const [visible, setVisible] = useState(false);
  return (
    <label className={`passwordField ${className}`.trim()}>
      <span>{label}</span>
      <div className="passwordFieldControl">
        <input {...inputProps} type={visible ? "text" : "password"} aria-label={label} />
        <button type="button" onClick={() => setVisible((value) => !value)} aria-label={`${visible ? "隐藏" : "显示"}${label}`} title={visible ? "隐藏密码" : "显示密码"}>
          {visible ? <EyeOff size={17} /> : <Eye size={17} />}
        </button>
      </div>
      {hint && <small>{hint}</small>}
    </label>
  );
}
