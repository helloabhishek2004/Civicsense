import {
  ReportItem,
  ReportFilterParams,
  ReportListResult,
  ReportStats,
  ALLOWED_TRANSITIONS,
  DepartmentName,
  CivicCategory,
  ClosureReason,
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
import { IReportRepository } from './IReportRepository';
import { SEED_REPORTS } from '../mock/seedReports';
import { RepositoryError } from '../api/apiError';

export class MockReportRepository implements IReportRepository {
  private reports: ReportItem[];
  private aiJobs: AIJob[] = [];
  private aiEvents: AIJobEvent[] = [];

  constructor() {
    this.reports = JSON.parse(JSON.stringify(SEED_REPORTS));
    this.initMockJobs();
  }

  private initMockJobs() {
    // Populate realistic mock jobs for demo visualization
    const r1 = this.reports[0];
    if (r1) {
      const jobId = 'job-seed-001';
      const now = new Date().toISOString();
      const mockJob: AIJob = {
        id: jobId,
        report_id: r1.id,
        status: 'COMPLETED',
        current_stage: 'COMPLETED',
        review_required: false,
        review_completed: false,
        queued_at: now,
        started_at: now,
        completed_at: now,
        attempt_count: 1,
        execution_mode: 'synchronous_demo',
        processor_name: 'Deterministic Demo Processor',
        created_at: now,
        updated_at: now,
      };
      this.aiJobs.push(mockJob);
      this.aiEvents.push({
        id: 'ev-001',
        job_id: jobId,
        report_id: r1.id,
        stage: 'INTAKE_VALIDATION',
        status: 'COMPLETED',
        message: 'Intake coordinates and description verified.',
        started_at: now,
        duration_ms: 12,
        created_at: now,
      });
      this.aiEvents.push({
        id: 'ev-002',
        job_id: jobId,
        report_id: r1.id,
        stage: 'COMPLETED',
        status: 'COMPLETED',
        message: 'Automated AI triage completed with high confidence.',
        started_at: now,
        duration_ms: 45,
        created_at: now,
      });
    }
  }

  private async simulateLatency(ms: number = 100): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async getReports(params: ReportFilterParams = {}): Promise<ReportListResult> {
    await this.simulateLatency();

    let filtered = [...this.reports];

    // Filter by lifecycle phase
    if (params.phase && params.phase !== 'ALL') {
      const phaseStatusMap: Record<string, BackendReportStatus[]> = {
        INTAKE: ['SUBMITTED', 'AI_PROCESSING', 'AI_PROCESSED'],
        VERIFICATION: ['VERIFICATION_REQUIRED', 'VERIFIED'],
        WORKFLOW: ['PRIORITIZED', 'ASSIGNED', 'IN_PROGRESS'],
        RESOLUTION: ['RESOLVED', 'RESOLUTION_VERIFIED', 'CLOSED'],
      };
      const allowedInPhase = phaseStatusMap[params.phase] || [];
      filtered = filtered.filter((r) => allowedInPhase.includes(r.status));
    }

    // Filter by specific status
    if (params.status) {
      filtered = filtered.filter((r) => r.status === params.status);
    }

    // Filter by category
    if (params.category && params.category !== 'ALL') {
      filtered = filtered.filter((r) => r.category === params.category);
    }

    // Filter by severity
    if (params.severity && params.severity !== 'ALL') {
      filtered = filtered.filter((r) => r.severity === params.severity);
    }

    // Filter by priority
    if (params.priority && params.priority !== 'ALL') {
      filtered = filtered.filter((r) => r.priority === params.priority);
    }

    // Filter by department
    if (params.department && params.department !== 'ALL') {
      filtered = filtered.filter((r) => r.department === params.department);
    }

    // Search query
    if (params.search && params.search.trim()) {
      const q = params.search.trim().toLowerCase();
      filtered = filtered.filter(
        (r) =>
          r.trackingId.toLowerCase().includes(q) ||
          r.description.toLowerCase().includes(q) ||
          (r.addressHint && r.addressHint.toLowerCase().includes(q)) ||
          (r.citizenName && r.citizenName.toLowerCase().includes(q)) ||
          r.category.toLowerCase().includes(q)
      );
    }

    // Sorting
    const sortBy = params.sortBy || 'createdAt';
    const sortOrder = params.sortOrder || 'desc';
    const multiplier = sortOrder === 'asc' ? 1 : -1;

    const severityWeight: Record<BackendSeverityLevel, number> = {
      CRITICAL: 4,
      HIGH: 3,
      MEDIUM: 2,
      LOW: 1,
    };

    const priorityWeight: Record<BackendPriorityLevel, number> = {
      CRITICAL: 4,
      HIGH: 3,
      MEDIUM: 2,
      LOW: 1,
    };

    filtered.sort((a, b) => {
      if (sortBy === 'severity') {
        return (severityWeight[a.severity] - severityWeight[b.severity]) * multiplier;
      }
      if (sortBy === 'priority') {
        return (priorityWeight[a.priority] - priorityWeight[b.priority]) * multiplier;
      }
      if (sortBy === 'updatedAt') {
        return (new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime()) * multiplier;
      }
      return (new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()) * multiplier;
    });

    const total = filtered.length;
    const page = params.page || 1;
    const pageSize = params.pageSize || 10;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));

    const startIndex = (page - 1) * pageSize;
    const items = filtered.slice(startIndex, startIndex + pageSize);

    return {
      items,
      total,
      page,
      pageSize,
      totalPages,
    };
  }

  async getReportById(id: string): Promise<ReportItem> {
    await this.simulateLatency();
    const report = this.reports.find((r) => r.id === id || r.trackingId === id);
    if (!report) {
      throw new RepositoryError(
        `Report with ID "${id}" does not exist.`,
        'NOT_FOUND',
        { statusCode: 404 }
      );
    }
    return JSON.parse(JSON.stringify(report));
  }

  async getStats(): Promise<ReportStats> {
    await this.simulateLatency();
    const totalReports = this.reports.length;
    const pendingReview = this.reports.filter((r) =>
      ['SUBMITTED', 'VERIFICATION_REQUIRED'].includes(r.status)
    ).length;
    const inProgress = this.reports.filter((r) =>
      ['ASSIGNED', 'IN_PROGRESS'].includes(r.status)
    ).length;
    const resolvedToday = this.reports.filter((r) =>
      ['RESOLVED', 'RESOLUTION_VERIFIED', 'CLOSED'].includes(r.status)
    ).length;
    const criticalIssues = this.reports.filter((r) => r.severity === 'CRITICAL').length;

    return {
      totalReports,
      pendingReview,
      inProgress,
      resolvedToday,
      criticalIssues,
      avgResolutionDays: 2.3,
      humanOverrideRate: 8.4,
      aiAgreementRate: 91.2,
    };
  }

  async getMapPoints(): Promise<ReportItem[]> {
    await this.simulateLatency();
    return JSON.parse(JSON.stringify(this.reports));
  }

  async transitionStatus(
    id: string,
    nextStatus: BackendReportStatus,
    reason?: string,
    notes?: string,
    actor: string = 'Authorized Officer'
  ): Promise<ReportItem> {
    await this.simulateLatency();
    const index = this.reports.findIndex((r) => r.id === id || r.trackingId === id);
    if (index === -1) {
      throw new RepositoryError(`Report not found`, 'NOT_FOUND', { statusCode: 404 });
    }

    const current = this.reports[index];
    const allowed = ALLOWED_TRANSITIONS[current.status];

    if (!allowed.includes(nextStatus)) {
      throw new RepositoryError(
        `Invalid transition from ${current.status} to ${nextStatus}. Allowed: ${allowed.join(', ') || 'None (Terminal)'}`,
        'INVALID_TRANSITION',
        { statusCode: 400 }
      );
    }

    const now = new Date().toISOString();
    const fromStatus = current.status;
    current.status = nextStatus;
    current.updatedAt = now;

    if (nextStatus === 'RESOLVED') {
      current.resolvedAt = now;
    }

    if (nextStatus === 'CLOSED' && reason) {
      current.closureReason = reason as ClosureReason;
      current.closureNotes = notes;
    }

    current.auditTrail.unshift({
      id: `aud-${Date.now()}`,
      timestamp: now,
      actor,
      action: `Status transitioned to ${nextStatus}${reason ? ` (${reason})` : ''}`,
      fromStatus,
      toStatus: nextStatus,
      notes,
    });

    return JSON.parse(JSON.stringify(current));
  }

  async verifyReport(
    id: string,
    decision: BackendVerificationDecision,
    verifiedCategory?: CivicCategory,
    verifiedSeverity?: BackendSeverityLevel,
    notes?: string,
    actor: string = 'Triage Officer'
  ): Promise<ReportItem> {
    await this.simulateLatency();
    const index = this.reports.findIndex((r) => r.id === id || r.trackingId === id);
    if (index === -1) {
      throw new RepositoryError(`Report not found`, 'NOT_FOUND', { statusCode: 404 });
    }

    const report = this.reports[index];
    const now = new Date().toISOString();

    report.verifications.unshift({
      id: `ver-${Date.now()}`,
      report_id: report.id,
      decision,
      reviewer_id: actor,
      verified_category: verifiedCategory || report.category,
      verified_severity: verifiedSeverity || report.severity,
      notes: notes || null,
      created_at: now,
    });

    if (verifiedCategory) report.category = verifiedCategory;
    if (verifiedSeverity) report.severity = verifiedSeverity;

    if (decision === 'REJECTED' || decision === 'DUPLICATE') {
      return this.transitionStatus(
        id,
        'CLOSED',
        decision === 'DUPLICATE' ? 'DUPLICATE' : 'INVALID_REPORT',
        notes,
        actor
      );
    } else {
      return this.transitionStatus(id, 'VERIFIED', undefined, notes, actor);
    }
  }

  async assignDepartment(
    id: string,
    department: DepartmentName,
    assignedOfficer?: string,
    actor: string = 'Operational Manager'
  ): Promise<ReportItem> {
    await this.simulateLatency();
    const index = this.reports.findIndex((r) => r.id === id || r.trackingId === id);
    if (index === -1) {
      throw new RepositoryError(`Report not found`, 'NOT_FOUND', { statusCode: 404 });
    }

    const report = this.reports[index];
    report.department = department;
    if (assignedOfficer) {
      report.assignedOfficer = assignedOfficer;
    }

    const now = new Date().toISOString();
    report.auditTrail.unshift({
      id: `aud-${Date.now()}`,
      timestamp: now,
      actor,
      action: `Assigned to ${department}${assignedOfficer ? ` (Officer: ${assignedOfficer})` : ''}`,
    });

    if (report.status === 'VERIFIED' || report.status === 'PRIORITIZED') {
      return this.transitionStatus(id, 'ASSIGNED', undefined, undefined, actor);
    }

    report.updatedAt = now;
    return JSON.parse(JSON.stringify(report));
  }

  async acknowledgeJob(
    id: string,
    assignedOfficer?: string,
    notes?: string
  ): Promise<ReportItem> {
    await this.simulateLatency();
    const index = this.reports.findIndex((r) => r.id === id || r.trackingId === id);
    if (index === -1) {
      throw new RepositoryError(`Report not found`, 'NOT_FOUND', { statusCode: 404 });
    }
    const report = this.reports[index];
    if (assignedOfficer) report.assignedOfficer = assignedOfficer;
    return this.transitionStatus(id, 'IN_PROGRESS', undefined, notes, assignedOfficer || 'Department Officer');
  }

  async completeJob(
    id: string,
    resolverNotes: string,
    resolvedBy?: string
  ): Promise<ReportItem> {
    await this.simulateLatency();
    return this.transitionStatus(id, 'RESOLVED', undefined, resolverNotes, resolvedBy || 'Department Officer');
  }

  async rejectJob(
    id: string,
    rejectionReason: BackendDepartmentRejectionReason,
    notes: string,
    suggestedDepartment?: string
  ): Promise<ReportItem> {
    await this.simulateLatency();
    const index = this.reports.findIndex((r) => r.id === id || r.trackingId === id);
    if (index === -1) {
      throw new RepositoryError(`Report not found`, 'NOT_FOUND', { statusCode: 404 });
    }
    const report = this.reports[index];
    report.reassignmentRequired = true;
    return this.transitionStatus(
      id,
      'PRIORITIZED',
      `Rejected (${rejectionReason})`,
      `${notes}${suggestedDepartment ? ` [Suggested: ${suggestedDepartment}]` : ''}`,
      'Department Officer'
    );
  }

  async getReportAssignments(id: string): Promise<BackendAssignmentRead[]> {
    await this.simulateLatency();
    const index = this.reports.findIndex((r) => r.id === id || r.trackingId === id);
    if (index === -1) return [];
    return this.reports[index].assignments || [];
  }

  async addInternalNote(
    id: string,
    content: string,
    author: string,
    authorRole: string
  ): Promise<ReportItem> {
    await this.simulateLatency();
    const index = this.reports.findIndex((r) => r.id === id || r.trackingId === id);
    if (index === -1) {
      throw new RepositoryError(`Report not found`, 'NOT_FOUND', { statusCode: 404 });
    }

    const report = this.reports[index];
    const now = new Date().toISOString();
    if (!report.internalNotes) {
      report.internalNotes = [];
    }

    report.internalNotes.unshift({
      id: `note-${Date.now()}`,
      author,
      authorRole,
      content,
      createdAt: now,
    });

    report.auditTrail.unshift({
      id: `aud-${Date.now()}`,
      timestamp: now,
      actor: `${author} (${authorRole})`,
      action: `Added internal operational note`,
      notes: content,
    });

    report.updatedAt = now;
    return JSON.parse(JSON.stringify(report));
  }

  async prioritizeReport(
    id: string,
    priority: BackendPriorityLevel,
    actor: string = 'Triage Officer'
  ): Promise<ReportItem> {
    await this.simulateLatency();
    const index = this.reports.findIndex((r) => r.id === id || r.trackingId === id);
    if (index === -1) {
      throw new RepositoryError(`Report not found`, 'NOT_FOUND', { statusCode: 404 });
    }

    const report = this.reports[index];
    report.priority = priority;
    const now = new Date().toISOString();
    report.auditTrail.unshift({
      id: `aud-${Date.now()}`,
      timestamp: now,
      actor,
      action: `Priority adjusted to ${priority}`,
    });

    if (report.status === 'VERIFIED') {
      return this.transitionStatus(id, 'PRIORITIZED', undefined, undefined, actor);
    }

    report.updatedAt = now;
    return JSON.parse(JSON.stringify(report));
  }

  async triggerAIProcess(id: string): Promise<AIJob> {
    await this.simulateLatency(300);
    const report = this.reports.find((r) => r.id === id || r.trackingId === id);
    if (!report) {
      throw new RepositoryError('Report not found', 'NOT_FOUND', { statusCode: 404 });
    }

    const jobId = `job-${Date.now()}`;
    const now = new Date().toISOString();
    const isVague = report.description.toLowerCase().includes('something') || report.description.length < 20;

    const stages = [
      'INTAKE_VALIDATION',
      'PREPROCESSING',
      'VISION_ANALYSIS',
      'TEXT_ANALYSIS',
      'FUSION',
      'DECISION',
    ] as const;

    // Generate stage events
    stages.forEach((st, idx) => {
      this.aiEvents.push({
        id: `ev-${Date.now()}-${idx}`,
        job_id: jobId,
        report_id: report.id,
        stage: st,
        status: 'COMPLETED',
        message: `Stage ${st} evaluated deterministically in mock simulation mode.`,
        started_at: now,
        completed_at: now,
        duration_ms: 15 + idx * 8,
        created_at: now,
      });
    });

    const reviewRequired = isVague;
    const finalStage = reviewRequired ? 'HUMAN_REVIEW' : 'COMPLETED';

    this.aiEvents.push({
      id: `ev-${Date.now()}-final`,
      job_id: jobId,
      report_id: report.id,
      stage: finalStage,
      status: reviewRequired ? 'STARTED' : 'COMPLETED',
      message: reviewRequired
        ? 'Mandatory human verification required: Low confidence or vague problem statement.'
        : 'Automated AI triage completed successfully with high confidence.',
      started_at: now,
      completed_at: now,
      duration_ms: 25,
      created_at: now,
    });

    const job: AIJob = {
      id: jobId,
      report_id: report.id,
      status: 'COMPLETED',
      current_stage: finalStage,
      review_required: reviewRequired,
      review_completed: false,
      review_reason: reviewRequired ? 'LOW_CONFIDENCE' : undefined,
      queued_at: now,
      started_at: now,
      completed_at: now,
      attempt_count: 1,
      execution_mode: 'synchronous_demo',
      processor_name: 'Deterministic Demo Processor',
      created_at: now,
      updated_at: now,
    };
    this.aiJobs.unshift(job);

    // Update report lifecycle state
    report.status = reviewRequired ? 'VERIFICATION_REQUIRED' : 'AI_PROCESSED';
    report.updatedAt = now;

    return job;
  }

  async getReportAI(id: string): Promise<ReportAIResult> {
    await this.simulateLatency();
    const report = this.reports.find((r) => r.id === id || r.trackingId === id);
    if (!report) {
      throw new RepositoryError('Report not found', 'NOT_FOUND', { statusCode: 404 });
    }

    const latestJob = this.aiJobs.find((j) => j.report_id === report.id);
    const now = new Date().toISOString();

    return {
      report_id: report.id,
      tracking_id: report.trackingId,
      report_status: report.status,
      latest_job: latestJob,
      ai_analysis: {
        id: `ana-${report.id}`,
        report_id: report.id,
        predicted_category: report.category,
        confidence: report.confidence || 0.88,
        severity: report.severity,
        priority: report.priority,
        evidence_agreement: report.evidenceAgreement || 0.92,
        review_required: report.reviewRequired,
        analysis_metadata: {
          processor_name: 'Deterministic Demo Processor',
          execution_mode: 'synchronous_demo',
          disclaimer: 'Deterministic Prototype Engine (Not a trained deep learning model)',
          vision_prediction: {
            category: report.category,
            severity: report.severity,
            confidence: 0.85,
            has_image: (report.evidences && report.evidences.length > 0),
          },
          text_prediction: {
            category: report.category,
            severity: report.severity,
            confidence: 0.89,
            matched_terms: [report.category.toLowerCase()],
          },
          fusion_metrics: {
            modality_agreement: 0.92,
            conflict_reasons: [],
          },
          decision_rationale: 'Multimodal signals concordant with high confidence.',
          job_id: latestJob?.id,
          processing_duration_ms: 120,
        },
        created_at: report.createdAt,
      },
      verification: report.verifications && report.verifications.length > 0
        ? {
            id: 'ver-seed',
            reviewer_id: 'triage.officer@civicsense.gov',
            decision: 'CONFIRMED',
            verified_category: report.category,
            verified_severity: report.severity,
            notes: 'Human officer confirmed defect status.',
            created_at: now,
          }
        : undefined,
      execution_mode: 'synchronous_prototype',
      processor_name: 'CivicSense Prototype AI (Deterministic Demo Processor)',
      disclaimer:
        'Deterministic Prototype AI / Demo Simulation. Rule-based text pattern & vision metadata analysis.',
    };
  }

  async getReportAIEvents(id: string): Promise<AIJobEvent[]> {
    await this.simulateLatency();
    const report = this.reports.find((r) => r.id === id || r.trackingId === id);
    if (!report) return [];
    return this.aiEvents
      .filter((e) => e.report_id === report.id)
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
  }

  async getAIJobs(
    params: {
      status?: string;
      stage?: string;
      page?: number;
      pageSize?: number;
    } = {}
  ): Promise<AIJobListResult> {
    await this.simulateLatency();
    let filtered = [...this.aiJobs];
    if (params.status) {
      filtered = filtered.filter((j) => j.status === params.status);
    }
    if (params.stage) {
      filtered = filtered.filter((j) => j.current_stage === params.stage);
    }
    const total = filtered.length;
    const page = params.page || 1;
    const pageSize = params.pageSize || 20;
    const start = (page - 1) * pageSize;
    return {
      items: filtered.slice(start, start + pageSize),
      total,
      page,
      page_size: pageSize,
    };
  }

  async getAIMetrics(): Promise<AIMetrics> {
    await this.simulateLatency();
    const total = this.aiJobs.length;
    const completed = this.aiJobs.filter((j) => j.status === 'COMPLETED').length;
    const awaiting = this.aiJobs.filter((j) => j.current_stage === 'HUMAN_REVIEW').length;

    return {
      total_jobs: { value: total, sample_size: total, display_state: 'AVAILABLE' },
      completed_jobs: { value: completed, sample_size: total, display_state: 'AVAILABLE' },
      failed_jobs: { value: 0, sample_size: total, display_state: 'AVAILABLE' },
      active_jobs: { value: 0, sample_size: total, display_state: 'AVAILABLE' },
      awaiting_human_review: { value: awaiting, sample_size: total, display_state: 'AVAILABLE' },
      avg_processing_latency_ms: { value: 135.4, sample_size: completed, display_state: 'AVAILABLE' },
      low_confidence_rate: { value: 12.5, sample_size: total, display_state: 'AVAILABLE' },
      modality_disagreement_rate: { value: 6.2, sample_size: total, display_state: 'AVAILABLE' },
      human_override_rate: { value: 8.4, sample_size: 24, display_state: 'AVAILABLE' },
      time_window: 'ALL_TIME',
      generated_at: new Date().toISOString(),
    };
  }

  async getAIHealth(): Promise<AIHealthStatus> {
    await this.simulateLatency();
    return {
      status: 'available',
      execution_mode: 'synchronous_prototype',
      processor_mode: 'deterministic_demo',
      processor_name: 'CivicSense Prototype AI (Deterministic Demo Processor)',
      production_model_available: false,
      background_worker_available: false,
      supported_stages: [
        'INTAKE_VALIDATION',
        'PREPROCESSING',
        'VISION_ANALYSIS',
        'TEXT_ANALYSIS',
        'FUSION',
        'DECISION',
        'HUMAN_REVIEW',
        'COMPLETED',
      ],
      active_jobs_count: 0,
      total_jobs_processed: this.aiJobs.length,
      timestamp: new Date().toISOString(),
    };
  }
}
