import { AlertTriangle, CheckCircle2, OctagonAlert } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import type { SafetyReport } from "@/types/marine";

const statusMap = {
  "All Clear": { icon: CheckCircle2, color: "text-safe", border: "border-safe/40" },
  Warning: { icon: AlertTriangle, color: "text-warn", border: "border-warn/40" },
  Unsafe: { icon: OctagonAlert, color: "text-danger", border: "border-danger/40" },
} as const;

interface Props {
  data?: SafetyReport | undefined;
  loading?: boolean | undefined;
  error?: string | null | undefined;
}

export function SafetyAlerts({ data, loading, error }: Props) {
  const status = data ? statusMap[data.status] : statusMap["All Clear"];
  const Icon = status.icon;

  return (
    <section className="panel flex h-full flex-col p-4">
      <h2 className="text-sm font-semibold text-shell">Safety &amp; Alerts</h2>

      {error ? (
        <p className="mt-4 text-sm text-danger">Unable to retrieve safety data.</p>
      ) : loading || !data ? (
        <div className="mt-4 space-y-3">
          <Skeleton className="h-16 w-full rounded-lg bg-muted" />
          <Skeleton className="h-20 w-full rounded-lg bg-muted" />
        </div>
      ) : (
        <>
          <div className={`mt-4 rounded-lg border ${status.border} bg-deep px-3 py-3`}>
            <p className={`flex items-center gap-2 text-base font-semibold ${status.color}`}>
              <Icon className="size-5" />
              {data.status}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">{data.message}</p>
          </div>

          <dl className="mt-3 space-y-2">
            {data.indicators.map((ind) => (
              <div
                key={ind.label}
                className="flex items-center justify-between rounded-lg border border-border px-3 py-2 text-sm"
              >
                <dt className="text-muted-foreground">{ind.label}</dt>
                <dd
                  className={
                    ind.level === "high"
                      ? "text-danger"
                      : ind.level === "moderate"
                        ? "text-warn"
                        : "text-safe"
                  }
                >
                  {ind.value}
                </dd>
              </div>
            ))}
          </dl>
        </>
      )}
    </section>
  );
}
