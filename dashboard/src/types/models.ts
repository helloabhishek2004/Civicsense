import {
  BackendReportStatus,
  BackendSeverityLevel,
  BackendPriorityLevel,
  BackendVerificationDecision,
  BackendEvidenceRead,
  BackendAIAnalysisRead,
  BackendVerificationRead,
  BackendAssignmentStatus,
  BackendDepartmentRejectionReason,
  BackendAssignmentRead,
  BackendDepartmentWorkloadStats,
  BackendDepartmentRead,
} from './api/backendContracts';

export type {
  BackendReportStatus,
  BackendSeverityLevel,
  BackendPriorityLevel,
  BackendVerificationDecision,
  BackendAssignmentStatus,
  BackendDepartmentRejectionReason,
  BackendAssignmentRead,
  BackendDepartmentWorkloadStats,
  BackendDepartmentRead,
};

export type CivicCategory =
  | 'Pothole'
  | 'Garbage'
  | 'Water Leakage'
  | 'Streetlight'
  | 'Road Damage'
  | 'Drainage'
  | 'Infrastructure'
  | 'Other';

export type DepartmentName =
  | 'Roads & Bridges'
  | 'Solid Waste Management'
  | 'Water Supply & Sewerage'
  | 'Street Lighting & Electrical'
  | 'Town Planning & Enforcement'
  | 'General Public Works';

export type ClosureReason =
  | 'INVALID_REPORT'
  | 'DUPLICATE'
  | 'OUT_OF_SCOPE'
  | 'INSUFFICIENT_EVIDENCE'
  | 'RESOLVED_EXTERNALLY'
  | 'OTHER';

export type LifecyclePhase = 'ALL' | 'INTAKE' | 'VERIFICATION' | 'WORKFLOW' | 'RESOLUTION';

export interface AuditEvent {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  fromStatus?: BackendReportStatus;
  toStatus?: BackendReportStatus;
  notes?: string;
}

export interface InternalNote {
  id: string;
  author: string;
  authorRole: string;
  content: string;
  createdAt: string;
}

export interface SlaInfo {
  targetHours: number;
  remainingHours: number;
  isBreached: boolean;
  deadline: string;
}

export interface ReportItem {
  id: string;
  trackingId: string;
  status: BackendReportStatus;
  category: CivicCategory;
  description: string;
  citizenId?: string;
  citizenName?: string;
  citizenPhone?: string;
  citizenEmail?: string;
  citizenPostalCode?: string;
  latitude: number;
  longitude: number;
  addressHint?: string;
  departmentId?: string;
  department?: DepartmentName;
  assignedOfficer?: string;
  severity: BackendSeverityLevel;
  priority: BackendPriorityLevel;
  reassignmentRequired?: boolean;
  confidence?: number;
  evidenceAgreement?: number;
  reviewRequired: boolean;
  evidences: BackendEvidenceRead[];
  aiAnalyses: BackendAIAnalysisRead[];
  verifications: BackendVerificationRead[];
  assignments?: BackendAssignmentRead[];
  currentAssignment?: BackendAssignmentRead | null;
  edgeMetadata?: Record<string, unknown> | null;
  internalNotes?: InternalNote[];
  sla?: SlaInfo;
  closureReason?: ClosureReason;
  closureNotes?: string;
  auditTrail: AuditEvent[];
  issueId?: string;
  createdAt: string;
  updatedAt: string;
  resolvedAt?: string;
}

/**
 * Server-authoritative transition map strictly matching backend ReportLifecycleManager._TRANSITION_MAP
 */
export const ALLOWED_TRANSITIONS: Record<BackendReportStatus, readonly BackendReportStatus[]> = {
  SUBMITTED: ['AI_PROCESSING', 'VERIFIED', 'CLOSED'],
  AI_PROCESSING: ['AI_PROCESSED', 'VERIFICATION_REQUIRED'],
  AI_PROCESSED: ['VERIFICATION_REQUIRED', 'VERIFIED', 'PRIORITIZED', 'ASSIGNED', 'CLOSED'],
  VERIFICATION_REQUIRED: ['VERIFIED', 'CLOSED', 'ASSIGNED'],
  VERIFIED: ['PRIORITIZED', 'ASSIGNED', 'CLOSED'],
  PRIORITIZED: ['ASSIGNED', 'IN_PROGRESS'],
  ASSIGNED: ['IN_PROGRESS', 'PRIORITIZED'],
  IN_PROGRESS: ['RESOLVED', 'ASSIGNED'],
  RESOLVED: ['RESOLUTION_VERIFIED', 'IN_PROGRESS'],
  RESOLUTION_VERIFIED: ['CLOSED'],
  CLOSED: [],
} as const;

export interface ReportFilterParams {
  phase?: LifecyclePhase;
  status?: BackendReportStatus;
  category?: CivicCategory | 'ALL';
  severity?: BackendSeverityLevel | 'ALL';
  priority?: BackendPriorityLevel | 'ALL';
  department?: DepartmentName | 'ALL';
  reassignmentRequired?: boolean;
  issueId?: string;
  search?: string;
  page?: number;
  pageSize?: number;
  sortBy?:
    | 'createdAt'
    | 'priority'
    | 'severity'
    | 'updatedAt'
    | 'trackingId'
    | 'category'
    | 'status'
    | 'addressHint'
    | string;
  sortOrder?: 'asc' | 'desc';
}

export interface ReportListResult {
  items: ReportItem[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface ReportStats {
  totalReports: number;
  pendingReview: number;
  inProgress: number;
  resolvedToday: number;
  criticalIssues: number;
  avgResolutionDays: number;
  humanOverrideRate: number; // Defensible metric (e.g. 8.4%)
  aiAgreementRate: number; // Defensible metric (e.g. 91.2%)
}
