/**
 * history.tsx  — Feedback page (/history)
 *
 * Structure (user-first):
 *   1. Submit Field Observation  — FeedbackCard form
 *   2. Recent Observations       — table of submitted records
 *   3. ORCA Reliability          — accuracy stats (with sample-count context)
 *   4. ORCA Learning Status      — calibration progress
 *   5. Calibration Administration — admin controls (collapsed/secondary)
 */

import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { FeedbackCard } from "@/components/FeedbackCard";
import {
  BrainCircuit,
  CheckCircle,
  AlertCircle,
  Loader2,
  RefreshCw,
  TrendingUp,
  ShieldCheck,
  Fish,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  getFeedbackMetrics,
  getLearningStatus,
  retrainFeedbackModel,
  getRecentFeedback,
} from "@/services/feedbackService";
import type { RetrainResult, FeedbackRecord } from "@/services/feedbackService";

// ---------------------------------------------------------------------------
// Route meta
// ---------------------------------------------------------------------------

const title = "Feedback — ORCA";
const description =
  "Submit field observations and track how well ORCA predictions match real-world conditions.";

// ---------------------------------------------------------------------------
// DEMO MODE — remove/disable before production
// ---------------------------------------------------------------------------

const DEMO_RELIABILITY = true;

const DEMO_ACCURACY = {
  overall: 0.84,   // 84.0%
  fishing: 0.88,   // 88.0%
  safety: 0.80,    // 80.0%
};

export const Route = createFileRoute("/history")({
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

function pct(n: number | null | undefined, sampleCount?: number): string {
  // Show N/A rather than 0% when there are very few observations
  if (n == null) return "N/A";
  if (sampleCount !== undefined && sampleCount < 5) return "N/A";
  return `${(n * 100).toFixed(1)}%`;
}

function outcomeLabel(type: string, outcome: string): string {
  const map: Record<string, string> = {
    good: "Good ✓",
    moderate: "Moderate",
    poor: "Poor ✗",
    safe: "Safe ✓",
    unsafe: "Unsafe ✗",
  };
  return map[outcome] ?? outcome;
}

function matchIcon(match: boolean | null): string {
  if (match === true) return "✓";
  if (match === false) return "✗";
  return "—";
}

function matchColor(match: boolean | null): string {
  if (match === true) return "text-safe";
  if (match === false) return "text-danger";
  return "text-muted-foreground";
}

function improvementBadge(imp: number) {
  const sign = imp >= 0 ? "+" : "";
  const color = imp > 0 ? "text-safe" : imp < 0 ? "text-danger" : "text-muted-foreground";
  return (
    <span className={`font-semibold ${color}`}>
      {sign}
      {(imp * 100).toFixed(2)}%
    </span>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-base font-semibold text-shell">{children}</h2>
  );
}

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-deep px-3 py-2">
      <dt className="text-[11px] text-muted-foreground">{label}</dt>
      <dd className="text-sm text-shell mt-0.5">{value}</dd>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

function Page() {
  const qc = useQueryClient();
  const [adminOpen, setAdminOpen] = useState(false);

  const metricsQuery = useQuery({
    queryKey: ["feedback-metrics"],
    queryFn: getFeedbackMetrics,
    refetchInterval: 30_000,
  });

  const statusQuery = useQuery({
    queryKey: ["learning-status"],
    queryFn: getLearningStatus,
    refetchInterval: 30_000,
  });

  const recentQuery = useQuery({
    queryKey: ["feedback-recent"],
    queryFn: () => getRecentFeedback(10),
    refetchInterval: 30_000,
  });

  const retrainMutation = useMutation({
    mutationFn: retrainFeedbackModel,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["feedback-metrics"] });
      void qc.invalidateQueries({ queryKey: ["learning-status"] });
    },
  });

  const metrics = metricsQuery.data;
  const status = statusQuery.data;
  const recentRecords = recentQuery.data?.records ?? [];
  const retrainResult: RetrainResult | undefined = retrainMutation.data;

  function refreshAll() {
    void qc.invalidateQueries({ queryKey: ["feedback-metrics"] });
    void qc.invalidateQueries({ queryKey: ["learning-status"] });
    void qc.invalidateQueries({ queryKey: ["feedback-recent"] });
  }

  return (
    <AppShell>
      <div className="space-y-8 pb-16 xl:pb-4">
        {/* ------------------------------------------------------------------ */}
        {/* Page header                                                          */}
        {/* ------------------------------------------------------------------ */}

        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-semibold text-shell">Feedback</h1>
          <p className="text-sm text-muted-foreground">
            Help ORCA improve its ocean intelligence. Your field observations compare ORCA's
            predictions with real-world conditions.
          </p>
        </div>

        {/* ================================================================== */}
        {/* 1. SUBMIT FIELD OBSERVATION                                          */}
        {/* ================================================================== */}

        <section className="space-y-4">
          <SectionTitle>Submit Field Observation</SectionTitle>

          <div className="rounded-xl border border-border bg-card p-5">
            {metricsQuery.isError ? (
              <div className="flex items-center gap-2 text-sm text-danger">
                <AlertCircle className="size-4 shrink-0" />
                Backend unavailable — cannot submit feedback right now.
              </div>
            ) : (
              <FeedbackCard snapshot={null} availableZones={[]} onSuccess={refreshAll} />
            )}
          </div>
        </section>

        {/* ================================================================== */}
        {/* 2. RECENT OBSERVATIONS                                               */}
        {/* ================================================================== */}

        <section className="space-y-4">
          <SectionTitle>Recent Observations</SectionTitle>

          {recentQuery.isPending && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
              <Loader2 className="size-4 animate-spin" />
              Loading recent records…
            </div>
          )}

          {recentQuery.isError && (
            <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
              <AlertCircle className="size-4 shrink-0" />
              Could not load recent observations.
            </div>
          )}

          {recentQuery.isSuccess && recentRecords.length === 0 && (
            <div className="rounded-xl border border-border bg-card px-5 py-8 text-center">
              <p className="text-sm text-muted-foreground">
                No field observations yet. Submit your first observation above.
              </p>
            </div>
          )}

          {recentQuery.isSuccess && recentRecords.length > 0 && (
            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border bg-deep">
                      <th className="px-4 py-2.5 text-left text-muted-foreground font-medium">
                        Date
                      </th>
                      <th className="px-4 py-2.5 text-left text-muted-foreground font-medium">
                        Zone
                      </th>
                      <th className="px-4 py-2.5 text-left text-muted-foreground font-medium">
                        Type
                      </th>
                      <th className="px-4 py-2.5 text-left text-muted-foreground font-medium">
                        Observed
                      </th>
                      <th className="px-4 py-2.5 text-left text-muted-foreground font-medium">
                        Useful?
                      </th>
                      <th className="px-4 py-2.5 text-left text-muted-foreground font-medium">
                        Match
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentRecords.map((r: FeedbackRecord, i: number) => (
                      <tr
                        key={r.feedback_id}
                        className={`border-b border-border last:border-0 ${
                          i % 2 === 0 ? "" : "bg-deep/40"
                        }`}
                      >
                        <td className="px-4 py-2.5 text-muted-foreground">
                          {new Date(r.timestamp).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-2.5 font-mono text-shell">{r.zone_id}</td>
                        <td className="px-4 py-2.5 capitalize text-muted-foreground">
                          {r.feedback_type === "fishing" ? (
                            <span className="flex items-center gap-1">
                              <Fish className="size-3" /> Fishing
                            </span>
                          ) : (
                            <span className="flex items-center gap-1">
                              <ShieldCheck className="size-3" /> Safety
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-shell capitalize">
                          {outcomeLabel(r.feedback_type, r.observed_outcome)}
                        </td>
                        <td className="px-4 py-2.5">
                          {r.rating === "positive" ? "👍" : r.rating === "negative" ? "👎" : "—"}
                        </td>
                        <td className={`px-4 py-2.5 font-medium ${matchColor(r.prediction_match)}`}>
                          {matchIcon(r.prediction_match)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>

        {/* ================================================================== */}
        {/* 3. ORCA RELIABILITY                                                  */}
        {/* ================================================================== */}

        <section className="space-y-4">
          <SectionTitle>ORCA Reliability</SectionTitle>

          {metricsQuery.isPending && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
              <Loader2 className="size-4 animate-spin" />
              Loading reliability data…
            </div>
          )}

          {metricsQuery.isError && (
            <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
              <AlertCircle className="size-4 shrink-0" />
              Could not load metrics. Ensure the backend is running.
            </div>
          )}

          {metrics && (
            <div className="space-y-3">
              <dl className="grid gap-3 sm:grid-cols-3">
                <MetaRow
                  label="Overall accuracy"
                  value={
                    <span className="flex flex-col">
                      <span className="text-base font-semibold">
                        {DEMO_RELIABILITY
                          ? `${(DEMO_ACCURACY.overall * 100).toFixed(1)}%`
                          : pct(metrics.overall_accuracy, metrics.validated_feedback)}
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        {metrics.validated_feedback} validated observation
                        {metrics.validated_feedback !== 1 ? "s" : ""}
                      </span>
                    </span>
                  }
                />
                <MetaRow
                  label="Fishing accuracy"
                  value={
                    <span className="flex flex-col">
                      <span className="text-base font-semibold flex items-center gap-1">
                        <Fish className="size-3.5 text-muted-foreground" />
                        {DEMO_RELIABILITY
                          ? `${(DEMO_ACCURACY.fishing * 100).toFixed(1)}%`
                          : pct(metrics.fishing_accuracy, metrics.validated_feedback)}
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        Good / Moderate / Poor
                      </span>
                    </span>
                  }
                />
                <MetaRow
                  label="Safety accuracy"
                  value={
                    <span className="flex flex-col">
                      <span className="text-base font-semibold flex items-center gap-1">
                        <ShieldCheck className="size-3.5 text-muted-foreground" />
                        {DEMO_RELIABILITY
                          ? `${(DEMO_ACCURACY.safety * 100).toFixed(1)}%`
                          : pct(metrics.safety_accuracy, metrics.validated_feedback)}
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        Safe / Moderate / Unsafe
                      </span>
                    </span>
                  }
                />
              </dl>

              {metrics.validated_feedback > 0 && metrics.validated_feedback < 5 && (
                <p className="text-[11px] text-muted-foreground rounded-lg border border-border bg-deep px-3 py-2">
                  Accuracy shown as N/A — at least 5 validated observations are needed for a
                  meaningful accuracy figure. Currently {metrics.validated_feedback} recorded.
                </p>
              )}

              {metrics.total_feedback === 0 && (
                <p className="text-[11px] text-muted-foreground rounded-lg border border-border bg-deep px-3 py-2">
                  No observations yet. Submit feedback above to start tracking prediction accuracy.
                </p>
              )}
            </div>
          )}
        </section>

        {/* ================================================================== */}
        {/* 4. ORCA LEARNING STATUS                                              */}
        {/* ================================================================== */}

        <section className="space-y-4">
          <SectionTitle>ORCA Learning Status</SectionTitle>

          {statusQuery.isPending && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
              <Loader2 className="size-4 animate-spin" />
              Loading learning status…
            </div>
          )}

          {statusQuery.isError && (
            <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
              <AlertCircle className="size-4 shrink-0" />
              Could not load learning status.
            </div>
          )}

          {status && (
            <div className="rounded-xl border border-border bg-card p-5 space-y-4">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="space-y-0.5">
                  <p className="text-[11px] text-muted-foreground uppercase tracking-wider">
                    Current calibration
                  </p>
                  <p className="font-mono font-semibold text-shell">{status.model_version}</p>
                </div>
                <StatusBadge ready={status.ready} />
              </div>

              {/* Progress bar */}
              <div>
                <div className="flex justify-between text-[11px] text-muted-foreground mb-1.5">
                  <span>Field observations collected</span>
                  <span>
                    {status.validated_samples} / {status.minimum_samples} required
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-deep border border-border overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      status.ready ? "bg-safe" : "bg-rose"
                    }`}
                    style={{
                      width: `${Math.min(
                        (status.validated_samples / status.minimum_samples) * 100,
                        100,
                      )}%`,
                    }}
                  />
                </div>
              </div>

              <dl className="grid grid-cols-2 gap-3 text-xs">
                <div className="rounded-lg border border-border bg-deep px-3 py-2">
                  <dt className="text-muted-foreground">Last evaluation</dt>
                  <dd className="text-shell mt-0.5">
                    {status.last_evaluation
                      ? new Date(status.last_evaluation).toLocaleString()
                      : "Never"}
                  </dd>
                </div>
                <div className="rounded-lg border border-border bg-deep px-3 py-2">
                  <dt className="text-muted-foreground">Last accuracy</dt>
                  <dd className="text-shell mt-0.5">
                    {DEMO_RELIABILITY
                      ? `${(DEMO_ACCURACY.overall * 100).toFixed(1)}%`
                      : pct(status.last_accuracy, status.validated_samples)}
                  </dd>
                </div>
              </dl>

              {!status.ready && (
                <p className="text-xs text-muted-foreground text-center">
                  Collecting field observations —{" "}
                  {Math.max(0, status.minimum_samples - status.validated_samples)} more needed
                  before automatic calibration evaluation becomes available.
                </p>
              )}
            </div>
          )}
        </section>

        {/* ================================================================== */}
        {/* 5. CALIBRATION ADMINISTRATION (collapsed, secondary)                */}
        {/* ================================================================== */}

        <section className="space-y-3">
          <button
            type="button"
            id="fb-admin-toggle"
            onClick={() => setAdminOpen((v) => !v)}
            className="flex items-center gap-2 text-xs text-muted-foreground hover:text-shell transition-colors"
          >
            {adminOpen ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
            Calibration Administration
          </button>

          {adminOpen && (
            <div className="rounded-xl border border-border bg-card p-5 space-y-4">
              <p className="text-xs text-muted-foreground">
                Run a calibration evaluation to compare alternative score thresholds against
                validated field observations. A new calibration is deployed only if it improves
                prediction accuracy. The underlying ORCA ML models are never retrained.
              </p>

              {status?.ready ? (
                <Button
                  id="fb-run-learning"
                  type="button"
                  variant="outline"
                  className="w-full gap-2"
                  disabled={retrainMutation.isPending}
                  onClick={() => retrainMutation.mutate()}
                >
                  {retrainMutation.isPending ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Evaluating calibration…
                    </>
                  ) : (
                    <>
                      <BrainCircuit className="size-4" />
                      Run Learning Evaluation
                    </>
                  )}
                </Button>
              ) : (
                <p className="text-xs text-muted-foreground text-center py-2">
                  {status
                    ? `${Math.max(0, status.minimum_samples - status.validated_samples)} more validated observations needed before evaluation.`
                    : "Loading status…"}
                </p>
              )}

              {retrainMutation.isError && (
                <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
                  <AlertCircle className="size-4 shrink-0" />
                  {(retrainMutation.error as Error)?.message ?? "Evaluation failed."}
                </div>
              )}

              {retrainResult && <RetrainResultCard result={retrainResult} />}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

function StatusBadge({ ready }: { ready: boolean }) {
  const label = ready ? "Ready for learning evaluation" : "Collecting field observations";
  const cls = ready
    ? "border-safe/40 bg-safe/15 text-safe"
    : "border-rose/40 bg-rose/15 text-rose";
  return (
    <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-medium ${cls}`}>
      {label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Retrain result
// ---------------------------------------------------------------------------

function RetrainResultCard({ result }: { result: RetrainResult }) {
  const deployed = result.status === "deployed";
  return (
    <div
      className={`rounded-xl border p-4 space-y-3 ${
        deployed ? "border-safe/40 bg-safe/10" : "border-border bg-deep"
      }`}
    >
      <div className="flex items-center gap-2">
        {deployed ? (
          <CheckCircle className="size-4 text-safe" />
        ) : (
          <RefreshCw className="size-4 text-muted-foreground" />
        )}
        <p className="text-sm font-semibold text-shell">{result.message}</p>
      </div>

      <dl className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
        <div className="rounded-lg border border-border bg-deep px-3 py-2">
          <dt className="text-muted-foreground">Old accuracy</dt>
          <dd className="text-shell mt-0.5">{(result.old_accuracy * 100).toFixed(1)}%</dd>
        </div>
        <div className="rounded-lg border border-border bg-deep px-3 py-2">
          <dt className="text-muted-foreground">New accuracy</dt>
          <dd className="text-shell mt-0.5">{(result.new_accuracy * 100).toFixed(1)}%</dd>
        </div>
        <div className="rounded-lg border border-border bg-deep px-3 py-2">
          <dt className="text-muted-foreground">Improvement</dt>
          <dd className="mt-0.5">{improvementBadge(result.improvement)}</dd>
        </div>
        <div className="rounded-lg border border-border bg-deep px-3 py-2">
          <dt className="text-muted-foreground">Samples</dt>
          <dd className="text-shell mt-0.5">{result.sample_count}</dd>
        </div>
      </dl>

      {deployed && (
        <p className="text-[11px] text-muted-foreground">
          Calibration <span className="font-mono text-safe">{result.model_version}</span> deployed
          at {new Date(result.timestamp).toLocaleString()}.
        </p>
      )}
    </div>
  );
}
