import { useState, useEffect, useRef } from "react";
import { Navigation, MapPin, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { navigateRoute } from "@/services/routeService";
import type { NavigationResult } from "@/types/marine";

type NavMode = "idle" | "selecting_start" | "selecting_destination";

interface Props {
  onRouteCalculated: (result: NavigationResult) => void;
  userLocation: { latitude: number; longitude: number };
  /** Called whenever the internal selection mode changes so the map can update cursor/click behaviour. */
  onModeChange?: (mode: NavMode) => void;
  /** Called once on mount with a stable handler function; the parent forwards Leaflet map-click events to it. */
  onRegisterClickHandler?: (handler: ((lat: number, lng: number) => void) | null) => void;
}

export function NavigationPanel({
  onRouteCalculated,
  userLocation,
  onModeChange,
  onRegisterClickHandler,
}: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [mode, setMode] = useState<NavMode>("idle");
  const [startPoint, setStartPoint] = useState<{ lat: number; lng: number } | null>(null);
  const [destinationPoint, setDestinationPoint] = useState<{ lat: number; lng: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Keep a ref to the current mode so the stable map-click handler can read it.
  const modeRef = useRef<NavMode>(mode);
  modeRef.current = mode;

  // Notify parent when mode changes (drives map cursor / Leaflet click binding).
  useEffect(() => {
    onModeChange?.(mode);
  }, [mode, onModeChange]);

  // Register (and later unregister) a stable click handler with the parent once.
  useEffect(() => {
    const handler = (lat: number, lng: number) => {
      if (modeRef.current === "selecting_start") {
        setStartPoint({ lat, lng });
        setMode("selecting_destination");
      } else if (modeRef.current === "selecting_destination") {
        setDestinationPoint({ lat, lng });
        setMode("idle");
      }
    };
    onRegisterClickHandler?.(handler);
    // Unregister when NavigationPanel unmounts.
    return () => {
      onRegisterClickHandler?.(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onRegisterClickHandler]);

  const handleSetStartFromCurrent = () => {
    setStartPoint({ lat: userLocation.latitude, lng: userLocation.longitude });
    setMode("selecting_destination");
  };

  const handleSetStartFromMap = () => {
    setMode("selecting_start");
  };

  const handleCalculateRoute = async () => {
    if (!startPoint || !destinationPoint) return;

    setLoading(true);
    setError(null);

    try {
      const result = await navigateRoute(
        startPoint.lat,
        startPoint.lng,
        destinationPoint.lat,
        destinationPoint.lng,
      );

      if (result.success) {
        onRouteCalculated(result);
        setIsOpen(false);
        // Reset for next use
        setStartPoint(null);
        setDestinationPoint(null);
        setMode("idle");
      } else {
        setError(result.error || "Failed to calculate route");
      }
    } catch (err) {
      setError("Navigation service unavailable");
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setStartPoint(null);
    setDestinationPoint(null);
    setMode("idle");
    setError(null);
  };

  const handleCancel = () => {
    setIsOpen(false);
    handleClear();
  };

  if (!isOpen) {
    return (
      <Button
        onClick={() => setIsOpen(true)}
        variant="outline"
        size="sm"
        className="gap-2"
      >
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
        {/* Start Point Selection */}
        <div className="rounded-lg border border-border bg-deep p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] text-muted-foreground">Start Point</span>
            {!startPoint && (
              <div className="flex gap-1.5">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={handleSetStartFromCurrent}
                  className="text-xs"
                >
                  <MapPin className="size-3 mr-1" />
                  Use Current
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleSetStartFromMap}
                  className="text-xs"
                >
                  Pick on Map
                </Button>
              </div>
            )}
          </div>
          {startPoint ? (
            <div className="text-sm text-shell">
              {startPoint.lat.toFixed(4)}, {startPoint.lng.toFixed(4)}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              {mode === "selecting_start" ? "⬡ Click on map to set start point…" : "Not set"}
            </div>
          )}
        </div>

        {/* Destination Point Selection */}
        <div className="rounded-lg border border-border bg-deep p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] text-muted-foreground">Destination</span>
          </div>
          {destinationPoint ? (
            <div className="text-sm text-shell">
              {destinationPoint.lat.toFixed(4)}, {destinationPoint.lng.toFixed(4)}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              {mode === "selecting_destination" ? "⬡ Click on map to set destination…" : "Not set"}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <Button
            onClick={handleCalculateRoute}
            disabled={!startPoint || !destinationPoint || loading}
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
          <Button
            variant="outline"
            onClick={handleClear}
            disabled={loading}
          >
            Clear
          </Button>
        </div>

        {/* Instructions */}
        <div className="text-[11px] text-muted-foreground">
          {mode === "selecting_start" ? (
            <p>Click anywhere on the map to set your start point.</p>
          ) : mode === "selecting_destination" ? (
            <p>Click anywhere on the map to set your destination.</p>
          ) : !startPoint ? (
            <p>Use your current location or pick a point on the map as start.</p>
          ) : !destinationPoint ? (
            <p>Click on the map to set your destination.</p>
          ) : (
            <p>Click "Calculate Route" to generate your navigation path.</p>
          )}
        </div>
      </div>
    </div>
  );
}
