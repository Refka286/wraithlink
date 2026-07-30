type Tone = "red" | "blue" | "neutral";

const toneClasses: Record<Tone, string> = {
  red: "bg-red-700 text-white",
  blue: "bg-blue-700 text-white",
  neutral: "bg-ink-600 text-ink-50",
};

export function Badge({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium tracking-wide ${toneClasses[tone]}`}>
      {children}
    </span>
  );
}

export function riskTierTone(tier: string | null): Tone {
  if (tier === "forbidden") return "red";
  if (tier === "approval") return "red";
  if (tier === "automatic") return "blue";
  return "neutral";
}

export function actionStatusTone(status: string): Tone {
  if (status === "blocked" || status === "failed") return "red";
  if (status === "awaiting_approval") return "red";
  if (status === "completed") return "blue";
  return "neutral";
}

export function severityTone(severity: string): Tone {
  if (severity === "critical" || severity === "high") return "red";
  if (severity === "medium") return "blue";
  return "neutral";
}

export function engagementStatusTone(_status: string): Tone {
  return "blue";
}
