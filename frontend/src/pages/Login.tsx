import { FormEvent, useState } from "react";
import axios from "axios";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setError(String(err.response.data.detail));
      } else {
        setError("Invalid email or password. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <div className="auth-logo-icon">🧾</div>
          <div className="auth-logo-text">
            BillScan
            <span>AI Expense Tracker</span>
          </div>
        </div>

        <h2 className="auth-heading">Welcome back</h2>
        <p className="auth-subheading">Sign in to your account to continue</p>

        <form onSubmit={handleSubmit}>
          <label className="field-label" htmlFor="email">Email address</label>
          <div className="input-group" style={{ marginBottom: "0.75rem" }}>
            <span className="input-group-icon">
              <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
                <path d="M2 6l8 5 8-5M2 6v9a1 1 0 001 1h14a1 1 0 001-1V6a1 1 0 00-1-1H3a1 1 0 00-1 1z" />
              </svg>
            </span>
            <input
              id="email"
              className="input"
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          <label className="field-label" htmlFor="password">Password</label>
          <div className="input-group" style={{ marginBottom: "1.25rem" }}>
            <span className="input-group-icon">
              <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="9" width="14" height="10" rx="2" />
                <path d="M7 9V6a3 3 0 016 0v3" />
              </svg>
            </span>
            <input
              id="password"
              className="input"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>

          {error && (
            <div className="error-message">
              <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round">
                <circle cx="10" cy="10" r="8" />
                <path d="M10 6v4M10 14h.01" />
              </svg>
              {error}
            </div>
          )}

          <button className="btn" type="submit" disabled={loading} style={{ width: "100%", justifyContent: "center" }}>
            {loading ? (
              <>
                <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                Signing in…
              </>
            ) : "Sign in"}
          </button>
        </form>

        <div className="auth-divider" />
        <p style={{ color: "var(--muted)", fontSize: "0.875rem", textAlign: "center" }}>
          Don't have an account?{" "}
          <Link to="/register" style={{ fontWeight: 600 }}>Create one free</Link>
        </p>
      </div>
    </div>
  );
}