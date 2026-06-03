import { FormEvent, useState } from "react";
import axios from "axios";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(email, password, fullName || undefined);
      navigate("/");
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setError(String(err.response.data.detail));
      } else {
        setError("Registration failed — this email may already be in use.");
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

        <h2 className="auth-heading">Create your account</h2>
        <p className="auth-subheading">Start tracking expenses in minutes</p>

        <form onSubmit={handleSubmit}>
          <label className="field-label" htmlFor="fullName">Full name <span style={{ color: "var(--muted)" }}>(optional)</span></label>
          <div className="input-group" style={{ marginBottom: "0.75rem" }}>
            <span className="input-group-icon">
              <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
                <circle cx="10" cy="7" r="4" />
                <path d="M3 17c0-3.3 3.1-6 7-6s7 2.7 7 6" />
              </svg>
            </span>
            <input
              id="fullName"
              className="input"
              placeholder="Jane Smith"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              autoComplete="name"
            />
          </div>

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
          <div className="input-group" style={{ marginBottom: "0.35rem" }}>
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
              placeholder="Min. 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
              autoComplete="new-password"
            />
          </div>
          <p style={{ fontSize: "0.78rem", color: "var(--muted)", marginBottom: "1.25rem" }}>
            Use at least 8 characters for a strong password.
          </p>

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
                Creating account…
              </>
            ) : "Create account"}
          </button>
        </form>

        <div className="auth-divider" />
        <p style={{ color: "var(--muted)", fontSize: "0.875rem", textAlign: "center" }}>
          Already have an account?{" "}
          <Link to="/login" style={{ fontWeight: 600 }}>Sign in</Link>
        </p>
      </div>
    </div>
  );
}