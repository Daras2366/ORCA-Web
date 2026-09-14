import { useEffect, useState } from "react";
import { Navigation, MapPin, X, Loader2, Fish } from "lucide-react";
import { Button } from "@/components/ui/button";
import { navigateRoute } from "@/services/routeService";
import type { FishingZone, NavigationResult } from "@/types/marine";

interface Props {
  onRouteCalculated: (result: NavigationResult) => void;
  userLocation: {
    latitude: number;
    longitude: number;
  };
  zones: FishingZone[];
  initialZoneId?: string | null;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function NavigationPanel({ onRouteCalculated, userLocation, zones, initialZoneId, open, onOpenChange }: Props) {
  const [isOpen, setIsOpen] = useState(open ?? false);
  const [destinationZoneId, setDestinationZoneId] = useState(initialZoneId ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const normalizedZoneId = destinationZoneId.trim().toUpperCase();

  const selectedZone = zones.find((zone) => zone.zone_id.toUpperCase() === normalizedZoneId);

  useEffect(() => {
    if (initialZoneId) {
      setDestinationZoneId(initialZoneId);
      setError(null);
    }
  }, [initialZoneId]);

  useEffect(() => {
    if (open !== undefined) {
      setIsOpen(open);
    }
  }, [open]);

  const handleCalculateRoute = async () => {
    setError(null);

    if (!normalizedZoneId) {
      setError("Enter a PFZ ID to set the destination.");
      return;
    }

    if (!selectedZone) {
      setError(`PFZ "${normalizedZoneId}" was not found. Enter a valid PFZ ID from the map.`);
      return;
    }

    setLoading(true);

    try {
      // The user selects a PFZ ID.
      // We resolve that ID to its existing backend-provided coordinates
      // and send those coordinates to the existing A* navigation service.
      const result = await navigateRoute(
        userLocation.latitude,
        userLocation.longitude,
        selectedZone.latitude,
        selectedZone.longitude,
      );

      if (result.success) {
        onRouteCalculated(result);
        setIsOpen(false);
      } else {
        setError(result.error || "Failed to calculate route.");
      }
    } catch (err) {
      setError("Navigation service unavailable.");
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setDestinationZoneId("");
    setError(null);
  };

  const handleCancel = () => {
    setIsOpen(false);
    onOpenChange?.(false);
    handleClear();
  };

  const handleUseRecommended = () => {
    const recommended = zones.find((zone) => zone.recommended);

    if (recommended) {
      setDestinationZoneId(recommended.zone_id);
      setError(null);
    }
  };

  if (!isOpen) {
    return (
      <Button onClick={() => setIsOpen(true)} variant="outline" size="sm" className="gap-2">
        <Navigation className="size-4" />
        Plan Route
      </Button>
    );
  }

  return (
    <div className="panel p-4 border-t border-border">
      <div className="flex items-center justify-between mb-4">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-shell">
          <Navigation className="size-4 text-accent" />
          Route Planning
        </h3>

        <Button variant="ghost" size="sm" onClick={handleCancel}>
          <X className="size-4" />
        </Button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-danger/10 border border-danger/20 p-3 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="space-y-3">
        {/* Start Point */}
        <div className="rounded-lg border border-border bg-deep p-3">
          <div className="flex items-center gap-2 mb-2">
            <MapPin className="size-3.5 text-accent" />
            <span className="text-[11px] text-muted-foreground">Start Point</span>
          </div>

          <div className="text-sm text-shell">
            {userLocation.latitude.toFixed(4)}, {userLocation.longitude.toFixed(4)}
          </div>

          <div className="mt-1 text-[11px] text-muted-foreground">Your current vessel location</div>
        </div>

        {/* Destination PFZ */}
        <div className="rounded-lg border border-border bg-deep p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Fish className="size-3.5 text-accent" />
              <span className="text-[11px] text-muted-foreground">Destination PFZ</span>
            </div>

            {zones.some((zone) => zone.recommended) && (
              <button
                type="button"
                onClick={handleUseRecommended}
                className="text-[10px] text-accent hover:underline"
              >
                Use recommended
              </button>
            )}
          </div>

          <input
            type="text"
            value={destinationZoneId}
            onChange={(event) => {
              setDestinationZoneId(event.target.value.toUpperCase());
              setError(null);
            }}
            placeholder="Enter PFZ ID, e.g. PFZ0047"
            className="w-full rounded-md border border-border bg-abyss px-3 py-2 text-sm text-shell outline-none placeholder:text-muted-foreground focus:border-accent"
            autoComplete="off"
            spellCheck={false}
          />

          {normalizedZoneId && selectedZone && (
            <div className="mt-2 rounded-md border border-safe/20 bg-safe/5 px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-shell">{selectedZone.zone_id}</span>

                <span className="text-[10px] text-muted-foreground">
                  {selectedZone.potential} potential
                </span>
              </div>

              <div className="mt-1 text-[10px] text-muted-foreground">
                Destination located at {selectedZone.latitude.toFixed(4)},{" "}
                {selectedZone.longitude.toFixed(4)}
              </div>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <Button
            onClick={handleCalculateRoute}
            disabled={!normalizedZoneId || !selectedZone || loading}
            className="flex-1"
          >
            {loading ? (
              <>
                <Loader2 className="size-4 mr-2 animate-spin" />
                Calculating...
              </>
            ) : (
              "Calculate Route"
            )}
          </Button>

          <Button variant="outline" onClick={handleClear} disabled={loading}>
            Clear
          </Button>
        </div>
      </div>
    </div>
  );
}
