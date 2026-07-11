import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ fullName: "", email: "", password: "" });
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await register(form.email, form.password, form.fullName);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    }
  }
  return (
    <section className="auth-screen">
      <form className="auth-card" onSubmit={submit}>
        <h1>Create account</h1>
        <p>Build a private document Q&A workspace.</p>
        {error && <div className="error">{error}</div>}
        <label>Name<input value={form.fullName} onChange={(e) => setForm({ ...form, fullName: e.target.value })} /></label>
        <label>Email<input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} type="email" required /></label>
        <label>Password<input value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} type="password" minLength={8} required /></label>
        <button>Create account</button>
        <span>Already registered? <Link to="/login">Sign in</Link></span>
      </form>
    </section>
  );
}
