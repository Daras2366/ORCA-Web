import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { ComingSoon } from "@/components/ComingSoon";

const title = "Saved Locations — ORCA";
const description = "Save home ports and frequent fishing grounds for one-tap access.";

export const Route = createFileRoute("/saved-locations")({
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
      <ComingSoon title="Saved Locations" description="Save home ports and frequent fishing grounds for one-tap access." />
    </AppShell>
  );
}
