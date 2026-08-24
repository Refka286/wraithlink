import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, ApiError } from "../api/client";
import type { AnalyticsSummary } from "../api/types";
import { ErrorBanner, Spinner } from "../components/Feedback";

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];
const SEVERITY_LABELS: Record<string, string> = {
  critical: "Critique",
  high: "Elevee",
  medium: "Moyenne",
  low: "Faible",
  info: "Information",
};
// canonical palette, shared with backend/app/reporting/templates/report.html
const SEVERITY_COLORS: Record<string, string> = {
  critical: "#b91c1c",
  high: "#dc2626",
  medium: "#d97706",
  low: "#64748b",
  info: "#9ca3af",
};

const TIER_ORDER = ["automatic", "approval", "forbidden"];
const TIER_LABELS: Record<string, string> = {
  automatic: "Automatique",
  approval: "Approbation",
  forbidden: "Interdit",
};
const TIER_COLORS: Record<string, string> = {
  automatic: "#2ee6d6",
  approval: "#f59e0b",
  forbidden: "#b91c1c",
};

const tooltipStyle = {
  background: "#101828",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 8,
  fontSize: 12,
  color: "#f4f4f5",
};

function StatTile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="panel !p-4 text-center">
      <span className="block text-2xl font-extrabold text-ink-50">{value}</span>
      <span className="text-xs uppercase tracking-wide text-ink-500">{label}</span>
    </div>
  );
}

export function Statistics() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<AnalyticsSummary>("/analytics/summary")
      .then(setSummary)
      .catch((err) => setError(err instanceof ApiError ? err.message : "chargement impossible"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner label="chargement des statistiques..." />;
  if (error) {
    return <ErrorBanner>{error}</ErrorBanner>;
  }
  if (!summary) return null;

  const severityData = SEVERITY_ORDER.map((severity) => ({
    severity,
    label: SEVERITY_LABELS[severity],
    count: summary.findings_by_severity[severity] ?? 0,
  }));

  const toolData = Object.entries(summary.tool_usage)
    .sort((a, b) => b[1] - a[1])
    .map(([tool, count]) => ({ tool, count }));

  const tierData = TIER_ORDER.filter((tier) => (summary.tier_distribution[tier] ?? 0) > 0).map((tier) => ({
    tier,
    label: TIER_LABELS[tier],
    count: summary.tier_distribution[tier],
  }));

  const optionA = summary.approval_option_ratio["A"] ?? 0;
  const optionB = summary.approval_option_ratio["B"] ?? 0;
  const optionTotal = optionA + optionB;
  const optionAPct = optionTotal > 0 ? Math.round((optionA / optionTotal) * 100) : 0;

  const avgApproval = summary.average_approval_seconds;
  const avgApprovalLabel =
    avgApproval === null
      ? "-"
      : avgApproval < 60
        ? `${avgApproval.toFixed(0)} s`
        : avgApproval < 3600
          ? `${(avgApproval / 60).toFixed(1)} min`
          : `${(avgApproval / 3600).toFixed(1)} h`;

  return (
    <div className="space-y-8">
      <div>
        <span className="eyebrow">Vue globale</span>
        <h1 className="text-2xl font-extrabold text-ink-50">Statistiques</h1>
        <p className="mt-1 text-sm text-ink-400">Donnees agregees sur l'ensemble des engagements.</p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Engagements" value={summary.total_engagements} />
        <StatTile label="Actions executees" value={summary.total_actions} />
        <StatTile label="Decisions d'approbation" value={summary.total_approvals} />
        <StatTile label="Delai moyen d'approbation" value={avgApprovalLabel} />
      </div>

      <section className="panel">
        <h2 className="mb-4 text-lg font-semibold text-ink-50">Vulnerabilites par severite</h2>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={severityData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
            <XAxis dataKey="label" tick={{ fill: "#a1a1aa", fontSize: 12 }} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} />
            <YAxis allowDecimals={false} tick={{ fill: "#a1a1aa", fontSize: 12 }} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} />
            <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]} minPointSize={2}>
              {severityData.map((entry) => (
                <Cell key={entry.severity} fill={SEVERITY_COLORS[entry.severity]} />
              ))}
              <LabelList dataKey="count" position="top" style={{ fill: "#a1a1aa", fontSize: 11 }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="panel">
          <h2 className="mb-4 text-lg font-semibold text-ink-50">Utilisation par outil</h2>
          {toolData.length === 0 ? (
            <p className="text-ink-500">aucune action enregistree.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={toolData} layout="vertical" margin={{ left: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
                <XAxis type="number" allowDecimals={false} tick={{ fill: "#a1a1aa", fontSize: 12 }} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} />
                <YAxis type="category" dataKey="tool" width={80} tick={{ fill: "#a1a1aa", fontSize: 12 }} axisLine={{ stroke: "rgba(255,255,255,0.1)" }} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                <Bar dataKey="count" fill="#4f7cff" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </section>

        <section className="panel">
          <h2 className="mb-4 text-lg font-semibold text-ink-50">Repartition par tier de risque</h2>
          {tierData.length === 0 ? (
            <p className="text-ink-500">aucune action classee.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={tierData} dataKey="count" nameKey="label" innerRadius={55} outerRadius={90} paddingAngle={2}>
                  {tierData.map((entry) => (
                    <Cell key={entry.tier} fill={TIER_COLORS[entry.tier]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 12, color: "#a1a1aa" }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </section>
      </div>

      <section className="panel">
        <h2 className="mb-4 text-lg font-semibold text-ink-50">Decisions d'approbation : option choisie</h2>
        {optionTotal === 0 ? (
          <p className="text-ink-500">aucune decision d'approbation enregistree.</p>
        ) : (
          <div>
            <div className="flex h-4 overflow-hidden rounded-full border border-hairline">
              <div className="bg-accent" style={{ width: `${optionAPct}%` }} />
              <div className="bg-accent2" style={{ width: `${100 - optionAPct}%` }} />
            </div>
            <div className="mt-3 flex justify-between text-xs text-ink-400">
              <span>
                <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-accent" />
                Option A (conservatrice) : {optionA} ({optionAPct}%)
              </span>
              <span>
                Option B (agressive) : {optionB} ({100 - optionAPct}%)
                <span className="ml-1.5 inline-block h-2 w-2 rounded-full bg-accent2" />
              </span>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
