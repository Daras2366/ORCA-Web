/**
 * VesselForm.tsx — Create / Edit vessel dialog using shadcn Dialog + react-hook-form.
 */

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2 } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { VesselOut } from "@/services/vesselService";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const VESSEL_TYPE_OPTIONS = [
  { value: "small_fishing_boat", label: "Small Fishing Boat" },
  { value: "gillnetter", label: "Gillnetter" },
  { value: "trawler", label: "Trawler" },
  { value: "longliner", label: "Longliner" },
  { value: "purse_seiner", label: "Purse Seiner" },
  { value: "other", label: "Other" },
] as const;

export const ENGINE_TYPE_OPTIONS = [
  { value: "outboard", label: "Outboard" },
  { value: "inboard", label: "Inboard" },
  { value: "diesel", label: "Diesel" },
  { value: "petrol", label: "Petrol" },
  { value: "other", label: "Other" },
] as const;

// ---------------------------------------------------------------------------
// Schema + types
// ---------------------------------------------------------------------------

/**
 * VesselFormValues uses concrete nullable types (never `undefined` for numeric
 * fields) so that exactOptionalPropertyTypes and zodResolver work together.
 * Coercion from empty-string → null happens in the JSX onChange handlers.
 */
export interface VesselFormValues {
  name: string;
  vessel_type: string;
  length_m: number | null;
  engine_type: string | null;
  engine_power_hp: number | null;
  cruising_speed_kmh: number | null;
  fuel_capacity_l: number | null;
}

const vesselSchema = z.object({
  name: z.string().min(1, "Name is required.").max(255),
  vessel_type: z.string().min(1, "Vessel type is required."),
  length_m: z.number().positive("Must be positive.").nullable(),
  engine_type: z.string().nullable(),
  engine_power_hp: z.number().positive("Must be positive.").nullable(),
  cruising_speed_kmh: z.number().positive("Must be positive.").nullable(),
  fuel_capacity_l: z.number().positive("Must be positive.").nullable(),
}) satisfies z.ZodType<VesselFormValues>;


// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface VesselFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** If provided, the form pre-fills for editing. */
  vessel?: VesselOut | null;
  onSubmit: (values: VesselFormValues) => Promise<void>;
}

export function VesselForm({ open, onOpenChange, vessel, onSubmit }: VesselFormProps) {
  const [error, setError] = useState<string | null>(null);
  const isEditing = Boolean(vessel);

  const form = useForm<VesselFormValues>({
    resolver: zodResolver(vesselSchema),
    defaultValues: {
      name: "",
      vessel_type: "other",
      length_m: null,
      engine_type: null,
      engine_power_hp: null,
      cruising_speed_kmh: null,
      fuel_capacity_l: null,
    },
  });

  // Reset form values whenever the dialog opens or the vessel changes.
  useEffect(() => {
    if (open) {
      form.reset({
        name: vessel?.name ?? "",
        vessel_type: vessel?.vessel_type ?? "other",
        length_m: vessel?.length_m ?? null,
        engine_type: vessel?.engine_type ?? null,
        engine_power_hp: vessel?.engine_power_hp ?? null,
        cruising_speed_kmh: vessel?.cruising_speed_kmh ?? null,
        fuel_capacity_l: vessel?.fuel_capacity_l ?? null,
      });
      setError(null);
    }
  }, [open, vessel, form]);

  const handleSubmit = async (values: VesselFormValues) => {
    setError(null);
    try {
      await onSubmit(values);
      onOpenChange(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save vessel.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        id="vessel-form-dialog"
        className="max-w-lg gap-0 overflow-hidden p-0"
        style={{
          background: "linear-gradient(145deg, var(--deep) 0%, var(--abyss) 100%)",
          border: "1px solid var(--border)",
        }}
      >
        <DialogHeader className="border-b border-border px-6 py-5">
          <DialogTitle className="text-base font-semibold text-shell">
            {isEditing ? "Edit Vessel" : "Add Vessel"}
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            {isEditing
              ? "Update your vessel's details."
              : "Enter your vessel's details. All fields except name are optional."}
          </DialogDescription>
        </DialogHeader>

        <div className="overflow-y-auto px-6 py-5">
          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
              {/* Name */}
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Vessel Name *</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        id="vessel-name"
                        placeholder="e.g. Ocean Star"
                        autoComplete="off"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Vessel Type */}
              <FormField
                control={form.control}
                name="vessel_type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Vessel Type *</FormLabel>
                    <Select
                      onValueChange={field.onChange}
                      value={field.value ?? "other"}
                    >
                      <FormControl>
                        <SelectTrigger id="vessel-type">
                          <SelectValue placeholder="Select type" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {VESSEL_TYPE_OPTIONS.map((o) => (
                          <SelectItem key={o.value} value={o.value}>
                            {o.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Length + Engine Type side by side */}
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="length_m"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Length (m)</FormLabel>
                      <FormControl>
                        <Input
                          id="vessel-length"
                          type="number"
                          placeholder="e.g. 12.5"
                          step="0.1"
                          min="0"
                          value={field.value ?? ""}
                          onChange={(e) =>
                            field.onChange(
                              e.target.value === "" ? null : parseFloat(e.target.value),
                            )
                          }
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="engine_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Engine Type</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        value={field.value ?? ""}
                      >
                        <FormControl>
                          <SelectTrigger id="vessel-engine-type">
                            <SelectValue placeholder="Select…" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {ENGINE_TYPE_OPTIONS.map((o) => (
                            <SelectItem key={o.value} value={o.value}>
                              {o.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {/* Engine Power + Cruising Speed */}
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="engine_power_hp"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Engine Power (hp)</FormLabel>
                      <FormControl>
                        <Input
                          id="vessel-engine-power"
                          type="number"
                          placeholder="e.g. 150"
                          min="0"
                          value={field.value ?? ""}
                          onChange={(e) =>
                            field.onChange(
                              e.target.value === "" ? null : parseFloat(e.target.value),
                            )
                          }
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="cruising_speed_kmh"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Cruising Speed (km/h)</FormLabel>
                      <FormControl>
                        <Input
                          id="vessel-speed"
                          type="number"
                          placeholder="e.g. 25"
                          min="0"
                          value={field.value ?? ""}
                          onChange={(e) =>
                            field.onChange(
                              e.target.value === "" ? null : parseFloat(e.target.value),
                            )
                          }
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {/* Fuel Capacity */}
              <FormField
                control={form.control}
                name="fuel_capacity_l"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Fuel Capacity (L)</FormLabel>
                    <FormControl>
                      <Input
                        id="vessel-fuel"
                        type="number"
                        placeholder="e.g. 500"
                        min="0"
                        value={field.value ?? ""}
                        onChange={(e) =>
                          field.onChange(
                            e.target.value === "" ? null : parseFloat(e.target.value),
                          )
                        }
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {error && (
                <p className="rounded-md border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
                  {error}
                </p>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => onOpenChange(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  id="vessel-form-submit"
                  disabled={form.formState.isSubmitting}
                >
                  {form.formState.isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 size-4 animate-spin" />
                      Saving…
                    </>
                  ) : isEditing ? (
                    "Save Changes"
                  ) : (
                    "Add Vessel"
                  )}
                </Button>
              </div>
            </form>
          </Form>
        </div>
      </DialogContent>
    </Dialog>
  );
}
