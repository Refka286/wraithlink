import type { LucideIcon } from "lucide-react";

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2.5 py-6 text-sm text-ink-400">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-ink-600 border-t-accent" />
      {label && <span>{label}</span>}
    </div>
  );
}

export function ErrorBanner({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2 rounded-card border border-red-800 bg-red-900/20 p-3 text-sm text-red-400">
      <span className="mt-0.5 text-red-500">!</span>
      <span>{children}</span>
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  hint,
}: {
  icon: LucideIcon;
  title: string;
  hint?: string;
}) {
  return (
    <div className="panel flex flex-col items-center gap-2 py-10 text-center">
      <Icon size={26} strokeWidth={1.5} className="text-ink-600" />
      <p className="text-sm font-medium text-ink-300">{title}</p>
      {hint && <p className="max-w-sm text-xs text-ink-500">{hint}</p>}
    </div>
  );
}
