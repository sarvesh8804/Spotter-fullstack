import { useEffect, useMemo } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

export const STOP_COLORS = {
  start: "#9aa3b2",
  pickup: "#2f6fed",
  dropoff: "#1f9d63",
  fuel: "#f0a020",
  rest_break: "#7c6cf0",
  overnight: "#e25d6a",
  end: "#1f9d63",
};

/** Continental US overview before a trip is planned */
const USA_CENTER = [39.5, -98.35];
const USA_ZOOM = 4;

function makeIcon(kind) {
  const color = STOP_COLORS[kind] || "#2f6fed";
  return L.divIcon({
    className: "stop-marker",
    html: `<span style="background:${color}"></span>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

function FitBounds({ positions, stops }) {
  const map = useMap();
  useEffect(() => {
    const pts = [
      ...positions,
      ...stops.filter((s) => s.lat && s.lon).map((s) => [s.lat, s.lon]),
    ];
    if (pts.length) {
      map.fitBounds(pts, { padding: [28, 28] });
    } else {
      map.setView(USA_CENTER, USA_ZOOM);
    }
  }, [map, positions, stops]);
  return null;
}

function InvalidateSize({ active }) {
  const map = useMap();
  useEffect(() => {
    const id = window.setTimeout(() => map.invalidateSize(), 80);
    return () => window.clearTimeout(id);
  }, [map, active]);
  return null;
}

export default function RouteMap({
  geometry,
  stops,
  summary,
  locations,
  active = true,
}) {
  const positions = useMemo(
    () => (geometry || []).map(([lon, lat]) => [lat, lon]),
    [geometry]
  );

  const visibleStops = (stops || []).filter(
    (s) => s.lat && s.lon && s.kind !== "end"
  );

  const hasRoute = positions.length > 0;

  const eta = summary
    ? `${summary.days} day${summary.days === 1 ? "" : "s"} · ${summary.total_driving_hours}h drive`
    : null;

  return (
    <div className="map-shell">
      <MapContainer
        center={USA_CENTER}
        zoom={USA_ZOOM}
        scrollWheelZoom
        className="route-map"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        {hasRoute && (
          <Polyline
            positions={positions}
            pathOptions={{ color: "#16181d", weight: 3.5, opacity: 0.85 }}
          />
        )}
        <FitBounds positions={positions} stops={visibleStops} />
        <InvalidateSize active={active} />
        {visibleStops.map((stop, i) => (
          <Marker
            key={`${stop.kind}-${i}`}
            position={[stop.lat, stop.lon]}
            icon={makeIcon(stop.kind)}
          >
            <Popup>
              <strong>{stop.label}</strong>
              <br />
              {new Date(stop.time).toLocaleString()}
              <br />
              {stop.duration_hours > 0 && `${stop.duration_hours}h · `}
              {stop.miles_from_start} mi
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {!hasRoute && (
        <div className="map-chip map-chip-bottom">
          <span>United States overview</span>
          <strong>No route yet</strong>
          <em className="badge-yellow">Plan a trip</em>
        </div>
      )}

      {summary && (
        <>
          <div className="map-chip map-chip-top">
            <strong>
              {(locations?.current?.query || "Start").split(",")[0]}
              {" → "}
              {(locations?.dropoff?.query || "End").split(",")[0]}
            </strong>
            <span>{summary.route_miles} mi</span>
          </div>
          <div className="map-chip map-chip-bottom">
            <span>Plan ready</span>
            <strong>{eta}</strong>
            <em className="badge-yellow">
              {summary.cycle_remaining_end}h cycle left
            </em>
          </div>
        </>
      )}
    </div>
  );
}
