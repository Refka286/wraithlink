import { useEffect, useState, type FormEvent } from "react";
import { Users as UsersIcon } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { UserAccount, UserRole } from "../api/types";
import { Badge } from "../components/Badge";
import { EmptyState, ErrorBanner, Spinner } from "../components/Feedback";

export function Users() {
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("reader");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await api.get<UserAccount[]>("/users");
      setUsers(data);
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "chargement impossible");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    setCreating(true);
    try {
      await api.post<UserAccount>("/users", { email, password, role });
      setEmail("");
      setPassword("");
      setRole("reader");
      await refresh();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "creation impossible");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <span className="eyebrow">Administration</span>
        <h1 className="text-2xl font-extrabold text-ink-50">Utilisateurs</h1>
        <p className="mt-1 text-sm text-ink-400">
          Comptes ayant acces a la plateforme. Aucune auto-inscription ni reinitialisation de mot de
          passe : la creation de compte se fait exclusivement ici.
        </p>
      </div>

      {loading && <Spinner label="chargement des utilisateurs..." />}
      {loadError && <ErrorBanner>{loadError}</ErrorBanner>}

      {!loading && !loadError && (
        <div className="space-y-2">
          {users.map((account) => (
            <div key={account.id} className="panel flex items-center justify-between !p-4">
              <div>
                <p className="font-medium text-ink-50">{account.email}</p>
                <p className="text-xs text-ink-500">
                  cree le {new Date(account.created_at).toLocaleString("fr-FR")}
                </p>
              </div>
              <Badge tone={account.role === "admin" ? "warning" : account.role === "pentester" ? "accent" : "neutral"}>
                {account.role}
              </Badge>
            </div>
          ))}
          {users.length === 0 && (
            <EmptyState icon={UsersIcon} title="Aucun utilisateur" hint="Creez le premier compte ci-dessous." />
          )}
        </div>
      )}

      <section className="panel">
        <h2 className="mb-4 text-lg font-semibold text-ink-50">Nouvel utilisateur</h2>
        <form onSubmit={handleCreate} className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-sm text-ink-300">Email</label>
            <input
              required
              type="email"
              placeholder="collegue@exemple.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="field"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-ink-300">Mot de passe temporaire</label>
            <input
              required
              type="text"
              minLength={8}
              placeholder="8 caracteres minimum"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="field"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-ink-300">Role</label>
            <select value={role} onChange={(e) => setRole(e.target.value as UserRole)} className="field w-auto">
              <option value="reader">reader</option>
              <option value="pentester">pentester</option>
              <option value="admin">admin</option>
            </select>
          </div>
          <button type="submit" disabled={creating} className="btn-primary">
            {creating ? "creation..." : "creer l'utilisateur"}
          </button>
        </form>
        {formError && <div className="mt-3"><ErrorBanner>{formError}</ErrorBanner></div>}
      </section>
    </div>
  );
}
