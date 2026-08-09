import { MapContainer, TileLayer, Marker } from "react-leaflet";
import { divIcon } from "leaflet";
import "leaflet/dist/leaflet.css";

const RISK_COLOR = {
  LOW: "#34d399",
  GUARDED: "#34d399",
  ELEVATED: "#f5a623",
  HIGH: "#f24545",
  CRITICAL: "#f24545",
};

function riskIcon(riskLevel) {
  const color = RISK_COLOR[riskLevel] ?? "#7d8a91";
  return divIcon({
    className: "",
    html: `<span style="display:block;width:20px;height:20px;border-radius:50%;background:${color};border:3px solid #0f1417;box-shadow:0 0 0 6px ${color}33;"></span>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
}

// Deliberately minimal — a resident needs to see roughly where the affected
// area is, not click around exploring multiple nodes or device status.
export function ResidentMap({ latitude, longitude, riskLevel }) {
  if (latitude == null || longitude == null) {
    return (
      <div className="resident-map-frame">
        <p className="empty-state">Location not available yet.</p>
      </div>
    );
  }

  return (
    <div className="resident-map-frame">
      <MapContainer
        center={[latitude, longitude]}
        zoom={14}
        scrollWheelZoom={false}
        dragging={false}
        zoomControl={false}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Marker position={[latitude, longitude]} icon={riskIcon(riskLevel)} />
      </MapContainer>
    </div>
  );
}
