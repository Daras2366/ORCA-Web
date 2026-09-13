import { useEffect, useRef, type MutableRefObject } from "react";
import L from "leaflet";
import { MapContainer, Marker, Popup, TileLayer, useMap, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { LocateRequest } from "@/hooks/useMapLocate";
import type { FishingZone, UserLocation, NavigationResult } from "@/types/marine";

function zoneColor(zone: FishingZone) {
  if (zone.potential === "High") return "var(--safe)";
  if (zone.potential === "Medium") return "var(--blush)";
  return "var(--plum)";
}

function zoneIcon(zone: FishingZone) {
  const size = zone.recommended ? 30 : 22;
  const ring = zone.recommended
    ? `box-shadow:0 0 0 3px var(--accent);`
    : `box-shadow:0 0 0 2px var(--abyss);`;
  return L.divIcon({
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `<div style="width:${size}px;height:${size}px;border-radius:9999px;background:${zoneColor(
      zone,
    )};${ring}display:flex;align-items:center;justify-content:center;color:#03121e;font-size:10px;font-weight:700;font-family:Inter,sans-serif;">${
      zone.recommended ? "★" : ""
    }</div>`,
  });
}

const vesselIcon = L.divIcon({
  className: "",
  iconSize: [18, 18],
  iconAnchor: [9, 9],
  html: `<div style="width:18px;height:18px;border-radius:4px;background:var(--shell);box-shadow:0 0 0 3px var(--deep);"></div>`,
});

const startIcon = L.divIcon({
  className: "",
  iconSize: [24, 24],
  iconAnchor: [12, 12],
  html: `<div style="width:24px;height:24px;border-radius:50%;background:#22c55e;border:3px solid #ffffff;box-shadow:0 0 0 3px #22c55e;"></div>`,
});

const destinationIcon = L.divIcon({
  className: "",
  iconSize: [24, 24],
  iconAnchor: [12, 12],
  html: `<div style="width:24px;height:24px;border-radius:50%;background:#ef4444;border:3px solid #ffffff;box-shadow:0 0 0 3px #ef4444;"></div>`,
});

interface Props {
  zones: FishingZone[];
  location: UserLocation;
  onShowRoute: (zoneId: string) => void;
  locateRequest: LocateRequest | null;
  navigationResult?: NavigationResult | null;
}

function ZoneMapController({
  locateRequest,
  markerRefs,
  zones,
}: {
  locateRequest: LocateRequest | null;
  markerRefs: MutableRefObject<Record<string, L.Marker | null>>;
  zones: FishingZone[];
}) {
  const map = useMap();

  useEffect(() => {
    if (!locateRequest) return;

    const zone = zones.find(
      (candidate) => candidate.zone_id.toUpperCase() === locateRequest.zoneId,
    );
    if (!zone) return;

    const marker = markerRefs.current[zone.zone_id];
    const target: L.LatLngExpression = [zone.latitude, zone.longitude];

    const openPopup = () => {
      marker?.openPopup();
    };

    map.flyTo(target, 11, { duration: 0.75 });
    map.once("moveend", openPopup);

    return () => {
      map.off("moveend", openPopup);
    };
  }, [locateRequest, markerRefs, zones, map]);

  return null;
}

function LocationMapController({ location }: { location: UserLocation }) {
  const map = useMap();

  useEffect(() => {
    map.flyTo([location.latitude, location.longitude], Math.max(map.getZoom(), 7), {
      duration: 0.75,
    });
  }, [location.latitude, location.longitude, map]);

  return null;
}

export default function LeafletMap({
  zones,
  location,
  onShowRoute,
  locateRequest,
  navigationResult,
}: Props) {
  const markerRefs = useRef<Record<string, L.Marker | null>>({});

  return (
    <div className="orca-map h-full w-full">
      <MapContainer
        center={[9.8, 75.6]}
        zoom={7}
        scrollWheelZoom={false}
        className="h-full w-full"
        attributionControl
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
        />

        <ZoneMapController locateRequest={locateRequest} markerRefs={markerRefs} zones={zones} />

        <LocationMapController location={location} />

        {/* Navigation Route Line */}
        {navigationResult?.success && navigationResult.geojson.coordinates.length > 0 && (
          <Polyline
            positions={navigationResult.geojson.coordinates.map(([lng, lat]) => [lat, lng])}
            color="#3b82f6"
            weight={3}
            opacity={0.8}
          />
        )}

        {/* Start Point Marker */}
        {navigationResult?.success && (
          <Marker
            position={[
              navigationResult.snapped_start.latitude,
              navigationResult.snapped_start.longitude,
            ]}
            icon={startIcon}
          >
            <Popup>
              <p className="text-sm font-semibold text-shell">Start Point</p>
              <p className="text-xs text-muted-foreground">
                {navigationResult.snapped_start.latitude.toFixed(4)},{" "}
                {navigationResult.snapped_start.longitude.toFixed(4)}
              </p>
            </Popup>
          </Marker>
        )}

        {/* Destination Point Marker */}
        {navigationResult?.success && (
          <Marker
            position={[
              navigationResult.snapped_destination.latitude,
              navigationResult.snapped_destination.longitude,
            ]}
            icon={destinationIcon}
          >
            <Popup>
              <p className="text-sm font-semibold text-shell">Destination</p>
              <p className="text-xs text-muted-foreground">
                {navigationResult.snapped_destination.latitude.toFixed(4)},{" "}
                {navigationResult.snapped_destination.longitude.toFixed(4)}
              </p>
            </Popup>
          </Marker>
        )}

        <Marker position={[location.latitude, location.longitude]} icon={vesselIcon}>
          <Popup>
            <p className="text-sm font-semibold text-shell">Your Vessel</p>
            <p className="text-xs text-muted-foreground">
              {location.latitude.toFixed(3)}, {location.longitude.toFixed(3)}
            </p>
          </Popup>
        </Marker>

        {zones.map((zone) => (
          <Marker
            key={zone.zone_id}
            ref={(marker) => {
              markerRefs.current[zone.zone_id] = marker;
            }}
            position={[zone.latitude, zone.longitude]}
            icon={zoneIcon(zone)}
          >
            <Popup>
              <div className="w-48 space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-shell">{zone.zone_id}</p>
                  {zone.recommended && (
                    <span className="rounded-full bg-rose px-2 py-0.5 text-[10px] text-primary-foreground">
                      Recommended
                    </span>
                  )}
                </div>
                <div>
                  <p className="text-[11px] text-muted-foreground">Fishing Potential</p>
                  <p className="text-sm text-shell">
                    {zone.hsi.toFixed(2)} — {zone.potential}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <p className="text-muted-foreground">SST</p>
                    <p className="text-shell">
                      {zone.sst_c != null ? `${zone.sst_c.toFixed(2)}°C` : "N/A"}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Chlorophyll</p>
                    <p className="text-shell">
                      {zone.chlorophyll_mg_m3 != null
                        ? `${zone.chlorophyll_mg_m3.toFixed(3)} mg/m³`
                        : "N/A"}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Safety</p>
                    <p className="text-shell">
                      {zone.safety_score != null ? `${zone.safety_score.toFixed(1)}/100` : "N/A"}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    onShowRoute(zone.zone_id);
                  }}
                  className="w-full rounded-md bg-rose px-2 py-1.5 text-xs font-medium text-primary-foreground"
                >
                  Show Route
                </button>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
