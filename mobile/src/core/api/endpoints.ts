/**
 * API Endpoints catalogue matching CivicSense Backend v1 specification.
 */
export const ENDPOINTS = {
  HEALTH: "/health",
  REPORTS: "/reports",
  REPORT_BY_ID: (identifier: string): string => `/reports/${encodeURIComponent(identifier)}`,
} as const;
