type Tone = "danger" | "warning" | "success" | "accent" | "neutral";

const toneClasses: Record<Tone, string> = {
  danger: "bg-red-700/15 text-red-400 border border-red-700/40",
  warning: "bg-warning/15 text-warning border border-warning/40",
  success: "bg-success/15 text-success border border-success/40",
  accent: "bg-accent/15 text-accent border border-accent/30",
  neutral: "bg-ink-700/60 text-ink-200 border border-hairline",
};

export function Badge({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold tracking-wide ${toneClasses[tone]}`}>
      {children}
    </span>
  );
}

// risk tier: automatic proceeds on its own (accent), approval pauses for a
// human decision (warning - not inherently dangerous), forbidden is a hard
// block (danger)
export function riskTierTone(tier: string | null): Tone {
  if (tier === "forbidden") return "danger";
  if (tier === "approval") return "warning";
  if (tier === "automatic") return "accent";
  return "neutral";
}

export function actionStatusTone(status: string): Tone {
  if (status === "blocked" || status === "failed") return "danger";
  if (status === "awaiting_approval" || status === "pending") return "warning";
  if (status === "completed") return "success";
  if (status === "running") return "accent";
  return "neutral";
}

export function severityTone(severity: string): Tone {
  if (severity === "critical" || severity === "high") return "danger";
  if (severity === "medium") return "warning";
  return "neutral";
}

export function engagementStatusTone(status: string): Tone {
  if (status === "approval_pending") return "warning";
  if (status === "closed") return "neutral";
  return "accent";
}

export function priorityTone(priority: string): Tone {
  if (priority === "high") return "danger";
  if (priority === "medium") return "warning";
  return "neutral";
}
