import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "../stores/AuthContext.jsx";
import { RoleGuard } from "./RoleGuard.jsx";


const LoginPage = lazy(() => import("../pages/login/LoginPage.jsx"));
const TeacherApp = lazy(() => import("../pages/teacher/TeacherApp.jsx"));
const AdminApp = lazy(() => import("../pages/admin/AdminApp.jsx"));
const StudentExperience = lazy(() => import("../App.jsx").then((module) => ({ default: module.StudentExperience })));


function Loading() {
  return <div className="platformLoading" role="status"><span />正在加载页面</div>;
}


function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  return <Navigate to={user ? `/${user.role}` : "/login"} replace />;
}


function StudentRoute() {
  const { user, logout } = useAuth();
  return <StudentExperience currentUser={user} onLogout={logout} />;
}


export function RouterApp() {
  return (
    <BrowserRouter basename="/foundation-smart-companion">
      <AuthProvider>
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route path="/" element={<HomeRedirect />} />
            <Route path="/login" element={<LoginPage />} />
            <Route element={<RoleGuard allowedRoles={["student"]} />}>
              <Route path="/student/*" element={<StudentRoute />} />
            </Route>
            <Route element={<RoleGuard allowedRoles={["teacher"]} />}>
              <Route path="/teacher/*" element={<TeacherApp />} />
            </Route>
            <Route element={<RoleGuard allowedRoles={["admin"]} />}>
              <Route path="/admin/*" element={<AdminApp />} />
            </Route>
            <Route path="*" element={<HomeRedirect />} />
          </Routes>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}
