import { describe, it, expect } from 'vitest';
import { queryKeys } from '@/services/queryKeys';

describe('Query Keys Factory', () => {
  it('generates consistent reports root key', () => {
    expect(queryKeys.reports.all).toEqual(['reports']);
  });

  it('generates list keys parameterized by filter', () => {
    const filters = { page: 1, pageSize: 10, category: 'Pothole' as const };
    expect(queryKeys.reports.list(filters)).toEqual([
      'reports',
      'list',
      { page: 1, pageSize: 10, category: 'Pothole' },
    ]);
  });

  it('generates detail key parameterized by ID', () => {
    expect(queryKeys.reports.detail('rep-001')).toEqual([
      'reports',
      'detail',
      'rep-001',
    ]);
  });

  it('generates stats key', () => {
    expect(queryKeys.reports.stats()).toEqual(['reports', 'stats']);
  });

  it('generates mapPoints key', () => {
    expect(queryKeys.reports.mapPoints()).toEqual(['reports', 'map']);
  });

  it('generates issue query keys', () => {
    expect(queryKeys.issues.all).toEqual(['issues']);
    expect(queryKeys.issues.detail('iss-123')).toEqual(['issues', 'detail', 'iss-123']);
    expect(queryKeys.issues.priority('iss-123')).toEqual(['issues', 'priority', 'iss-123']);
    expect(queryKeys.issues.reports('iss-123', 1, 10)).toEqual(['issues', 'reports', 'iss-123', { page: 1, pageSize: 10 }]);
  });

  it('generates candidate matches query keys', () => {
    expect(queryKeys.matches.all).toEqual(['matches']);
    expect(queryKeys.matches.pending()).toEqual(['matches', 'pending']);
  });
});
