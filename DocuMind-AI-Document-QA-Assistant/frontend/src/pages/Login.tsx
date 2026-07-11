import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }
  return (
    <section className="auth-screen">
      <form className="auth-card" onSubmit={submit}>
        <h1>DocuMind</h1>
        <p>Sign in to query your document library.</p>
        {error && <div className="error">{error}</div>}
        <label>Email<input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required /></label>
        <label>Password<input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required /></label>
        <button>Sign in</button>
        <span>New here? <Link to="/register">Create an account</Link></span>
      </form>
    </section>
  );
}
