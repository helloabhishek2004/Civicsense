import { BackendSeverityLevel } from '@/types/api/backendContracts';
import { CivicCategory } from '@/types/models';

export interface MapPoint {
  id: string;
  trackingId: string;
  latitude: number;
  longitude: number;
  category: CivicCategory;
  severity: BackendSeverityLevel;
  description: string;
  addressHint?: string;
}

export interface MapProviderProps {
  points: MapPoint[];
  center: [number, number];
  zoom?: number;
  onSelectPoint?: (id: string) => void;
  className?: string;
}

export type MapProviderType = 'leaflet' | 'google-maps';
