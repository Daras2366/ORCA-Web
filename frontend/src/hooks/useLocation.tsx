import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { defaultLocation } from "@/data/mockData";
import type { UserLocation } from "@/types/marine";

interface LocationContextValue {
  location: UserLocation;
  setLocation: (loc: UserLocation) => void;
  useBrowserLocation: () => void;
  detecting: boolean;
  error: string | null;
}

const LocationContext = createContext<LocationContextValue | null>(null);

export function LocationProvider({ children }: { children: ReactNode }) {
  const [location, setLocation] = useState<UserLocation>(defaultLocation);
  const [detecting, setDetecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const useBrowserLocation = useCallback(() => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setError("Geolocation is not available in this browser.");
      return;
    }
    setDetecting(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({
          latitude: Number(pos.coords.latitude.toFixed(4)),
          longitude: Number(pos.coords.longitude.toFixed(4)),
          city: "Current Position",
          state: "",
          country: "",
        });
        setDetecting(false);
      },
      () => {
        setError("Unable to detect your location.");
        setDetecting(false);
      },
      { timeout: 8000 },
    );
  }, []);

  const value = useMemo(
    () => ({ location, setLocation, useBrowserLocation, detecting, error }),
    [location, useBrowserLocation, detecting, error],
  );

  return <LocationContext.Provider value={value}>{children}</LocationContext.Provider>;
}

export function useLocationContext() {
  const ctx = useContext(LocationContext);
  if (!ctx) throw new Error("useLocationContext must be used inside LocationProvider");
  return ctx;
}

export function formatLocation(loc: UserLocation) {
  return [loc.city, loc.state].filter(Boolean).join(", ");
}
