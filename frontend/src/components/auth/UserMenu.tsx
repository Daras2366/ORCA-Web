/**
 * UserMenu.tsx — Avatar/dropdown for authenticated users.
 *
 * Shows name, user-type badge, link to /profile, and Logout button.
 * Rendered in the Header when the user is authenticated.
 */

import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { ChevronDown, LogOut, User } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";

const USER_TYPE_LABELS: Record<string, string> = {
  fisherman: "Fisherman",
  coast_guard: "Coast Guard",
  researcher: "Researcher",
  maritime_operator: "Maritime Operator",
  coastal_authority: "Coastal Authority",
  other: "Member",
};

function initials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function UserMenu() {
  const { user, logout } = useAuth();
  const [loggingOut, setLoggingOut] = useState(false);

  if (!user) return null;

  const label = USER_TYPE_LABELS[user.user_type] ?? "Member";
  const avatar = initials(user.name);

  const handleLogout = async () => {
    setLoggingOut(true);
    await logout();
    setLoggingOut(false);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          id="user-menu-trigger"
          variant="ghost"
          className="flex h-9 items-center gap-2 rounded-lg px-2 hover:bg-white/10"
        >
          {/* Avatar circle */}
          <span
            className="flex size-7 items-center justify-center rounded-full text-[11px] font-semibold text-primary-foreground"
            style={{ background: "var(--primary)" }}
          >
            {avatar}
          </span>

          <span className="hidden max-w-[100px] truncate text-sm text-shell sm:block">
            {user.name}
          </span>

          <ChevronDown className="size-3.5 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="z-[1000] w-56">
        {/* Identity header */}
        <DropdownMenuLabel className="flex flex-col gap-0.5 pb-2">
          <span className="truncate text-sm font-medium text-shell">
            {user.name}
          </span>
          <span className="truncate text-xs text-muted-foreground">
            {user.email}
          </span>
          <span className="mt-1 inline-flex w-fit items-center rounded-full bg-primary/20 px-2 py-0.5 text-[10px] font-medium text-primary">
            {label}
          </span>
        </DropdownMenuLabel>

        <DropdownMenuSeparator />

        <DropdownMenuItem asChild>
          <Link
            to="/profile"
            id="user-menu-profile"
            className="flex cursor-pointer items-center gap-2"
          >
            <User className="size-4" />
            My Profile
          </Link>
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          id="user-menu-logout"
          className="flex cursor-pointer items-center gap-2 text-danger focus:text-danger"
          onClick={handleLogout}
          disabled={loggingOut}
        >
          <LogOut className="size-4" />
          {loggingOut ? "Signing out…" : "Sign out"}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
