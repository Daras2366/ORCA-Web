/**
 * profile.tsx — Authenticated user profile page.
 *
 * Accessible at: /profile
 * Protected: redirects to dashboard if the user is not authenticated.
 * Renders inside AppShell so sidebar, header, and assistant are preserved.
 */

import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { Calendar, Globe, Mail, Shield, User } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/hooks/useAuth";

const title = "My Profile — ORCA";
const description = "View and manage your ORCA account profile.";

export const Route = createFileRoute("/profile")({
  head: () => ({
    meta: [
      { title },
      { name: "description", content: description },
    ],
  }),
  component: ProfilePage,
});

const USER_TYPE_LABELS: Record<string, string> = {
  fisherman: "Fisherman",
  coast_guard: "Coast Guard",
  researcher: "Researcher",
  maritime_operator: "Maritime Operator",
  coastal_authority: "Coastal Authority",
  other: "Member",
};

const LANGUAGE_LABELS: Record<string, string> = {
  en: "English",
  ta: "Tamil",
  hi: "Hindi",
  ml: "Malayalam",
  te: "Telugu",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof User;
  label: string;
  value: string;
}) {
  return (
    <div className="panel flex items-start gap-3 p-4">
      <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/15">
        <Icon className="size-4 text-primary" />
      </div>
      <div className="min-w-0">
        <p className="text-[11px] text-muted-foreground">{label}</p>
        <p className="mt-0.5 truncate text-sm font-medium text-shell">{value}</p>
      </div>
    </div>
  );
}

function ProfilePage() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const navigate = useNavigate();

  // Redirect guests to dashboard.
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate({ to: "/" });
    }
  }, [isLoading, isAuthenticated, navigate]);

  if (isLoading || !user) {
    return (
      <AppShell>
        <div className="flex h-40 items-center justify-center text-muted-foreground text-sm">
          Loading…
        </div>
      </AppShell>
    );
  }

  const initials = user.name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const typeLabel = USER_TYPE_LABELS[user.user_type] ?? user.user_type;
  const langLabel = LANGUAGE_LABELS[user.preferred_language] ?? user.preferred_language;

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl space-y-6 pb-16 xl:pb-4">
        {/* Profile card */}
        <div className="panel overflow-hidden">
          {/* Ocean accent banner */}
          <div
            className="h-24"
            style={{
              background:
                "linear-gradient(135deg, var(--plum) 0%, var(--deep) 50%, var(--abyss) 100%)",
            }}
          />

          {/* Avatar + name */}
          <div className="-mt-10 flex flex-col items-center px-6 pb-6">
            <div
              className="flex size-20 items-center justify-center rounded-full border-4 border-card text-2xl font-bold text-primary-foreground shadow-lg"
              style={{ background: "var(--primary)" }}
            >
              {initials}
            </div>

            <h1 className="mt-3 text-xl font-semibold text-shell">
              {user.name}
            </h1>

            <span className="mt-1.5 inline-flex items-center gap-1.5 rounded-full bg-primary/20 px-3 py-1 text-xs font-medium text-primary">
              <Shield className="size-3" />
              {typeLabel}
            </span>
          </div>
        </div>

        {/* Details grid */}
        <div>
          <h2 className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Account Details
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <StatCard icon={Mail} label="Email address" value={user.email} />
            <StatCard icon={User} label="Role" value={typeLabel} />
            <StatCard icon={Globe} label="Preferred language" value={langLabel} />
            <StatCard
              icon={Calendar}
              label="Member since"
              value={formatDate(user.created_at)}
            />
          </div>
        </div>

        {/* Sign out */}
        <div className="panel p-4">
          <p className="text-sm text-muted-foreground">
            Signing out will clear your session. All ORCA features remain available as a guest.
          </p>
          <button
            id="profile-logout"
            onClick={async () => {
              await logout();
              navigate({ to: "/" });
            }}
            className="mt-3 inline-flex items-center gap-2 rounded-lg border border-danger/40 bg-danger/10 px-4 py-2 text-sm font-medium text-danger transition-colors hover:bg-danger/20"
          >
            Sign out
          </button>
        </div>
      </div>
    </AppShell>
  );
}
