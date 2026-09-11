import React, { useEffect, useRef, useState } from 'react';
import { env } from '@/core/config/env';
import { useTheme } from '@/core/theme/ThemeContext';
import { BackendSeverityLevel } from '@/types/api/backendContracts';
import { MapProviderProps, MapPoint } from './types';
import { LeafletMapProvider } from './LeafletMapProvider';

const SEVERITY_COLORS: Record<BackendSeverityLevel, string> = {
  CRITICAL: '#B31412',
  HIGH: '#D93025',
  MEDIUM: '#E37400',
  LOW: '#1E8E3E',
};

// Singleton script loader for Google Maps
let googleMapsPromise: Promise<void> | null = null;

function loadGoogleMaps(apiKey: string): Promise<void> {
  if (typeof window !== 'undefined' && window.google?.maps) {
    return Promise.resolve();
  }
  if (googleMapsPromise) {
    return googleMapsPromise;
  }

  googleMapsPromise = new Promise((resolve, reject) => {
    const existingScript = document.getElementById('google-maps-script');
    if (existingScript) {
      if (window.google?.maps) {
        resolve();
      } else {
        existingScript.addEventListener('load', () => resolve());
        existingScript.addEventListener('error', (e) => reject(e));
      }
      return;
    }

    const script = document.createElement('script');
    script.id = 'google-maps-script';
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places`;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = (err) => {
      googleMapsPromise = null;
      reject(err);
    };
    document.head.appendChild(script);
  });

  return googleMapsPromise;
}

// Dark mode map styles for Google Maps
const DARK_MAP_STYLE: google.maps.MapTypeStyle[] = [
  { elementType: 'geometry', stylers: [{ color: '#242f3e' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#242f3e' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#746855' }] },
  {
    featureType: 'administrative.locality',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#d59563' }],
  },
  {
    featureType: 'poi',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#d59563' }],
  },
  {
    featureType: 'poi.park',
    elementType: 'geometry',
    stylers: [{ color: '#263c3f' }],
  },
  {
    featureType: 'poi.park',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#6b9a76' }],
  },
  {
    featureType: 'road',
    elementType: 'geometry',
    stylers: [{ color: '#38414e' }],
  },
  {
    featureType: 'road',
    elementType: 'geometry.stroke',
    stylers: [{ color: '#212a37' }],
  },
  {
    featureType: 'road',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#9ca5b3' }],
  },
  {
    featureType: 'road.highway',
    elementType: 'geometry',
    stylers: [{ color: '#746855' }],
  },
  {
    featureType: 'road.highway',
    elementType: 'geometry.stroke',
    stylers: [{ color: '#1f2835' }],
  },
  {
    featureType: 'road.highway',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#f3d19c' }],
  },
  {
    featureType: 'water',
    elementType: 'geometry',
    stylers: [{ color: '#17263c' }],
  },
  {
    featureType: 'water',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#515c6d' }],
  },
  {
    featureType: 'water',
    elementType: 'labels.text.stroke',
    stylers: [{ color: '#17263c' }],
  },
];

export const GoogleMapsProvider: React.FC<MapProviderProps> = ({
  points,
  center,
  zoom = 13,
  onSelectPoint,
  className = 'w-full h-full',
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<google.maps.Map | null>(null);
  const markersRef = useRef<google.maps.Marker[]>([]);
  const infoWindowRef = useRef<google.maps.InfoWindow | null>(null);

  const [hasError, setHasError] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const { resolvedTheme } = useTheme();

  // Load Google Maps script
  useEffect(() => {
    let isMounted = true;
    loadGoogleMaps(env.googleMapsApiKey)
      .then(() => {
        if (isMounted) {
          setIsLoaded(true);
        }
      })
      .catch((err) => {
        console.warn('[CivicSense Map] Google Maps failed to load, falling back to Leaflet:', err);
        if (isMounted) {
          setHasError(true);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Initialize Map
  useEffect(() => {
    if (!isLoaded || !mapRef.current || hasError || !window.google?.maps) return;

    if (!mapInstanceRef.current) {
      const initialMap = new google.maps.Map(mapRef.current, {
        center: { lat: center[0], lng: center[1] },
        zoom,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: true,
        styles: resolvedTheme === 'dark' ? DARK_MAP_STYLE : [],
      });
      mapInstanceRef.current = initialMap;
      infoWindowRef.current = new google.maps.InfoWindow();
    } else {
      mapInstanceRef.current.setOptions({
        styles: resolvedTheme === 'dark' ? DARK_MAP_STYLE : [],
      });
    }
  }, [isLoaded, hasError, resolvedTheme]);

  // Center updates
  useEffect(() => {
    if (mapInstanceRef.current && isLoaded) {
      mapInstanceRef.current.panTo({ lat: center[0], lng: center[1] });
    }
  }, [center, isLoaded]);

  // Update Markers for Citizen Reports
  useEffect(() => {
    if (!isLoaded || !mapInstanceRef.current || !window.google?.maps) return;

    const map = mapInstanceRef.current;
    const infoWindow = infoWindowRef.current;

    // Clear existing markers
    markersRef.current.forEach((m) => m.setMap(null));
    markersRef.current = [];

    // Create custom pin icon for report markers
    const createPin = (color: string) => {
      const svg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="30" height="40" viewBox="0 0 30 40">
          <defs>
            <filter id="shadow" x="-20%" y="-10%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="rgba(0,0,0,0.35)"/>
            </filter>
          </defs>
          <path d="M15 1C7.268 1 1 7.268 1 15c0 10.5 14 24 14 24s14-13.5 14-24c0-7.732-6.268-14-14-14z" fill="${color}" stroke="#FFFFFF" stroke-width="2.5" filter="url(#shadow)"/>
          <circle cx="15" cy="15" r="5" fill="#FFFFFF"/>
        </svg>
      `;
      return {
        url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`,
        scaledSize: new google.maps.Size(30, 40),
        anchor: new google.maps.Point(15, 40),
      };
    };

    const newMarkers = points.map((report: MapPoint) => {
      const pinColor = SEVERITY_COLORS[report.severity] || '#526B55';
      const marker = new google.maps.Marker({
        position: { lat: report.latitude, lng: report.longitude },
        map,
        title: `${report.trackingId} - ${report.category}`,
        icon: createPin(pinColor),
      });

      marker.addListener('click', () => {
        if (!infoWindow) return;

        const contentString = `
          <div style="font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif; padding: 4px; min-width: 210px; color: #1e293b;">
            <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 6px;">
              <span style="font-family: monospace; font-weight: 700; font-size: 11px; color: #526B55;">${report.trackingId}</span>
              <span style="font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 9999px; background: ${pinColor}15; color: ${pinColor}; text-transform: uppercase;">${report.severity}</span>
            </div>
            <div style="font-weight: 600; font-size: 13px; color: #0f172a; margin-bottom: 3px;">${report.category}</div>
            <p style="font-size: 11px; color: #64748b; margin: 0 0 6px 0; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${report.description}</p>
            <div style="font-size: 10px; color: #94a3b8; margin-bottom: 8px;">
              📍 ${report.addressHint || `${report.latitude.toFixed(4)}, ${report.longitude.toFixed(4)}`}
            </div>
            <div style="text-align: right;">
              <button id="inspect-report-${report.id}" style="background: #526B55; color: white; border: none; padding: 4px 10px; font-size: 11px; font-weight: 600; border-radius: 6px; cursor: pointer;">
                Inspect Report &rarr;
              </button>
            </div>
          </div>
        `;

        infoWindow.setContent(contentString);
        infoWindow.open(map, marker);

        // Bind button click inside InfoWindow
        setTimeout(() => {
          const btn = document.getElementById(`inspect-report-${report.id}`);
          if (btn && onSelectPoint) {
            btn.onclick = () => onSelectPoint(report.id);
          }
        }, 100);
      });

      return marker;
    });

    markersRef.current = newMarkers;

    // Optional: fit bounds if multiple points
    if (newMarkers.length > 1 && !center) {
      const bounds = new google.maps.LatLngBounds();
      newMarkers.forEach((m) => {
        const pos = m.getPosition();
        if (pos) bounds.extend(pos);
      });
      map.fitBounds(bounds);
    }
  }, [points, isLoaded, onSelectPoint]);

  // Zero-Downtime Fallback to Leaflet if script or API fails
  if (hasError) {
    return (
      <LeafletMapProvider
        points={points}
        center={center}
        zoom={zoom}
        onSelectPoint={onSelectPoint}
        className={className}
      />
    );
  }

  return (
    <div className="relative w-full h-full">
      <div ref={mapRef} className={className} />
      {!isLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-50/80 dark:bg-neutral-900/80 backdrop-blur-xs text-xs text-civic-text-muted">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-civic-green animate-ping" />
            <span>Loading Google Maps Platform...</span>
          </div>
        </div>
      )}
    </div>
  );
};
