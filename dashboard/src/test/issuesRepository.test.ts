import { describe, it, expect, vi } from 'vitest';
import { MockIssueRepository } from '@/services/repository/MockIssueRepository';
import { ApiIssueRepository } from '@/services/repository/ApiIssueRepository';
import { apiClient } from '@/services/api/apiClient';
import { RepositoryError } from '@/services/api/apiError';

describe('Issue Repositories & Reviewer Security', () => {
  describe('MockIssueRepository', () => {
    const repo = new MockIssueRepository();

    it('returns seed issues list', async () => {
      const result = await repo.getIssues();
      expect(result.items.length).toBeGreaterThan(0);
      expect(result.total).toBe(result.items.length);
      expect(result.items[0].id).toBe('iss-001');
      expect(result.items[0].category).toBe('Pothole');
    });

    it('returns issue by id or throws NOT_FOUND', async () => {
      const issue = await repo.getIssueById('iss-001');
      expect(issue.id).toBe('iss-001');
      expect(issue.reportCount).toBe(3);

      await expect(repo.getIssueById('non-existent-id')).rejects.toThrow(RepositoryError);
      try {
        await repo.getIssueById('non-existent-id');
      } catch (err) {
        expect((err as RepositoryError).kind).toBe('NOT_FOUND');
        expect((err as RepositoryError).statusCode).toBe(404);
      }
    });

    it('returns priority breakdown for an issue', async () => {
      const priority = await repo.getIssuePriority('iss-001');
      expect(priority.issueId).toBe('iss-001');
      expect(priority.priorityScore).toBe(78.5);
      expect(priority.priorityLevel).toBe('HIGH');
      expect(priority.breakdown).toBeDefined();
      expect(priority.breakdown?.severity_score).toBe(35.0);
    });

    it('returns linked reports for an issue', async () => {
      const result = await repo.getIssueReports('iss-001', 1, 10);
      expect(result.items.length).toBeGreaterThan(0);
      expect(result.total).toBeGreaterThan(0);
    });

    it('returns pending candidate matches', async () => {
      const result = await repo.getPendingMatches();
      expect(result.items.length).toBeGreaterThan(0);
      expect(result.items.every((m) => m.status === 'PENDING')).toBe(true);
    });

    it('fails closed when approving match without reviewer identity', async () => {
      await expect(repo.approveMatch('match-001', '')).rejects.toThrow(RepositoryError);
      await expect(repo.approveMatch('match-001', '   ')).rejects.toThrow(RepositoryError);

      try {
        await repo.approveMatch('match-001', '');
      } catch (err) {
        expect((err as RepositoryError).kind).toBe('UNAUTHORIZED');
        expect((err as RepositoryError).statusCode).toBe(401);
      }
    });

    it('approves match with valid reviewer identity', async () => {
      const res = await repo.approveMatch('match-001', 'BADGE-1234', 'Verified identical defect');
      expect(res.status).toBe('APPROVED');
      expect(res.reviewer_id).toBe('BADGE-1234');
    });

    it('fails closed when rejecting match without reviewer identity', async () => {
      await expect(repo.rejectMatch('match-002', '')).rejects.toThrow(RepositoryError);
      await expect(repo.rejectMatch('match-002', '   ')).rejects.toThrow(RepositoryError);
    });

    it('rejects match with valid reviewer identity and optional alternate issue', async () => {
      const res = await repo.rejectMatch('match-002', 'BADGE-1234', 'Different location', 'iss-002');
      expect(res.status).toBe('REJECTED');
      expect(res.reviewer_id).toBe('BADGE-1234');
    });
  });

  describe('ApiIssueRepository Reviewer Security Rule', () => {
    const apiRepo = new ApiIssueRepository();

    it('fails closed and throws 401 UNAUTHORIZED on empty reviewer ID for approve', async () => {
      await expect(apiRepo.approveMatch('match-abc', '')).rejects.toThrow(RepositoryError);
      await expect(apiRepo.approveMatch('match-abc', '  ')).rejects.toThrow(RepositoryError);

      try {
        await apiRepo.approveMatch('match-abc', '');
      } catch (err) {
        expect((err as RepositoryError).kind).toBe('UNAUTHORIZED');
        expect((err as RepositoryError).statusCode).toBe(401);
      }
    });

    it('fails closed and throws 401 UNAUTHORIZED on empty reviewer ID for reject', async () => {
      await expect(apiRepo.rejectMatch('match-abc', '')).rejects.toThrow(RepositoryError);
      await expect(apiRepo.rejectMatch('match-abc', '  ')).rejects.toThrow(RepositoryError);

      try {
        await apiRepo.rejectMatch('match-abc', '');
      } catch (err) {
        expect((err as RepositoryError).kind).toBe('UNAUTHORIZED');
        expect((err as RepositoryError).statusCode).toBe(401);
      }
    });

    it('forwards X-Reviewer-ID header and reviewer_id in payload when authenticated', async () => {
      const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
        match_id: 'match-abc',
        status: 'APPROVED',
        report_id: 'rep-123',
        issue_id: 'iss-456',
        reviewer_id: 'OFFICER-789',
        reviewed_at: '2026-03-31T12:00:00Z',
      });

      const res = await apiRepo.approveMatch('match-abc', 'OFFICER-789', 'Looks identical');
      expect(postSpy).toHaveBeenCalledWith(
        '/matches/match-abc/approve',
        { reviewer_id: 'OFFICER-789', notes: 'Looks identical' },
        { headers: { 'X-Reviewer-ID': 'OFFICER-789' } }
      );
      expect(res.status).toBe('APPROVED');

      postSpy.mockRestore();
    });

    it('correctly maps backend MatchRead fields (issue_id and combined_score)', async () => {
      const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValueOnce({
        items: [
          {
            id: 'match-xyz',
            report_id: 'rep-111',
            issue_id: 'iss-222',
            action: 'CANDIDATE',
            status: 'PENDING',
            combined_score: 0.654,
            text_similarity: 0.75,
            distance_meters: 55.2,
            category_match: 1.0,
            reasoning: ['Near location', 'Matching category'],
            embedding_model_version: 'all-MiniLM-L6-v2',
            created_at: '2026-03-31T10:00:00Z',
          },
        ],
        total: 1,
      });

      const result = await apiRepo.getPendingMatches();
      expect(result.items.length).toBe(1);
      expect(result.items[0].issueId).toBe('iss-222');
      expect(result.items[0].similarityScore).toBe(0.654);
      expect(result.items[0].reasoning?.length).toBe(2);

      getSpy.mockRestore();
    });

    it('gracefully handles missing or null issue_id in match response', async () => {
      const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValueOnce({
        items: [
          {
            id: 'match-unlinked',
            report_id: 'rep-333',
            issue_id: null,
            action: 'NEW_ISSUE',
            status: 'PENDING',
            combined_score: 0.12,
            text_similarity: 0.1,
            distance_meters: 999.0,
            category_match: 0.0,
            created_at: '2026-03-31T10:00:00Z',
          },
        ],
        total: 1,
      });

      const result = await apiRepo.getPendingMatches();
      expect(result.items[0].issueId).toBe('');
      expect(result.items[0].similarityScore).toBe(0.12);

      getSpy.mockRestore();
    });
  });
});