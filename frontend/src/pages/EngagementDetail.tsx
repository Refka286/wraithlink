import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";
import { AlertTriangle, CheckCircle2, ListChecks, ShieldAlert, Sparkles, XCircle } from "lucide-react";
import { api, ApiError, downloadReport, exportFindings, getSuggestions } from "../api/client";
import type { Action, Credential, Engagement, Finding, ReportRecord, Suggestion, ToolReference } from "../api/types";
import {
  Badge,
  actionStatusTone,
  engagementStatusTone,
  priorityTone,
  riskTierTone,
  severityTone,
} from "../components/Badge";
import { ApprovalPanel } from "../components/ApprovalPanel";
import { EmptyState, ErrorBanner, Spinner } from "../components/Feedback";

const TIER_LABELS: Record<string, string> = {
  automatic: "Automatique",
  approval: "Approbation requise",
  forbidden: "Interdit",
};

const TIER_NEXT_STEP: Record<string, string> = {
  automatic: "Cette action s'executera immediatement des la soumission, sans validation prealable.",
  approval:
    "Cette action sera mise en attente (statut awaiting_approval) et necessitera une decision d'approbation (option et justification) avant de pouvoir s'executer.",
  forbidden: "Cette action sera bloquee automatiquement des la soumission et ne pourra jamais s'executer.",
};

const RESULT_TONE_CLASS: Record<string, string> = {
  success: "text-success",
  warning: "text-warning",
  danger: "text-red-500",
};

// backed by the action's actual status plus real Finding rows (via
// findingCount, computed from the already-fetched findings list) - never
// inferred from finding count alone, since a completed scan can
// legitimately find nothing
function getActionResultSummary(action: Action, findingCount: number) {
  if (action.status === "failed" || action.status === "blocked") {
    return { icon: XCircle, text: action.error_summary ?? "Echec de l'action.", tone: "danger" as const };
  }
  if (action.status === "completed") {
    const partialSuffix = action.note ? " (resultats partiels - scan interrompu par timeout)" : "";
    if (findingCount > 0) {
      return {
        icon: action.note ? AlertTriangle : ShieldAlert,
        text: `${findingCount} constat(s) identifie(s)${partialSuffix}`,
        tone: "warning" as const,
      };
    }
    return {
      icon: action.note ? AlertTriangle : CheckCircle2,
      text: action.note
        ? `Aucune vulnerabilite detectee dans les resultats partiels${partialSuffix}`
        : "Aucune vulnerabilite detectee - analyse terminee avec succes",
      tone: action.note ? ("warning" as const) : ("success" as const),
    };
  }
  return null;
}

const KNOWN_TOOLS = [
  { tool: "nmap", profile: "syn-stealth", label: "nmap - scan de ports (automatique)", category: "Web" },
  { tool: "ffuf", profile: "default", label: "ffuf - decouverte de repertoires (automatique)", category: "Web" },
  { tool: "nuclei", profile: "default", label: "nuclei - templates par defaut (automatique)", category: "Web" },
  { tool: "nuclei", profile: "aggressive", label: "nuclei - mode agressif (approbation)", category: "Web" },
  { tool: "sqlmap", profile: "aggressive", label: "sqlmap - mode agressif (approbation)", category: "Web" },
  { tool: "acunetix", profile: "full-scan", label: "Acunetix - scan complet (approbation, licence requise)", category: "Web" },
  { tool: "bloodhound", profile: "collect", label: "bloodhound - collecte LDAP/SMB (automatique)", category: "Active Directory" },
  { tool: "netexec", profile: "kerberoast", label: "netexec - kerberoasting (approbation)", category: "Active Directory" },
  { tool: "netexec", profile: "dcsync", label: "netexec - dcsync (interdit)", category: "Active Directory" },
  { tool: "ad", profile: "bruteforce-massive", label: "brute-force massif AD (interdit)", category: "Active Directory" },
];

const TOOL_CATEGORIES = ["Web", "Active Directory"] as const;

// these adapters authenticate against AD (app/adapters/netexec.py,
// app/adapters/bloodhound.py) and need a saved credential set rather than
// a typed-in username/password - see the credentials vault
const CREDENTIAL_REQUIRED_TOOLS = new Set(["netexec", "bloodhound"]);

const CATEGORY_BY_TARGET_TYPE: Record<string, (typeof TOOL_CATEGORIES)[number]> = {
  web: "Web",
  active_directory: "Active Directory",
};

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
  const [exporting, setExporting] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [toolsReference, setToolsReference] = useState<ToolReference[]>([]);
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [selectedCredentialId, setSelectedCredentialId] = useState<string>("");

  useEffect(() => {
    api
      .get<ToolReference[]>("/tools")
      .then(setToolsReference)
      .catch(() => setToolsReference([]));
    api
      .get<Credential[]>("/credentials")
      .then(setCredentials)
      .catch(() => setCredentials([]));
  }, []);

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

  useEffect(() => {
    if (!engagement) return;
    const stillValid = engagement.targets.some((target) => target.id === selectedTargetId);
    if (!stillValid) {
      setSelectedTargetId(engagement.targets[0]?.id ?? "");
    }
  }, [engagement, selectedTargetId]);

  useEffect(() => {
    if (!engagement) return;
    const selectedTarget = engagement.targets.find((target) => target.id === selectedTargetId);
    const activeCategory = selectedTarget ? CATEGORY_BY_TARGET_TYPE[selectedTarget.type] : undefined;
    const currentChoice = KNOWN_TOOLS[selectedToolIndex];
    const stillValid = !activeCategory || currentChoice?.category === activeCategory;
    if (!stillValid) {
      const fallbackIndex = KNOWN_TOOLS.findIndex((tool) => tool.category === activeCategory);
      setSelectedToolIndex(fallbackIndex === -1 ? 0 : fallbackIndex);
    }
  }, [engagement, selectedTargetId, selectedToolIndex]);

  useEffect(() => {
    const requiresCredential = CREDENTIAL_REQUIRED_TOOLS.has(KNOWN_TOOLS[selectedToolIndex]?.tool);
    const stillValid = credentials.some((credential) => credential.id === selectedCredentialId);
    if (!requiresCredential) {
      setSelectedCredentialId("");
    } else if (!stillValid) {
      setSelectedCredentialId(credentials[0]?.id ?? "");
    }
  }, [selectedToolIndex, credentials, selectedCredentialId]);

  async function handleSubmitAction(event: FormEvent) {
    event.preventDefault();
    if (!engagementId) return;
    const choice = KNOWN_TOOLS[selectedToolIndex];
    const requiresCredential = CREDENTIAL_REQUIRED_TOOLS.has(choice.tool);
    if (requiresCredential && !selectedCredentialId) {
      setError("Selectionnez un jeu d'identifiants avant de soumettre cette action.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.post<Action>("/actions", {
        engagement_id: engagementId,
        target_id: selectedTargetId || null,
        tool: choice.tool,
        params: requiresCredential
          ? { profile: choice.profile, credential_id: selectedCredentialId }
          : { profile: choice.profile },
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
      await downloadReport(report.id, `${engagement?.name ?? "rapport"}-${report.id}.pdf`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "generation du rapport impossible");
    } finally {
      setGeneratingReport(false);
    }
  }

  async function handleDownloadReport(report: ReportRecord) {
    setError(null);
    try {
      await downloadReport(report.id, `${engagement?.name ?? "rapport"}-${report.id}.pdf`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "telechargement impossible");
    }
  }

  async function handleExportFindings() {
    if (!engagementId) return;
    setExporting(true);
    setError(null);
    try {
      await exportFindings(engagementId, "csv");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "export impossible");
    } finally {
      setExporting(false);
    }
  }

  async function handleGetSuggestions() {
    if (!engagementId) return;
    setLoadingSuggestions(true);
    setError(null);
    try {
      const data = await getSuggestions(engagementId);
      setSuggestions(data.suggestions);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "suggestions indisponibles");
    } finally {
      setLoadingSuggestions(false);
    }
  }

  if (!engagement) {
    return <Spinner label="chargement de l'engagement..." />;
  }

  const pendingApproval = actions.find((action) => action.status === "awaiting_approval");
  const findingCountByAction = findings.reduce<Record<string, number>>((counts, finding) => {
    counts[finding.action_id] = (counts[finding.action_id] ?? 0) + 1;
    return counts;
  }, {});
  const selectedTarget = engagement.targets.find((target) => target.id === selectedTargetId);
  const activeCategory = selectedTarget ? CATEGORY_BY_TARGET_TYPE[selectedTarget.type] : undefined;
  const visibleCategories = activeCategory ? [activeCategory] : TOOL_CATEGORIES;
  const selectedChoice = KNOWN_TOOLS[selectedToolIndex];
  const selectedProfileInfo = toolsReference
    .find((tool) => tool.tool === selectedChoice.tool)
    ?.profiles.find((profile) => profile.profile === selectedChoice.profile);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <span className="eyebrow">Engagement</span>
          <h1 className="text-2xl font-extrabold text-ink-50">{engagement.name}</h1>
          <p className="text-sm text-ink-500">
            {engagement.targets.length} cible(s) - portee validee :{" "}
            {engagement.scope_validated ? "oui" : "non"}
          </p>
        </div>
        <Badge tone={engagementStatusTone(engagement.status)}>{engagement.status}</Badge>
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}

      {pendingApproval && <ApprovalPanel action={pendingApproval} onDecided={refresh} />}

      <section className="panel">
        <h2 className="mb-4 text-lg font-semibold text-ink-50">Soumettre une action</h2>
        <form onSubmit={handleSubmitAction} className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-sm text-ink-300">Cible</label>
            <select
              value={selectedTargetId}
              onChange={(e) => setSelectedTargetId(e.target.value)}
              className="field w-auto"
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
              className="field w-auto"
            >
              {visibleCategories.map((category) => (
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
          {CREDENTIAL_REQUIRED_TOOLS.has(selectedChoice.tool) && (
            <div>
              <label className="mb-1 block text-sm text-ink-300">Jeu d'identifiants</label>
              <select
                value={selectedCredentialId}
                onChange={(e) => setSelectedCredentialId(e.target.value)}
                className="field w-auto"
              >
                <option value="">selectionner...</option>
                {credentials.map((credential) => (
                  <option key={credential.id} value={credential.id}>
                    {credential.label} ({credential.domain ? `${credential.domain}\\` : ""}
                    {credential.username})
                  </option>
                ))}
              </select>
              {credentials.length === 0 && (
                <p className="mt-1 text-xs text-ink-500">
                  Aucun identifiant enregistre - ajoutez-en un dans la page Identifiants.
                </p>
              )}
            </div>
          )}
          <button type="submit" disabled={submitting} className="btn-primary">
            {submitting ? "envoi..." : "soumettre"}
          </button>
        </form>
        {selectedTarget && (
          <p className="mt-2 text-xs text-ink-500">
            Actions filtrees pour une cible de type <span className="font-semibold">{selectedTarget.type}</span>.
          </p>
        )}
        {selectedProfileInfo && (
          <div className="mt-3 rounded-lg border border-hairline bg-surface p-3 text-sm">
            <p className="text-ink-300">{selectedProfileInfo.explanation}</p>
            <div className="mt-2 flex items-center gap-2">
              <Badge tone={riskTierTone(selectedProfileInfo.risk.tier)}>
                {TIER_LABELS[selectedProfileInfo.risk.tier] ?? selectedProfileInfo.risk.tier}
              </Badge>
              <span className="text-xs text-ink-500">
                {TIER_NEXT_STEP[selectedProfileInfo.risk.tier]}
              </span>
            </div>
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-ink-50">Fil des actions</h2>
        {actions.length === 0 && (
          <EmptyState
            icon={ListChecks}
            title="Aucune action soumise"
            hint="Utilisez le formulaire ci-dessus pour lancer un premier outil sur cet engagement."
          />
        )}
        <div className="space-y-2">
          {actions.map((action) => {
            const resultSummary = getActionResultSummary(action, findingCountByAction[action.id] ?? 0);
            return (
            <div key={action.id} className="panel !p-4">
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
              {resultSummary && (
                <p className={`mt-1.5 flex items-center gap-1.5 text-xs ${RESULT_TONE_CLASS[resultSummary.tone]}`}>
                  <resultSummary.icon size={13} />
                  {resultSummary.text}
                </p>
              )}
            </div>
            );
          })}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-ink-50">Vulnerabilites</h2>
        {findings.length === 0 && (
          <EmptyState
            icon={ShieldAlert}
            title="Aucune vulnerabilite enregistree"
            hint="Les constats des actions executees apparaitront ici automatiquement."
          />
        )}
        <div className="space-y-2">
          {findings.map((finding) => (
            <div key={finding.id} className="panel !p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-ink-50">{finding.type}</span>
                  <span className="rounded-full border border-hairline bg-surface px-2 py-0.5 text-[10px] text-ink-400">
                    {finding.compliance_reference}
                  </span>
                </div>
                <Badge tone={severityTone(finding.severity)}>{finding.severity}</Badge>
              </div>
              <p className="mt-1 text-xs text-ink-500">{finding.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2 className="mb-4 text-lg font-semibold text-ink-50">Suggestions IA</h2>
        <button onClick={handleGetSuggestions} disabled={loadingSuggestions} className="btn-primary">
          {loadingSuggestions ? "analyse..." : "obtenir des suggestions IA"}
        </button>
        {suggestions.length === 0 ? (
          <p className="mt-3 flex items-center gap-2 text-sm text-ink-500">
            <Sparkles size={15} className="text-ink-600" />
            aucune suggestion pour le moment.
          </p>
        ) : (
          <div className="mt-4 space-y-2">
            {suggestions.map((suggestion, index) => (
              <div key={`${suggestion.tool}-${index}`} className="panel !p-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-ink-50">{suggestion.tool}</span>
                  <Badge tone={priorityTone(suggestion.priority)}>{suggestion.priority}</Badge>
                </div>
                <p className="mt-1 text-xs text-ink-500">{suggestion.reasoning}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <h2 className="mb-4 text-lg font-semibold text-ink-50">Rapport</h2>
        <div className="flex flex-wrap gap-3">
          <button onClick={handleGenerateReport} disabled={generatingReport} className="btn-danger">
            {generatingReport ? "generation..." : "generer le rapport PDF"}
          </button>
          <button onClick={handleExportFindings} disabled={exporting} className="btn-secondary">
            {exporting ? "export..." : "exporter (CSV)"}
          </button>
        </div>
        <div className="mt-4 space-y-1">
          {reports.map((report) => (
            <button
              key={report.id}
              onClick={() => handleDownloadReport(report)}
              className="block text-xs font-medium text-accent underline hover:opacity-80"
            >
              telecharger le rapport du {new Date(report.created_at).toLocaleString("fr-FR")}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
