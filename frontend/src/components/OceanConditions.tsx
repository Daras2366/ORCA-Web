import { Droplets, Thermometer, Waves, Wind } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import type { OceanConditions as OceanConditionsData } from "@/types/marine";

const icons: Record<string, LucideIcon> = {
  sst: Thermometer,
  chlorophyll: Droplets,
  wind: Wind,
  waves: Waves,
};

interface Props {
  data?: OceanConditionsData | undefined;
  loading?: boolean | undefined;
  error?: string | null | undefined;
}

export function OceanConditions({ data, loading, error }: Props) {
  return (
    <section className="panel p-4">
      <h2 className="text-sm font-semibold text-shell">Weather &amp; Ocean Conditions</h2>

      {error ? (
        <p className="mt-4 text-sm text-danger">Unable to retrieve marine conditions.</p>
      ) : loading || !data ? (
        <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full rounded-lg bg-muted" />
          ))}
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {data.metrics.map((metric) => {
            const Icon = icons[metric.key] ?? Waves;
            return (
              <div
                key={metric.key}
                className="rounded-lg border border-border bg-deep px-3 py-3"
              >
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Icon className="size-4 text-accent" />
                  {metric.label}
                </div>
                <p className="mt-2 text-lg font-semibold text-shell">{metric.value}</p>
                <p className="text-xs text-blush">{metric.status}</p>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
