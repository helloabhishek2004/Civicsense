import {
  IssueItem,
  IssueListResult,
  PriorityBreakdown,
  CandidateMatchItem,
  MatchListResult,
  BackendReviewActionResponse,
} from '@/types/issues';
import { ReportListResult } from '@/types/models';
import { IIssueRepository, IssueFilterParams } from './IIssueRepository';
import { RepositoryError } from '../api/apiError';
import { SEED_REPORTS } from '../mock/seedReports';

export class MockIssueRepository implements IIssueRepository {
  private issues: IssueItem[] = [
    {
      id: 'iss-001',
      title: 'Pothole: Hazardous road crater on 5th Main',
      category: 'Pothole',
      status: 'OPEN',
      latitude: 12.9716,
      longitude: 77.5946,
      reportCount: 3,
      priorityScore: 78.5,
      priorityLevel: 'HIGH',
      priorityComputedAt: '2026-09-12T10:00:00Z',
      createdAt: '2026-09-10T08:00:00Z',
      updatedAt: '2026-09-12T10:00:00Z',
    },
    {
      id: 'iss-002',
      title: 'Garbage: Overflowing municipal dump near park',
      category: 'Garbage',
      status: 'OPEN',
      latitude: 12.975,
      longitude: 77.6,
      reportCount: 2,
      priorityScore: 45.2,
      priorityLevel: 'MEDIUM',
      priorityComputedAt: '2026-09-11T12:00:00Z',
      createdAt: '2026-09-09T09:30:00Z',
      updatedAt: '2026-09-11T12:00:00Z',
    },
  ];

  private matches: CandidateMatchItem[] = [
    {
      id: 'match-001',
      reportId: 'rep-002',
      issueId: 'iss-001',
      similarityScore: 0.68,
      status: 'PENDING',
      textSimilarity: 0.72,
      distanceMeters: 45.3,
      categoryMatch: 1.0,
      reasoning: [
        'Nearby location (45.3m away)',
        'Matching category: Pothole',
        'Semantic text similarity: 0.72',
      ],
      embeddingModelVersion: 'all-MiniLM-L6-v2-v1',
      createdAt: '2026-09-12T09:15:00Z',
    },
    {
      id: 'match-002',
      reportId: 'rep-003',
      issueId: 'iss-001',
      similarityScore: 0.58,
      status: 'PENDING',
      textSimilarity: 0.61,
      distanceMeters: 62.1,
      categoryMatch: 1.0,
      reasoning: [
        'Nearby location (62.1m away)',
        'Matching category: Pothole',
        'Semantic text similarity: 0.61',
      ],
      embeddingModelVersion: 'all-MiniLM-L6-v2-v1',
      createdAt: '2026-09-12T11:20:00Z',
    },
  ];

  async getIssues(params: IssueFilterParams = {}): Promise<IssueListResult> {
    let filtered = [...this.issues];
    if (params.category && params.category !== 'ALL') {
      filtered = filtered.filter((i) => i.category === params.category);
    }
    if (params.status && params.status !== 'ALL') {
      filtered = filtered.filter((i) => i.status === params.status);
    }

    const page = params.page || 1;
    const pageSize = params.pageSize || 10;
    const total = filtered.length;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    const start = (page - 1) * pageSize;
    const items = filtered.slice(start, start + pageSize);

    return {
      items,
      total,
      page,
      pageSize,
      totalPages,
    };
  }

  async getIssueById(id: string): Promise<IssueItem> {
    const issue = this.issues.find((i) => i.id === id);
    if (!issue) {
      throw new RepositoryError(`Issue ${id} not found`, 'NOT_FOUND', { statusCode: 404 });
    }
    return issue;
  }

  async getIssuePriority(id: string): Promise<PriorityBreakdown> {
    const issue = await this.getIssueById(id);
    return {
      issueId: issue.id,
      priorityScore: issue.priorityScore,
      priorityLevel: issue.priorityLevel,
      priorityComputedAt: issue.priorityComputedAt,
      breakdown: {
        severity_score: 35.0,
        report_volume_score: 24.5,
        unique_reporter_score: 9.0,
        recency_score: 6.0,
        persistence_score: 4.0,
        weighted_sum: 78.5,
        final_score_0_100: 78.5,
        priority_level: 'HIGH',
        formula_version: '1.0',
        report_count: 3,
        unique_reporter_count: 2,
        max_severity: 'HIGH',
      },
    };
  }

  async getIssueReports(id: string, page: number = 1, pageSize: number = 10): Promise<ReportListResult> {
    const linkedReports = SEED_REPORTS.filter((r) => r.issueId === id || id === 'iss-001');
    const total = linkedReports.length;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    const start = (page - 1) * pageSize;
    const items = linkedReports.slice(start, start + pageSize);

    return {
      items,
      total,
      page,
      pageSize,
      totalPages,
    };
  }

  async getPendingMatches(): Promise<MatchListResult> {
    const items = this.matches.filter((m) => m.status === 'PENDING');
    return {
      items,
      total: items.length,
    };
  }

  async approveMatch(
    matchId: string,
    reviewerId: string,
    notes?: string
  ): Promise<BackendReviewActionResponse> {
    if (!reviewerId || !reviewerId.trim()) {
      throw new RepositoryError(
        'A valid municipal reviewer ID is required to approve matches. Authentication credentials missing.',
        'UNAUTHORIZED',
        { statusCode: 401 }
      );
    }

    const match = this.matches.find((m) => m.id === matchId);
    if (!match) {
      throw new RepositoryError(`Match ${matchId} not found`, 'NOT_FOUND', { statusCode: 404 });
    }

    match.status = 'APPROVED';
    match.reviewerId = reviewerId.trim();
    match.reviewNotes = notes?.trim();
    match.reviewedAt = new Date().toISOString();

    return {
      match_id: match.id,
      status: 'APPROVED',
      report_id: match.reportId,
      issue_id: match.issueId,
      reviewer_id: reviewerId.trim(),
      reviewed_at: match.reviewedAt,
    };
  }

  async rejectMatch(
    matchId: string,
    reviewerId: string,
    notes?: string,
    linkToIssueId?: string
  ): Promise<BackendReviewActionResponse> {
    if (!reviewerId || !reviewerId.trim()) {
      throw new RepositoryError(
        'A valid municipal reviewer ID is required to reject matches. Authentication credentials missing.',
        'UNAUTHORIZED',
        { statusCode: 401 }
      );
    }

    const match = this.matches.find((m) => m.id === matchId);
    if (!match) {
      throw new RepositoryError(`Match ${matchId} not found`, 'NOT_FOUND', { statusCode: 404 });
    }

    match.status = 'REJECTED';
    match.reviewerId = reviewerId.trim();
    match.reviewNotes = notes?.trim();
    match.reviewedAt = new Date().toISOString();

    return {
      match_id: match.id,
      status: 'REJECTED',
      report_id: match.reportId,
      issue_id: linkToIssueId || null,
      reviewer_id: reviewerId.trim(),
      reviewed_at: match.reviewedAt,
    };
  }
}
