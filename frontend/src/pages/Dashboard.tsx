import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { FolderSearch } from "lucide-react";
import { api, ApiError } from "../api/client";
import type { Engagement, TargetType } from "../api/types";
import { Badge, engagementStatusTone } from "../components/Badge";
import { EmptyState, ErrorBanner, Spinner } from "../components/Feedback";

interface TargetDraft {
  host: string;
  type: TargetType;
}

export function Dashboard() {
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [clientName, setClientName] = useState("");
  const [scopeValidated, setScopeValidated] = useState(false);
  const [targets, setTargets] = useState<TargetDraft[]>([{ host: "host.docker.internal", type: "web" }]);
  const [creating, setCreating] = useState(false);

  async function refresh() {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await api.get<Engagement[]>("/engagements");
      setEngagements(data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setLoadError("votre session a expire. veuillez vous reconnecter.");
      } else {
        setLoadError(err instanceof ApiError ? err.message : "chargement impossible");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  function updateTarget(index: number, patch: Partial<TargetDraft>) {
    setTargets((prev) => prev.map((target, i) => (i === index ? { ...target, ...patch } : target)));
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setCreating(true);
    try {
      const cleanTargets = targets.filter((target) => target.host.trim() !== "");
      await api.post<Engagement>("/engagements", {
        name,
        client_name: clientName.trim() || null,
        scope_validated: scopeValidated,
        targets: cleanTargets,
      });
      setName("");
      setClientName("");
      setScopeValidated(false);
      setTargets([{ host: "", type: "web" }]);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "creation impossible");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-10">
      <section>
        <span className="eyebrow">Vue d'ensemble</span>
        <h1 className="mb-1 text-2xl font-extrabold text-ink-50">Engagements</h1>
        <p className="mb-6 text-sm text-ink-400">
          Vue d'ensemble des audits en cours et de leur statut dans le workflow guide par le risque.
        </p>

        {loading && <Spinner label="chargement des engagements..." />}
        {!loading && loadError && (
          <ErrorBanner>
            {loadError}{" "}
            <Link to="/login" className="font-semibold underline">
              Se reconnecter
            </Link>
          </ErrorBanner>
        )}
        {!loading && !loadError && engagements.length === 0 && (
          <EmptyState
            icon={FolderSearch}
            title="Aucun engagement pour le moment"
            hint="Creez votre premier engagement avec le formulaire ci-dessous pour commencer un audit."
          />
        )}

        <div className="space-y-3">
          {engagements.map((engagement) => (
            <Link
              key={engagement.id}
              to={`/engagements/${engagement.id}`}
              className="panel panel-hover flex items-center justify-between !p-4 hover:-translate-y-0.5"
            >
              <div>
                <p className="font-medium text-ink-50">{engagement.name}</p>
                <p className="text-xs text-ink-500">
                  {engagement.targets.length} cible(s) - cree le{" "}
                  {new Date(engagement.created_at).toLocaleString("fr-FR")}
                </p>
              </div>
              <Badge tone={engagementStatusTone(engagement.status)}>{engagement.status}</Badge>
            </Link>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2 className="mb-4 text-lg font-semibold text-ink-50">Nouvel engagement</h2>
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm text-ink-300">Nom</label>
            <input
              required
              placeholder="ex : Audit de securite - Application X"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="field"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm text-ink-300">Client (optionnel, apparait sur les rapports PDF)</label>
            <input
              placeholder="ex : Nom de l'entreprise cliente"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              className="field"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm text-ink-300">Cibles</label>
            <div className="space-y-2">
              {targets.map((target, index) => (
                <div key={index} className="flex gap-2">
                  <input
                    placeholder="hote ou IP"
                    value={target.host}
                    onChange={(e) => updateTarget(index, { host: e.target.value })}
                    className="field flex-1"
                  />
                  <select
                    value={target.type}
                    onChange={(e) => updateTarget(index, { type: e.target.value as TargetType })}
                    className="field w-auto"
                  >
                    <option value="web">web</option>
                    <option value="active_directory">active_directory</option>
                  </select>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={() => setTargets((prev) => [...prev, { host: "host.docker.internal", type: "web" }])}
              className="mt-2 text-sm font-medium text-accent hover:opacity-80"
            >
              + ajouter une cible
            </button>
            <p className="mt-2 text-xs text-ink-500">
              Pour une cible hebergee sur cette machine (ex : Juice Shop lance en local), utilisez{" "}
              <code className="rounded bg-ink-800 px-1">host.docker.internal</code> plutot que{" "}
              <code className="rounded bg-ink-800 px-1">localhost</code> : les outils s&apos;executent dans un
              conteneur isole ou <code className="rounded bg-ink-800 px-1">localhost</code> pointe vers le
              conteneur lui-meme, pas vers votre machine hote.
            </p>
          </div>

          <label className="flex items-center gap-2 text-sm text-ink-300">
            <input
              type="checkbox"
              checked={scopeValidated}
              onChange={(e) => setScopeValidated(e.target.checked)}
              className="h-4 w-4 accent-accent2"
            />
            Je confirme que le perimetre et l'autorisation de cet engagement ont ete valides
          </label>

          {error && <ErrorBanner>{error}</ErrorBanner>}

          <button type="submit" disabled={creating || !scopeValidated} className="btn-primary">
            {creating ? "creation..." : "creer l'engagement"}
          </button>
        </form>
      </section>
    </div>
  );
}
