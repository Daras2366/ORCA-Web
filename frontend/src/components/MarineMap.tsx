import { Suspense, lazy } from "react";
import { ClientOnly } from "@tanstack/react-router";
import { Layers, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { LocateRequest } from "@/hooks/useMapLocate";
import type { FishingZone, UserLocation, NavigationResult } from "@/types/marine";

// Lazy-load the Leaflet map. This import is ONLY used inside <ClientOnly>,
// so the TanStack Start compiler removes it from the SSR bundle entirely
// (handleClientOnlyJSX transform strips <ClientOnly> children on the server).
const LeafletMap = lazy(() => import("./map/LeafletMap.client"));

interface Props {
  zones: FishingZone[];
  location: UserLocation;
  loading?: boolean | undefined;
  error?: string | null | undefined;
  onShowRoute: (zoneId: string) => void;
  locateRequest?: LocateRequest | null;
  navigationResult?: NavigationResult | null;
}

function MapFallback({ label }: { label: string }) {
  return (
    <div className="flex h-full w-full items-center justify-center gap-2 bg-abyss text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin" />
      {label}
    </div>
  );
}

export function MarineMap({
  zones,
  location,
  loading,
  error,
  onShowRoute,
  locateRequest,
  navigationResult,
}: Props) {
  return (
    <section className="panel overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-shell">Potential Fishing Zones</h2>
        </div>
        <Button variant="outline" size="sm" className="gap-2" disabled title="Coming soon">
          <Layers className="size-4" />
          Layers
        </Button>
      </div>

      <div className="h-[340px] w-full md:h-[420px]">
        {error ? (
          <div className="flex h-full items-center justify-center px-6 text-center text-sm text-danger">
            Unable to retrieve fishing zone data.
          </div>
        ) : loading ? (
          <MapFallback label="Loading marine map…" />
        ) : (
          // ClientOnly ensures the Leaflet map (and its .client. imports) are
          // excluded from the SSR bundle by the TanStack Start compiler transform.
          <ClientOnly fallback={<MapFallback label="Loading marine map…" />}>
            <Suspense fallback={<MapFallback label="Loading marine map…" />}>
              <LeafletMap
                zones={zones}
                location={location}
                onShowRoute={onShowRoute}
                locateRequest={locateRequest ?? null}
                navigationResult={navigationResult}
              />
            </Suspense>
          </ClientOnly>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-4 border-t border-border px-4 py-2 text-[11px] text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-safe" /> High potential
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-blush" /> Medium
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-plum" /> Low
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-sm bg-shell" /> Your vessel
        </span>
      </div>
    </section>
  );
}
