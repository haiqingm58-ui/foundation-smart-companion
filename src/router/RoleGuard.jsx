import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../stores/AuthContext.jsx";


export function RoleGuard({ allowedRoles }) {
  const { user, loading } = useAuth();
  if (loading) {
    return <div className="platformLoading" role="status"><span />正在恢复登录状态</div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  if (!allowedRoles.includes(user.role)) return <Navigate to={`/${user.role}`} replace />;
  return <Outlet />;
}
