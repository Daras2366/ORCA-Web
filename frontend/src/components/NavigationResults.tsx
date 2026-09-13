import { Clock, Fuel, Ruler, Waves, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { NavigationResult } from "@/types/marine";

interface Props {
  result: NavigationResult;
  onClose: () => void;
}

export function NavigationResults({ result, onClose }: Props) {
  if (!result.success) {
    return null;
  }

  const hours = Math.floor(result.travel_time_h);
  const minutes = Math.round((result.travel_time_h - hours) * 60);
  const timeLabel = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;

  return (
    <div className="panel p-4 border-t border-border">
      <div className="flex items-center justify-between mb-4">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-shell">
          <Ruler className="size-4 text-accent" />
          Navigation Route
        </h3>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X className="size-4" />
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="rounded-lg border border-border bg-deep px-3 py-2">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mb-1">
            <Ruler className="size-3" />
            Distance
          </div>
          <p className="text-sm font-semibold text-shell">{result.distance_km.toFixed(1)} km</p>
        </div>

        <div className="rounded-lg border border-border bg-deep px-3 py-2">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mb-1">
            <Clock className="size-3" />
            Travel Time
          </div>
          <p className="text-sm font-semibold text-shell">{timeLabel}</p>
        </div>

        <div className="rounded-lg border border-border bg-deep px-3 py-2">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mb-1">
            <Fuel className="size-3" />
            Fuel (Est.)
          </div>
          <p className="text-sm font-semibold text-shell">{result.fuel_l.toFixed(0)} L</p>
        </div>

        <div className="rounded-lg border border-border bg-deep px-3 py-2">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mb-1">
            <Waves className="size-3" />
            Min Depth
          </div>
          <p className="text-sm font-semibold text-shell">{result.min_depth_m.toFixed(0)} m</p>
        </div>
      </div>

      {result.average_current_ms !== null && (
        <div className="rounded-lg border border-border bg-deep px-3 py-2 mb-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[11px] text-muted-foreground">Average Current</p>
              <p className="text-sm text-shell">{result.average_current_ms.toFixed(3)} m/s</p>
            </div>
            <div className="text-right">
              <p className="text-[11px] text-muted-foreground">Depth Range</p>
              <p className="text-sm text-shell">
                {result.min_depth_m.toFixed(0)} - {result.max_depth_m.toFixed(0)} m
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="text-[11px] text-muted-foreground">
        <p>Route calculated using deterministic A* pathfinding with bathymetry and current data.</p>
        <p className="mt-1">Fuel consumption is an estimate based on vessel profile configuration.</p>
      </div>
    </div>
  );
}
