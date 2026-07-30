import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Engagement, TargetType } from "../api/types";
import { Badge, engagementStatusTone } from "../components/Badge";

interface TargetDraft {
  host: string;
  type: TargetType;
}

export function Dashboard() {
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [scopeValidated, setScopeValidated] = useState(false);
  const [targets, setTargets] = useState<TargetDraft[]>([{ host: "", type: "web" }]);
  const [creating, setCreating] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const data = await api.get<Engagement[]>("/engagements");
      setEngagements(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "chargement impossible");
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
        scope_validated: scopeValidated,
        targets: cleanTargets,
      });
      setName("");
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
        <h1 className="mb-1 text-2xl font-bold text-ink-50">Engagements</h1>
        <p className="mb-6 text-sm text-ink-400">
          Vue d'ensemble des audits en cours et de leur statut dans le workflow guide par le risque.
        </p>

        {loading && <p className="text-ink-400">chargement...</p>}
        {!loading && engagements.length === 0 && (
          <p className="rounded border border-ink-700 bg-black p-6 text-ink-400">
            Aucun engagement pour le moment. Creez-en un ci-dessous.
          </p>
        )}

        <div className="space-y-3">
          {engagements.map((engagement) => (
            <Link
              key={engagement.id}
              to={`/engagements/${engagement.id}`}
              className="flex items-center justify-between rounded border border-ink-700 bg-black p-4 hover:border-blue-700"
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

      <section className="rounded border border-ink-700 bg-black p-6">
        <h2 className="mb-4 text-lg font-semibold text-ink-50">Nouvel engagement</h2>
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm text-ink-300">Nom</label>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded border border-ink-600 bg-ink-900 px-3 py-2 text-ink-50 outline-none focus:border-blue-600"
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
                    className="flex-1 rounded border border-ink-600 bg-ink-900 px-3 py-2 text-ink-50 outline-none focus:border-blue-600"
                  />
                  <select
                    value={target.type}
                    onChange={(e) => updateTarget(index, { type: e.target.value as TargetType })}
                    className="rounded border border-ink-600 bg-ink-900 px-3 py-2 text-ink-50 outline-none focus:border-blue-600"
                  >
                    <option value="web">web</option>
                    <option value="active_directory">active_directory</option>
                  </select>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={() => setTargets((prev) => [...prev, { host: "", type: "web" }])}
              className="mt-2 text-sm text-blue-400 hover:text-blue-300"
            >
              + ajouter une cible
            </button>
          </div>

          <label className="flex items-center gap-2 text-sm text-ink-300">
            <input
              type="checkbox"
              checked={scopeValidated}
              onChange={(e) => setScopeValidated(e.target.checked)}
              className="h-4 w-4 accent-red-700"
            />
            Je confirme que le perimetre et l'autorisation de cet engagement ont ete valides
          </label>

          {error && <p className="text-sm text-red-500">{error}</p>}

          <button
            type="submit"
            disabled={creating || !scopeValidated}
            className="rounded bg-red-700 px-4 py-2 font-medium text-white hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {creating ? "creation..." : "creer l'engagement"}
          </button>
        </form>
      </section>
    </div>
  );
}
