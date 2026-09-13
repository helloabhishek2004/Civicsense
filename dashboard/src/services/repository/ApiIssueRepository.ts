import {
  IssueItem,
  IssueListResult,
  PriorityBreakdown,
  CandidateMatchItem,
  MatchListResult,
  BackendIssueRead,
  BackendIssueListResponse,
  BackendPriorityBreakdownRead,
  BackendMatchRead,
  BackendMatchListResponse,
  BackendReviewActionResponse,
  ApproveMatchPayload,
  RejectMatchPayload,
} from '@/types/issues';
import { ReportListResult, BackendPriorityLevel } from '@/types/models';
import { BackendReportListResponse } from '@/types/api/backendContracts';
import { IIssueRepository, IssueFilterParams } from './IIssueRepository';
import { apiClient } from '../api/apiClient';
import { ENDPOINTS } from '../api/endpoints';
import { normalizeCategory, mapBackendToReportItem } from './ApiReportRepository';
import { normalizeIsoUtc } from '@/core/utils/dateUtils';
import { RepositoryError } from '../api/apiError';

export function mapBackendToIssueItem(raw: BackendIssueRead): IssueItem {
  return {
    id: raw.id,
    title: raw.title,
    category: normalizeCategory(raw.category),
    status: raw.status,
    latitude: raw.primary_latitude,
    longitude: raw.primary_longitude,
    reportCount: raw.report_count,
    priorityScore: raw.priority_score,
    priorityLevel: (raw.priority_level as BackendPriorityLevel) || null,
    priorityComputedAt: raw.priority_computed_at ? normalizeIsoUtc(raw.priority_computed_at) : null,
    createdAt: normalizeIsoUtc(raw.created_at),
    updatedAt: normalizeIsoUtc(raw.updated_at),
  };
}

export function mapBackendToMatchItem(raw: BackendMatchRead): CandidateMatchItem {
  return {
    id: raw.id,
    reportId: raw.report_id,
    issueId: raw.issue_id || raw.candidate_issue_id || '',
    similarityScore: raw.combined_score ?? raw.similarity_score ?? 0,
    status: raw.status,
    textSimilarity: raw.text_similarity,
    distanceMeters: raw.distance_meters,
    categoryMatch: raw.category_match,
    reasoning: raw.reasoning || undefined,
    embeddingModelVersion: raw.embedding_model_version || undefined,
    reviewedAt: raw.reviewed_at ? normalizeIsoUtc(raw.reviewed_at) : undefined,
    reviewerId: raw.reviewer_id || undefined,
    reviewNotes: raw.review_notes || undefined,
    createdAt: normalizeIsoUtc(raw.created_at),
  };
}

export class ApiIssueRepository implements IIssueRepository {
  async getIssues(params: IssueFilterParams = {}): Promise<IssueListResult> {
    const queryParams: Record<string, string | number | boolean | undefined> = {
      page: params.page || 1,
      page_size: params.pageSize || 10,
    };
    if (params.sort) queryParams.sort = params.sort;
    if (params.order) queryParams.order = params.order;
    if (params.category && params.category !== 'ALL') queryParams.category = params.category;
    if (params.status && params.status !== 'ALL') queryParams.status = params.status;

    const res = await apiClient.get<BackendIssueListResponse>(ENDPOINTS.ISSUES, {
      params: queryParams,
    });

    const items = res.items.map(mapBackendToIssueItem);
    const total = res.total;
    const page = res.page;
    const pageSize = res.page_size;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));

    return {
      items,
      total,
      page,
      pageSize,
      totalPages,
    };
  }

  async getIssueById(id: string): Promise<IssueItem> {
    const raw = await apiClient.get<BackendIssueRead>(ENDPOINTS.ISSUE_BY_ID(id));
    return mapBackendToIssueItem(raw);
  }

  async getIssuePriority(id: string): Promise<PriorityBreakdown> {
    const raw = await apiClient.get<BackendPriorityBreakdownRead>(ENDPOINTS.ISSUE_PRIORITY(id));
    return {
      issueId: raw.issue_id,
      priorityScore: raw.priority_score,
      priorityLevel: (raw.priority_level as BackendPriorityLevel) || null,
      priorityComputedAt: raw.priority_computed_at ? normalizeIsoUtc(raw.priority_computed_at) : null,
      breakdown: raw.breakdown,
    };
  }

  async getIssueReports(id: string, page: number = 1, pageSize: number = 10): Promise<ReportListResult> {
    const res = await apiClient.get<BackendReportListResponse>(ENDPOINTS.ISSUE_REPORTS(id), {
      params: {
        page,
        page_size: pageSize,
      },
    });

    const items = res.items.map(mapBackendToReportItem);
    const total = res.total;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));

    return {
      items,
      total,
      page: res.page,
      pageSize: res.page_size,
      totalPages,
    };
  }

  async getPendingMatches(): Promise<MatchListResult> {
    const res = await apiClient.get<BackendMatchListResponse>(ENDPOINTS.MATCHES_PENDING);
    const items = res.items.map(mapBackendToMatchItem);
    return {
      items,
      total: res.total,
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

    const payload: ApproveMatchPayload = {
      reviewer_id: reviewerId.trim(),
      notes: notes?.trim() || undefined,
    };

    return apiClient.post<BackendReviewActionResponse>(
      ENDPOINTS.MATCH_APPROVE(matchId),
      payload,
      {
        headers: {
          'X-Reviewer-ID': reviewerId.trim(),
        },
      }
    );
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

    const payload: RejectMatchPayload = {
      reviewer_id: reviewerId.trim(),
      notes: notes?.trim() || undefined,
      link_to_issue_id: linkToIssueId?.trim() || undefined,
    };

    return apiClient.post<BackendReviewActionResponse>(
      ENDPOINTS.MATCH_REJECT(matchId),
      payload,
      {
        headers: {
          'X-Reviewer-ID': reviewerId.trim(),
        },
      }
    );
  }
}
