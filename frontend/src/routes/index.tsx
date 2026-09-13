import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState, useMemo, useEffect, useCallback } from "react";
import { AppShell } from "@/components/AppShell";
import { MarineMap } from "@/components/MarineMap";
import { OceanConditions } from "@/components/OceanConditions";
import { RecommendedZone } from "@/components/RecommendedZone";
import { SafetyAlerts } from "@/components/SafetyAlerts";
import { QuickRouteEstimate } from "@/components/QuickRouteEstimate";
import { NavigationPanel } from "@/components/NavigationPanel";
import { NavigationResults } from "@/components/NavigationResults";
import { useLocationContext } from "@/hooks/useLocation";
import { useMapLocate } from "@/hooks/useMapLocate";
import { getFishingZones, getOceanConditions } from "@/services/oceanService";
import { getSafetyReport } from "@/services/safetyService";
import { getRouteEstimate } from "@/services/routeService";
import type { NavigationResult, ZoneFactor } from "@/types/marine";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const title = "ORCA — Marine Intelligence Dashboard";
const description =
  "ORCA gives fishers and marine operators potential fishing zones, ocean conditions, safety status and route estimates in one dashboard.";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
    ],
  }),
  component: Dashboard,
});

// Callback type expected by NavigationPanel – must match its internal signature.
type NavMode = "idle" | "selecting_start" | "selecting_destination";
type NavClickHandler = (lat: number, lng: number) => void;

function Dashboard() {
  const { location } = useLocationContext();
  const { registerZones, locateRequest } = useMapLocate();
  const [detailZone, setDetailZone] = useState<string | null>(null);

  // --- Navigation state ---
  const [navigationResult, setNavigationResult] = useState<NavigationResult | null>(null);
  const [navigationMode, setNavigationMode] = useState<NavMode>("idle");
  const [navMapClickHandler, setNavMapClickHandler] = useState<NavClickHandler | null>(null);

  // Stable map-click forwarder so MarineMap doesn't re-register listeners unnecessarily.
  const handleMapClick = useCallback(
    (lat: number, lng: number) => {
      navMapClickHandler?.(lat, lng);
    },
    [navMapClickHandler],
  );

  const handleRegisterNavClickHandler = useCallback((handler: NavClickHandler | null) => {
    setNavMapClickHandler(handler);
  }, []);

  const zonesQuery = useQuery({
    queryKey: ["fishing-zones", location.latitude, location.longitude],
    queryFn: () => getFishingZones(location),
  });
  const oceanQuery = useQuery({
    queryKey: ["ocean", location.latitude, location.longitude],
    queryFn: () => getOceanConditions(location),
  });
  const safetyQuery = useQuery({
    queryKey: ["safety", location.latitude, location.longitude],
    queryFn: () => getSafetyReport(location),
  });

  const zones = zonesQuery.data ?? [];
  const recommended = zones.find((z) => z.recommended) ?? zones[0];

  useEffect(() => {
    registerZones(zones.map((zone) => zone.zone_id));
  }, [zones, registerZones]);

  const routeQuery = useQuery({
    queryKey: ["route", location.latitude, location.longitude, recommended?.zone_id],
    queryFn: () => getRouteEstimate(location, recommended!.zone_id),
    enabled: Boolean(recommended),
  });

  // Build radar factors from real backend zone data (no mock fallback)
  const zoneFactors = useMemo<ZoneFactor[]>(() => {
    if (!recommended) return [];
    const factors: ZoneFactor[] = [
      { factor: "Fishing (HSI)", score: Math.round(recommended.hsi * 100) },
    ];
    if (recommended.safety_score != null) {
      factors.push({ factor: "Safety", score: Math.round(recommended.safety_score) });
    }
    if (recommended.confidence != null) {
      factors.push({ factor: "Confidence", score: Math.round(recommended.confidence * 100) });
    }
    return factors;
  }, [recommended]);

  const selected = zones.find((z) => z.zone_id === detailZone);

  return (
    <AppShell>
      <div className="space-y-4 pb-16 xl:pb-4">
        <MarineMap
          zones={zones}
          location={location}
          loading={zonesQuery.isPending}
          error={zonesQuery.isError ? "error" : null}
          onViewDetails={setDetailZone}
          locateRequest={locateRequest}
          navigationResult={navigationResult}
          onMapClick={handleMapClick}
          navigationMode={navigationMode}
        />

        {/* Navigation planning panel — rendered below the map */}
        <NavigationPanel
          userLocation={location}
          onRouteCalculated={(result) => setNavigationResult(result)}
          onModeChange={(mode) => setNavigationMode(mode)}
          onRegisterClickHandler={handleRegisterNavClickHandler}
        />

        {/* Navigation results panel — visible when a successful route exists */}
        {navigationResult?.success && (
          <NavigationResults result={navigationResult} onClose={() => setNavigationResult(null)} />
        )}

        <OceanConditions
          data={oceanQuery.data?.conditions}
          loading={oceanQuery.isPending}
          error={oceanQuery.isError ? "error" : null}
        />

        <div className="grid gap-4 lg:grid-cols-2">
          <RecommendedZone
            zone={recommended}
            factors={zoneFactors}
            loading={zonesQuery.isPending}
            error={zonesQuery.isError ? "error" : null}
          />
          <SafetyAlerts
            data={safetyQuery.data?.report}
            loading={safetyQuery.isPending}
            error={safetyQuery.isError ? "error" : null}
          />
        </div>

        <QuickRouteEstimate
          data={routeQuery.data}
          loading={routeQuery.isPending}
          error={routeQuery.isError ? "error" : null}
        />
      </div>

      <Dialog open={Boolean(detailZone)} onOpenChange={(o) => !o && setDetailZone(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{selected?.zone_id} details</DialogTitle>
            <DialogDescription>
              Zone data from ORCA backend. Marker positions are zone centroids, not official PFZ
              boundary polygons.
            </DialogDescription>
          </DialogHeader>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <Detail label="Fishing potential" value={selected ? selected.hsi.toFixed(2) : "—"} />
            <Detail label="Level" value={selected?.potential ?? "—"} />
            <Detail label="SST" value={selected?.sst_c != null ? `${selected.sst_c}°C` : "N/A"} />
            <Detail
              label="Chlorophyll"
              value={
                selected?.chlorophyll_mg_m3 != null ? `${selected.chlorophyll_mg_m3} mg/m³` : "N/A"
              }
            />
            <Detail
              label="Safety"
              value={selected?.safety_score != null ? `${selected.safety_score}/100` : "N/A"}
            />
            <Detail
              label="Coordinates"
              value={selected ? `${selected.latitude}, ${selected.longitude}` : "—"}
            />
          </dl>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border px-3 py-2">
      <dt className="text-[11px] text-muted-foreground">{label}</dt>
      <dd className="text-shell">{value}</dd>
    </div>
  );
}
