import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowUpDown,
  CheckCircle2,
  ChevronDown,
  CloudRain,
  Loader2,
  MapPin,
  OctagonAlert,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Waves,
  Wind,
  Zap,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useLocationContext, formatLocation } from "@/hooks/useLocation";
import { useMapLocate } from "@/hooks/useMapLocate";
import { getSafetyReport } from "@/services/safetyService";
import type { SafetyRawEvidence } from "@/services/safetyService";

// ---------------------------------------------------------------------------
// Meta
// ---------------------------------------------------------------------------

const title = "Safety & Alerts — ORCA";
const description =
  "Full safety history, cyclone tracking and alert subscriptions for your operating area.";

export const Route = createFileRoute("/safety")({
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
// Helpers
// ---------------------------------------------------------------------------

type RiskLevel = "LOW" | "MODERATE" | "HIGH" | "UNKNOWN";

const RISK_STYLES: Record<
  RiskLevel,
  { border: string; badge: string; icon: typeof ShieldCheck; text: string }
> = {
  LOW: {
    border: "border-safe/40",
    badge: "bg-safe/20 text-safe border-safe/40",
    icon: ShieldCheck,
    text: "text-safe",
  },
  MODERATE: {
    border: "border-warn/40",
    badge: "bg-warn/20 text-warn border-warn/40",
    icon: AlertTriangle,
    text: "text-warn",
  },
  HIGH: {
    border: "border-danger/40",
    badge: "bg-danger/20 text-danger border-danger/40",
    icon: OctagonAlert,
    text: "text-danger",
  },
  UNKNOWN: {
    border: "border-border",
    badge: "bg-muted text-muted-foreground border-border",
    icon: ShieldAlert,
    text: "text-muted-foreground",
  },
};

function normaliseLevel(level: string | null): RiskLevel {
  const up = (level ?? "").toUpperCase();
  if (up === "LOW" || up === "MODERATE" || up === "HIGH") return up as RiskLevel;
  return "UNKNOWN";
}

function fmtNum(
  v: number | null,
  decimals: number,
  unit: string,
): string {
  return v != null ? `${v.toFixed(decimals)} ${unit}`.trim() : "N/A";
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ConditionRow({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon?: React.ElementType;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border px-3 py-2 text-sm">
      <dt className="flex items-center gap-1.5 text-muted-foreground">
        {Icon && <Icon className="size-3.5 shrink-0" />}
        {label}
      </dt>
      <dd className="font-medium text-shell">{value}</dd>
    </div>
  );
}

function SectionSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="mt-4 space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full rounded-lg bg-muted" />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Safety Overview Card
// ---------------------------------------------------------------------------

function OverviewCard({ raw }: { raw: SafetyRawEvidence }) {
  const level = normaliseLevel(raw.risk_level);
  const styles = RISK_STYLES[level];
  const Icon = styles.icon;

  return (
    <div
      className={`rounded-xl border ${styles.border} bg-card p-4 space-y-4`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className={`rounded-full border p-2 ${styles.badge}`}>
            <Icon className="size-5" />
          </div>
          <div>
            <p className={`text-lg font-bold ${styles.text}`}>
              {level === "UNKNOWN" ? "No Data" : level + " RISK"}
            </p>
            <p className="text-xs text-muted-foreground">
              Nearest zone: {raw.zone_id ?? "—"}
            </p>
          </div>
        </div>
        <div className="flex gap-4 text-right">
          {raw.risk_score != null && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                Risk Score
              </p>
              <p className={`text-xl font-bold ${styles.text}`}>
                {raw.risk_score.toFixed(2)}
              </p>
            </div>
          )}
          {raw.safety_score != null && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                Safety Score
              </p>
              <p className="text-xl font-bold text-safe">
                {raw.safety_score.toFixed(1)}
                <span className="text-sm font-normal text-muted-foreground">
                  /100
                </span>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Weather & Sea Conditions
// ---------------------------------------------------------------------------

function WeatherSection({ raw }: { raw: SafetyRawEvidence }) {
  const hasAny =
    raw.wind_speed_ms != null ||
    raw.wave_height_m != null ||
    raw.wave_period_s != null ||
    raw.wave_direction_deg != null ||
    raw.current_speed_ms != null ||
    raw.rainfall_mean != null;

  return (
    <section className="panel p-4">
      <h2 className="text-sm font-semibold text-shell">
        Weather &amp; Sea Conditions
      </h2>
      {!hasAny ? (
        <p className="mt-4 text-sm text-muted-foreground">
          No weather or sea data available for this location.
        </p>
      ) : (
        <dl className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {raw.wind_speed_ms != null && (
            <ConditionRow
              icon={Wind}
              label="Wind Speed"
              value={fmtNum(raw.wind_speed_ms, 2, "m/s")}
            />
          )}
          {raw.wave_height_m != null && (
            <ConditionRow
              icon={Waves}
              label="Wave Height"
              value={fmtNum(raw.wave_height_m, 2, "m")}
            />
          )}
          {raw.wave_period_s != null && (
            <ConditionRow
              icon={Waves}
              label="Wave Period"
              value={fmtNum(raw.wave_period_s, 1, "s")}
            />
          )}
          {raw.wave_direction_deg != null && (
            <ConditionRow
              label="Wave Direction"
              value={fmtNum(raw.wave_direction_deg, 0, "°")}
            />
          )}
          {raw.current_speed_ms != null && (
            <ConditionRow
              label="Current Speed"
              value={fmtNum(raw.current_speed_ms, 2, "m/s")}
            />
          )}
          {raw.rainfall_mean != null && (
            <ConditionRow
              icon={CloudRain}
              label="Rainfall (mean)"
              value={fmtNum(raw.rainfall_mean, 1, "mm")}
            />
          )}
        </dl>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Cyclone / Storm Risk
// ---------------------------------------------------------------------------

function CycloneSection({ raw }: { raw: SafetyRawEvidence }) {
  const hasCyclone =
    raw.cyclone_distance_km != null || raw.cyclone_wind_kt != null;

  const isActive =
    hasCyclone &&
    (raw.cyclone_distance_km != null
      ? raw.cyclone_distance_km < 500
      : false);

  return (
    <section className="panel p-4">
      <h2 className="text-sm font-semibold text-shell">
        Cyclone &amp; Storm Risk
      </h2>
      {!hasCyclone ? (
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-safe/40 bg-safe/10 px-3 py-3">
          <CheckCircle2 className="size-4 text-safe" />
          <p className="text-sm text-safe">
            No cyclone or storm data detected near this location.
          </p>
        </div>
      ) : (
        <dl className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {raw.cyclone_distance_km != null && (
            <div
              className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${
                isActive
                  ? "border-danger/40 bg-danger/10"
                  : "border-border"
              }`}
            >
              <dt className="flex items-center gap-1.5 text-muted-foreground">
                <Zap className="size-3.5 shrink-0" />
                Distance to Cyclone
              </dt>
              <dd
                className={`font-medium ${
                  isActive ? "text-danger" : "text-shell"
                }`}
              >
                {fmtNum(raw.cyclone_distance_km, 1, "km")}
              </dd>
            </div>
          )}
          {raw.cyclone_wind_kt != null && (
            <div
              className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${
                isActive
                  ? "border-danger/40 bg-danger/10"
                  : "border-border"
              }`}
            >
              <dt className="flex items-center gap-1.5 text-muted-foreground">
                <Wind className="size-3.5 shrink-0" />
                Cyclone Wind
              </dt>
              <dd
                className={`font-medium ${
                  isActive ? "text-danger" : "text-shell"
                }`}
              >
                {fmtNum(raw.cyclone_wind_kt, 1, "kt")}
              </dd>
            </div>
          )}
        </dl>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Zone Alerts table (uses nearest zone only — ranking not exposed via proxy)
// ---------------------------------------------------------------------------

type SortKey = "risk_score" | "zone_id";
type FilterLevel = "ALL" | "LOW" | "MODERATE" | "HIGH";

const SORT_LABELS: Record<SortKey, string> = {
  risk_score: "Risk (highest first)",
  zone_id: "Zone ID",
};

function ZoneAlertsSection({ raw }: { raw: SafetyRawEvidence }) {
  const { locateZone } = useMapLocate();
  const [sortKey, setSortKey] = useState<SortKey>("risk_score");
  const [filter, setFilter] = useState<FilterLevel>("ALL");

  // We only have data for one zone (nearest) from the API.
  // Build a single-row list to enable the pattern without an extra API call.
  const level = normaliseLevel(raw.risk_level);

  const zones = useMemo(() => {
    if (!raw.zone_id) return [];
    return [
      {
        zone_id: raw.zone_id,
        risk_score: raw.risk_score,
        risk_level: level,
        safety_score: raw.safety_score,
      },
    ];
  }, [raw, level]);

  const filtered = useMemo(() => {
    let items = zones;
    if (filter !== "ALL") {
      items = items.filter((z) => z.risk_level === filter);
    }
    return [...items].sort((a, b) => {
      if (sortKey === "risk_score") {
        return (b.risk_score ?? 0) - (a.risk_score ?? 0);
      }
      return a.zone_id.localeCompare(b.zone_id);
    });
  }, [zones, filter, sortKey]);

  if (zones.length === 0) return null;

  return (
    <section className="panel p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-shell">
          Zone Alerts
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          {/* Filter tabs */}
          <div className="flex gap-1 rounded-lg border border-border bg-deep p-1">
            {(["ALL", "LOW", "MODERATE", "HIGH"] as FilterLevel[]).map((lv) => (
              <button
                key={lv}
                type="button"
                onClick={() => setFilter(lv)}
                className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                  filter === lv
                    ? "bg-card text-shell shadow-sm"
                    : "text-muted-foreground hover:text-shell"
                }`}
              >
                {lv === "ALL" ? "All" : lv}
              </button>
            ))}
          </div>

          {/* Sort dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
                <ArrowUpDown className="size-3" />
                {SORT_LABELS[sortKey]}
                <ChevronDown className="size-3" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {(Object.keys(SORT_LABELS) as SortKey[]).map((k) => (
                <DropdownMenuItem
                  key={k}
                  onClick={() => setSortKey(k)}
                  className={sortKey === k ? "font-semibold" : ""}
                >
                  {SORT_LABELS[k]}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {filtered.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted-foreground">
          No zones match the selected filter.
        </p>
      ) : (
        <div className="space-y-2">
          {filtered.map((zone) => {
            const zLevel = zone.risk_level;
            const zStyles = RISK_STYLES[zLevel];
            const ZIcon = zStyles.icon;
            return (
              <div
                key={zone.zone_id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-deep px-3 py-3"
              >
                <div className="flex items-center gap-3">
                  <ZIcon className={`size-4 shrink-0 ${zStyles.text}`} />
                  <div>
                    <p className="text-sm font-semibold text-shell">
                      {zone.zone_id}
                    </p>
                    <span
                      className={`mt-0.5 inline-block rounded-full border px-2 py-0.5 text-[10px] font-medium ${zStyles.badge}`}
                    >
                      {zLevel}
                    </span>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-4">
                  {zone.risk_score != null && (
                    <div className="text-right">
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                        Risk
                      </p>
                      <p className={`text-sm font-bold ${zStyles.text}`}>
                        {zone.risk_score.toFixed(2)}
                      </p>
                    </div>
                  )}
                  {zone.safety_score != null && (
                    <div className="text-right">
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                        Safety
                      </p>
                      <p className="text-sm font-bold text-safe">
                        {zone.safety_score.toFixed(1)}
                        <span className="text-[10px] font-normal text-muted-foreground">
                          /100
                        </span>
                      </p>
                    </div>
                  )}
                  <Button
                    id={`locate-${zone.zone_id}`}
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-7 gap-1.5 text-xs"
                    onClick={() => locateZone(zone.zone_id)}
                  >
                    <MapPin className="size-3" />
                    Locate on map
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

function Page() {
  const { location } = useLocationContext();

  const safetyQuery = useQuery({
    queryKey: ["safety", location.latitude, location.longitude],
    queryFn: () => getSafetyReport(location),
  });

  const raw = safetyQuery.data?.raw;
  const report = safetyQuery.data?.report;
  const locationLabel = formatLocation(location);
  const coordLabel = `${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}`;

  return (
    <AppShell>
      <div className="space-y-5 pb-16 xl:pb-4">
        {/* ── Page header ───────────────────────────────────────── */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <h1 className="text-xl font-semibold text-shell">
              Safety &amp; Alerts
            </h1>
            <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <MapPin className="size-3.5 shrink-0 text-accent" />
              {locationLabel ? `${locationLabel} · ${coordLabel}` : coordLabel}
            </p>
          </div>

          <Button
            id="safety-refresh"
            variant="outline"
            size="sm"
            className="gap-2"
            disabled={safetyQuery.isFetching}
            onClick={() => { void safetyQuery.refetch(); }}
          >
            <RefreshCw
              className={`size-3.5 ${safetyQuery.isFetching ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
        </div>

        {/* ── Refetch indicator ─────────────────────────────────── */}
        {safetyQuery.isFetching && !safetyQuery.isPending && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" />
            Refreshing…
          </div>
        )}

        {/* ── Last updated ──────────────────────────────────────── */}
        {report && (
          <p className="text-xs text-muted-foreground">
            Last updated: {new Date().toLocaleString()}
          </p>
        )}

        {/* ── Error state ───────────────────────────────────────── */}
        {safetyQuery.isError && (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-border bg-card py-16 text-center">
            <AlertCircle className="size-8 text-danger" />
            <p className="text-sm text-muted-foreground">
              Could not load safety data. Check that the backend is running.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => { void safetyQuery.refetch(); }}
            >
              Retry
            </Button>
          </div>
        )}

        {/* ── Loading state ─────────────────────────────────────── */}
        {safetyQuery.isPending && (
          <>
            <section className="panel p-4">
              <Skeleton className="mb-4 h-5 w-32 rounded bg-muted" />
              <Skeleton className="h-24 w-full rounded-xl bg-muted" />
            </section>
            <section className="panel p-4">
              <Skeleton className="mb-4 h-5 w-44 rounded bg-muted" />
              <SectionSkeleton rows={4} />
            </section>
            <section className="panel p-4">
              <Skeleton className="mb-4 h-5 w-36 rounded bg-muted" />
              <SectionSkeleton rows={2} />
            </section>
          </>
        )}

        {/* ── Content ───────────────────────────────────────────── */}
        {safetyQuery.isSuccess && raw && (
          <>
            {/* Safety Overview */}
            <section className="panel p-4">
              <h2 className="mb-4 text-sm font-semibold text-shell">
                Safety Overview
              </h2>
              <OverviewCard raw={raw} />
            </section>

            {/* Weather & Sea */}
            <WeatherSection raw={raw} />

            {/* Cyclone / Storm */}
            <CycloneSection raw={raw} />

            {/* Zone Alerts */}
            <ZoneAlertsSection raw={raw} />
          </>
        )}

        {/* ── Empty state ───────────────────────────────────────── */}
        {safetyQuery.isSuccess && !raw && (
          <div className="flex flex-col items-center gap-2 py-16 text-center">
            <ShieldAlert className="size-8 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">
              No safety data is available for this location.
            </p>
          </div>
        )}
      </div>
    </AppShell>
  );
}
