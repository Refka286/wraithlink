import { useEffect, useState, type FormEvent } from "react";
import { KeyRound, Trash2 } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { Credential } from "../api/types";
import { EmptyState, ErrorBanner, Spinner } from "../components/Feedback";

export function Credentials() {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [label, setLabel] = useState("");
  const [domain, setDomain] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await api.get<Credential[]>("/credentials");
      setCredentials(data);
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
      await api.post<Credential>("/credentials", {
        label,
        domain: domain || null,
        username,
        password,
      });
      setLabel("");
      setDomain("");
      setUsername("");
      setPassword("");
      await refresh();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "creation impossible");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(credentialId: string) {
    setFormError(null);
    try {
      await api.delete(`/credentials/${credentialId}`);
      await refresh();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "suppression impossible");
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <span className="eyebrow">Coffre-fort</span>
        <h1 className="text-2xl font-extrabold text-ink-50">Identifiants</h1>
        <p className="mt-1 text-sm text-ink-400">
          Jeux d'identifiants Active Directory chiffres (Fernet) au repos. Les mots de passe ne
          sont jamais renvoyes par l'API ni affiches ici - ils ne sont dechiffres que cote serveur,
          au moment precis ou un outil (netexec, bloodhound) est invoque.
        </p>
      </div>

      {loading && <Spinner label="chargement des identifiants..." />}
      {loadError && <ErrorBanner>{loadError}</ErrorBanner>}

      {!loading && !loadError && (
        <div className="space-y-2">
          {credentials.map((credential) => (
            <div key={credential.id} className="panel flex items-center justify-between !p-4">
              <div>
                <p className="font-medium text-ink-50">{credential.label}</p>
                <p className="text-xs text-ink-500">
                  {credential.domain ? `${credential.domain}\\` : ""}
                  {credential.username} · cree le {new Date(credential.created_at).toLocaleString("fr-FR")}
                </p>
              </div>
              <button
                onClick={() => handleDelete(credential.id)}
                className="btn-secondary flex items-center gap-1.5 !px-2.5 !py-1.5 text-xs text-red-500"
                title="Supprimer ce jeu d'identifiants"
              >
                <Trash2 size={14} />
                supprimer
              </button>
            </div>
          ))}
          {credentials.length === 0 && (
            <EmptyState
              icon={KeyRound}
              title="Aucun identifiant enregistre"
              hint="Ajoutez un premier jeu d'identifiants ci-dessous pour l'utiliser dans les actions Active Directory."
            />
          )}
        </div>
      )}

      <section className="panel">
        <h2 className="mb-4 text-lg font-semibold text-ink-50">Nouveau jeu d'identifiants</h2>
        <form onSubmit={handleCreate} className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-sm text-ink-300">Libelle</label>
            <input
              required
              type="text"
              placeholder="ex: dc01-admin"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              className="field"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-ink-300">Domaine</label>
            <input
              type="text"
              placeholder="ex: LAB.LOCAL"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              className="field"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-ink-300">Nom d'utilisateur</label>
            <input
              required
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="field"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-ink-300">Mot de passe</label>
            <input
              required
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="field"
            />
          </div>
          <button type="submit" disabled={creating} className="btn-primary">
            {creating ? "creation..." : "enregistrer"}
          </button>
        </form>
        {formError && <div className="mt-3"><ErrorBanner>{formError}</ErrorBanner></div>}
      </section>
    </div>
  );
}
