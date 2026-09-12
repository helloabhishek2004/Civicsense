import {
  ReportItem,
  ReportFilterParams,
  ReportListResult,
  ReportStats,
  DepartmentName,
  CivicCategory,
} from '@/types/models';
import {
  BackendReportStatus,
  BackendSeverityLevel,
  BackendPriorityLevel,
  BackendVerificationDecision,
  BackendAssignmentRead,
  BackendDepartmentRejectionReason,
} from '@/types/api/backendContracts';
import {
  AIJob,
  AIJobEvent,
  AIJobListResult,
  ReportAIResult,
  AIMetrics,
  AIHealthStatus,
} from '@/types/ai';

export interface IReportRepository {
  getReports(params?: ReportFilterParams): Promise<ReportListResult>;
  getReportById(id: string): Promise<ReportItem>;
  getStats(): Promise<ReportStats>;
  getMapPoints(): Promise<ReportItem[]>;
  transitionStatus(
    id: string,
    nextStatus: BackendReportStatus,
    reason?: string,
    notes?: string,
    actor?: string
  ): Promise<ReportItem>;
  verifyReport(
    id: string,
    decision: BackendVerificationDecision,
    verifiedCategory?: CivicCategory,
    verifiedSeverity?: BackendSeverityLevel,
    notes?: string,
    actor?: string
  ): Promise<ReportItem>;
  assignDepartment(
    id: string,
    department: DepartmentName,
    assignedOfficer?: string,
    actor?: string
  ): Promise<ReportItem>;
  acknowledgeJob(
    id: string,
    assignedOfficer?: string,
    notes?: string
  ): Promise<ReportItem>;
  completeJob(
    id: string,
    resolverNotes: string,
    resolvedBy?: string
  ): Promise<ReportItem>;
  rejectJob(
    id: string,
    rejectionReason: BackendDepartmentRejectionReason,
    notes: string,
    suggestedDepartment?: string
  ): Promise<ReportItem>;
  getReportAssignments(id: string): Promise<BackendAssignmentRead[]>;
  prioritizeReport(
    id: string,
    priority: BackendPriorityLevel,
    actor?: string
  ): Promise<ReportItem>;
  addInternalNote(
    id: string,
    content: string,
    author: string,
    authorRole: string
  ): Promise<ReportItem>;
  triggerAIProcess(id: string): Promise<AIJob>;
  getReportAI(id: string): Promise<ReportAIResult>;
  getReportAIEvents(id: string): Promise<AIJobEvent[]>;
  getAIJobs(params?: {
    status?: string;
    stage?: string;
    page?: number;
    pageSize?: number;
  }): Promise<AIJobListResult>;
  getAIMetrics(): Promise<AIMetrics>;
  getAIHealth(): Promise<AIHealthStatus>;
}
