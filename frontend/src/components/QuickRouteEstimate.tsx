import { useState } from "react";
import { Clock, Fuel, Route as RouteIcon, Ruler } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { RouteEstimate } from "@/types/marine";

interface Props {
  data?: RouteEstimate | undefined;
  loading?: boolean | undefined;
  error?: string | null | undefined;
}

export function QuickRouteEstimate({ data, loading, error }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <section className="panel p-4">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-shell">
          <RouteIcon className="size-4 text-accent" />
          Quick Route Estimate
        </h2>
        <span className="rounded-full border border-border px-2 py-0.5 text-[10px] uppercase tracking-wide text-blush">
          Beta
        </span>
      </div>

      {error ? (
        <p className="mt-4 text-sm text-danger">Unable to retrieve route estimate.</p>
      ) : loading || !data ? (
        <Skeleton className="mt-4 h-28 w-full rounded-lg bg-muted" />
      ) : (
        <>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border border-border bg-deep px-3 py-2">
              <p className="text-[11px] text-muted-foreground">From</p>
              <p className="text-sm text-shell">{data.from_label}</p>
              <p className="text-xs text-muted-foreground">{data.from_sub}</p>
            </div>
            <div className="rounded-lg border border-border bg-deep px-3 py-2">
              <p className="text-[11px] text-muted-foreground">To</p>
              <p className="text-sm text-shell">{data.to_label}</p>
              <p className="text-xs text-muted-foreground">{data.to_sub}</p>
            </div>
          </div>

          <div className="mt-3 grid grid-cols-3 gap-3">
            <Metric icon={<Ruler className="size-4 text-accent" />} label="Distance" value={`${data.distance_km} km`} />
            <Metric icon={<Clock className="size-4 text-accent" />} label="Estimated Time" value={data.duration_label} />
            <Metric icon={<Fuel className="size-4 text-accent" />} label="Fuel Required" value={`${data.fuel_litres} L`} />
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
            <p className="text-[11px] text-muted-foreground">{data.note}</p>
            <Button size="sm" variant="secondary" onClick={() => setOpen(true)}>
              View Details
            </Button>
          </div>
        </>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Route estimate details</DialogTitle>
          </DialogHeader>
          <ul className="space-y-2 text-sm text-shell">
            <li>Distance: {data?.distance_km} km</li>
            <li>Estimated time: {data?.duration_label}</li>
            <li>Fuel required: {data?.fuel_litres} L</li>
            {data?.note && <li className="text-muted-foreground">{data.note}</li>}
          </ul>
          <p className="text-xs text-muted-foreground">
            Distance is a straight-line estimate between your location and the zone centroid.
            It is not navigation-grade route geometry and does not provide turn-by-turn guidance.
          </p>
        </DialogContent>
      </Dialog>
    </section>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border px-3 py-2">
      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
        {icon}
        {label}
      </div>
      <p className="mt-1 text-sm font-semibold text-shell">{value}</p>
    </div>
  );
}
