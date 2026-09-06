import { Link } from "@tanstack/react-router";
import {
  Anchor,
  Bookmark,
  CircleHelp,
  Fish,
  History,
  LayoutDashboard,
  Settings,
  ShieldAlert,
  Waves,
} from "lucide-react";
import { OrcaLogo } from "./OrcaLogo";
import { cn } from "@/lib/utils";

const primaryNav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/fishing-zones", label: "Fishing Zones", icon: Fish },
  { to: "/ocean-conditions", label: "Ocean Conditions", icon: Waves },
  { to: "/safety", label: "Safety & Alerts", icon: ShieldAlert },
] as const;

const secondaryNav = [
  { to: "/saved-locations", label: "Saved Locations", icon: Bookmark },
  { to: "/history", label: "History", icon: History },
] as const;

const tertiaryNav = [
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/help", label: "Help & About", icon: CircleHelp },
] as const;

function NavList({
  items,
  onNavigate,
}: {
  items:
    | readonly (typeof primaryNav)[number][]
    | readonly { to: string; label: string; icon: typeof Anchor }[];
  onNavigate?: (() => void) | undefined;
}) {
  return (
    <div className="space-y-1">
      {items.map(({ to, label, icon: Icon }) => (
        <Link
          key={to}
          to={to}
          onClick={onNavigate}
          activeOptions={{ exact: to === "/" }}
          className={cn(
            "flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-white/80",
            "transition-colors hover:bg-white/10 hover:text-white",
          )}
          activeProps={{
            className: "bg-white/20 text-white font-medium backdrop-blur-sm",
          }}
        >
          <Icon className="size-4 shrink-0" />
          <span className="truncate">{label}</span>
        </Link>
      ))}
    </div>
  );
}

export function Sidebar({ onNavigate }: { onNavigate?: (() => void) | undefined }) {
  return (
    <aside className="relative flex h-full w-full flex-col border-r border-sidebar-border bg-sidebar overflow-hidden">
      {/* Background image */}
      <div
        className="absolute inset-0 w-full h-full"
        style={{
          backgroundImage: "url(/images/orca-sidebar-bg.png)",
          backgroundSize: "cover",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
        }}
      />

      {/* Subtle gradient overlay for readability — deep ocean blue treatment */}
      <div
        className="absolute inset-0 w-full h-full"
        style={{
          background:
            "linear-gradient(to bottom, rgba(3, 18, 32, 0.70) 0%, rgba(3, 18, 32, 0.48) 25%, rgba(3, 18, 32, 0.28) 50%, rgba(3, 18, 32, 0.12) 75%, rgba(3, 18, 32, 0.05) 100%)",
        }}
      />

      {/* Content container with higher z-index */}
      <div className="relative z-10 flex h-full w-full flex-col">
        <div className="flex items-start gap-3 border-b border-sidebar-border/30 px-4 py-5">
          <OrcaLogo className="size-9 shrink-0" />
          <div className="min-w-0">
            <p className="text-lg font-semibold tracking-[0.14em] text-shell">ORCA</p>
            <p className="text-[11px] leading-tight text-muted-foreground">
              Ocean Research &amp;
              <br />
              Capability Assistant
            </p>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4">
          <NavList items={primaryNav} onNavigate={onNavigate} />
          <div className="my-3 h-px bg-sidebar-border/30" />
          <NavList items={secondaryNav} onNavigate={onNavigate} />
          <div className="my-3 h-px bg-sidebar-border/30" />
          <NavList items={tertiaryNav} onNavigate={onNavigate} />
        </nav>
      </div>
    </aside>
  );
}
