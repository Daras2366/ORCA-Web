import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export interface LocateRequest {
  zoneId: string;
  key: number;
}

interface MapLocateContextValue {
  locateRequest: LocateRequest | null;
  locateZone: (zoneId: string) => void;
  availableZoneIds: ReadonlySet<string>;
  registerZones: (zoneIds: string[]) => void;
}

const MapLocateContext = createContext<MapLocateContextValue | null>(null);

export function MapLocateProvider({ children }: { children: ReactNode }) {
  const [locateRequest, setLocateRequest] = useState<LocateRequest | null>(null);
  const [availableZoneIds, setAvailableZoneIds] = useState<ReadonlySet<string>>(
    () => new Set(),
  );

  const locateZone = useCallback((zoneId: string) => {
    const normalized = zoneId.toUpperCase();
    setLocateRequest((prev) => ({
      zoneId: normalized,
      key: (prev?.key ?? 0) + 1,
    }));
  }, []);

  const registerZones = useCallback((zoneIds: string[]) => {
    const normalized = new Set(zoneIds.map((id) => id.toUpperCase()));

    setAvailableZoneIds((prev) => {
      if (prev.size === normalized.size && [...prev].every((id) => normalized.has(id))) {
        return prev;
      }

      return normalized;
    });
  }, []);

  const value = useMemo(
    () => ({ locateRequest, locateZone, availableZoneIds, registerZones }),
    [locateRequest, locateZone, availableZoneIds, registerZones],
  );

  return <MapLocateContext.Provider value={value}>{children}</MapLocateContext.Provider>;
}

export function useMapLocate() {
  const ctx = useContext(MapLocateContext);
  if (!ctx) {
    throw new Error("useMapLocate must be used within MapLocateProvider");
  }
  return ctx;
}
