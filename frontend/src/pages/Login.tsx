import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import { ErrorBanner } from "../components/Feedback";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "connexion impossible");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="flex min-h-screen items-center justify-center bg-night px-6"
      style={{
        backgroundImage:
          "radial-gradient(circle at 20% 20%, rgba(79,124,255,0.18), transparent 45%), radial-gradient(circle at 80% 10%, rgba(46,230,214,0.15), transparent 40%)",
      }}
    >
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <span className="eyebrow">Acces plateforme</span>
          <h1 className="text-3xl font-extrabold tracking-tight">
            <span className="grad-text">Wraithlink</span>
          </h1>
        </div>
        <form onSubmit={handleSubmit} className="panel space-y-4">
          <div>
            <label className="mb-1 block text-sm text-ink-300">Email</label>
            <input
              type="email"
              required
              placeholder="vous@exemple.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="field"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-ink-300">Mot de passe</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="field"
            />
          </div>
          {error && <ErrorBanner>{error}</ErrorBanner>}
          <button type="submit" disabled={submitting} className="btn-primary w-full">
            {submitting ? "connexion..." : "se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}
