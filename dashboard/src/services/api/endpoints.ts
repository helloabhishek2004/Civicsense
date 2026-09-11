export const ENDPOINTS = {
  HEALTH: '/health',
  REPORTS: '/reports',
  REPORT_BY_ID: (id: string) => `/reports/${id}`,
  VERIFY_REPORT: (id: string) => `/reports/${id}/verify`,
  TRANSITION_REPORT: (id: string) => `/reports/${id}/transition`,
  REPORT_STATS: '/reports/stats',
  REPORT_AI_PROCESS: (id: string) => `/reports/${id}/ai/process`,
  REPORT_AI: (id: string) => `/reports/${id}/ai`,
  REPORT_AI_EVENTS: (id: string) => `/reports/${id}/ai/events`,
  AI_JOBS: '/ai/jobs',
  AI_METRICS: '/ai/metrics',
  AI_HEALTH: '/ai/health',
} as const;
