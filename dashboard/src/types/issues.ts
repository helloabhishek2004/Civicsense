import { BackendPriorityLevel, CivicCategory } from './models';

export interface BackendIssueRead {
  id: string;
  title: string;
  category: string;
  status: string;
  primary_latitude: number;
  primary_longitude: number;
  report_count: number;
  priority_score: number | null;
  priority_level: string | null;
  priority_computed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BackendIssueListResponse {
  items: BackendIssueRead[];
  total: number;
  page: number;
  page_size: number;
}

export interface PriorityBreakdownDetail {
  severity_score?: number;
  report_volume_score?: number;
  unique_reporter_score?: number;
  recency_score?: number;
  persistence_score?: number;
  weighted_sum?: number;
  final_score_0_100?: number;
  priority_level?: string;
  formula_version?: string;
  report_count?: number;
  unique_reporter_count?: number;
  latest_report_at?: string | null;
  issue_age_days?: number;
  max_severity?: string | null;
  [key: string]: unknown;
}

export interface BackendPriorityBreakdownRead {
  issue_id: string;
  priority_score: number | null;
  priority_level: string | null;
  priority_computed_at: string | null;
  breakdown: PriorityBreakdownDetail | null;
}

export interface BackendMatchRead {
  id: string;
  report_id: string;
  issue_id?: string | null;
  candidate_issue_id?: string;
  combined_score?: number;
  similarity_score?: number;
  action?: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  text_similarity: number;
  distance_meters: number;
  category_match: number;
  visual_similarity?: number;
  reasoning?: string[] | null;
  embedding_model_version?: string | null;
  reviewed_at?: string | null;
  reviewer_id?: string | null;
  review_notes?: string | null;
  created_at: string;
}

export interface BackendMatchListResponse {
  items: BackendMatchRead[];
  total: number;
}

export interface BackendReviewActionResponse {
  match_id: string;
  status: string;
  report_id: string;
  issue_id?: string | null;
  reviewer_id: string;
  reviewed_at?: string | null;
}

// Domain Model Types for Dashboard

export interface IssueItem {
  id: string;
  title: string;
  category: CivicCategory;
  status: string;
  latitude: number;
  longitude: number;
  reportCount: number;
  priorityScore: number | null;
  priorityLevel: BackendPriorityLevel | null;
  priorityComputedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface IssueListResult {
  items: IssueItem[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface PriorityBreakdown {
  issueId: string;
  priorityScore: number | null;
  priorityLevel: BackendPriorityLevel | null;
  priorityComputedAt: string | null;
  breakdown: PriorityBreakdownDetail | null;
}

export interface CandidateMatchItem {
  id: string;
  reportId: string;
  issueId: string;
  similarityScore: number;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  textSimilarity: number;
  distanceMeters: number;
  categoryMatch: number;
  visualSimilarity?: number;
  reasoning?: string[];
  embeddingModelVersion?: string;
  reviewedAt?: string;
  reviewerId?: string;
  reviewNotes?: string;
  createdAt: string;
}

export interface MatchListResult {
  items: CandidateMatchItem[];
  total: number;
}

export interface ApproveMatchPayload {
  reviewer_id: string;
  notes?: string;
}

export interface RejectMatchPayload {
  reviewer_id: string;
  notes?: string;
  link_to_issue_id?: string;
}
