import React from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { MapPin } from 'lucide-react';
import { env } from '@/core/config/env';
import { SeverityBadge } from '@/core/components/SeverityBadge';
import { BackendSeverityLevel } from '@/types/api/backendContracts';
import { MapProviderProps } from './types';

const SEVERITY_COLORS: Record<BackendSeverityLevel, string> = {
  CRITICAL: '#B31412',
  HIGH: '#D93025',
  MEDIUM: '#E37400',
  LOW: '#1E8E3E',
};

const createMarkerPin = (severity: BackendSeverityLevel) => {
  const color = SEVERITY_COLORS[severity] || '#526B55';
  return L.divIcon({
    className: 'custom-pin',
    html: `<div style="background-color: ${color}; width: 22px; height: 22px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center;"><div style="width: 6px; height: 6px; border-radius: 50%; background: white;"></div></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
    popupAnchor: [0, -12],
  });
};

export const LeafletMapProvider: React.FC<MapProviderProps> = ({
  points,
  center,
  zoom = 13,
  onSelectPoint,
  className = 'w-full h-full',
}) => {
  return (
    <MapContainer
      center={center}
      zoom={zoom}
      scrollWheelZoom={true}
      className={className}
    >
      <TileLayer url={env.mapTileUrl} attribution={env.mapAttribution} />
      {points.map((report) => (
        <Marker
          key={report.id}
          position={[report.latitude, report.longitude]}
          icon={createMarkerPin(report.severity)}
        >
          <Popup>
            <div className="p-1 min-w-[200px] text-xs space-y-2">
              <div className="flex items-center justify-between gap-2 border-b pb-1">
                <strong className="font-mono text-civic-text-primary">{report.trackingId}</strong>
                <SeverityBadge severity={report.severity} size="sm" />
              </div>
              <div className="font-semibold text-civic-green">{report.category}</div>
              <p className="text-gray-600 text-[11px] line-clamp-2">{report.description}</p>
              <div className="text-[10px] text-gray-500 flex items-center gap-1">
                <MapPin className="w-3 h-3 text-civic-green shrink-0" />
                <span className="truncate">{report.addressHint || 'Coordinates recorded'}</span>
              </div>
              {onSelectPoint && (
                <div className="pt-1 flex justify-end">
                  <button
                    type="button"
                    onClick={() => onSelectPoint(report.id)}
                    className="text-xs text-civic-green font-medium hover:underline flex items-center gap-1"
                  >
                    View Full Details →
                  </button>
                </div>
              )}
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
};
