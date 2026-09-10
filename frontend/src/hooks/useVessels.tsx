/**
 * useVessels.tsx — React context for vessel list + selected vessel state.
 *
 * - Loads the vessel list when the user is authenticated.
 * - Persists `selectedVesselId` in localStorage, keyed by user ID
 *   so multiple users on the same browser don't interfere.
 * - Exposes full CRUD helpers that keep state in sync.
 * - Guests see an empty state and no vessel-related errors.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { useAuth } from "@/hooks/useAuth";
import {
  createVessel,
  deleteVessel,
  listVessels,
  updateVessel,
  type VesselCreate,
  type VesselOut,
  type VesselUpdate,
} from "@/services/vesselService";

// ---------------------------------------------------------------------------
// Context types
// ---------------------------------------------------------------------------

interface VesselContextValue {
  vessels: VesselOut[];
  selectedVesselId: string | null;
  selectedVessel: VesselOut | null;
  isLoading: boolean;
  error: string | null;
  // Mutations
  addVessel: (payload: VesselCreate) => Promise<VesselOut>;
  editVessel: (id: string, payload: VesselUpdate) => Promise<VesselOut>;
  removeVessel: (id: string) => Promise<void>;
  selectVessel: (id: string | null) => void;
  refresh: () => Promise<void>;
}

const VesselContext = createContext<VesselContextValue | null>(null);

// ---------------------------------------------------------------------------
// localStorage helpers
// ---------------------------------------------------------------------------

function selectedKey(userId: string): string {
  return `orca_selected_vessel_${userId}`;
}

function readSelected(userId: string): string | null {
  return localStorage.getItem(selectedKey(userId));
}

function writeSelected(userId: string, id: string | null): void {
  if (id === null) {
    localStorage.removeItem(selectedKey(userId));
  } else {
    localStorage.setItem(selectedKey(userId), id);
  }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function VesselProvider({ children }: { children: ReactNode }) {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();

  const [vessels, setVessels] = useState<VesselOut[]>([]);
  const [selectedVesselId, setSelectedVesselIdState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load vessels when the user logs in; clear when they log out.
  useEffect(() => {
    if (authLoading) return;

    if (!isAuthenticated || !user) {
      setVessels([]);
      setSelectedVesselIdState(null);
      setError(null);
      return;
    }

    // Restore persisted selection for this user.
    const persisted = readSelected(user.id);

    setIsLoading(true);
    listVessels()
      .then((list) => {
        setVessels(list);
        // Only restore if the vessel still exists.
        if (persisted && list.some((v) => v.id === persisted)) {
          setSelectedVesselIdState(persisted);
        } else {
          setSelectedVesselIdState(null);
          writeSelected(user.id, null);
        }
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to load vessels.");
      })
      .finally(() => setIsLoading(false));
  }, [isAuthenticated, authLoading, user]);

  const refresh = useCallback(async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    try {
      const list = await listVessels();
      setVessels(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to refresh vessels.");
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  const addVessel = useCallback(
    async (payload: VesselCreate): Promise<VesselOut> => {
      const vessel = await createVessel(payload);
      setVessels((prev) => [...prev, vessel]);
      return vessel;
    },
    [],
  );

  const editVessel = useCallback(
    async (id: string, payload: VesselUpdate): Promise<VesselOut> => {
      const updated = await updateVessel(id, payload);
      setVessels((prev) => prev.map((v) => (v.id === id ? updated : v)));
      return updated;
    },
    [],
  );

  const removeVessel = useCallback(
    async (id: string): Promise<void> => {
      await deleteVessel(id);
      setVessels((prev) => prev.filter((v) => v.id !== id));
      // Deselect if the deleted vessel was selected.
      setSelectedVesselIdState((prev) => {
        if (prev === id) {
          if (user) writeSelected(user.id, null);
          return null;
        }
        return prev;
      });
    },
    [user],
  );

  const selectVessel = useCallback(
    (id: string | null) => {
      setSelectedVesselIdState(id);
      if (user) writeSelected(user.id, id);
    },
    [user],
  );

  const selectedVessel = vessels.find((v) => v.id === selectedVesselId) ?? null;

  return (
    <VesselContext.Provider
      value={{
        vessels,
        selectedVesselId,
        selectedVessel,
        isLoading,
        error,
        addVessel,
        editVessel,
        removeVessel,
        selectVessel,
        refresh,
      }}
    >
      {children}
    </VesselContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useVessels(): VesselContextValue {
  const ctx = useContext(VesselContext);
  if (!ctx) throw new Error("useVessels must be used within <VesselProvider>");
  return ctx;
}
