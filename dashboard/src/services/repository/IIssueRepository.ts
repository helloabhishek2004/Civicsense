import {
  IssueItem,
  IssueListResult,
  PriorityBreakdown,
  MatchListResult,
  BackendReviewActionResponse,
} from '@/types/issues';
import { ReportListResult } from '@/types/models';

export interface IssueFilterParams {
  sort?: string;
  order?: 'asc' | 'desc';
  category?: string;
  status?: string;
  page?: number;
  pageSize?: number;
}

export interface IIssueRepository {
  getIssues(params?: IssueFilterParams): Promise<IssueListResult>;
  getIssueById(id: string): Promise<IssueItem>;
  getIssuePriority(id: string): Promise<PriorityBreakdown>;
  getIssueReports(id: string, page?: number, pageSize?: number): Promise<ReportListResult>;
  getPendingMatches(): Promise<MatchListResult>;
  approveMatch(matchId: string, reviewerId: string, notes?: string): Promise<BackendReviewActionResponse>;
  rejectMatch(
    matchId: string,
    reviewerId: string,
    notes?: string,
    linkToIssueId?: string
  ): Promise<BackendReviewActionResponse>;
}
