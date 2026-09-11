/**
 * Canonical Backend API Contracts (mirroring FastAPI Pydantic schemas)
 */

export type BackendReportStatus =
  | 'SUBMITTED'
  | 'AI_PROCESSING'
  | 'AI_PROCESSED'
  | 'VERIFICATION_REQUIRED'
  | 'VERIFIED'
  | 'PRIORITIZED'
  | 'ASSIGNED'
  | 'IN_PROGRESS'
  | 'RESOLVED'
  | 'RESOLUTION_VERIFIED'
  | 'CLOSED';

export type BackendSeverityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type BackendPriorityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type BackendEvidenceType = 'IMAGE' | 'TEXT' | 'METADATA';
export type BackendVerificationDecision = 'CONFIRMED' | 'CORRECTED' | 'REJECTED' | 'DUPLICATE';

export interface BackendEvidenceRead {
  id: string;
  report_id: string;
  evidence_type: BackendEvidenceType;
  storage_uri: string;
  file_hash: string | null;
  mime_type: string | null;
  file_size_bytes: number | null;
  metadata_json?: Record<string, unknown> | null;
  created_at: string;
}

export interface BackendModelVersionRead {
  id: string;
  model_name: string;
  model_version: string;
  preprocessing_version?: string | null;
  embedding_model?: string | null;
  embedding_version?: string | null;
  created_at: string;
}

export interface BackendAIAnalysisRead {
  id: string;
  report_id: string;
  predicted_category?: string | null;
  confidence?: number | null;
  severity?: BackendSeverityLevel | null;
  priority?: BackendPriorityLevel | null;
  evidence_agreement?: number | null;
  review_required?: boolean | null;
  model_version?: BackendModelVersionRead | null;
  analysis_metadata?: Record<string, unknown> | null;
  created_at: string;
}

export interface BackendVerificationRead {
  id: string;
  report_id: string;
  decision: BackendVerificationDecision;
  reviewer_id?: string | null;
  verified_category?: string | null;
  verified_severity?: BackendSeverityLevel | null;
  notes?: string | null;
  created_at: string;
}

export interface BackendReportRead {
  id: string;
  tracking_id: string;
  status: BackendReportStatus;
  citizen_id?: string | null;
  latitude: number;
  longitude: number;
  address_hint?: string | null;
  description: string;
  issue_id?: string | null;
  evidences: BackendEvidenceRead[];
  ai_analyses: BackendAIAnalysisRead[];
  verifications: BackendVerificationRead[];
  created_at: string;
  updated_at: string;
}

export interface BackendReportListResponse {
  items: BackendReportRead[];
  total: number;
  page: number;
  page_size: number;
}

export interface BackendErrorResponse {
  error: {
    code: string;
    message: string;
    request_id?: string;
    details?: Array<{ loc: string[]; msg: string; type: string }>;
  };
}
