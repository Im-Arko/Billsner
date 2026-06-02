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
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.data?.detail) {
        setError(String(error.response.data.detail));
      } else {
        setError("Invalid email or password");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h2 style={{ marginBottom: "1rem" }}>Sign in</h2>
        <form onSubmit={handleSubmit}>
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
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <p style={{ color: "var(--danger)", marginBottom: "0.75rem" }}>{error}</p>}
          <button className="btn" type="submit" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p style={{ marginTop: "1rem", color: "var(--muted)", fontSize: "0.9rem" }}>
          No account? <Link to="/register">Register</Link>
        </p>
      </div>
    </div>
  );
}
