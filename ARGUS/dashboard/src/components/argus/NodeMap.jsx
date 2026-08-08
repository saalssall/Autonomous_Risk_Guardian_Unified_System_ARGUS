import { MapContainer, TileLayer, Marker, Tooltip, useMap } from "react-leaflet";
import { divIcon } from "leaflet";
import { useEffect } from "react";
import "leaflet/dist/leaflet.css";

const STATUS_COLOR = {
  HEALTHY: "#34d399",
  DEGRADED: "#f5a623",
  OFFLINE: "#f24545",
};

function markerIcon(status, isSelected) {
  const color = STATUS_COLOR[status] ?? "#7d8a91";
  const size = isSelected ? 22 : 16;
  return divIcon({
    className: "",
    html: `<span style="display:block;width:${size}px;height:${size}px;border-radius:50%;background:${color};border:2px solid #0f1417;box-shadow:0 0 0 3px ${color}33;"></span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

// Recenters the map when the node list first loads, without fighting the
// user if they've since panned around.
function FitOnce({ nodes }) {
  const map = useMap();
  useEffect(() => {
    if (nodes.length === 0) return;
    const bounds = nodes.map((n) => [n.latitude, n.longitude]);
    if (bounds.length === 1) {
      map.setView(bounds[0], 14);
    } else {
      map.fitBounds(bounds, { padding: [40, 40] });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes.length > 0]);
  return null;
}

export function NodeMap({ nodes, selectedNodeId, onSelect }) {
  const defaultCenter = [-27.4698, 153.0251]; // Brisbane — used only until real nodes load

  return (
    <div className="panel map-panel">
      <p className="eyebrow">Node map</p>
      <div className="map-frame">
        {nodes.length === 0 ? (
          <div className="feed-placeholder">
            <span>◉</span>
            <p>Waiting for nodes to report in.</p>
          </div>
        ) : (
          <MapContainer center={defaultCenter} zoom={13} scrollWheelZoom={true} style={{ height: "100%", width: "100%" }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <FitOnce nodes={nodes} />
            {nodes.map((node) => (
              <Marker
                key={node.node_id}
                position={[node.latitude, node.longitude]}
                icon={markerIcon(node.status, node.node_id === selectedNodeId)}
                eventHandlers={{ click: () => onSelect(node.node_id) }}
              >
                <Tooltip direction="top" offset={[0, -10]}>
                  {node.node_id} · {node.status}
                </Tooltip>
              </Marker>
            ))}
          </MapContainer>
        )}
      </div>
      <div className="map-legend">
        {Object.entries(STATUS_COLOR).map(([label, color]) => (
          <span key={label} className="legend-item">
            <span className="legend-dot" style={{ background: color }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
