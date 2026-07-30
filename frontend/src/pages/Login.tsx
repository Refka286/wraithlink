import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";

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
    <div className="mx-auto mt-16 max-w-sm">
      <div className="mb-8 text-center">
        <span className="text-2xl font-bold text-red-600">Aegis</span>
        <span className="text-2xl font-bold text-blue-500">Pen</span>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4 rounded border border-ink-700 bg-black p-6">
        <div>
          <label className="mb-1 block text-sm text-ink-300">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded border border-ink-600 bg-ink-900 px-3 py-2 text-ink-50 outline-none focus:border-blue-600"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-ink-300">Mot de passe</label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded border border-ink-600 bg-ink-900 px-3 py-2 text-ink-50 outline-none focus:border-blue-600"
          />
        </div>
        {error && <p className="text-sm text-red-500">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded bg-red-700 py-2 font-medium text-white hover:bg-red-600 disabled:opacity-50"
        >
          {submitting ? "connexion..." : "se connecter"}
        </button>
      </form>
    </div>
  );
}
