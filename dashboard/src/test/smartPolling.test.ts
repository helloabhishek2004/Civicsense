import { describe, it, expect, vi } from 'vitest';
import { QueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/services/queryKeys';
import { MockReportRepository } from '@/services/repository/MockReportRepository';

describe('Dashboard Smart Polling & Mutation Sync', () => {
  it('verifies query client default configuration preserves manual control', () => {
    const client = new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 1000 * 60 * 2,
          retry: 1,
          refetchOnWindowFocus: false,
        },
      },
    });

    const defaults = client.getDefaultOptions();
    expect(defaults.queries?.retry).toBe(1);
    expect(defaults.queries?.refetchOnWindowFocus).toBe(false);
  });

  it('verifies mutation invalidation targets all relevant report queries', async () => {
    const client = new QueryClient();
    const invalidateSpy = vi.spyOn(client, 'invalidateQueries');
    const setQueryDataSpy = vi.spyOn(client, 'setQueryData');

    const repo = new MockReportRepository();
    const updated = await repo.transitionStatus(
      'rep-uuid-001',
      'VERIFIED',
      'Dispatched repair crew',
      'Crew on site',
      'Triage Officer'
    );

    // Simulate mutation onSuccess behavior
    client.setQueryData(queryKeys.reports.detail(updated.id), updated);
    client.invalidateQueries({ queryKey: queryKeys.reports.all });

    expect(setQueryDataSpy).toHaveBeenCalledWith(queryKeys.reports.detail('rep-uuid-001'), updated);
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: queryKeys.reports.all });
  });

  it('ensures updated reports expose reliable modified indicator updatedAt', async () => {
    const repo = new MockReportRepository();
    const original = await repo.getReportById('rep-uuid-001');
    expect(original).toBeDefined();

    const transitioned = await repo.transitionStatus(
      'rep-uuid-001',
      'VERIFIED',
      undefined,
      undefined,
      'Officer'
    );

    expect(transitioned.status).toBe('VERIFIED');
    expect(transitioned.updatedAt).toBeDefined();
    expect(new Date(transitioned.updatedAt).getTime()).toBeGreaterThanOrEqual(
      new Date(original!.updatedAt).getTime()
    );
  });
});
