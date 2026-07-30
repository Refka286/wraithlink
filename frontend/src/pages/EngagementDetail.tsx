import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { Action, Engagement, Finding, ReportRecord } from "../api/types";
import { Badge, actionStatusTone, engagementStatusTone, riskTierTone, severityTone } from "../components/Badge";
import { ApprovalPanel } from "../components/ApprovalPanel";

const KNOWN_TOOLS = [
  { tool: "nmap", profile: "syn-stealth", label: "nmap - scan de ports (automatique)", category: "Web" },
  { tool: "ffuf", profile: "default", label: "ffuf - decouverte de repertoires (automatique)", category: "Web" },
  { tool: "nuclei", profile: "default", label: "nuclei - templates par defaut (automatique)", category: "Web" },
  { tool: "nuclei", profile: "aggressive", label: "nuclei - mode agressif (approbation)", category: "Web" },
  { tool: "sqlmap", profile: "aggressive", label: "sqlmap - mode agressif (approbation)", category: "Web" },
  { tool: "bloodhound", profile: "collect", label: "bloodhound - collecte LDAP/SMB (automatique)", category: "Active Directory" },
  { tool: "netexec", profile: "kerberoast", label: "netexec - kerberoasting (approbation)", category: "Active Directory" },
  { tool: "netexec", profile: "dcsync", label: "netexec - dcsync (interdit)", category: "Active Directory" },
  { tool: "ad", profile: "bruteforce-massive", label: "brute-force massif AD (interdit)", category: "Active Directory" },
];

const TOOL_CATEGORIES = ["Web", "Active Directory"] as const;

export function EngagementDetail() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const [engagement, setEngagement] = useState<Engagement | null>(null);
  const [actions, setActions] = useState<Action[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [selectedTargetId, setSelectedTargetId] = useState<string>("");
  const [selectedToolIndex, setSelectedToolIndex] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);

  const refresh = useCallback(async () => {
    if (!engagementId) return;
    try {
      const [engagementData, actionsData, findingsData] = await Promise.all([
        api.get<Engagement>(`/engagements/${engagementId}`),
        api.get<Action[]>(`/actions?engagement_id=${engagementId}`),
        api.get<Finding[]>(`/findings?engagement_id=${engagementId}`),
      ]);
      setEngagement(engagementData);
      setActions(actionsData);
      setFindings(findingsData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "chargement impossible");
    }
  }, [engagementId]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 4000);
    return () => clearInterval(interval);
  }, [refresh]);

  async function handleSubmitAction(event: FormEvent) {
    event.preventDefault();
    if (!engagementId) return;
    setSubmitting(true);
    setError(null);
    try {
      const choice = KNOWN_TOOLS[selectedToolIndex];
      await api.post<Action>("/actions", {
        engagement_id: engagementId,
        target_id: selectedTargetId || null,
        tool: choice.tool,
        params: { profile: choice.profile },
      });
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "soumission impossible");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGenerateReport() {
    if (!engagementId) return;
    setGeneratingReport(true);
    setError(null);
    try {
      const report = await api.post<ReportRecord>(`/reports/${engagementId}`);
      setReports((prev) => [report, ...prev]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "generation du rapport impossible");
    } finally {
      setGeneratingReport(false);
    }
  }

  if (!engagement) {
    return <p className="text-ink-400">chargement...</p>;
  }

  const pendingApproval = actions.find((action) => action.status === "awaiting_approval");

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink-50">{engagement.name}</h1>
          <p className="text-sm text-ink-500">
            {engagement.targets.length} cible(s) - portee validee :{" "}
            {engagement.scope_validated ? "oui" : "non"}
          </p>
        </div>
        <Badge tone={engagementStatusTone(engagement.status)}>{engagement.status}</Badge>
      </div>

      {error && <p className="rounded border border-red-800 bg-red-900/20 p-3 text-sm text-red-400">{error}</p>}

      {pendingApproval && (
        <ApprovalPanel action={pendingApproval} onDecided={refresh} />
      )}

      <section className="rounded border border-ink-700 bg-black p-6">
        <h2 className="mb-4 text-lg font-semibold text-ink-50">Soumettre une action</h2>
        <form onSubmit={handleSubmitAction} className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-sm text-ink-300">Cible</label>
            <select
              value={selectedTargetId}
              onChange={(e) => setSelectedTargetId(e.target.value)}
              className="rounded border border-ink-600 bg-ink-900 px-3 py-2 text-ink-50 outline-none focus:border-blue-600"
            >
              <option value="">aucune cible specifique</option>
              {engagement.targets.map((target) => (
                <option key={target.id} value={target.id}>
                  {target.host}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm text-ink-300">Action</label>
            <select
              value={selectedToolIndex}
              onChange={(e) => setSelectedToolIndex(Number(e.target.value))}
              className="rounded border border-ink-600 bg-ink-900 px-3 py-2 text-ink-50 outline-none focus:border-blue-600"
            >
              {TOOL_CATEGORIES.map((category) => (
                <optgroup key={category} label={category}>
                  {KNOWN_TOOLS.map((choice, index) =>
                    choice.category === category ? (
                      <option key={`${choice.tool}-${choice.profile}`} value={index}>
                        {choice.label}
                      </option>
                    ) : null
                  )}
                </optgroup>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="rounded bg-blue-700 px-4 py-2 font-medium text-white hover:bg-blue-600 disabled:opacity-50"
          >
            {submitting ? "envoi..." : "soumettre"}
          </button>
        </form>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-ink-50">Fil des actions</h2>
        {actions.length === 0 && <p className="text-ink-500">aucune action soumise.</p>}
        <div className="space-y-2">
          {actions.map((action) => (
            <div key={action.id} className="rounded border border-ink-700 bg-black p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-ink-50">{action.tool}</span>
                  <span className="text-xs text-ink-500">{JSON.stringify(action.params)}</span>
                </div>
                <div className="flex items-center gap-2">
                  {action.tier && <Badge tone={riskTierTone(action.tier)}>{action.tier}</Badge>}
                  <Badge tone={actionStatusTone(action.status)}>{action.status}</Badge>
                </div>
              </div>
              {action.risk_score !== null && (
                <p className="mt-1 text-xs text-ink-500">score de risque : {action.risk_score.toFixed(2)}</p>
              )}
              {Boolean(action.result?.error) && (
                <p className="mt-1 text-xs text-red-500">{String(action.result?.error)}</p>
              )}
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-ink-50">Vulnerabilites</h2>
        {findings.length === 0 && <p className="text-ink-500">aucune vulnerabilite enregistree.</p>}
        <div className="space-y-2">
          {findings.map((finding) => (
            <div key={finding.id} className="rounded border border-ink-700 bg-black p-4">
              <div className="flex items-center justify-between">
                <span className="font-medium text-ink-50">{finding.type}</span>
                <Badge tone={severityTone(finding.severity)}>{finding.severity}</Badge>
              </div>
              <p className="mt-1 text-xs text-ink-500">{finding.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded border border-ink-700 bg-black p-6">
        <h2 className="mb-4 text-lg font-semibold text-ink-50">Rapport</h2>
        <button
          onClick={handleGenerateReport}
          disabled={generatingReport}
          className="rounded bg-red-700 px-4 py-2 font-medium text-white hover:bg-red-600 disabled:opacity-50"
        >
          {generatingReport ? "generation..." : "generer le rapport PDF"}
        </button>
        <div className="mt-4 space-y-1">
          {reports.map((report) => (
            <p key={report.id} className="text-xs text-ink-500">
              {report.pdf_ref} - {new Date(report.created_at).toLocaleString("fr-FR")}
            </p>
          ))}
        </div>
      </section>
    </div>
  );
}
