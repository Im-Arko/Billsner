import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Dashboard from "./pages/Dashboard";
import Expenses from "./pages/Expenses";
import Login from "./pages/Login";
import Register from "./pages/Register";

function PrivateLayout({ children }: { children: React.ReactNode }) {
  const { logout, user } = useAuth();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>Bill Analyzer</h1>
        <NavLink to="/" end>
          Dashboard
        </NavLink>
        <NavLink to="/expenses">Expenses</NavLink>
        <div style={{ flex: 1 }} />
        <p style={{ fontSize: "0.8rem", color: "var(--muted)", padding: "0 1rem" }}>
          {user?.email}
        </p>
        <button
          className="btn btn-outline"
          style={{ margin: "0.5rem 1rem" }}
          onClick={logout}
        >
          Logout
        </button>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <p style={{ padding: "2rem" }}>Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  return <PrivateLayout>{children}</PrivateLayout>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/expenses"
        element={
          <ProtectedRoute>
            <Expenses />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
