import { useState } from "react";
import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer } from "recharts";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { FishingZone, ZoneFactor } from "@/types/marine";

interface Props {
  zone?: FishingZone | undefined;
  factors: ZoneFactor[];
  loading?: boolean | undefined;
  error?: string | null | undefined;
}

export function RecommendedZone({ zone, factors, loading, error }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <section className="panel flex h-full flex-col p-4">
      <h2 className="text-sm font-semibold text-shell">Recommended Fishing Zone</h2>

      {error ? (
        <p className="mt-4 text-sm text-danger">Unable to retrieve zone recommendation.</p>
      ) : loading || !zone ? (
        <Skeleton className="mt-4 h-56 w-full rounded-lg bg-muted" />
      ) : (
        <>
          <div className="mt-3 flex items-center justify-between">
            <p className="text-xl font-semibold tracking-wide text-shell">{zone.zone_id}</p>
            <span className="rounded-full bg-rose px-2.5 py-1 text-[10px] font-medium text-primary-foreground">
              Best Match
            </span>
          </div>

          <div className="mt-3 rounded-lg border border-border bg-deep px-3 py-2">
            <p className="text-[11px] text-muted-foreground">Fishing Potential (HSI)</p>
            <p className="text-2xl font-semibold text-shell">{zone.hsi.toFixed(2)}</p>
            <p className="text-xs text-safe">{zone.potential}</p>
          </div>

          <div className="mt-2 h-44 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={factors} outerRadius="72%">
                <PolarGrid stroke="var(--plum)" />
                <PolarAngleAxis
                  dataKey="factor"
                  tick={{ fill: "var(--muted-foreground)", fontSize: 10 }}
                />
                <Radar
                  dataKey="score"
                  stroke="var(--blush)"
                  fill="var(--rose)"
                  fillOpacity={0.55}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          <Button className="mt-2 w-full" onClick={() => setOpen(true)}>
            View Analysis
          </Button>
        </>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{zone?.zone_id} analysis</DialogTitle>
            <DialogDescription>
              Zone scores are produced live by the ORCA backend agents (Ocean, Safety, Route).
              Coordinates are zone centroids.
            </DialogDescription>
          </DialogHeader>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <Row label="Fishing potential (HSI)" value={zone ? zone.hsi.toFixed(2) : "—"} />
            <Row label="Potential level" value={zone?.potential ?? "—"} />
            <Row label="SST" value={zone?.sst_c != null ? `${zone.sst_c}°C` : "N/A"} />
            <Row
              label="Chlorophyll"
              value={zone?.chlorophyll_mg_m3 != null ? `${zone.chlorophyll_mg_m3} mg/m³` : "N/A"}
            />
            <Row
              label="Safety score"
              value={zone?.safety_score != null ? `${zone.safety_score}/100` : "N/A"}
            />
            <Row label="Confidence" value={zone ? `${Math.round(zone.confidence * 100)}%` : "—"} />
          </dl>
        </DialogContent>
      </Dialog>
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border px-3 py-2">
      <dt className="text-[11px] text-muted-foreground">{label}</dt>
      <dd className="text-shell">{value}</dd>
    </div>
  );
}
