import { describe, it, expect } from 'vitest';
import { queryKeys } from '@/services/queryKeys';
import { MockReportRepository } from '@/services/repository/MockReportRepository';

describe('AI Operations & Query Keys', () => {
  const repo = new MockReportRepository();

  describe('queryKeys.ai', () => {
    it('generates consistent ai query keys', () => {
      expect(queryKeys.ai.all).toEqual(['ai']);
      expect(queryKeys.ai.detail('rep-123')).toEqual(['ai', 'report', 'rep-123']);
      expect(queryKeys.ai.events('rep-123')).toEqual(['ai', 'events', 'rep-123']);
      expect(queryKeys.ai.jobs({ stage: 'VISION_ANALYSIS' })).toEqual([
        'ai',
        'jobs',
        { stage: 'VISION_ANALYSIS' },
      ]);
      expect(queryKeys.ai.metrics()).toEqual(['ai', 'metrics']);
      expect(queryKeys.ai.health()).toEqual(['ai', 'health']);
    });
  });

  describe('MockReportRepository AI Methods', () => {
    it('returns honest AI health status', async () => {
      const health = await repo.getAIHealth();
      expect(health.status).toBe('available');
      expect(health.execution_mode).toBe('synchronous_prototype');
      expect(health.processor_name).toContain('Deterministic Demo Processor');
      expect(health.supported_stages.length).toBe(8);
    });

    it('returns structured AI metrics with display states', async () => {
      const metrics = await repo.getAIMetrics();
      expect(metrics.total_jobs).toBeDefined();
      expect(metrics.completed_jobs).toBeDefined();
      expect(metrics.active_jobs).toBeDefined();
      expect(metrics.avg_processing_latency_ms).toBeDefined();
      expect(metrics.time_window).toBe('ALL_TIME');
      expect(['AVAILABLE', 'INSUFFICIENT_DATA']).toContain(metrics.total_jobs.display_state);
    });

    it('returns jobs list with stages and review requirements', async () => {
      const jobsList = await repo.getAIJobs({ page: 1, pageSize: 10 });
      expect(jobsList.items.length).toBeGreaterThan(0);
      const firstJob = jobsList.items[0];
      expect(firstJob.id).toBeDefined();
      expect(firstJob.report_id).toBeDefined();
      expect(firstJob.current_stage).toBeDefined();
      expect(typeof firstJob.review_required).toBe('boolean');
    });

    it('triggers deterministic AI pipeline simulation', async () => {
      // Find a report to trigger
      const reports = await repo.getReports({ page: 1, pageSize: 5 });
      const targetReport = reports.items[0];

      const job = await repo.triggerAIProcess(targetReport.id);
      expect(job.report_id).toBe(targetReport.id);
      expect(job.status).toBe('COMPLETED');
      expect(job.processor_name).toContain('Deterministic Demo Processor');

      const aiResult = await repo.getReportAI(targetReport.id);
      expect(aiResult.latest_job?.id).toBe(job.id);
      expect(aiResult.ai_analysis).toBeDefined();
      expect(aiResult.ai_analysis?.confidence).toBeGreaterThan(0);
      expect(aiResult.disclaimer).toBeDefined();

      const events = await repo.getReportAIEvents(targetReport.id);
      expect(events.length).toBeGreaterThanOrEqual(6);
      expect(events[0].stage).toBe('INTAKE_VALIDATION');
    });
  });
});
