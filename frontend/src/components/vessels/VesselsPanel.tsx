/**
 * VesselsPanel.tsx — My Vessels section rendered on the /profile page.
 *
 * Shows vessel cards with:
 *   - Select as active vessel (persisted in localStorage)
 *   - Edit vessel (opens VesselForm in edit mode)
 *   - Delete vessel (with confirmation)
 *   - Add vessel button (opens VesselForm in create mode)
 *
 * Guests never see this panel (the profile page already redirects guests).
 */

import { useState } from "react";
import {
  Anchor,
  CheckCircle2,
  Circle,
  Edit3,
  Fuel,
  Gauge,
  Plus,
  Ruler,
  Trash2,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useVessels } from "@/hooks/useVessels";
import { VesselForm, VESSEL_TYPE_OPTIONS, ENGINE_TYPE_OPTIONS, type VesselFormValues } from "./VesselForm";
import type { VesselCreate, VesselOut } from "@/services/vesselService";

// ---------------------------------------------------------------------------
// Label helpers
// ---------------------------------------------------------------------------

function vesselTypeLabel(value: string): string {
  return VESSEL_TYPE_OPTIONS.find((o) => o.value === value)?.label ?? value;
}

function engineTypeLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return ENGINE_TYPE_OPTIONS.find((o) => o.value === value)?.label ?? value;
}

// ---------------------------------------------------------------------------
// VesselCard
// ---------------------------------------------------------------------------

function VesselCard({
  vessel,
  isSelected,
  onSelect,
  onEdit,
  onDelete,
}: {
  vessel: VesselOut;
  isSelected: boolean;
  onSelect: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      className={`panel relative flex flex-col gap-3 p-4 transition-all ${
        isSelected
          ? "ring-2 ring-primary ring-offset-2 ring-offset-card"
          : "hover:ring-1 hover:ring-border"
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/15">
            <Anchor className="size-4 text-primary" />
          </div>
          <div>
            <p className="font-medium text-shell leading-tight">{vessel.name}</p>
            <p className="text-[11px] text-muted-foreground">
              {vesselTypeLabel(vessel.vessel_type)}
            </p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex shrink-0 items-center gap-1">
          <button
            id={`vessel-edit-${vessel.id}`}
            onClick={onEdit}
            title="Edit vessel"
            className="flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-white/10 hover:text-shell"
          >
            <Edit3 className="size-3.5" />
          </button>
          <button
            id={`vessel-delete-${vessel.id}`}
            onClick={onDelete}
            title="Delete vessel"
            className="flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-danger/10 hover:text-danger"
          >
            <Trash2 className="size-3.5" />
          </button>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
        {vessel.length_m != null && (
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Ruler className="size-3 shrink-0" />
            {vessel.length_m} m
          </span>
        )}
        {vessel.engine_type && (
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Zap className="size-3 shrink-0" />
            {engineTypeLabel(vessel.engine_type)}
          </span>
        )}
        {vessel.engine_power_hp != null && (
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Gauge className="size-3 shrink-0" />
            {vessel.engine_power_hp} hp
          </span>
        )}
        {vessel.cruising_speed_kmh != null && (
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Gauge className="size-3 shrink-0" />
            {vessel.cruising_speed_kmh} km/h
          </span>
        )}
        {vessel.fuel_capacity_l != null && (
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Fuel className="size-3 shrink-0" />
            {vessel.fuel_capacity_l} L
          </span>
        )}
      </div>

      {/* Select button */}
      <button
        id={`vessel-select-${vessel.id}`}
        onClick={onSelect}
        className={`flex w-full items-center justify-center gap-2 rounded-lg border py-1.5 text-xs font-medium transition-colors ${
          isSelected
            ? "border-primary/40 bg-primary/10 text-primary"
            : "border-border text-muted-foreground hover:border-primary/30 hover:bg-primary/5 hover:text-primary"
        }`}
      >
        {isSelected ? (
          <>
            <CheckCircle2 className="size-3.5" />
            Active Vessel
          </>
        ) : (
          <>
            <Circle className="size-3.5" />
            Set as Active
          </>
        )}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// VesselsPanel
// ---------------------------------------------------------------------------

export function VesselsPanel() {
  const { vessels, selectedVesselId, isLoading, error, addVessel, editVessel, removeVessel, selectVessel } =
    useVessels();

  const [formOpen, setFormOpen] = useState(false);
  const [editingVessel, setEditingVessel] = useState<VesselOut | null>(null);
  const [deletingVesselId, setDeletingVesselId] = useState<string | null>(null);

  const handleAdd = () => {
    setEditingVessel(null);
    setFormOpen(true);
  };

  const handleEdit = (vessel: VesselOut) => {
    setEditingVessel(vessel);
    setFormOpen(true);
  };

  const handleFormSubmit = async (values: VesselFormValues) => {
    const payload: VesselCreate = {
      name: values.name,
      vessel_type: values.vessel_type,
      length_m: values.length_m,
      engine_type: values.engine_type,
      engine_power_hp: values.engine_power_hp,
      cruising_speed_kmh: values.cruising_speed_kmh,
      fuel_capacity_l: values.fuel_capacity_l,
    };
    if (editingVessel) {
      await editVessel(editingVessel.id, payload);
    } else {
      await addVessel(payload);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deletingVesselId) return;
    await removeVessel(deletingVesselId);
    setDeletingVesselId(null);
  };

  const deletingVessel = vessels.find((v) => v.id === deletingVesselId);

  return (
    <section>
      {/* Section header */}
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          My Vessels
        </h2>
        <Button
          id="add-vessel-btn"
          size="sm"
          variant="outline"
          className="h-7 gap-1.5 px-3 text-xs"
          onClick={handleAdd}
        >
          <Plus className="size-3.5" />
          Add Vessel
        </Button>
      </div>

      {/* States */}
      {isLoading && (
        <p className="text-sm text-muted-foreground">Loading vessels…</p>
      )}

      {error && (
        <p className="rounded-md border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}

      {!isLoading && !error && vessels.length === 0 && (
        <div className="panel flex flex-col items-center gap-3 py-8 text-center">
          <div className="flex size-12 items-center justify-center rounded-xl bg-primary/10">
            <Anchor className="size-6 text-primary/60" />
          </div>
          <div>
            <p className="text-sm font-medium text-shell">No vessels yet</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Add your vessel to save its details for future ORCA sessions.
            </p>
          </div>
          <Button id="add-first-vessel-btn" size="sm" onClick={handleAdd} className="gap-2">
            <Plus className="size-3.5" />
            Add Your First Vessel
          </Button>
        </div>
      )}

      {!isLoading && vessels.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {vessels.map((vessel) => (
            <VesselCard
              key={vessel.id}
              vessel={vessel}
              isSelected={vessel.id === selectedVesselId}
              onSelect={() =>
                selectVessel(vessel.id === selectedVesselId ? null : vessel.id)
              }
              onEdit={() => handleEdit(vessel)}
              onDelete={() => setDeletingVesselId(vessel.id)}
            />
          ))}
        </div>
      )}

      {/* Create / Edit form dialog */}
      <VesselForm
        open={formOpen}
        onOpenChange={setFormOpen}
        vessel={editingVessel}
        onSubmit={handleFormSubmit}
      />

      {/* Delete confirmation dialog */}
      <AlertDialog
        open={deletingVesselId !== null}
        onOpenChange={(open) => !open && setDeletingVesselId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete vessel?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete{" "}
              <strong className="text-shell">{deletingVessel?.name}</strong>.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel id="vessel-delete-cancel">Cancel</AlertDialogCancel>
            <AlertDialogAction
              id="vessel-delete-confirm"
              onClick={handleDeleteConfirm}
              className="bg-danger text-danger-foreground hover:bg-danger/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  );
}
