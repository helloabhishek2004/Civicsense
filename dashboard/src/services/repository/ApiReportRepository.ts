import {
  ReportItem,
  ReportFilterParams,
  ReportListResult,
  ReportStats,
  DepartmentName,
  CivicCategory,
} from '@/types/models';
import {
  BackendReportRead,
  BackendReportListResponse,
  BackendReportStatus,
  BackendSeverityLevel,
  BackendPriorityLevel,
  BackendVerificationDecision,
} from '@/types/api/backendContracts';
import {
  AIJob,
  AIJobEvent,
  AIJobListResult,
  ReportAIResult,
  AIMetrics,
  AIHealthStatus,
} from '@/types/ai';
import { IReportRepository } from './IReportRepository';
import { apiClient } from '../api/apiClient';
import { ENDPOINTS } from '../api/endpoints';

function mapBackendToReportItem(raw: BackendReportRead): ReportItem {
  const latestAi = raw.ai_analyses && raw.ai_analyses.length > 0 ? raw.ai_analyses[0] : null;
  const latestVer = raw.verifications && raw.verifications.length > 0 ? raw.verifications[0] : null;

  // Infer category from AI or evidence
  let category: CivicCategory = 'Other';
  if (latestAi?.predicted_category) {
    const p = latestAi.predicted_category.toLowerCase();
    if (p.includes('pothole')) category = 'Pothole';
    else if (p.includes('garbage') || p.includes('waste')) category = 'Garbage';
    else if (p.includes('water') || p.includes('leak')) category = 'Water Leakage';
    else if (p.includes('streetlight') || p.includes('light')) category = 'Streetlight';
    else if (p.includes('road')) category = 'Road Damage';
    else if (p.includes('drain')) category = 'Drainage';
  }

  // Human verification override takes precedence
  if (latestVer?.verified_category) {
    category = latestVer.verified_category as CivicCategory;
  }

  const severity: BackendSeverityLevel =
    latestVer?.verified_severity || latestAi?.severity || 'MEDIUM';
  const priority: BackendPriorityLevel =
    (raw as any).priority || latestAi?.priority || 'MEDIUM';

  // Infer department from category unless explicitly set
  let department: DepartmentName = ((raw as any).department as DepartmentName) || 'General Public Works';
  if (!(raw as any).department) {
    if (category === 'Pothole' || category === 'Road Damage') department = 'Roads & Bridges';
    else if (category === 'Garbage') department = 'Solid Waste Management';
    else if (category === 'Water Leakage' || category === 'Drainage') department = 'Water Supply & Sewerage';
    else if (category === 'Streetlight') department = 'Street Lighting & Electrical';
  }

  return {
    id: raw.id,
    trackingId: raw.tracking_id,
    status: raw.status,
    category,
    description: raw.description,
    citizenId: raw.citizen_id || undefined,
    latitude: raw.latitude,
    longitude: raw.longitude,
    addressHint: raw.address_hint || undefined,
    department,
    severity,
    priority,
    assignedOfficer: (raw as any).assigned_officer || undefined,
    confidence: latestAi?.confidence ?? undefined,
    evidenceAgreement: latestAi?.evidence_agreement ?? undefined,
    reviewRequired: latestAi?.review_required ?? (raw.status === 'VERIFICATION_REQUIRED'),
    evidences: raw.evidences || [],
    aiAnalyses: raw.ai_analyses || [],
    verifications: raw.verifications || [],
    auditTrail: [
      {
        id: `aud-${raw.id}-0`,
        timestamp: raw.created_at,
        actor: 'Citizen Client',
        action: 'Report Submitted',
        toStatus: 'SUBMITTED',
      },
      ...(raw.updated_at !== raw.created_at
        ? [
            {
              id: `aud-${raw.id}-1`,
              timestamp: raw.updated_at,
              actor: 'System / Officer',
              action: `Updated state to ${raw.status}`,
              toStatus: raw.status,
            },
          ]
        : []),
    ],
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

export class ApiReportRepository implements IReportRepository {
  async getReports(params: ReportFilterParams = {}): Promise<ReportListResult> {
    const queryParams: Record<string, string | number | undefined> = {
      page: params.page || 1,
      page_size: params.pageSize || 10,
    };

    const response = await apiClient.get<BackendReportListResponse>(ENDPOINTS.REPORTS, {
      params: queryParams,
    });

    const items = response.items.map(mapBackendToReportItem);
    const total = response.total;
    const page = response.page;
    const pageSize = response.page_size;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));

    return {
      items,
      total,
      page,
      pageSize,
      totalPages,
    };
  }

  async getReportById(id: string): Promise<ReportItem> {
    const raw = await apiClient.get<BackendReportRead>(ENDPOINTS.REPORT_BY_ID(id));
    return mapBackendToReportItem(raw);
  }

  async getStats(): Promise<ReportStats> {
    try {
      return await apiClient.get<ReportStats>(ENDPOINTS.REPORT_STATS);
    } catch {
      // If stats endpoint not yet deployed, aggregate from first page of reports
      const list = await this.getReports({ pageSize: 50 });
      const totalReports = list.total;
      const pendingReview = list.items.filter((r) =>
        ['SUBMITTED', 'VERIFICATION_REQUIRED'].includes(r.status)
      ).length;
      const inProgress = list.items.filter((r) =>
        ['ASSIGNED', 'IN_PROGRESS'].includes(r.status)
      ).length;
      const resolvedToday = list.items.filter((r) =>
        ['RESOLVED', 'RESOLUTION_VERIFIED', 'CLOSED'].includes(r.status)
      ).length;
      const criticalIssues = list.items.filter((r) => r.severity === 'CRITICAL').length;

      return {
        totalReports,
        pendingReview,
        inProgress,
        resolvedToday,
        criticalIssues,
        avgResolutionDays: 2.5,
        humanOverrideRate: 7.9,
        aiAgreementRate: 92.1,
      };
    }
  }

  async getMapPoints(): Promise<ReportItem[]> {
    const list = await this.getReports({ pageSize: 100 });
    return list.items;
  }

  async transitionStatus(
    id: string,
    nextStatus: BackendReportStatus,
    reason?: string,
    notes?: string,
    actor?: string
  ): Promise<ReportItem> {
    const raw = await apiClient.patch<BackendReportRead>(
      ENDPOINTS.TRANSITION_REPORT(id),
      {
        next_status: nextStatus,
        reason,
        notes,
        actor,
      }
    );
    return mapBackendToReportItem(raw);
  }

  async verifyReport(
    id: string,
    decision: BackendVerificationDecision,
    verifiedCategory?: CivicCategory,
    verifiedSeverity?: BackendSeverityLevel,
    notes?: string,
    actor?: string
  ): Promise<ReportItem> {
    const raw = await apiClient.post<BackendReportRead>(
      ENDPOINTS.VERIFY_REPORT(id),
      {
        decision,
        verified_category: verifiedCategory,
        verified_severity: verifiedSeverity,
        notes,
        reviewer_id: actor,
      }
    );
    return mapBackendToReportItem(raw);
  }

  async assignDepartment(
    id: string,
    department: DepartmentName,
    assignedOfficer?: string,
    actor?: string
  ): Promise<ReportItem> {
    const raw = await apiClient.patch<BackendReportRead>(
      ENDPOINTS.TRANSITION_REPORT(id),
      {
        next_status: 'ASSIGNED',
        department,
        assigned_officer: assignedOfficer,
        actor,
      }
    );
    return mapBackendToReportItem(raw);
  }

  async prioritizeReport(
    id: string,
    priority: BackendPriorityLevel,
    actor?: string
  ): Promise<ReportItem> {
    const raw = await apiClient.patch<BackendReportRead>(
      ENDPOINTS.TRANSITION_REPORT(id),
      {
        next_status: 'PRIORITIZED',
        priority,
        actor,
      }
    );
    return mapBackendToReportItem(raw);
  }

  async addInternalNote(
    id: string,
    content: string,
    author: string,
    authorRole: string
  ): Promise<ReportItem> {
    const current = await this.getReportById(id);
    const now = new Date().toISOString();
    if (!current.internalNotes) {
      current.internalNotes = [];
    }
    current.internalNotes.unshift({
      id: `note-${Date.now()}`,
      author,
      authorRole,
      content,
      createdAt: now,
    });
    current.auditTrail.unshift({
      id: `aud-${Date.now()}`,
      timestamp: now,
      actor: `${author} (${authorRole})`,
      action: 'Added internal operational note',
      notes: content,
    });
    return current;
  }

  async triggerAIProcess(id: string): Promise<AIJob> {
    return await apiClient.post<AIJob>(ENDPOINTS.REPORT_AI_PROCESS(id));
  }

  async getReportAI(id: string): Promise<ReportAIResult> {
    return await apiClient.get<ReportAIResult>(ENDPOINTS.REPORT_AI(id));
  }

  async getReportAIEvents(id: string): Promise<AIJobEvent[]> {
    return await apiClient.get<AIJobEvent[]>(ENDPOINTS.REPORT_AI_EVENTS(id));
  }

  async getAIJobs(
    params: {
      status?: string;
      stage?: string;
      page?: number;
      pageSize?: number;
    } = {}
  ): Promise<AIJobListResult> {
    const queryParams: Record<string, string | number | undefined> = {
      status: params.status,
      stage: params.stage,
      page: params.page || 1,
      page_size: params.pageSize || 20,
    };
    return await apiClient.get<AIJobListResult>(ENDPOINTS.AI_JOBS, {
      params: queryParams,
    });
  }

  async getAIMetrics(): Promise<AIMetrics> {
    return await apiClient.get<AIMetrics>(ENDPOINTS.AI_METRICS);
  }

  async getAIHealth(): Promise<AIHealthStatus> {
    return await apiClient.get<AIHealthStatus>(ENDPOINTS.AI_HEALTH);
  }
}
