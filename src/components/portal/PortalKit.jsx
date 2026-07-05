import { AlertCircle, ChevronRight, LogOut, Menu, Search, X } from "lucide-react";
import { useEffect, useState } from "react";


export function PortalShell({ roleLabel, navItems, active, onNavigate, user, onLogout, children }) {
  const [open, setOpen] = useState(false);
  const activeItem = navItems.find((item) => item.key === active) || navItems[0];
  return (
    <div className="portalShell">
      <aside className={`portalSidebar ${open ? "open" : ""}`} aria-label={`${roleLabel}导航`}>
        <div className="portalBrand">
          <img src={`${import.meta.env.BASE_URL}college-logo.jpg`} alt="湖南大学土木工程学院院徽" />
          <div><strong>《基础工程》智慧学伴</strong><span>{roleLabel}</span></div>
          <button className="portalMobileClose" type="button" onClick={() => setOpen(false)} aria-label="关闭导航"><X size={20} /></button>
        </div>
        <nav className="portalNav">
          {navItems.map(({ key, label, icon: Icon }) => (
            <button key={key} type="button" className={active === key ? "active" : ""} onClick={() => { onNavigate(key); setOpen(false); }} aria-current={active === key ? "page" : undefined}>
              <Icon size={19} /><span>{label}</span><ChevronRight className="portalNavArrow" size={16} />
            </button>
          ))}
        </nav>
        <div className="portalIdentity">
          <span className="portalAvatar">{user?.name?.slice(0, 1) || "用"}</span>
          <div><strong>{user?.name || "用户"}</strong><span>{user?.college || "土木工程学院"}</span></div>
          <button type="button" onClick={onLogout} aria-label="退出登录" title="退出登录"><LogOut size={18} /></button>
        </div>
      </aside>
      {open && <button type="button" className="portalScrim" aria-label="关闭导航" onClick={() => setOpen(false)} />}
      <main className="portalMain">
        <header className="portalTopbar">
          <button className="portalMenu" type="button" onClick={() => setOpen(true)} aria-label="打开导航"><Menu size={21} /></button>
          <div><span>{roleLabel}</span><strong>{activeItem?.label}</strong></div>
          <div className="portalTopUser"><span>{user?.name}</span><span className="portalAvatar">{user?.name?.slice(0, 1) || "用"}</span></div>
        </header>
        <div className="portalContent">{children}</div>
      </main>
    </div>
  );
}


export function PageHeading({ eyebrow, title, description, actions }) {
  return <header className="portalPageHeading"><div><span>{eyebrow}</span><h1>{title}</h1>{description && <p>{description}</p>}</div>{actions && <div className="portalHeadingActions">{actions}</div>}</header>;
}


export function StatGrid({ items }) {
  return <div className="portalStats">{items.map(({ label, value, note, icon: Icon, tone = "blue" }) => <article className={`portalStat ${tone}`} key={label}><div><span>{label}</span><strong>{value ?? 0}</strong><small>{note}</small></div>{Icon && <Icon size={22} />}</article>)}</div>;
}


export function Panel({ title, description, actions, children, className = "" }) {
  return <section className={`portalPanel ${className}`}><header><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{actions && <div className="portalPanelActions">{actions}</div>}</header><div className="portalPanelBody">{children}</div></section>;
}


export function SearchField({ value, onChange, placeholder = "搜索" }) {
  return <label className="portalSearch"><Search size={17} /><span className="srOnly">{placeholder}</span><input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} /></label>;
}


export function DataTable({ columns, rows, empty = "暂无数据" }) {
  if (!rows?.length) return <EmptyState title={empty} />;
  return <div className="portalTableWrap"><table className="portalTable"><thead><tr>{columns.map((column) => <th key={column.key}>{column.label}</th>)}</tr></thead><tbody>{rows.map((row) => <tr key={row.id}>{columns.map((column) => <td key={column.key} data-label={column.label}>{column.render ? column.render(row) : row[column.key] ?? "-"}</td>)}</tr>)}</tbody></table></div>;
}


export function EmptyState({ title, description = "数据会在完成相关操作后显示在这里。" }) {
  return <div className="portalEmpty"><AlertCircle size={24} /><strong>{title}</strong><p>{description}</p></div>;
}


export function LoadingState() {
  return <div className="portalSkeleton" role="status" aria-label="正在加载"><span /><span /><span /></div>;
}


export function ErrorState({ message, retry }) {
  return <div className="portalError" role="alert"><AlertCircle size={20} /><span>{message || "数据加载失败"}</span>{retry && <button type="button" onClick={retry}>重试</button>}</div>;
}


export function Modal({ title, children, onClose, footer, wide = false }) {
  useEffect(() => {
    const onKey = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return <div className="portalModalBackdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className={`portalModal ${wide ? "wide" : ""}`} role="dialog" aria-modal="true" aria-label={title}><header><h2>{title}</h2><button type="button" onClick={onClose} aria-label="关闭"><X size={20} /></button></header><div className="portalModalBody">{children}</div>{footer && <footer>{footer}</footer>}</section></div>;
}


export function ConfirmDialog({ title, message, confirmLabel = "确认", danger = false, onConfirm, onClose }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const confirm = async () => {
    setBusy(true);
    setError("");
    try { await onConfirm(); onClose(); } catch (reason) { setError(reason.message || "操作失败"); setBusy(false); }
  };
  return <Modal title={title} onClose={busy ? () => {} : onClose}><div className="portalConfirm"><p>{message}</p>{error && <p className="portalFormError">{error}</p>}<div className="portalFormActions"><button type="button" onClick={onClose} disabled={busy}>取消</button><button type="button" className={danger ? "portalDanger" : "portalPrimary"} onClick={confirm} disabled={busy}>{busy ? "正在处理..." : confirmLabel}</button></div></div></Modal>;
}


export function Toast({ message, tone = "success", onClose }) {
  useEffect(() => { const timer = setTimeout(onClose, 3200); return () => clearTimeout(timer); }, [onClose]);
  return <div className={`portalToast ${tone}`} role="status"><span>{message}</span><button type="button" onClick={onClose} aria-label="关闭提示"><X size={16} /></button></div>;
}


export function StatusBadge({ status }) {
  const map = { active: "正常", disabled: "停用", published: "已发布", draft: "草稿", closed: "已结束", submitted: "待批改", graded: "已批改", class: "班级可见", private: "仅自己" };
  return <span className={`portalBadge ${status}`}>{map[status] || status || "未知"}</span>;
}


export function Field({ label, children, hint }) {
  return <label className="portalField"><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>;
}
