import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { ComingSoon } from "@/components/ComingSoon";

const title = "Help & About — ORCA";
const description = "Learn how ORCA works, data sources and safety guidance.";

export const Route = createFileRoute("/help")({
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
      <ComingSoon title="Help &amp; About" description="Learn how ORCA works, data sources and safety guidance." />
    </AppShell>
  );
}
