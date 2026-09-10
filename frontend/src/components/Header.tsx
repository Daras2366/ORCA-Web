import { useEffect, useState } from "react";
import { LogIn, MapPin, Menu, Navigation, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { formatLocation, useLocationContext } from "@/hooks/useLocation";
import { useAuth } from "@/hooks/useAuth";
import { AuthModal } from "@/components/auth/AuthModal";
import { UserMenu } from "@/components/auth/UserMenu";

export function Header({ onOpenMenu }: { onOpenMenu?: () => void }) {
  const { location, setLocation, useBrowserLocation, detecting, error } = useLocationContext();
  const { isAuthenticated, isLoading } = useAuth();
  const [authOpen, setAuthOpen] = useState(false);

  const [latitude, setLatitude] = useState(String(location.latitude));
  const [longitude, setLongitude] = useState(String(location.longitude));
  const [coordinateError, setCoordinateError] = useState<string | null>(null);

  // Keep the inputs synchronized when the location changes
  // through browser geolocation or another part of the app.
  useEffect(() => {
    setLatitude(String(location.latitude));
    setLongitude(String(location.longitude));
  }, [location.latitude, location.longitude]);

  const handleManualLocation = (e: React.FormEvent) => {
    e.preventDefault();

    const lat = Number(latitude);
    const lon = Number(longitude);

    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      setCoordinateError("Please enter valid numbers.");
      return;
    }

    if (lat < -90 || lat > 90) {
      setCoordinateError("Latitude must be between -90 and 90.");
      return;
    }

    if (lon < -180 || lon > 180) {
      setCoordinateError("Longitude must be between -180 and 180.");
      return;
    }

    setCoordinateError(null);

    setLocation({
      latitude: Number(lat.toFixed(4)),
      longitude: Number(lon.toFixed(4)),
      city: "Custom Position",
      state: "",
      country: "",
    });
  };

  return (
    <header
      className="relative flex flex-wrap items-start justify-between gap-4 overflow-hidden border-b border-border px-4 py-4 md:px-6"
      style={{
        backgroundImage: "url('/images/orca-header-bg.png')",
        backgroundSize: "cover",
        backgroundPosition: "center 35%",
        backgroundRepeat: "no-repeat",
      }}
    >
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

          {/* z-[1000] keeps the panel above Leaflet's map layers */}
          <PopoverContent align="end" sideOffset={8} className="z-[1000] w-80 space-y-4">
            {/* Current coordinates */}
            <div>
              <p className="text-sm font-medium text-shell">Location</p>

              <p className="mt-1 text-xs text-muted-foreground">
                {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
              </p>
            </div>

            {/* Browser location */}
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

            {/* Manual coordinates */}
            <div className="border-t border-border pt-3">
              <p className="text-sm font-medium text-shell">Set Location Manually</p>

              <p className="mt-1 text-xs text-muted-foreground">
                Enter latitude and longitude for your demo.
              </p>
            </div>

            <form onSubmit={handleManualLocation} className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label htmlFor="latitude" className="mb-1 block text-xs text-muted-foreground">
                    Latitude
                  </label>

                  <Input
                    id="latitude"
                    type="number"
                    step="0.0001"
                    min="-90"
                    max="90"
                    value={latitude}
                    onChange={(e) => {
                      setLatitude(e.target.value);
                      setCoordinateError(null);
                    }}
                    placeholder="9.9312"
                    className="h-9"
                  />
                </div>

                <div>
                  <label htmlFor="longitude" className="mb-1 block text-xs text-muted-foreground">
                    Longitude
                  </label>

                  <Input
                    id="longitude"
                    type="number"
                    step="0.0001"
                    min="-180"
                    max="180"
                    value={longitude}
                    onChange={(e) => {
                      setLongitude(e.target.value);
                      setCoordinateError(null);
                    }}
                    placeholder="76.2673"
                    className="h-9"
                  />
                </div>
              </div>

              {coordinateError && <p className="text-xs text-danger">{coordinateError}</p>}

              <Button type="submit" className="w-full" size="sm">
                Apply Coordinates
              </Button>
            </form>

            {error && <p className="text-xs text-danger">{error}</p>}
          </PopoverContent>
        </Popover>

        <div className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs text-muted-foreground">
          <span className="size-2 rounded-full bg-safe" />
          Live Data
        </div>

        {/* Auth — Sign In button for guests, UserMenu for authenticated users */}
        {!isLoading && (
          isAuthenticated ? (
            <UserMenu />
          ) : (
            <Button
              id="header-sign-in"
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => setAuthOpen(true)}
            >
              <LogIn className="size-4" />
              Sign In
            </Button>
          )
        )}
      </div>

      <AuthModal open={authOpen} onOpenChange={setAuthOpen} />
    </header>
  );
}