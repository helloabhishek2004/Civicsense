/**
 * CivicSense Google Maps Platform Migration Contract
 *
 * This contract establishes the operational interface for migrating the municipal
 * geospatial visualization layer from OpenStreetMap/Leaflet to Google Maps Platform JavaScript API v3.
 *
 * Architectural Invariants:
 * 1. Zero Downtime: If VITE_GOOGLE_MAPS_API_KEY is missing or the script fails to load,
 *    the system automatically falls back to LeafletMapProvider without user disruption.
 * 2. Vector Map Capabilities: Google Maps allows AdvancedMarkerElement, custom pin SVGs,
 *    and municipal ward boundary GeoJSON overlays.
 * 3. Marker Clustering: For large-scale defect deployments (>500 markers), use
 *    @googlemaps/markerclusterer to maintain 60fps rendering.
 */
export interface GoogleMapsConfiguration {
  apiKey: string;
  mapId?: string;
  libraries: ('places' | 'geometry' | 'marker')[];
  defaultCenter: { lat: number; lng: number };
  defaultZoom: number;
}

export interface GoogleMapsProviderContract {
  isConfigured: () => boolean;
  loadScript: () => Promise<boolean>;
}

import { env } from '@/core/config/env';

export const isGoogleMapsAvailable = (): boolean => {
  const apiKey = env.googleMapsApiKey || (import.meta as any).env?.VITE_GOOGLE_MAPS_API_KEY;
  return typeof apiKey === 'string' && apiKey.trim().length > 0;
};
