import { ReportFilterParams } from '@/types/models';

export const queryKeys = {
  reports: {
    all: ['reports'] as const,
    lists: () => [...queryKeys.reports.all, 'list'] as const,
    list: (filters: ReportFilterParams) => [...queryKeys.reports.lists(), filters] as const,
    details: () => [...queryKeys.reports.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.reports.details(), id] as const,
    stats: () => [...queryKeys.reports.all, 'stats'] as const,
    mapPoints: () => [...queryKeys.reports.all, 'map'] as const,
    assignments: (id: string) => [...queryKeys.reports.all, 'assignments', id] as const,
  },
  departments: {
    all: ['departments'] as const,
    lists: () => [...queryKeys.departments.all, 'list'] as const,
    list: (activeOnly?: boolean) => [...queryKeys.departments.lists(), { activeOnly }] as const,
    details: () => [...queryKeys.departments.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.departments.details(), id] as const,
    stats: (id: string) => [...queryKeys.departments.all, 'stats', id] as const,
    reports: (id: string, filters?: Record<string, any>) =>
      [...queryKeys.departments.all, 'reports', id, filters || {}] as const,
  },
  system: {
    health: ['system', 'health'] as const,
  },
  ai: {
    all: ['ai'] as const,
    detail: (reportId: string) => ['ai', 'report', reportId] as const,
    events: (reportId: string) => ['ai', 'events', reportId] as const,
    jobs: (filters?: Record<string, any>) => ['ai', 'jobs', filters || {}] as const,
    metrics: () => ['ai', 'metrics'] as const,
    health: () => ['ai', 'health'] as const,
  },
};
