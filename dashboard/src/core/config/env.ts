/**
 * Strict Environment Configuration & Startup Validator
 * Enforces explicit data mode and API configuration.
 */

export type DataMode = 'api' | 'mock';

interface EnvConfig {
  dataMode: DataMode;
  apiBaseUrl: string;
  mapTileUrl: string;
  mapAttribution: string;
  googleMapsApiKey: string;
  isMock: boolean;
  isApi: boolean;
}

function getValidatedEnv(): EnvConfig {
  const rawMode = (import.meta.env.VITE_DATA_MODE || 'mock').trim().toLowerCase();

  if (rawMode !== 'api' && rawMode !== 'mock') {
    throw new Error(
      `[CivicSense Config Error] Invalid VITE_DATA_MODE: "${rawMode}". ` +
        `Allowed values are strictly "api" or "mock". Check your .env file.`
    );
  }

  const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace(
    /\/+$/,
    ''
  );

  const mapTileUrl =
    import.meta.env.VITE_MAP_TILE_URL ||
    'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

  const mapAttribution =
    import.meta.env.VITE_MAP_ATTRIBUTION ||
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

  const googleMapsApiKey = (
    import.meta.env.VITE_GOOGLE_MAPS_API_KEY ||
    'AIzaSyBfu83qLayQRq4xrmzQStrcV7vXMSIm0Mw'
  ).trim();

  return {
    dataMode: rawMode as DataMode,
    apiBaseUrl,
    mapTileUrl,
    mapAttribution,
    googleMapsApiKey,
    isMock: rawMode === 'mock',
    isApi: rawMode === 'api',
  };
}

export const env: EnvConfig = getValidatedEnv();
