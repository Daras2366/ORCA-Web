import { useState } from "react";
import { MapPin, Menu, Navigation, Search, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { formatLocation, useLocationContext } from "@/hooks/useLocation";

export function Header({ onOpenMenu }: { onOpenMenu?: () => void }) {
  const { location, setLocation, useBrowserLocation, detecting, error } = useLocationContext();
  const [query, setQuery] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLocation({ ...location, city: query.trim(), state: "" });
    setQuery("");
  };

  return (
    <header className="flex flex-wrap items-start justify-between gap-4 border-b border-border px-4 py-4 md:px-6">
      <div className="flex items-start gap-3">
        {onOpenMenu && (
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={onOpenMenu}>
            <Menu className="size-5" />
            <span className="sr-only">Open navigation</span>
          </Button>
        )}
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold text-shell md:text-2xl">
            Good Morning, Captain.
            <Sun className="size-5 text-accent" />
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Real-time ocean intelligence for safer and smarter journeys.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="secondary" size="sm" className="gap-2">
              <MapPin className="size-4 text-accent" />
              {formatLocation(location)}
            </Button>
          </PopoverTrigger>
          <PopoverContent align="end" className="w-72 space-y-3">
            <div>
              <p className="text-sm font-medium text-shell">Location</p>
              <p className="text-xs text-muted-foreground">
                {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="w-full justify-start gap-2"
              onClick={useBrowserLocation}
              disabled={detecting}
            >
              <Navigation className="size-4" />
              {detecting ? "Detecting…" : "Use My Location"}
            </Button>
            <form onSubmit={handleSearch} className="flex gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search location"
                className="h-9"
              />
              <Button type="submit" size="icon" className="size-9 shrink-0">
                <Search className="size-4" />
                <span className="sr-only">Search</span>
              </Button>
            </form>
            {error && <p className="text-xs text-danger">{error}</p>}
          </PopoverContent>
        </Popover>

        <div className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs text-muted-foreground">
          <span className="size-2 rounded-full bg-safe" />
          Live Data
        </div>
      </div>
    </header>
  );
}
