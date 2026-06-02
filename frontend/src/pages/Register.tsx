import { FormEvent, useState } from "react";
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
    } catch {
      setError("Registration failed — email may already exist");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h2 style={{ marginBottom: "1rem" }}>Create account</h2>
        <form onSubmit={handleSubmit}>
          <input
            className="input"
            placeholder="Full name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
          <input
            className="input"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className="input"
            type="password"
            placeholder="Password (min 8 chars)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
          {error && <p style={{ color: "var(--danger)", marginBottom: "0.75rem" }}>{error}</p>}
          <button className="btn" type="submit" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Creating…" : "Register"}
          </button>
        </form>
        <p style={{ marginTop: "1rem", color: "var(--muted)", fontSize: "0.9rem" }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
