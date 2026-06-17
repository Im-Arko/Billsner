import { FormEvent, useState } from "react";
import axios from "axios";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

        .auth-root {
          min-height: 100vh;
          background: #0a0a0f;
          display: flex;
          font-family: 'DM Sans', sans-serif;
          color: #e8e6e0;
          overflow: hidden;
          position: relative;
        }

        /* Ambient glow */
        .auth-root::before {
          content: '';
          position: fixed;
          top: -20%;
          right: -10%;
          width: 600px;
          height: 600px;
          background: radial-gradient(circle, rgba(245,158,11,0.08) 0%, transparent 65%);
          pointer-events: none;
          z-index: 0;
        }
        .auth-root::after {
          content: '';
          position: fixed;
          bottom: -20%;
          left: -10%;
          width: 500px;
          height: 500px;
          background: radial-gradient(circle, rgba(59,130,246,0.05) 0%, transparent 65%);
          pointer-events: none;
          z-index: 0;
        }

        /* Left panel */
        .auth-panel-left {
          flex: 1;
          display: none;
          flex-direction: column;
          justify-content: space-between;
          padding: 3rem;
          background: linear-gradient(135deg, #0f0f18 0%, #0a0a0f 100%);
          border-right: 1px solid rgba(255,255,255,0.04);
          position: relative;
          z-index: 1;
        }
        @media (min-width: 900px) {
          .auth-panel-left { display: flex; }
        }

        .panel-grid {
          position: absolute;
          inset: 0;
          background-image:
            linear-gradient(#f5f5f5 1px, transparent 1px),
            linear-gradient(90deg, #f5f5f5 1px, transparent 1px);
          background-size: 48px 48px;
          pointer-events: none;
          
        }

        .panel-tagline {
          font-family: 'Syne', sans-serif;
          font-size: 2.5rem;
          font-weight: 700;
          line-height: 1.15;
          color: #f0ede6;
          letter-spacing: -0.03em;
        }
        .panel-tagline em {
          font-style: normal;
          color: #f59e0b;
        }

        .panel-features {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        .panel-feature {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          font-size: 0.875rem;
          color: rgba(232,230,224,0.55);
        }
        .panel-feature-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #f59e0b;
          flex-shrink: 0;
        }

        /* Right panel / form */
        .auth-panel-right {
          flex: 0 0 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 2rem 1.5rem;
          position: relative;
          z-index: 1;
        }
        @media (min-width: 900px) {
          .auth-panel-right { flex: 0 0 480px; }
        }

        .auth-form-box {
          width: 100%;
          max-width: 400px;
          animation: fadeUp 0.5s ease both;
        }
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(16px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        /* Wordmark */
        .wordmark {
          display: flex;
          align-items: center;
          gap: 0.6rem;
          margin-bottom: 2.5rem;
        }
        .wordmark-icon {
          width: 38px;
          height: 38px;
          background: linear-gradient(135deg, #f59e0b, #d97706);
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.1rem;
          box-shadow: 0 0 20px rgba(245,158,11,0.25);
        }
        .wordmark-text {
          font-family: 'Syne', sans-serif;
          font-size: 1.25rem;
          font-weight: 700;
          color: #f0ede6;
          letter-spacing: -0.02em;
        }
        .wordmark-sub {
          font-size: 0.7rem;
          font-weight: 400;
          color: rgba(232,230,224,0.4);
          letter-spacing: 0.08em;
          text-transform: uppercase;
          display: block;
          margin-top: 1px;
        }

        .form-heading {
          font-family: 'Syne', sans-serif;
          font-size: 1.75rem;
          font-weight: 700;
          color: #f0ede6;
          letter-spacing: -0.03em;
          margin: 0 0 0.375rem;
        }
        .form-sub {
          font-size: 0.875rem;
          color: rgba(232,230,224,0.45);
          margin: 0 0 2rem;
        }

        .field-group {
          margin-bottom: 1rem;
        }
        .field-label {
          display: block;
          font-size: 0.8rem;
          font-weight: 500;
          color: rgba(232,230,224,0.6);
          letter-spacing: 0.04em;
          text-transform: uppercase;
          margin-bottom: 0.4rem;
        }
        .field-wrap {
          position: relative;
        }
        .field-icon {
          position: absolute;
          left: 0.875rem;
          top: 50%;
          transform: translateY(-50%);
          color: rgba(232,230,224,0.25);
          pointer-events: none;
          display: flex;
        }
        .field-input {
          width: 100%;
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 10px;
          padding: 0.75rem 0.875rem 0.75rem 2.6rem;
          font-family: 'DM Sans', sans-serif;
          font-size: 0.9rem;
          color: #e8e6e0;
          outline: none;
          transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
          box-sizing: border-box;
        }
        .field-input::placeholder { color: rgba(232,230,224,0.2); }
        .field-input:focus {
          border-color: rgba(245,158,11,0.5);
          background: rgba(245,158,11,0.04);
          box-shadow: 0 0 0 3px rgba(245,158,11,0.08);
        }
        .field-action {
          position: absolute;
          right: 0.75rem;
          top: 50%;
          transform: translateY(-50%);
          background: none;
          border: none;
          cursor: pointer;
          color: rgba(232,230,224,0.3);
          display: flex;
          padding: 0.25rem;
          transition: color 0.15s;
        }
        .field-action:hover { color: rgba(232,230,224,0.6); }

        .error-box {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          background: rgba(248,113,113,0.08);
          border: 1px solid rgba(248,113,113,0.2);
          border-radius: 8px;
          padding: 0.6rem 0.875rem;
          font-size: 0.8rem;
          color: #fca5a5;
          margin-bottom: 1rem;
          animation: fadeUp 0.2s ease;
        }

        .submit-btn {
          width: 100%;
          padding: 0.8rem;
          background: linear-gradient(135deg, #f59e0b, #d97706);
          border: none;
          border-radius: 10px;
          font-family: 'Syne', sans-serif;
          font-size: 0.95rem;
          font-weight: 600;
          color: #0a0a0f;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          transition: opacity 0.15s, transform 0.15s, box-shadow 0.15s;
          box-shadow: 0 4px 20px rgba(245,158,11,0.25);
          margin-top: 1.25rem;
          letter-spacing: 0.01em;
        }
        .submit-btn:hover:not(:disabled) {
          opacity: 0.92;
          transform: translateY(-1px);
          box-shadow: 0 6px 24px rgba(245,158,11,0.35);
        }
        .submit-btn:active:not(:disabled) { transform: translateY(0); }
        .submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        .spinner-sm {
          width: 14px; height: 14px;
          border: 2px solid rgba(10,10,15,0.3);
          border-top-color: #0a0a0f;
          border-radius: 50%;
          animation: spin 0.6s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .auth-divider {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          margin: 1.5rem 0;
          color: rgba(232,230,224,0.15);
          font-size: 0.75rem;
        }
        .auth-divider::before, .auth-divider::after {
          content: '';
          flex: 1;
          height: 1px;
          background: rgba(255,255,255,0.06);
        }

        .auth-footer {
          text-align: center;
          font-size: 0.85rem;
          color: rgba(232,230,224,0.4);
        }
        .auth-link {
          color: #f59e0b;
          font-weight: 500;
          text-decoration: none;
        }
        .auth-link:hover { text-decoration: underline; }

        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

.auth-root {
  min-height: 100vh;
  background: #f5f5f4;
  display: flex;
  font-family: 'Inter', sans-serif;
  color: #0a0a0a;
}

.auth-root::before,
.auth-root::after {
  display: none;
}

.auth-panel-left {
  background: #ffffff;
  border-right: 1.5px solid #e5e5e5;
}


.panel-tagline {
  font-size: 3rem;
  font-weight: 900;
  letter-spacing: -0.05em;
  color: #0a0a0a;
  font-family: 'Inter', sans-serif;
}

.panel-tagline em {
  color: #2563eb;
}

.panel-feature {
  color: #525252;
  font-size: 0.9rem;
}

.panel-feature-dot {
  background: #2563eb;
}

.auth-form-box {
  background: #ffffff;
  border: 1.5px solid #e5e5e5;
  border-radius: 16px;
  padding: 2rem;
  max-width: 420px;
}

.wordmark {
  margin-bottom: 2rem;
}

.wordmark-icon {
  width: 44px;
  height: 44px;
  background: #2563eb;
  border-radius: 10px;
  box-shadow: none;
}

.wordmark-text {
  font-family: 'Inter', sans-serif;
  font-size: 1.4rem;
  font-weight: 900;
  color: #0a0a0a;
}

.wordmark-sub {
  color: #737373;
  letter-spacing: 0.08em;
}

.form-heading {
  font-family: 'Inter', sans-serif;
  font-size: 2rem;
  font-weight: 900;
  letter-spacing: -0.04em;
  color: #0a0a0a;
}

.form-sub {
  color: #737373;
}

.field-label {
  color: #525252;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.field-icon {
  color: #a3a3a3;
}

.field-input {
  width: 100%;
  background: #ffffff;
  border: 1.5px solid #d4d4d4;
  border-radius: 8px;
  color: #0a0a0a;
  font-family: 'Inter', sans-serif;
}

.field-input::placeholder {
  color: #a3a3a3;
}

.field-input:focus {
  border-color: #2563eb;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.08);
}

.field-action {
  color: #a3a3a3;
}

.field-action:hover {
  color: #404040;
}

.error-box {
  background: #fef2f2;
  border: 1.5px solid #fca5a5;
  color: #b91c1c;
  border-radius: 10px;
}

.submit-btn {
  background: #2563eb;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-family: 'Inter', sans-serif;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  box-shadow: none;
}

.submit-btn:hover:not(:disabled) {
  background: #1d4ed8;
  transform: none;
}

.submit-btn:disabled {
  opacity: 0.5;
}

.spinner-sm {
  border: 2px solid rgba(255,255,255,0.25);
  border-top-color: white;
}

.auth-divider {
  color: #a3a3a3;
}

.auth-divider::before,
.auth-divider::after {
  background: #e5e5e5;
}

.auth-footer {
  color: #737373;
}

.auth-link {
  color: #2563eb;
  font-weight: 600;
}

.auth-link:hover {
  text-decoration: underline;
}

      `}</style>

      <div className="auth-root">
        {/* Left decorative panel */}
        <div className="auth-panel-left">
          <div className="panel-grid" />
          <div>
            <p className="panel-tagline">
              Track every rupee.<br />
              <em>Effortlessly.</em>
            </p>
          </div>
          <div className="panel-features">
            {[
              "AI-powered bill scanning & categorisation",
              "Instant duplicate detection",
              "Natural language expense search",
              "Export to CSV, XLSX & PDF",
            ].map((f) => (
              <div className="panel-feature" key={f}>
                <span className="panel-feature-dot" />
                {f}
              </div>
            ))}
          </div>
        </div>

        {/* Right form panel */}
        <div className="auth-panel-right">
          <div className="auth-form-box">
            <div className="wordmark">
              <div className="wordmark-icon">🧾</div>
              <div>
                <div className="wordmark-text">Billsner</div>
                <span className="wordmark-sub">AI Expense Tracker</span>
              </div>
            </div>

            <h1 className="form-heading">Welcome back</h1>
            <p className="form-sub">Sign in to your account to continue</p>

            <form onSubmit={handleSubmit}>
              <div className="field-group">
                <label className="field-label" htmlFor="email">Email</label>
                <div className="field-wrap">
                  <span className="field-icon">
                    <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
                      <path d="M2 6l8 5 8-5M2 6v9a1 1 0 001 1h14a1 1 0 001-1V6a1 1 0 00-1-1H3a1 1 0 00-1 1z" />
                    </svg>
                  </span>
                  <input
                    id="email"
                    className="field-input"
                    type="email"
                    placeholder="you@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                  />
                </div>
              </div>

              <div className="field-group">
                <label className="field-label" htmlFor="password">Password</label>
                <div className="field-wrap">
                  <span className="field-icon">
                    <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="9" width="14" height="10" rx="2" />
                      <path d="M7 9V6a3 3 0 016 0v3" />
                    </svg>
                  </span>
                  <input
                    id="password"
                    className="field-input"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                    style={{ paddingRight: "2.6rem" }}
                  />
                  <button
                    type="button"
                    className="field-action"
                    onClick={() => setShowPassword((s) => !s)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? (
                      <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round"><path d="M17 10s-3 5-7 5-7-5-7-5 3-5 7-5 7 5 7 5z"/><circle cx="10" cy="10" r="2"/><line x1="2" y1="2" x2="18" y2="18"/></svg>
                    ) : (
                      <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round"><path d="M17 10s-3 5-7 5-7-5-7-5 3-5 7-5 7 5 7 5z"/><circle cx="10" cy="10" r="2"/></svg>
                    )}
                  </button>
                </div>
              </div>

              {error && (
                <div className="error-box" role="alert">
                  <svg width="13" height="13" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round"><circle cx="10" cy="10" r="8"/><path d="M10 6v4M10 14h.01"/></svg>
                  {error}
                </div>
              )}

              <button className="submit-btn" type="submit" disabled={loading}>
                {loading ? <><span className="spinner-sm" />Signing in…</> : "Sign in"}
              </button>
            </form>

            <div className="auth-divider">or</div>

            <p className="auth-footer">
              Don't have an account?{" "}
              <Link to="/register" className="auth-link">Create one free</Link>
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
