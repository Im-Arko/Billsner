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
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const passwordStrength = (() => {
    if (password.length === 0) return null;
    if (password.length < 6) return { level: 0, label: "Too short", color: "#f87171" };
    if (password.length < 8) return { level: 1, label: "Weak", color: "#fb923c" };
    if (/[A-Z]/.test(password) && /[0-9]/.test(password)) return { level: 3, label: "Strong", color: "#34d399" };
    return { level: 2, label: "Fair", color: "#fbbf24" };
  })();

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
        .auth-root::before {
          content: '';
          position: fixed;
          top: -20%;
          right: -10%;
          width: 600px; height: 600px;
          background: radial-gradient(circle, rgba(245,158,11,0.08) 0%, transparent 65%);
          pointer-events: none; z-index: 0;
        }
        .auth-root::after {
          content: '';
          position: fixed;
          bottom: -20%; left: -10%;
          width: 500px; height: 500px;
          background: radial-gradient(circle, rgba(59,130,246,0.05) 0%, transparent 65%);
          pointer-events: none; z-index: 0;
        }

        .auth-panel-left {
          flex: 1; display: none; flex-direction: column;
          justify-content: space-between; padding: 3rem;
          background: linear-gradient(135deg, #0f0f18 0%, #0a0a0f 100%);
          border-right: 1px solid rgba(255,255,255,0.04);
          position: relative; z-index: 1;
        }
        @media (min-width: 900px) { .auth-panel-left { display: flex; } }

        .panel-grid {
          position: absolute; inset: 0;
          background-image:
            linear-gradient(rgba(245,158,11,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(245,158,11,0.03) 1px, transparent 1px);
          background-size: 48px 48px; pointer-events: none;
        }
        .panel-tagline {
          font-family: 'Syne', sans-serif; font-size: 2.5rem;
          font-weight: 700; line-height: 1.15; color: #f0ede6; letter-spacing: -0.03em;
        }
        .panel-tagline em { font-style: normal; color: #f59e0b; }
        .panel-features { display: flex; flex-direction: column; gap: 1rem; }
        .panel-feature { display: flex; align-items: center; gap: 0.75rem; font-size: 0.875rem; color: rgba(232,230,224,0.55); }
        .panel-feature-dot { width: 6px; height: 6px; border-radius: 50%; background: #f59e0b; flex-shrink: 0; }

        .auth-panel-right {
          flex: 0 0 100%; display: flex; align-items: center;
          justify-content: center; padding: 2rem 1.5rem;
          position: relative; z-index: 1; overflow-y: auto;
        }
        @media (min-width: 900px) { .auth-panel-right { flex: 0 0 480px; } }

        .auth-form-box {
          width: 100%; max-width: 400px;
          animation: fadeUp 0.5s ease both; padding: 1rem 0;
        }
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(16px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        .wordmark { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 2.5rem; }
        .wordmark-icon {
          width: 38px; height: 38px;
          background: linear-gradient(135deg, #f59e0b, #d97706);
          border-radius: 10px; display: flex; align-items: center;
          justify-content: center; font-size: 1.1rem;
          box-shadow: 0 0 20px rgba(245,158,11,0.25);
        }
        .wordmark-text { font-family: 'Syne', sans-serif; font-size: 1.25rem; font-weight: 700; color: #f0ede6; letter-spacing: -0.02em; }
        .wordmark-sub { font-size: 0.7rem; font-weight: 400; color: rgba(232,230,224,0.4); letter-spacing: 0.08em; text-transform: uppercase; display: block; margin-top: 1px; }

        .form-heading { font-family: 'Syne', sans-serif; font-size: 1.75rem; font-weight: 700; color: #f0ede6; letter-spacing: -0.03em; margin: 0 0 0.375rem; }
        .form-sub { font-size: 0.875rem; color: rgba(232,230,224,0.45); margin: 0 0 2rem; }

        .field-group { margin-bottom: 1rem; }
        .field-label { display: block; font-size: 0.8rem; font-weight: 500; color: rgba(232,230,224,0.6); letter-spacing: 0.04em; text-transform: uppercase; margin-bottom: 0.4rem; }
        .field-optional { color: rgba(232,230,224,0.25); font-size: 0.75rem; text-transform: none; letter-spacing: 0; }
        .field-wrap { position: relative; }
        .field-icon { position: absolute; left: 0.875rem; top: 50%; transform: translateY(-50%); color: rgba(232,230,224,0.25); pointer-events: none; display: flex; }
        .field-input {
          width: 100%; background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.08); border-radius: 10px;
          padding: 0.75rem 0.875rem 0.75rem 2.6rem;
          font-family: 'DM Sans', sans-serif; font-size: 0.9rem; color: #e8e6e0;
          outline: none; transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
          box-sizing: border-box;
        }
        .field-input::placeholder { color: rgba(232,230,224,0.2); }
        .field-input:focus { border-color: rgba(245,158,11,0.5); background: rgba(245,158,11,0.04); box-shadow: 0 0 0 3px rgba(245,158,11,0.08); }
        .field-action { position: absolute; right: 0.75rem; top: 50%; transform: translateY(-50%); background: none; border: none; cursor: pointer; color: rgba(232,230,224,0.3); display: flex; padding: 0.25rem; transition: color 0.15s; }
        .field-action:hover { color: rgba(232,230,224,0.6); }

        .strength-bar { display: flex; gap: 3px; margin-top: 0.4rem; }
        .strength-seg { height: 3px; flex: 1; border-radius: 2px; background: rgba(255,255,255,0.07); transition: background 0.3s; }
        .strength-label { font-size: 0.72rem; color: rgba(232,230,224,0.4); margin-top: 0.25rem; }

        .error-box {
          display: flex; align-items: center; gap: 0.5rem;
          background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.2);
          border-radius: 8px; padding: 0.6rem 0.875rem;
          font-size: 0.8rem; color: #fca5a5; margin-bottom: 1rem;
          animation: fadeUp 0.2s ease;
        }

        .submit-btn {
          width: 100%; padding: 0.8rem;
          background: linear-gradient(135deg, #f59e0b, #d97706);
          border: none; border-radius: 10px;
          font-family: 'Syne', sans-serif; font-size: 0.95rem; font-weight: 600;
          color: #0a0a0f; cursor: pointer;
          display: flex; align-items: center; justify-content: center; gap: 0.5rem;
          transition: opacity 0.15s, transform 0.15s, box-shadow 0.15s;
          box-shadow: 0 4px 20px rgba(245,158,11,0.25);
          margin-top: 1.25rem; letter-spacing: 0.01em;
        }
        .submit-btn:hover:not(:disabled) { opacity: 0.92; transform: translateY(-1px); box-shadow: 0 6px 24px rgba(245,158,11,0.35); }
        .submit-btn:active:not(:disabled) { transform: translateY(0); }
        .submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        .spinner-sm { width: 14px; height: 14px; border: 2px solid rgba(10,10,15,0.3); border-top-color: #0a0a0f; border-radius: 50%; animation: spin 0.6s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }

        .auth-divider { display: flex; align-items: center; gap: 0.75rem; margin: 1.5rem 0; color: rgba(232,230,224,0.15); font-size: 0.75rem; }
        .auth-divider::before, .auth-divider::after { content: ''; flex: 1; height: 1px; background: rgba(255,255,255,0.06); }

        .auth-footer { text-align: center; font-size: 0.85rem; color: rgba(232,230,224,0.4); }
        .auth-link { color: #f59e0b; font-weight: 500; text-decoration: none; }
        .auth-link:hover { text-decoration: underline; }
      `}</style>

      <div className="auth-root">
        <div className="auth-panel-left">
          <div className="panel-grid" />
          <p className="panel-tagline">Up and running<br /><em>in minutes.</em></p>
          <div className="panel-features">
            {[
              "Free forever — no credit card needed",
              "AI reads your bills automatically",
              "Supports photos, PDFs and scans",
              "Team-ready with role-based access",
            ].map((f) => (
              <div className="panel-feature" key={f}>
                <span className="panel-feature-dot" />
                {f}
              </div>
            ))}
          </div>
        </div>

        <div className="auth-panel-right">
          <div className="auth-form-box">
            <div className="wordmark">
              <div className="wordmark-icon">🧾</div>
              <div>
                <div className="wordmark-text">BillScan</div>
                <span className="wordmark-sub">AI Expense Tracker</span>
              </div>
            </div>

            <h1 className="form-heading">Create your account</h1>
            <p className="form-sub">Start tracking expenses in minutes</p>

            <form onSubmit={handleSubmit}>
              <div className="field-group">
                <label className="field-label" htmlFor="fullName">
                  Full name <span className="field-optional">(optional)</span>
                </label>
                <div className="field-wrap">
                  <span className="field-icon">
                    <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="10" cy="7" r="4" /><path d="M3 17c0-3.3 3.1-6 7-6s7 2.7 7 6" />
                    </svg>
                  </span>
                  <input id="fullName" className="field-input" placeholder="Jane Smith" value={fullName} onChange={(e) => setFullName(e.target.value)} autoComplete="name" />
                </div>
              </div>

              <div className="field-group">
                <label className="field-label" htmlFor="email">Email address</label>
                <div className="field-wrap">
                  <span className="field-icon">
                    <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
                      <path d="M2 6l8 5 8-5M2 6v9a1 1 0 001 1h14a1 1 0 001-1V6a1 1 0 00-1-1H3a1 1 0 00-1 1z" />
                    </svg>
                  </span>
                  <input id="email" className="field-input" type="email" placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
                </div>
              </div>

              <div className="field-group">
                <label className="field-label" htmlFor="password">Password</label>
                <div className="field-wrap">
                  <span className="field-icon">
                    <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="9" width="14" height="10" rx="2" /><path d="M7 9V6a3 3 0 016 0v3" />
                    </svg>
                  </span>
                  <input
                    id="password" className="field-input"
                    type={showPassword ? "text" : "password"}
                    placeholder="Min. 8 characters"
                    value={password} onChange={(e) => setPassword(e.target.value)}
                    minLength={8} required autoComplete="new-password"
                    style={{ paddingRight: "2.6rem" }}
                  />
                  <button type="button" className="field-action" onClick={() => setShowPassword((s) => !s)} aria-label={showPassword ? "Hide" : "Show"}>
                    {showPassword
                      ? <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round"><path d="M17 10s-3 5-7 5-7-5-7-5 3-5 7-5 7 5 7 5z"/><circle cx="10" cy="10" r="2"/><line x1="2" y1="2" x2="18" y2="18"/></svg>
                      : <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round"><path d="M17 10s-3 5-7 5-7-5-7-5 3-5 7-5 7 5 7 5z"/><circle cx="10" cy="10" r="2"/></svg>
                    }
                  </button>
                </div>
                {passwordStrength && (
                  <>
                    <div className="strength-bar">
                      {[0,1,2].map((i) => (
                        <div key={i} className="strength-seg" style={{ background: i <= passwordStrength.level - 1 ? passwordStrength.color : undefined }} />
                      ))}
                    </div>
                    <div className="strength-label" style={{ color: passwordStrength.color }}>{passwordStrength.label}</div>
                  </>
                )}
              </div>

              {error && (
                <div className="error-box" role="alert">
                  <svg width="13" height="13" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round"><circle cx="10" cy="10" r="8"/><path d="M10 6v4M10 14h.01"/></svg>
                  {error}
                </div>
              )}

              <button className="submit-btn" type="submit" disabled={loading}>
                {loading ? <><span className="spinner-sm" />Creating account…</> : "Create account"}
              </button>
            </form>

            <div className="auth-divider">or</div>

            <p className="auth-footer">
              Already have an account?{" "}
              <Link to="/login" className="auth-link">Sign in</Link>
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
