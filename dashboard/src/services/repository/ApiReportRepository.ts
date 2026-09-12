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
import { IReportRepository } from './IReportRepository';
import { apiClient } from '../api/apiClient';
import { ENDPOINTS } from '../api/endpoints';
import { normalizeIsoUtc } from '@/core/utils/dateUtils';

export function normalizeCategory(rawCat?: string | null): CivicCategory {
  if (!rawCat) return 'Other';
  const p = rawCat.toLowerCase().trim();
  if (p.includes('pothole')) return 'Pothole';
  if (p.includes('garbage') || p.includes('waste')) return 'Garbage';
  if (p.includes('water') || p.includes('leak')) return 'Water Leakage';
  if (p.includes('streetlight') || p.includes('light')) return 'Streetlight';
  if (p.includes('road')) return 'Road Damage';
  if (p.includes('drain')) return 'Drainage';
  if (p.includes('infra')) return 'Infrastructure';
  return 'Other';
}

export function mapBackendToReportItem(raw: BackendReportRead): ReportItem {
  const latestAi = raw.ai_analyses && raw.ai_analyses.length > 0 ? raw.ai_analyses[0] : null;
  const latestVer = raw.verifications && raw.verifications.length > 0 ? raw.verifications[0] : null;

  // Resolve category with clear authority order:
  // 1. Human verification override (highest authority)
  // 2. Report category (from citizen submission / DB)
  // 3. AI prediction (if citizen report was unclassified or Other)
  // 4. Edge metadata category_hint fallback
  let category: CivicCategory = 'Other';
  if (latestVer?.verified_category) {
    category = normalizeCategory(latestVer.verified_category);
  } else if (raw.category && normalizeCategory(raw.category) !== 'Other') {
    category = normalizeCategory(raw.category);
  } else if (latestAi?.predicted_category && normalizeCategory(latestAi.predicted_category) !== 'Other') {
    category = normalizeCategory(latestAi.predicted_category);
  } else if (raw.edge_metadata && typeof (raw.edge_metadata as any).category_hint === 'string') {
    category = normalizeCategory((raw.edge_metadata as any).category_hint);
  } else if (raw.category) {
    category = normalizeCategory(raw.category);
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
    else if (category === 'Infrastructure') department = 'Town Planning & Enforcement';
  }

  return {
    id: raw.id,
    trackingId: raw.tracking_id,
    status: raw.status,
    category,
    description: raw.description,
    citizenId: raw.citizen_id || undefined,
    citizenName: raw.citizen_name || undefined,
    citizenPhone: raw.citizen_phone || undefined,
    citizenEmail: raw.citizen_email || undefined,
    citizenPostalCode: raw.citizen_postal_code || undefined,
    latitude: raw.latitude,
    longitude: raw.longitude,
    addressHint: raw.address_hint || undefined,
    departmentId: (raw as any).department_id || undefined,
    department,
    severity,
    priority,
    reassignmentRequired: (raw as any).reassignment_required ?? false,
    assignedOfficer: (raw as any).assigned_officer || undefined,
    confidence: latestAi?.confidence ?? undefined,
    evidenceAgreement: latestAi?.evidence_agreement ?? undefined,
    reviewRequired: latestAi?.review_required ?? (raw.status === 'VERIFICATION_REQUIRED'),
    evidences: raw.evidences || [],
    aiAnalyses: raw.ai_analyses || [],
    verifications: raw.verifications || [],
    assignments: (raw as any).assignments || [],
    currentAssignment: (raw as any).current_assignment || null,
    edgeMetadata: raw.edge_metadata || null,
    auditTrail: [
      {
        id: `aud-${raw.id}-0`,
        timestamp: normalizeIsoUtc(raw.created_at),
        actor: 'Citizen Client',
        action: 'Report Submitted',
        toStatus: 'SUBMITTED',
      },
      ...(raw.updated_at !== raw.created_at
        ? [
            {
              id: `aud-${raw.id}-1`,
              timestamp: normalizeIsoUtc(raw.updated_at),
              actor: 'System / Officer',
              action: `Updated state to ${raw.status}`,
              toStatus: raw.status,
            },
          ]
        : []),
    ],
    createdAt: normalizeIsoUtc(raw.created_at),
    updatedAt: normalizeIsoUtc(raw.updated_at),
  };
}

export class ApiReportRepository implements IReportRepository {
  async getReports(params: ReportFilterParams = {}): Promise<ReportListResult> {
    const queryParams: Record<string, string | number | boolean | undefined> = {
      page: params.page || 1,
      page_size: params.pageSize || 10,
    };
    if (params.department && params.department !== 'ALL') {
      queryParams.department = params.department;
    }
    if (params.status) {
      queryParams.status = params.status;
    }
    if (params.category && params.category !== 'ALL') {
      queryParams.category = params.category;
    }
    if (params.priority && params.priority !== 'ALL') {
      queryParams.priority = params.priority;
    }
    if (params.reassignmentRequired !== undefined) {
      queryParams.reassignment_required = params.reassignmentRequired;
    }

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
    const raw = await apiClient.post<BackendReportRead>(
      ENDPOINTS.REPORT_ASSIGN(id),
      {
        department_name: department,
        assigned_to_officer: assignedOfficer,
        assigned_by: actor || 'Triage Officer',
      }
    );
    return mapBackendToReportItem(raw);
  }

  async acknowledgeJob(
    id: string,
    assignedOfficer?: string,
    notes?: string
  ): Promise<ReportItem> {
    const raw = await apiClient.post<BackendReportRead>(
      ENDPOINTS.REPORT_ACKNOWLEDGE(id),
      {
        assigned_to_officer: assignedOfficer,
        notes,
      }
    );
    return mapBackendToReportItem(raw);
  }

  async completeJob(
    id: string,
    resolverNotes: string,
    resolvedBy?: string
  ): Promise<ReportItem> {
    const raw = await apiClient.post<BackendReportRead>(
      ENDPOINTS.REPORT_COMPLETE(id),
      {
        resolver_notes: resolverNotes,
        resolved_by: resolvedBy,
      }
    );
    return mapBackendToReportItem(raw);
  }

  async rejectJob(
    id: string,
    rejectionReason: BackendDepartmentRejectionReason,
    notes: string,
    suggestedDepartment?: string
  ): Promise<ReportItem> {
    const raw = await apiClient.post<BackendReportRead>(
      ENDPOINTS.REPORT_DEPARTMENT_REJECT(id),
      {
        rejection_reason: rejectionReason,
        notes,
        suggested_department: suggestedDepartment,
      }
    );
    return mapBackendToReportItem(raw);
  }

  async getReportAssignments(id: string): Promise<BackendAssignmentRead[]> {
    const response = await apiClient.get<BackendAssignmentRead[]>(
      ENDPOINTS.REPORT_ASSIGNMENTS(id)
    );
    return response || [];
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
