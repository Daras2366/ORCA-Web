import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState, useMemo, useEffect } from "react";
import {
  Search,
  MapPin,
  ArrowUpDown,
  Fish,
  Loader2,
  AlertCircle,
  Thermometer,
  Droplets,
  ShieldCheck,
  ChevronDown,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useLocationContext } from "@/hooks/useLocation";
import { useMapLocate } from "@/hooks/useMapLocate";
import { getFishingZones } from "@/services/oceanService";
import type { FishingZone, PotentialLevel } from "@/types/marine";

const title = "Fishing Zones — ORCA";
const description =
  "Browse and compare all potential fishing zones with filters, distance and detailed scoring.";

export const Route = createFileRoute("/fishing-zones")({
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

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371.0088;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.asin(Math.sqrt(a));
}

const POTENTIAL_COLOR: Record<PotentialLevel, string> = {
  High: "bg-safe/20 text-safe border-safe/40",
  Medium: "bg-rose/20 text-rose border-rose/40",
  Low: "bg-muted text-muted-foreground border-border",
};

type SortKey = "hsi" | "safety" | "distance" | "confidence";

const SORT_LABELS: Record<SortKey, string> = {
  hsi: "Fishing Potential (HSI)",
  safety: "Safest first",
  distance: "Closest first",
  confidence: "Confidence",
};

type FilterLevel = "All" | PotentialLevel;

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Stat({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-muted-foreground">
        {icon}
        {label}
      </span>
      <span className="text-sm font-medium text-shell">{value}</span>
    </div>
  );
}

function ZoneCard({
  zone,
  distanceKm,
  onLocate,
  onDetails,
}: {
  zone: FishingZone;
  distanceKm: number;
  onLocate: (id: string) => void;
  onDetails: (zone: FishingZone) => void;
}) {
  return (
    <article className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 transition-colors hover:border-rose/40">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-shell">{zone.zone_id}</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">{distanceKm.toFixed(1)} km away</p>
        </div>
        <span
          className={`rounded-full border px-2 py-0.5 text-xs font-medium ${POTENTIAL_COLOR[zone.potential]}`}
        >
          {zone.potential}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 rounded-lg border border-border bg-deep p-3">
        <Stat label="HSI" value={zone.hsi.toFixed(2)} icon={<Fish className="size-3" />} />
        <Stat
          label="Safety"
          value={zone.safety_score != null ? `${zone.safety_score.toFixed(1)}/100` : "N/A"}
          icon={<ShieldCheck className="size-3" />}
        />
        <Stat label="Confidence" value={`${Math.round(zone.confidence * 100)}%`} />
        {zone.sst_c != null && (
          <Stat
            label="SST"
            value={`${zone.sst_c.toFixed(2)}°C`}
            icon={<Thermometer className="size-3" />}
          />
        )}
        {zone.chlorophyll_mg_m3 != null && (
          <Stat
            label="Chlorophyll"
            value={`${zone.chlorophyll_mg_m3.toFixed(3)} mg/m³`}
            icon={<Droplets className="size-3" />}
          />
        )}
        <Stat
          label="Coordinates"
          value={`${zone.latitude.toFixed(2)}, ${zone.longitude.toFixed(2)}`}
        />
      </div>

      <div className="flex gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-7 flex-1 gap-1.5 text-xs"
          onClick={() => onLocate(zone.zone_id)}
        >
          <MapPin className="size-3" />
          Locate on map
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 flex-1 text-xs"
          onClick={() => onDetails(zone)}
        >
          View Details
        </Button>
      </div>
    </article>
  );
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border px-3 py-2">
      <dt className="text-[11px] text-muted-foreground">{label}</dt>
      <dd className="text-shell">{value}</dd>
    </div>
  );
}

function ZoneDetailDialog({
  zone,
  distanceKm,
  onClose,
}: {
  zone: FishingZone | null;
  distanceKm: number | null;
  onClose: () => void;
}) {
  return (
    <Dialog open={Boolean(zone)} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{zone?.zone_id} — Zone Details</DialogTitle>
          <DialogDescription>
            Live data from the ORCA Ocean Agent. Positions are zone centroids.
          </DialogDescription>
        </DialogHeader>
        {zone && (
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <DetailItem label="Zone ID" value={zone.zone_id} />
            <DetailItem label="Potential level" value={zone.potential} />
            <DetailItem label="HSI score" value={zone.hsi.toFixed(2)} />
            <DetailItem
              label="Safety score"
              value={zone.safety_score != null ? `${zone.safety_score.toFixed(1)}/100` : "N/A"}
            />
            <DetailItem label="Confidence" value={`${Math.round(zone.confidence * 100)}%`} />
            <DetailItem
              label="SST"
              value={zone.sst_c != null ? `${zone.sst_c.toFixed(2)}°C` : "N/A"}
            />
            <DetailItem
              label="Chlorophyll"
              value={
                zone.chlorophyll_mg_m3 != null
                  ? `${zone.chlorophyll_mg_m3.toFixed(3)} mg/m³`
                  : "N/A"
              }
            />
            <DetailItem
              label="Coordinates"
              value={`${zone.latitude.toFixed(2)}, ${zone.longitude.toFixed(2)}`}
            />
            {distanceKm !== null && (
              <DetailItem label="Distance" value={`${distanceKm.toFixed(1)} km`} />
            )}
            <DetailItem label="Recommended" value={zone.recommended ? "Yes ✓" : "No"} />
          </dl>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

function Page() {
  const { location } = useLocationContext();
  const { locateZone, registerZones } = useMapLocate();

  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("hsi");
  const [filterLevel, setFilterLevel] = useState<FilterLevel>("All");
  const [detailZone, setDetailZone] = useState<FishingZone | null>(null);

  const zonesQuery = useQuery({
    queryKey: ["fishing-zones", location.latitude, location.longitude],
    queryFn: () => getFishingZones(location),
  });

  const zones = zonesQuery.data ?? [];

  useEffect(() => {
    registerZones(zones.map((z) => z.zone_id));
  }, [zones, registerZones]);

  const withDistance = useMemo(
    () =>
      zones.map((z) => ({
        zone: z,
        distanceKm: haversineKm(location.latitude, location.longitude, z.latitude, z.longitude),
      })),
    [zones, location],
  );

  const displayed = useMemo(() => {
    let items = withDistance;

    if (filterLevel !== "All") {
      items = items.filter((i) => i.zone.potential === filterLevel);
    }

    if (search.trim()) {
      const q = search.trim().toUpperCase();
      items = items.filter((i) => i.zone.zone_id.toUpperCase().includes(q));
    }

    return [...items].sort((a, b) => {
      if (sortKey === "hsi") return b.zone.hsi - a.zone.hsi;
      if (sortKey === "safety") {
        return (b.zone.safety_score ?? 0) - (a.zone.safety_score ?? 0);
      }
      if (sortKey === "distance") return a.distanceKm - b.distanceKm;
      if (sortKey === "confidence") return b.zone.confidence - a.zone.confidence;
      return 0;
    });
  }, [withDistance, filterLevel, search, sortKey]);

  const detailDistance = useMemo(() => {
    if (!detailZone) return null;
    return withDistance.find((i) => i.zone.zone_id === detailZone.zone_id)?.distanceKm ?? null;
  }, [detailZone, withDistance]);

  const levelCounts = useMemo(
    () => ({
      All: zones.length,
      High: zones.filter((z) => z.potential === "High").length,
      Medium: zones.filter((z) => z.potential === "Medium").length,
      Low: zones.filter((z) => z.potential === "Low").length,
    }),
    [zones],
  );

  return (
    <AppShell>
      <div className="space-y-5 pb-16 xl:pb-4">
        {/* Page header */}
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-semibold text-shell">Fishing Zones</h1>
          <p className="text-sm text-muted-foreground">
            Live ocean data · {zones.length} zone{zones.length !== 1 ? "s" : ""} loaded
          </p>
        </div>

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[180px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="fz-search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search zone ID…"
              className="h-9 bg-deep pl-8 text-sm"
            />
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs">
                <ArrowUpDown className="size-3.5" />
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

          <div className="flex gap-1 rounded-lg border border-border bg-deep p-1">
            {(["All", "High", "Medium", "Low"] as FilterLevel[]).map((lv) => (
              <button
                key={lv}
                type="button"
                onClick={() => setFilterLevel(lv)}
                className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                  filterLevel === lv
                    ? "bg-card text-shell shadow-sm"
                    : "text-muted-foreground hover:text-shell"
                }`}
              >
                {lv}
                <span className="ml-1 text-[10px] opacity-60">{levelCounts[lv]}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Loading */}
        {zonesQuery.isPending && (
          <div className="flex items-center justify-center gap-2 py-24 text-muted-foreground">
            <Loader2 className="size-5 animate-spin" />
            <span className="text-sm">Loading fishing zones…</span>
          </div>
        )}

        {/* Error */}
        {zonesQuery.isError && (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-border bg-card py-16 text-center">
            <AlertCircle className="size-8 text-danger" />
            <p className="text-sm text-muted-foreground">
              Could not load fishing zones. Check the backend is running.
            </p>
            <Button variant="outline" size="sm" onClick={() => zonesQuery.refetch()}>
              Retry
            </Button>
          </div>
        )}

        {/* Empty */}
        {zonesQuery.isSuccess && displayed.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-16 text-center">
            <Fish className="size-8 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">No zones match your filters.</p>
          </div>
        )}

        {/* Zone cards */}
        {zonesQuery.isSuccess && displayed.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-2 2xl:grid-cols-3">
            {displayed.map(({ zone, distanceKm }) => (
              <ZoneCard
                key={zone.zone_id}
                zone={zone}
                distanceKm={distanceKm}
                onLocate={locateZone}
                onDetails={setDetailZone}
              />
            ))}
          </div>
        )}
      </div>

      <ZoneDetailDialog
        zone={detailZone}
        distanceKm={detailDistance}
        onClose={() => setDetailZone(null)}
      />
    </AppShell>
  );
}
