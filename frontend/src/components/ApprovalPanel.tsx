import { useState } from "react";
import { api, ApiError } from "../api/client";
import type { Action, ApprovalOption } from "../api/types";

export function ApprovalPanel({ action, onDecided }: { action: Action; onDecided: () => void }) {
  const [option, setOption] = useState<ApprovalOption | null>(null);
  const [justification, setJustification] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDecide() {
    if (!option || justification.trim().length === 0) {
      setError("choisissez une option et motivez la decision");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.post(`/approvals/${action.id}`, { option_chosen: option, justification });
      onDecided();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "decision impossible");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="rounded-card border-2 border-red-700 bg-card p-6">
      <span className="eyebrow !text-red-400">Point de decision sensible</span>
      <h2 className="mb-1 text-lg font-semibold text-red-400">Porte d'approbation</h2>
      <p className="mb-4 text-sm text-ink-400">
        Action <span className="font-medium text-ink-100">{action.tool}</span> classee en tier{" "}
        <span className="font-medium text-red-400">{action.tier}</span> (score{" "}
        {action.risk_score?.toFixed(2)}). Une decision humaine explicite est requise avant execution.
      </p>

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <button
          type="button"
          onClick={() => setOption("A")}
          className={`rounded-card border p-4 text-left transition-colors ${
            option === "A" ? "border-accent2 bg-accent2/10" : "border-hairline hover:border-accent2"
          }`}
        >
          <p className="font-medium text-accent2">Option A - Conservatrice</p>
          <p className="mt-1 text-xs text-ink-400">
            Execution limitee, moins de trafic, priorite a la discretion. Reduit le risque operationnel
            au prix d'une couverture plus faible.
          </p>
        </button>
        <button
          type="button"
          onClick={() => setOption("B")}
          className={`rounded-card border p-4 text-left transition-colors ${
            option === "B" ? "border-red-500 bg-red-900/20" : "border-hairline hover:border-red-700"
          }`}
        >
          <p className="font-medium text-red-400">Option B - Agressive</p>
          <p className="mt-1 text-xs text-ink-400">
            Execution complete, couverture maximale. Augmente le bruit genere et le risque
            operationnel sur la cible.
          </p>
        </button>
      </div>

      <label className="mb-1 block text-sm text-ink-300">Justification (obligatoire, tracee dans l'audit)</label>
      <textarea
        value={justification}
        onChange={(e) => setJustification(e.target.value)}
        rows={3}
        className="field"
      />

      {error && <p className="mt-2 text-sm text-red-500">{error}</p>}

      <button onClick={handleDecide} disabled={submitting} className="btn-danger mt-4">
        {submitting ? "validation..." : "valider la decision"}
      </button>
    </section>
  );
}
