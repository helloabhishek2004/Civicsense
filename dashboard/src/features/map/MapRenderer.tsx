import React from 'react';
import { GoogleMapsProvider } from './GoogleMapsProvider';
import { LeafletMapProvider } from './LeafletMapProvider';
import { MapProviderProps, MapProviderType } from './types';
import { isGoogleMapsAvailable } from './GoogleMapsContract';

export interface MapRendererProps extends MapProviderProps {
  preferredProvider?: MapProviderType;
}

export const MapRenderer: React.FC<MapRendererProps> = ({
  preferredProvider = 'google-maps',
  ...props
}) => {
  // If google maps is requested and API key is present, render Google Maps
  if (preferredProvider === 'google-maps' && isGoogleMapsAvailable()) {
    return <GoogleMapsProvider {...props} />;
  }

  // Fallback to Leaflet
  return <LeafletMapProvider {...props} />;
};

