import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  Droplets,
  Loader2,
  MapPin,
  RefreshCw,
  Thermometer,
  Waves,
  Wind,
  Fish,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useLocationContext, formatLocation } from "@/hooks/useLocation";
import { getOceanConditions } from "@/services/oceanService";

// ---------------------------------------------------------------------------
// Meta
// ---------------------------------------------------------------------------

const title = "Ocean Conditions — ORCA";
const description =
  "Detailed sea surface temperature, chlorophyll, wind and wave analysis with forecast trends.";

export const Route = createFileRoute("/ocean-conditions")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
    ],
  }),
  component: Page,
});

// ---------------------------------------------------------------------------
// Icon map keyed by OceanMetric.key
// ---------------------------------------------------------------------------

const METRIC_ICONS: Record<string, LucideIcon> = {
  sst: Thermometer,
  chlorophyll: Droplets,
  current: Waves,
  distance: Fish,
  wind: Wind,
  waves: Waves,
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function MetricCard({
  icon: Icon,
  label,
  value,
  status,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  status: string;
}) {
  const isNA = value === "N/A";
  return (
    <article className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className="size-4 shrink-0 text-accent" />
        <span className="truncate uppercase tracking-wider">{label}</span>
      </div>
      <p
        className={`min-w-0 break-words text-2xl font-bold leading-tight ${
          isNA ? "text-muted-foreground" : "text-shell"
        }`}
      >
        {value}
      </p>
      <p className="text-xs text-blush">{status}</p>
    </article>
  );
}

function MetricCardSkeleton() {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
      <Skeleton className="h-4 w-24 rounded bg-muted" />
      <Skeleton className="h-8 w-32 rounded bg-muted" />
      <Skeleton className="h-3 w-16 rounded bg-muted" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

function Page() {
  const { location } = useLocationContext();

  const oceanQuery = useQuery({
    queryKey: ["ocean", location.latitude, location.longitude],
    queryFn: () => getOceanConditions(location),
  });

  const conditions = oceanQuery.data?.conditions;
  const raw = oceanQuery.data?.raw;

  const locationLabel = formatLocation(location);
  const coordLabel = `${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}`;

  return (
    <AppShell>
      <div className="space-y-6 pb-16 xl:pb-4">
        {/* ── Page header ────────────────────────────────────────── */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <h1 className="text-xl font-semibold text-shell">Ocean Conditions</h1>
            <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <MapPin className="size-3.5 shrink-0 text-accent" />
              {locationLabel
                ? `${locationLabel} · ${coordLabel}`
                : coordLabel}
              {raw?.zone_id && (
                <span className="ml-1 rounded-full border border-border bg-deep px-2 py-0.5 text-[10px] text-muted-foreground">
                  nearest zone: {raw.zone_id}
                </span>
              )}
            </p>
          </div>

          <Button
            id="oc-refresh"
            variant="outline"
            size="sm"
            className="gap-2"
            disabled={oceanQuery.isFetching}
            onClick={() => { void oceanQuery.refetch(); }}
          >
            <RefreshCw
              className={`size-3.5 ${oceanQuery.isFetching ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
        </div>

        {/* ── Updated-at timestamp ───────────────────────────────── */}
        {conditions && (
          <p className="text-xs text-muted-foreground">
            Last updated: {conditions.updated_at}
          </p>
        )}

        {/* ── Error state ────────────────────────────────────────── */}
        {oceanQuery.isError && (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-border bg-card py-16 text-center">
            <AlertCircle className="size-8 text-danger" />
            <p className="text-sm text-muted-foreground">
              Could not load ocean conditions. Check that the backend is running.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => { void oceanQuery.refetch(); }}
            >
              Retry
            </Button>
          </div>
        )}

        {/* ── Loading state ──────────────────────────────────────── */}
        {oceanQuery.isPending && (
          <section className="panel p-4">
            <h2 className="text-sm font-semibold text-shell">Current Conditions</h2>
            <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {[0, 1, 2, 3].map((i) => (
                <MetricCardSkeleton key={i} />
              ))}
            </div>
          </section>
        )}

        {/* ── Loading spinner overlay for refetch ───────────────── */}
        {oceanQuery.isFetching && !oceanQuery.isPending && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" />
            Refreshing…
          </div>
        )}

        {/* ── Current Conditions ─────────────────────────────────── */}
        {oceanQuery.isSuccess && conditions && (
          <section className="panel p-4">
            <h2 className="text-sm font-semibold text-shell">Current Conditions</h2>

            {conditions.metrics.length === 0 ? (
              <p className="mt-4 text-sm text-muted-foreground">
                No ocean data is available for this location.
              </p>
            ) : (
              <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                {conditions.metrics.map((metric) => {
                  const Icon = METRIC_ICONS[metric.key] ?? Waves;
                  return (
                    <MetricCard
                      key={metric.key}
                      icon={Icon}
                      label={metric.label}
                      value={metric.value}
                      status={metric.status}
                    />
                  );
                })}
              </div>
            )}
          </section>
        )}

        {/* ── Data Summary ───────────────────────────────────────── */}
        {oceanQuery.isSuccess && raw && (
          <section className="panel p-4">
            <h2 className="mb-4 text-sm font-semibold text-shell">Data Summary</h2>
            <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <SummaryRow
                label="Source Zone"
                value={raw.zone_id ?? "N/A"}
              />
              <SummaryRow
                label="Fishing Score (HSI)"
                value={
                  raw.fishing_score != null
                    ? raw.fishing_score.toFixed(4)
                    : "N/A"
                }
              />
              <SummaryRow
                label="Sea Surface Temp"
                value={raw.sst_c != null ? `${raw.sst_c.toFixed(2)} °C` : "N/A"}
              />
              <SummaryRow
                label="Chlorophyll"
                value={
                  raw.chlorophyll_mean != null
                    ? `${raw.chlorophyll_mean.toFixed(3)} mg/m³`
                    : "N/A"
                }
              />
              <SummaryRow
                label="Current Speed"
                value={
                  raw.current_speed_ms != null
                    ? `${raw.current_speed_ms.toFixed(2)} m/s`
                    : "N/A"
                }
              />
              {raw.pfz_distance_km != null && (
                <SummaryRow
                  label="Distance to Zone"
                  value={`${raw.pfz_distance_km.toFixed(1)} km`}
                />
              )}
            </dl>
          </section>
        )}

        {/* ── Empty state: success but no metrics ───────────────── */}
        {oceanQuery.isSuccess &&
          conditions &&
          conditions.metrics.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-16 text-center">
              <Waves className="size-8 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">
                No ocean metrics are available for this location.
              </p>
            </div>
          )}
      </div>
    </AppShell>
  );
}

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border px-3 py-2 text-sm">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium text-shell">{value}</dd>
    </div>
  );
}
