/**
 * Environment configuration for CivicSense Mobile.
 * Configurable via Expo environment variables without editing code.
 */
export const ENV = {
  // Default to 10.0.2.2 for Android Emulator, localhost for iOS simulator/web
  API_BASE_URL: process.env.EXPO_PUBLIC_API_BASE_URL || "http://10.0.2.2:8000/api/v1",
  TIMEOUT_MS: 10000,
  APP_VERSION: "0.1.0",
} as const;
