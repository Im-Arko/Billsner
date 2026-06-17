import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Dashboard from "./pages/Dashboard";
import Expenses from "./pages/Expenses";
import Login from "./pages/Login";
import Register from "./pages/Register";

function NavIcon({ d }: { d: string }) {
  return (
    <svg className="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  );
}

function PrivateLayout({ children }: { children: React.ReactNode }) {
  const { logout, user } = useAuth();
  const initials = user?.full_name
    ? user.full_name.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase()
    : user?.email?.[0]?.toUpperCase() ?? "U";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">🧾</div>
          <div className="sidebar-logo-text">
            <div className="sidebar-logo-name">Billsner</div>
            <div className="sidebar-logo-tagline">
              AI Expense Tracker
            </div>
          </div>
        </div>

        <span className="nav-section-label">Navigation</span>

        <NavLink to="/" end>
          <NavIcon d="M3 9.5L10 3l7 6.5V17a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z" />
          Dashboard
        </NavLink>
        <NavLink to="/expenses">
          <NavIcon d="M4 5h12M4 10h12M4 15h7" />
          Expenses
        </NavLink>

        <div className="sidebar-spacer" />

        <div className="sidebar-user">
          <div className="sidebar-user-row">
            <div className="sidebar-avatar">{initials}</div>
            <span className="sidebar-user-email">{user?.email}</span>
          </div>
          <button className="btn btn-outline btn-sm" style={{ width: "100%" }} onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return (
    <div className="loading-screen">
      <div className="spinner" />
      <span style={{ fontSize: "0.875rem" }}>Loading…</span>
    </div>
  );
  if (!user) return <Navigate to="/login" replace />;
  return <PrivateLayout>{children}</PrivateLayout>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/expenses" element={<ProtectedRoute><Expenses /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
  