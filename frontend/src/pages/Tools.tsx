import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { ToolReference } from "../api/types";
import { Badge, riskTierTone } from "../components/Badge";
import { ErrorBanner, Spinner } from "../components/Feedback";

const TIER_LABELS: Record<string, string> = {
  automatic: "Automatique",
  approval: "Approbation requise",
  forbidden: "Interdit",
};

export function Tools() {
  const [tools, setTools] = useState<ToolReference[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<ToolReference[]>("/tools")
      .then(setTools)
      .catch((err) => setError(err instanceof ApiError ? err.message : "chargement impossible"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <span className="eyebrow">Reference</span>
        <h1 className="text-2xl font-extrabold text-ink-50">Outils</h1>
        <p className="mt-1 text-sm text-ink-400">
          Ce que fait chaque outil disponible sur la plateforme, comment il fonctionne techniquement,
          et comment son niveau de risque est calcule.
        </p>
      </div>

      {loading && <Spinner label="chargement des outils..." />}
      {error && <ErrorBanner>{error}</ErrorBanner>}

      <div className="space-y-6">
        {tools.map((tool) => (
          <section key={tool.tool} className="panel">
            <h2 className="text-lg font-semibold text-ink-50">{tool.label}</h2>
            <p className="mt-2 text-sm text-ink-200">{tool.what_is}</p>

            <div className="mt-4">
              <p className="eyebrow !mb-2">Fonctionnement technique</p>
              <p className="text-sm leading-relaxed text-ink-300">{tool.how_it_works}</p>
            </div>

            <div className="mt-4">
              <p className="eyebrow !mb-2">Exemple de constat produit</p>
              <div className="rounded-lg border border-hairline bg-surface p-3">
                <span className="font-mono text-xs text-accent">{tool.example_finding.type}</span>
                <p className="mt-1 text-sm text-ink-300">{tool.example_finding.description}</p>
              </div>
            </div>

            <div className="mt-5 space-y-3">
              <p className="eyebrow !mb-0">Profils disponibles</p>
              {tool.profiles.map((profile) => (
                <div key={profile.profile} className="rounded-lg border border-hairline p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium text-ink-50">{profile.label}</span>
                    <div className="flex items-center gap-2">
                      <Badge tone={riskTierTone(profile.risk.tier)}>
                        {TIER_LABELS[profile.risk.tier] ?? profile.risk.tier}
                      </Badge>
                      <span className="text-xs text-ink-500">score {profile.risk.score.toFixed(2)}</span>
                    </div>
                  </div>
                  <p className="mt-2 text-sm text-ink-300">{profile.explanation}</p>
                  <p className="mt-2 text-xs text-ink-500">{profile.risk.tier_reason}</p>
                  <p className="mt-2 text-[11px] text-ink-600">
                    impact {profile.risk.impact} · detectabilite {profile.risk.detectability} · reversibilite{" "}
                    {profile.risk.reversibility}
                    {profile.risk.sensitive ? " · marque sensible" : ""}
                  </p>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
