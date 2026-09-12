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

export type BackendAssignmentStatus = 'ASSIGNED' | 'IN_PROGRESS' | 'COMPLETED' | 'REJECTED';
export type BackendDepartmentRejectionReason =
  | 'OUT_OF_JURISDICTION'
  | 'INSUFFICIENT_ACCESS'
  | 'DUPLICATE_WORK_ORDER'
  | 'REQUIRES_MAJOR_BUDGET'
  | 'INSUFFICIENT_INFORMATION'
  | 'OTHER';

export interface BackendAssignmentRead {
  id: string;
  report_id: string;
  department_id?: string | null;
  department_name: string;
  assigned_by: string;
  assigned_to_officer?: string | null;
  status: BackendAssignmentStatus;
  rejection_reason?: BackendDepartmentRejectionReason | null;
  notes?: string | null;
  created_at: string;
  resolved_at?: string | null;
}

export interface BackendDepartmentWorkloadStats {
  department_id: string;
  department_name: string;
  department_code: string;
  total_assigned: number;
  pending_acknowledgment: number;
  in_progress: number;
  resolved: number;
  rejected_assignments: number;
  reassignment_required: number;
}

export interface BackendDepartmentRead {
  id: string;
  name: string;
  code: string;
  description?: string | null;
  head_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  sla_hours_default: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  stats?: BackendDepartmentWorkloadStats | null;
}

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
  category?: string | null;
  citizen_id?: string | null;
  citizen_name?: string | null;
  citizen_phone?: string | null;
  citizen_email?: string | null;
  citizen_postal_code?: string | null;
  latitude: number;
  longitude: number;
  address_hint?: string | null;
  description: string;
  issue_id?: string | null;
  department_id?: string | null;
  department?: string | null;
  assigned_officer?: string | null;
  priority?: BackendPriorityLevel | null;
  reassignment_required?: boolean;
  evidences: BackendEvidenceRead[];
  ai_analyses: BackendAIAnalysisRead[];
  verifications: BackendVerificationRead[];
  assignments?: BackendAssignmentRead[];
  current_assignment?: BackendAssignmentRead | null;
  edge_metadata?: Record<string, unknown> | null;
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
