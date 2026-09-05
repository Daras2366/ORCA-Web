import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { ComingSoon } from "@/components/ComingSoon";

const title = "History — ORCA";
const description = "Review past queries, trips and zone recommendations.";

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

function Page() {
  return (
    <AppShell>
      <ComingSoon title="History" description="Review past queries, trips and zone recommendations." />
    </AppShell>
  );
}
