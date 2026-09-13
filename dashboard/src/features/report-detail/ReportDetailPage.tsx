import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MapRenderer } from '../map/MapRenderer';
import {
  ArrowLeft,
  MapPin,
  User,
  Phone,
  Mail,
  Bot,
  CheckCircle,
  AlertTriangle,
  FileCheck,
  Send,
  Building,
  RotateCcw,
  XCircle,
  Hash,
  Maximize2,
  Clock,
  Lock,
  ShieldCheck,
  MessageSquare,
  Plus,
  Play,
  Sparkles,
  ExternalLink,
  ShieldAlert,
  UserCheck,
  Flame,
  Cpu,
  GitCompare,
  RefreshCw,
  Smartphone,
  Layers,
} from 'lucide-react';
import { reportRepository } from '@/services/repository/reportRepository';
import { queryKeys } from '@/services/queryKeys';
import { useAuth } from '@/core/auth/AuthContext';
import { can } from '@/core/auth/permissions';
import { env } from '@/core/config/env';
import { resolveMediaUrl } from '@/core/utils/mediaUtils';
import { parseUtcDate, formatDateTime, formatTime, formatDateFull } from '@/core/utils/dateUtils';
import {
  ALLOWED_TRANSITIONS,
  BackendReportStatus,
  BackendSeverityLevel,
  BackendPriorityLevel,
  CivicCategory,
  ClosureReason,
  DepartmentName,
  ReportItem,
} from '@/types/models';
import { BackendDepartmentRejectionReason } from '@/types/api/backendContracts';
import { StatusBadge } from '@/core/components/StatusBadge';
import { SeverityBadge } from '@/core/components/SeverityBadge';
import { PriorityBadge } from '@/core/components/PriorityBadge';
import { CivicButton } from '@/core/components/CivicButton';
import { Modal } from '@/core/components/Modal';
import { ErrorBanner } from '@/core/components/ErrorBanner';
import { LoadingSkeleton } from '@/core/components/LoadingSkeleton';
import { motion, type Variants } from 'motion/react';

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.02,
    },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.35,
      ease: [0.16, 1, 0.3, 1],
    },
  },
};

export const ReportDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  // Active modal state
  const [activeModal, setActiveModal] = useState<
    'VERIFY' | 'REJECT' | 'PRIORITIZE' | 'ASSIGN' | 'RESOLVE' | 'DECLINE_JOB' | 'IMAGE_PREVIEW' | null
  >(null);

  // Form states for transitions
  const [verifiedCategory, setVerifiedCategory] = useState<CivicCategory>('Pothole');
  const [verifiedSeverity, setVerifiedSeverity] = useState<BackendSeverityLevel>('MEDIUM');
  const [closureReason, setClosureReason] = useState<ClosureReason>('INVALID_REPORT');
  const [targetPriority, setTargetPriority] = useState<BackendPriorityLevel>('MEDIUM');
  const [targetDepartment, setTargetDepartment] = useState<DepartmentName>('Roads & Bridges');
  const [assignedOfficer, setAssignedOfficer] = useState('');
  const [actionNotes, setActionNotes] = useState('');
  const [declineReason, setDeclineReason] =
    useState<BackendDepartmentRejectionReason>('OUT_OF_JURISDICTION');
  const [declineNotes, setDeclineNotes] = useState('');
  const [previewImageUri, setPreviewImageUri] = useState<string | null>(null);
  const [newNoteContent, setNewNoteContent] = useState('');
  const [imageLoadFailed, setImageLoadFailed] = useState(false);

  // Fetch report data
  const {
    data: report,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.reports.detail(id || ''),
    queryFn: () => reportRepository.getReportById(id || ''),
    enabled: !!id,
    refetchInterval: 4000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });

  const rawImageUri = report?.evidences?.[0]?.storage_uri;
  const resolvedImageUrl = resolveMediaUrl(rawImageUri);

  useEffect(() => {
    setImageLoadFailed(false);
  }, [report?.id]);

  useEffect(() => {
    if (report) {
      console.log('[CivicSense][Audit] Detail fields presence:', {
        reportId: report.id,
        trackingId: report.trackingId,
        hasRawImage: !!rawImageUri,
        hasResolvedImage: !!resolvedImageUrl,
        hasCitizenName: !!report.citizenName,
        hasCitizenPhone: !!report.citizenPhone,
      });
    }
  }, [report, rawImageUri, resolvedImageUrl]);

  // Fetch persisted AI Result and Job State
  const {
    data: aiResult,
    refetch: refetchAI,
  } = useQuery({
    queryKey: queryKeys.ai.detail(id || ''),
    queryFn: () => reportRepository.getReportAI(id || ''),
    enabled: !!id,
    refetchInterval: (query) => {
      const jobStatus = query.state.data?.latest_job?.status;
      return jobStatus === 'PROCESSING' || jobStatus === 'QUEUED' || report?.status === 'AI_PROCESSING' ? 2000 : false;
    },
  });

  // AI Process Trigger Mutation
  const aiProcessMutation = useMutation({
    mutationFn: async () => {
      return reportRepository.triggerAIProcess(report!.id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.detail(report!.id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.detail(report!.id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.events(report!.id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.jobs() });
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.metrics() });
    },
  });

  // Server-confirmed transition mutation
  const transitionMutation = useMutation({
    mutationFn: async ({
      nextStatus,
      reason,
      notes,
    }: {
      nextStatus: BackendReportStatus;
      reason?: string;
      notes?: string;
    }) => {
      return reportRepository.transitionStatus(
        report!.id,
        nextStatus,
        reason,
        notes,
        user ? `${user.name} (${user.role})` : 'Authorized Officer'
      );
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.reports.detail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      setActiveModal(null);
      setActionNotes('');
    },
  });

  // Verify mutation
  const verifyMutation = useMutation({
    mutationFn: async () => {
      return reportRepository.verifyReport(
        report!.id,
        'CONFIRMED',
        verifiedCategory,
        verifiedSeverity,
        actionNotes,
        user ? `${user.name} (${user.role})` : 'Triage Officer'
      );
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.reports.detail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      setActiveModal(null);
      setActionNotes('');
    },
  });

  // Reject / Duplicate mutation
  const rejectMutation = useMutation({
    mutationFn: async () => {
      return reportRepository.verifyReport(
        report!.id,
        closureReason === 'DUPLICATE' ? 'DUPLICATE' : 'REJECTED',
        undefined,
        undefined,
        actionNotes,
        user ? `${user.name} (${user.role})` : 'Triage Officer'
      );
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.reports.detail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      setActiveModal(null);
      setActionNotes('');
    },
  });

  // Assign mutation
  const assignMutation = useMutation({
    mutationFn: async () => {
      return reportRepository.assignDepartment(
        report!.id,
        targetDepartment,
        assignedOfficer || undefined,
        user ? `${user.name} (${user.role})` : 'Department Manager'
      );
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.reports.detail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.departments.all });
      setActiveModal(null);
      setActionNotes('');
    },
  });

  // Acknowledge Job Mutation (Department Workflow)
  const acknowledgeJobMutation = useMutation({
    mutationFn: async () => {
      return reportRepository.acknowledgeJob(
        report!.id,
        user ? `${user.name} (${user.role})` : 'Department Supervisor',
        actionNotes || 'Job acknowledged and crew mobilization commenced'
      );
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.reports.detail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.departments.all });
      setActionNotes('');
    },
  });

  // Decline Job Mutation (Department Workflow)
  const declineJobMutation = useMutation({
    mutationFn: async () => {
      return reportRepository.rejectJob(
        report!.id,
        declineReason,
        declineNotes
      );
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.reports.detail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.departments.all });
      setActiveModal(null);
      setDeclineNotes('');
    },
  });

  // Prioritize mutation
  const prioritizeMutation = useMutation({
    mutationFn: async () => {
      return reportRepository.prioritizeReport(
        report!.id,
        targetPriority,
        user ? `${user.name} (${user.role})` : 'Triage Officer'
      );
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.reports.detail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      setActiveModal(null);
    },
  });

  // Add internal operational note mutation
  const addNoteMutation = useMutation({
    mutationFn: async (content: string) => {
      return reportRepository.addInternalNote(
        report!.id,
        content,
        user ? user.name : 'Authorized Officer',
        user ? user.role : 'TRIAGE_OFFICER'
      );
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.reports.detail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      setNewNoteContent('');
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <LoadingSkeleton className="h-64 w-full rounded-civic" />
            <LoadingSkeleton className="h-48 w-full rounded-civic" />
          </div>
          <div className="space-y-6">
            <LoadingSkeleton className="h-72 w-full rounded-civic" />
          </div>
        </div>
      </div>
    );
  }

  if (isError || !report) {
    return (
      <div className="space-y-4">
        <CivicButton
          variant="outline"
          size="sm"
          onClick={() => navigate('/reports')}
          leftIcon={<ArrowLeft className="w-4 h-4" />}
        >
          Back to Reports
        </CivicButton>
        <ErrorBanner
          title="Report Not Found"
          message={error instanceof Error ? error.message : 'The requested report could not be loaded.'}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const allowedTransitions = ALLOWED_TRANSITIONS[report.status] || [];
  const latestAi = report.aiAnalyses && report.aiAnalyses.length > 0 ? report.aiAnalyses[0] : null;
  const latestVerification =
    report.verifications && report.verifications.length > 0 ? report.verifications[0] : null;

  // Permissions
  const canViewPhone = can(user, 'view_citizen_phone');
  const canVerify = can(user, 'verify_report');
  const canPrioritize = can(user, 'prioritize_report');
  const canAssign = can(user, 'assign_department');
  const canStartWork = can(user, 'start_work');
  const canResolve = can(user, 'resolve_report');
  const canVerifyResolution = can(user, 'verify_resolution');
  const canClose = can(user, 'close_report');

  // Privacy-aware phone masking
  const formatCitizenPhone = (phone?: string) => {
    if (!phone) return 'Not registered';
    if (canViewPhone) return phone;
    const clean = phone.trim();
    if (clean.length < 8) return '••••••••';
    const start = clean.slice(0, Math.min(7, clean.length - 4));
    const end = clean.slice(-2);
    return `${start}••••${end}`;
  };

  // SLA Calculation
  const calculateSla = (item: ReportItem) => {
    if (item.sla) return item.sla;
    const slaHoursMap: Record<BackendPriorityLevel, number> = {
      CRITICAL: 24,
      HIGH: 48,
      MEDIUM: 72,
      LOW: 168,
    };
    const targetHours = slaHoursMap[item.priority] || 72;
    const createdMs = parseUtcDate(item.createdAt)?.getTime() ?? Date.now();
    const deadlineMs = createdMs + targetHours * 3600 * 1000;
    const nowMs = Date.now();
    const remainingHours = Math.round((deadlineMs - nowMs) / (3600 * 1000));
    return {
      targetHours,
      remainingHours,
      isBreached: remainingHours < 0,
      deadline: new Date(deadlineMs).toISOString(),
    };
  };

  const slaInfo = calculateSla(report);

  // Honest AI State Info
  const getAiStateDisplay = () => {
    if (report.status === 'SUBMITTED') {
      return {
        badgeText: 'AI Analysis Pending',
        badgeClass: 'bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-900/60 dark:text-slate-300 dark:border-slate-700',
        message: 'Citizen report entered intake queue. AI multimodal inference pipeline has not been executed yet.',
        isPending: false,
      };
    }
    if (report.status === 'AI_PROCESSING') {
      const stageName = aiResult?.latest_job?.current_stage || 'PROCESSING';
      return {
        badgeText: `AI Pipeline Active (${stageName})`,
        badgeClass: 'bg-purple-100 text-purple-800 border-purple-300 animate-pulse dark:bg-purple-950/60 dark:text-purple-300 dark:border-purple-800',
        message: 'Deterministic multimodal pipeline is evaluating attached photo and citizen text.',
        isPending: true,
      };
    }
    if (report.status === 'VERIFICATION_REQUIRED' || report.reviewRequired || aiResult?.latest_job?.review_required) {
      return {
        badgeText: 'Manual Triage Required',
        badgeClass: 'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800',
        message: aiResult?.latest_job?.review_reason || 'Autonomous confidence or agreement threshold was not met. Officer review is mandatory.',
        isPending: false,
      };
    }
    if (report.status === 'AI_PROCESSED') {
      return {
        badgeText: 'AI Inferences Available',
        badgeClass: 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800',
        message: 'Autonomous multimodal feature extraction completed. Recommendations ready for triage verification.',
        isPending: false,
      };
    }
    return {
      badgeText: 'Human Verified',
      badgeClass: 'bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800',
      message: 'AI findings were evaluated and verified into municipal resolution workflows.',
      isPending: false,
    };
  };

  const aiDisplay = getAiStateDisplay();

  // Lifecycle Stage Banner info
  const getStageHeaderInfo = () => {
    switch (report.status) {
      case 'SUBMITTED':
        return {
          title: 'Intake Stage: Awaiting Processing',
          desc: 'Citizen submission is stored. Autonomous AI evaluation or immediate officer triage required.',
          barColor: 'bg-amber-500',
        };
      case 'AI_PROCESSING':
        return {
          title: 'Intake Stage: AI Pipeline Active',
          desc: 'Vision and language inference microservices are currently analyzing submitted evidence.',
          barColor: 'bg-purple-500',
        };
      case 'AI_PROCESSED':
        return {
          title: 'Triage Stage: AI Inferences Available',
          desc: 'Automated analysis complete. Ready for triage officer verification or direct prioritization.',
          barColor: 'bg-blue-500',
        };
      case 'VERIFICATION_REQUIRED':
        return {
          title: 'Triage Stage: Human Verification Mandatory',
          desc: 'Confidence threshold or modality conflict triggered a required human inspection verdict.',
          barColor: 'bg-amber-600',
        };
      case 'VERIFIED':
        return {
          title: 'Planning Stage: Verified & Pending Priority',
          desc: 'Authenticity confirmed. Assign dispatch priority and route to the responsible municipal department.',
          barColor: 'bg-emerald-600',
        };
      case 'PRIORITIZED':
        return {
          title: 'Planning Stage: Priority Assigned',
          desc: `Urgency SLA set to ${report.priority}. Ready for departmental assignment or emergency crew dispatch.`,
          barColor: 'bg-blue-600',
        };
      case 'ASSIGNED':
        return {
          title: 'Dispatch Stage: Assigned to Department',
          desc: `Routed to ${report.department || 'General Public Works'}. Awaiting field crew mobilization.`,
          barColor: 'bg-indigo-600',
        };
      case 'IN_PROGRESS':
        return {
          title: 'Field Execution: Work in Progress',
          desc: 'Field personnel mobilized. Repair operations actively underway on site.',
          barColor: 'bg-orange-500',
        };
      case 'RESOLVED':
        return {
          title: 'Quality Assurance: Field Repair Reported',
          desc: 'Work completed by engineering crew. Awaiting supervisory physical inspection and sign-off.',
          barColor: 'bg-teal-600',
        };
      case 'RESOLUTION_VERIFIED':
        return {
          title: 'Quality Assurance: Resolution Confirmed',
          desc: 'Municipal inspector confirmed defect repair. Ready for formal archival and ticket closure.',
          barColor: 'bg-emerald-600',
        };
      case 'CLOSED':
        return {
          title: 'Archived: Report Closed',
          desc: `Terminal state. Record archived with justification: ${report.closureReason || 'COMPLETED'}.`,
          barColor: 'bg-slate-500',
        };
      default:
        return {
          title: 'Municipal Operations Workspace',
          desc: 'Managing civic defect lifecycle.',
          barColor: 'bg-civic-green',
        };
    }
  };

  const stageInfo = getStageHeaderInfo();

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6 pb-16"
    >
      {/* Top Breadcrumb & Controls */}
      <motion.div variants={itemVariants} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <CivicButton
            variant="outline"
            size="sm"
            onClick={() => navigate('/reports')}
            leftIcon={<ArrowLeft className="w-4 h-4" />}
          >
            Reports Queue
          </CivicButton>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-xl font-bold tracking-tight text-civic-text-primary dark:text-civic-dark-text-primary font-mono">
                {report.trackingId}
              </h1>
              <StatusBadge status={report.status} />
              <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-gray-100 text-civic-text-secondary dark:bg-civic-dark-surface-elevated dark:text-civic-dark-text-secondary border border-civic-border dark:border-civic-dark-border">
                {report.category}
              </span>
            </div>
            <p className="text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary mt-0.5">
              Submitted on <span title={formatDateFull(report.createdAt)}>{formatDateTime(report.createdAt)}</span> • Last modified{' '}
              <span title={formatDateFull(report.updatedAt)}>{formatTime(report.updatedAt)}</span>
            </p>
          </div>
        </div>

        {/* Operational Severity & Priority Badges */}
        <div className="flex items-center gap-2 shrink-0">
          <SeverityBadge severity={report.severity} />
          <PriorityBadge priority={report.priority} />
        </div>
      </motion.div>

      {/* Reassignment Required Callout */}
      {report.reassignmentRequired && (
        <motion.div
          variants={itemVariants}
          className="p-4 rounded-civic border border-amber-300 bg-amber-50 dark:bg-amber-950/40 dark:border-amber-900/60 flex items-start gap-3 text-xs shadow-civic-card"
        >
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h3 className="font-semibold text-amber-900 dark:text-amber-200 text-sm">
              Department Reassignment Required
            </h3>
            <p className="text-amber-800 dark:text-amber-300 leading-relaxed">
              A municipal department previously declined this work order. Review the assignment history below to verify the decline reason and reassign this report to the appropriate department.
            </p>
          </div>
        </motion.div>
      )}

      {/* Operational Stage Banner */}
      <motion.div variants={itemVariants} className="p-4 rounded-civic border border-civic-border bg-civic-surface dark:bg-civic-dark-surface dark:border-civic-dark-border shadow-civic-card flex items-center justify-between gap-4 relative overflow-hidden">
        <div className={`absolute left-0 top-0 bottom-0 w-1.5 ${stageInfo.barColor}`} />
        <div className="pl-2">
          <h2 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
            {stageInfo.title}
          </h2>
          <p className="text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary mt-0.5">
            {stageInfo.desc}
          </p>
        </div>
        <div className="hidden md:flex items-center gap-2 text-xs font-mono text-civic-text-muted">
          <span>State:</span>
          <strong className="text-civic-text-primary dark:text-civic-dark-text-primary">
            {report.status}
          </strong>
        </div>
      </motion.div>

      {/* Main Workspace Layout: 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* LEFT COLUMN (2 Cols): Evidence, Citizen Description, AI Multimodal Intelligence, Geospatial Map */}
        <motion.div variants={itemVariants} className="lg:col-span-2 space-y-6">
          {/* 1. Photographic Evidence Gallery */}
          <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary flex items-center gap-2">
                Photographic Evidence
              </h2>
              {/* Honest Demo Synthetic Asset indicator */}
              <span className="text-[11px] px-2 py-0.5 rounded font-medium bg-amber-50 text-amber-800 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/60 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-amber-600" />
                [Demo Synthetic Evidence]
              </span>
            </div>

            {resolvedImageUrl && !imageLoadFailed ? (
              <div className="space-y-3">
                <div className="relative rounded-lg overflow-hidden border border-civic-border dark:border-civic-dark-border bg-black/5 aspect-video flex items-center justify-center group">
                  <img
                    src={resolvedImageUrl}
                    alt="Citizen submitted evidence"
                    onError={() => setImageLoadFailed(true)}
                    className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-[1.01]"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      setPreviewImageUri(resolvedImageUrl);
                      setActiveModal('IMAGE_PREVIEW');
                    }}
                    className="absolute bottom-3 right-3 px-3 py-1.5 rounded-lg bg-black/70 hover:bg-black/90 text-white text-xs font-medium backdrop-blur-sm flex items-center gap-1.5 transition-colors shadow-sm"
                  >
                    <Maximize2 className="w-3.5 h-3.5" /> Full Resolution
                  </button>
                </div>

                {/* Evidence Metadata & Honest SHA-256 Hash */}
                <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-civic-text-muted p-3 rounded-lg bg-gray-50 dark:bg-civic-dark-surface-elevated border border-civic-border/60 dark:border-civic-dark-border/60">
                  <div className="flex items-center gap-1.5 font-mono">
                    <Hash className="w-3.5 h-3.5 text-civic-green" />
                    <span className="text-civic-text-secondary dark:text-civic-dark-text-secondary">
                      SHA-256:
                    </span>
                    <span className="truncate max-w-[240px] sm:max-w-xs text-civic-text-primary dark:text-civic-dark-text-primary font-bold">
                      {report.evidences[0]?.file_hash || 'Simulated SHA-256 Fixture'}
                    </span>
                  </div>
                  <span className="text-civic-text-secondary dark:text-civic-dark-text-secondary">
                    {report.evidences[0]?.mime_type || 'image/jpeg'} •{' '}
                    {report.evidences[0]?.file_size_bytes
                      ? `${(report.evidences[0].file_size_bytes / 1024 / 1024).toFixed(2)} MB`
                      : 'High resolution'}
                  </span>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-civic-text-muted border border-dashed rounded-lg bg-gray-50/50 dark:bg-civic-dark-surface-elevated/20">
                {imageLoadFailed
                  ? 'Photographic evidence attachment could not be loaded.'
                  : 'No photographic evidence attached to this report.'}
              </div>
            )}
          </div>

          {/* Edge Preprocessing Provenance Card (Phase 1) */}
          <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-teal-50 text-teal-700 dark:bg-teal-950/50 dark:text-teal-300">
                  <Smartphone className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                    Client Edge Preprocessing Provenance
                  </h2>
                  <span className="text-[10px] text-civic-text-muted font-mono">
                    {report.edgeMetadata
                      ? `Contract v${(report.edgeMetadata as any).contract_version || '1.0.0'} • Client Processor v${(report.edgeMetadata as any).client_processing?.processor_version || '1.0.0'}`
                      : 'Non-edge / legacy citizen submission'}
                  </span>
                </div>
              </div>

              {report.edgeMetadata ? (
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full border bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800">
                  <CheckCircle className="w-3 h-3" /> Preprocessed on Device
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2.5 py-0.5 rounded-full border bg-gray-50 text-gray-600 border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700">
                  Direct Ingestion
                </span>
              )}
            </div>

            {report.edgeMetadata ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-civic-dark-surface-elevated border border-civic-border/60 dark:border-civic-dark-border/60">
                    <span className="block text-[10px] text-civic-text-muted uppercase tracking-wider">Preview Scaled</span>
                    <span className="text-xs font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                      {(report.edgeMetadata as any).image_quality?.width && (report.edgeMetadata as any).image_quality?.height
                        ? `${(report.edgeMetadata as any).image_quality.width} × ${(report.edgeMetadata as any).image_quality.height} px`
                        : 'No image'}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-civic-dark-surface-elevated border border-civic-border/60 dark:border-civic-dark-border/60">
                    <span className="block text-[10px] text-civic-text-muted uppercase tracking-wider">Lighting & Focus</span>
                    <span className="text-xs font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                      {(report.edgeMetadata as any).image_quality
                        ? `${(report.edgeMetadata as any).image_quality.is_blurry ? 'Blurry' : 'Sharp'} (Lum: ${(((report.edgeMetadata as any).image_quality.brightness ?? 0.5) as number).toFixed(2)})`
                        : 'N/A'}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-civic-dark-surface-elevated border border-civic-border/60 dark:border-civic-dark-border/60">
                    <span className="block text-[10px] text-civic-text-muted uppercase tracking-wider">Text Features</span>
                    <span className="text-xs font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                      {(report.edgeMetadata as any).text_features
                        ? `${(report.edgeMetadata as any).text_features.word_count || 0} words normalized`
                        : 'Raw text'}
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-civic-dark-surface-elevated border border-civic-border/60 dark:border-civic-dark-border/60">
                    <span className="block text-[10px] text-civic-text-muted uppercase tracking-wider">On-Device Embeddings</span>
                    <span className="text-xs font-semibold text-amber-600 dark:text-amber-400">
                      Not Enabled (Phase 1)
                    </span>
                  </div>
                </div>

                {/* Structured Linguistic Hints Extracted Deterministically on Edge */}
                {(report.edgeMetadata as any).text_features && (
                  <div className="p-3 rounded-lg bg-teal-50/40 dark:bg-teal-950/20 border border-teal-200/60 dark:border-teal-900/40 text-xs">
                    <span className="font-medium text-teal-800 dark:text-teal-300">Client Linguistic Hints: </span>
                    <span className="text-civic-text-secondary dark:text-civic-dark-text-secondary">
                      {[
                        ...(((report.edgeMetadata as any).text_features.category_terms as string[]) || []).map((t: string) => `[Category: ${t}]`),
                        ...(((report.edgeMetadata as any).text_features.severity_terms as string[]) || []).map((t: string) => `[Severity: ${t}]`),
                        ...(((report.edgeMetadata as any).text_features.urgency_terms as string[]) || []).map((t: string) => `[Urgency: ${t}]`),
                        ...(((report.edgeMetadata as any).text_features.location_terms as string[]) || []).map((t: string) => `[Location: ${t}]`),
                      ].join(' ') || 'No dictionary terms matched'}
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary">
                This report was ingested directly without client-side edge preprocessing metadata. Server-side validation and feature extraction applied canonical defaults.
              </p>
            )}
          </div>

          {/* 2. Citizen Description & Privacy-Aware Attribution */}
          <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
            <h2 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary mb-2">
              Citizen Problem Description
            </h2>
            <p className="text-sm text-civic-text-primary dark:text-civic-dark-text-primary leading-relaxed bg-gray-50/80 dark:bg-civic-dark-surface-elevated/50 p-4 rounded-lg border border-civic-border dark:border-civic-dark-border whitespace-pre-wrap">
              {report.description}
            </p>

            {/* Attribution with Permission-Aware Phone Masking */}
            <div className="mt-4 flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-civic-border dark:border-civic-dark-border text-xs">
              <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-civic-text-muted" />
                <span className="text-civic-text-secondary dark:text-civic-dark-text-secondary">Reporter:</span>
                <span className="font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                  {report.citizenName || 'Registered Citizen'}
                </span>
                {report.citizenId && (
                  <span className="font-mono text-[11px] text-civic-text-muted">
                    ({report.citizenId})
                  </span>
                )}
              </div>

              {/* Privacy Masked Phone */}
              <div className="flex items-center gap-2">
                <Phone className="w-4 h-4 text-civic-text-muted" />
                <span className="text-civic-text-secondary dark:text-civic-dark-text-secondary">Contact:</span>
                <span className="font-mono font-medium text-civic-text-primary dark:text-civic-dark-text-primary">
                  {formatCitizenPhone(report.citizenPhone)}
                </span>
                {canViewPhone ? (
                  <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300 font-sans">
                    <ShieldCheck className="w-3 h-3 text-emerald-600" /> Authorized View
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300 font-sans" title="Phone masked for citizen privacy. Triage authorization required.">
                    <Lock className="w-3 h-3 text-amber-600" /> Masked (Privacy Policy)
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* 3. AI Multimodal Intelligence & Operations Panel */}
          <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-purple-50 text-purple-700 dark:bg-purple-950/50 dark:text-purple-300">
                  <Bot className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                    AI Multimodal Intelligence & Pipeline
                  </h2>
                  <span className="text-[10px] text-civic-text-muted font-mono">
                    {aiResult?.processor_name || 'CivicSense Deterministic Demo Processor'}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {/* Honest AI State Badge */}
                <span className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${aiDisplay.badgeClass}`}>
                  {aiDisplay.isPending ? (
                    <RefreshCw className="w-3 h-3 animate-spin" />
                  ) : (
                    <AlertTriangle className="w-3 h-3" />
                  )}
                  {aiDisplay.badgeText}
                </span>

                <button
                  type="button"
                  onClick={() =>
                    navigate(aiResult?.latest_job?.id ? `/ai-operations?jobId=${aiResult.latest_job.id}` : '/ai-operations')
                  }
                  className="text-xs text-civic-green dark:text-civic-green-light font-medium hover:underline flex items-center gap-1 ml-1"
                >
                  Inspect in Operations <ExternalLink className="w-3 h-3" />
                </button>
              </div>
            </div>

            {/* AI State Explanation */}
            <p className="text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary mb-4">
              {aiDisplay.message}
            </p>

            {/* STATE: SUBMITTED (Not processed yet) */}
            {report.status === 'SUBMITTED' && !aiResult?.ai_analysis && (
              <div className="p-5 rounded-lg bg-gray-50/70 dark:bg-civic-dark-surface-elevated/40 border border-dashed border-civic-border dark:border-civic-dark-border text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary text-center space-y-3">
                <div className="w-10 h-10 mx-auto rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-500">
                  <Cpu className="w-5 h-5" />
                </div>
                <div>
                  <p className="font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                    AI multimodal analysis has not been run for this report
                  </p>
                  <p className="text-[11px] text-civic-text-muted mt-0.5">
                    The citizen submission is in the intake queue. Queueing will invoke the 8-stage multimodal pipeline.
                  </p>
                </div>
                {canVerify && (
                  <CivicButton
                    variant="primary"
                    size="sm"
                    leftIcon={<Play className="w-3.5 h-3.5" />}
                    isLoading={aiProcessMutation.isPending}
                    onClick={() => aiProcessMutation.mutate()}
                  >
                    Queue AI Processing
                  </CivicButton>
                )}
              </div>
            )}

            {/* STATE: AI_PROCESSING (Live Pipeline Progression) */}
            {report.status === 'AI_PROCESSING' && (
              <div className="p-4 rounded-lg bg-purple-50/50 dark:bg-purple-950/20 border border-purple-200 dark:border-purple-900/40 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <RefreshCw className="w-4 h-4 text-purple-600 dark:text-purple-400 animate-spin" />
                    <span className="text-xs font-semibold text-purple-900 dark:text-purple-200">
                      Processing Pipeline Active: Stage{' '}
                      <span className="font-mono text-purple-700 dark:text-purple-300 font-bold">
                        {aiResult?.latest_job?.current_stage || 'ANALYSIS'}
                      </span>
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      refetch();
                      refetchAI();
                    }}
                    className="text-[11px] text-purple-700 dark:text-purple-300 hover:underline flex items-center gap-1"
                  >
                    <RefreshCw className="w-3 h-3" /> Refresh
                  </button>
                </div>

                {/* Progress bar stages */}
                <div className="grid grid-cols-4 sm:grid-cols-8 gap-1 pt-1">
                  {[
                    'INTAKE_VALIDATION',
                    'PREPROCESSING',
                    'VISION_ANALYSIS',
                    'TEXT_ANALYSIS',
                    'FUSION',
                    'DECISION',
                    'HUMAN_REVIEW',
                    'COMPLETED',
                  ].map((st, idx) => {
                    const currentStage = aiResult?.latest_job?.current_stage || 'PREPROCESSING';
                    const allStages = [
                      'INTAKE_VALIDATION',
                      'PREPROCESSING',
                      'VISION_ANALYSIS',
                      'TEXT_ANALYSIS',
                      'FUSION',
                      'DECISION',
                      'HUMAN_REVIEW',
                      'COMPLETED',
                    ];
                    const currentIdx = allStages.indexOf(currentStage);
                    const isPassed = idx < currentIdx;
                    const isCurrent = idx === currentIdx;

                    return (
                      <div
                        key={st}
                        className={`text-[9px] text-center p-1 rounded font-mono truncate ${
                          isCurrent
                            ? 'bg-purple-600 text-white font-bold animate-pulse'
                            : isPassed
                            ? 'bg-purple-200 text-purple-900 dark:bg-purple-900/50 dark:text-purple-200'
                            : 'bg-gray-100 text-gray-400 dark:bg-civic-dark-surface-elevated dark:text-gray-600'
                        }`}
                        title={st}
                      >
                        {idx + 1}. {st.split('_')[0]}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* RESULTS: Inferences Available */}
            {(aiResult?.ai_analysis || latestAi) && (
              <div className="space-y-4">
                {/* 1. Core Decision Metrics */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3 rounded-lg border border-civic-border bg-gray-50/50 dark:border-civic-dark-border dark:bg-civic-dark-surface-elevated/40">
                    <span className="text-[11px] text-civic-text-muted font-medium uppercase tracking-wider block">
                      AI Confidence
                    </span>
                    <span className="text-xl font-bold text-civic-text-primary dark:text-civic-dark-text-primary font-mono">
                      {Math.round(
                        ((aiResult?.ai_analysis?.confidence ?? report.confidence ?? 0) as number) * 100
                      )}
                      %
                    </span>
                  </div>

                  <div className="p-3 rounded-lg border border-civic-border bg-gray-50/50 dark:border-civic-dark-border dark:bg-civic-dark-surface-elevated/40">
                    <span className="text-[11px] text-civic-text-muted font-medium uppercase tracking-wider block">
                      Modality Agreement
                    </span>
                    <span className="text-xl font-bold text-civic-text-primary dark:text-civic-dark-text-primary font-mono">
                      {Math.round(
                        ((aiResult?.ai_analysis?.evidence_agreement ?? report.evidenceAgreement ?? 0) as number) * 100
                      )}
                      %
                    </span>
                  </div>

                  <div className="p-3 rounded-lg border border-civic-border bg-gray-50/50 dark:border-civic-dark-border dark:bg-civic-dark-surface-elevated/40">
                    <span className="text-[11px] text-civic-text-muted font-medium uppercase tracking-wider block">
                      Inferred Category
                    </span>
                    <span className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary truncate block mt-1">
                      {aiResult?.ai_analysis?.predicted_category || latestAi?.predicted_category || report.category}
                    </span>
                  </div>

                  <div className="p-3 rounded-lg border border-civic-border bg-gray-50/50 dark:border-civic-dark-border dark:bg-civic-dark-surface-elevated/40">
                    <span className="text-[11px] text-civic-text-muted font-medium uppercase tracking-wider block">
                      Suggested Severity
                    </span>
                    <span className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary truncate block mt-1">
                      {aiResult?.ai_analysis?.severity || report.severity}
                    </span>
                  </div>
                </div>

                {/* 2. Multimodal Breakdown: Vision vs. Text */}
                {aiResult?.ai_analysis?.analysis_metadata && (
                  <div className="p-3.5 rounded-lg border border-purple-100 bg-purple-50/30 dark:border-purple-900/40 dark:bg-purple-950/20 text-xs space-y-3">
                    <div className="flex items-center justify-between border-b border-purple-100 dark:border-purple-900/40 pb-2">
                      <span className="font-semibold text-civic-text-primary dark:text-civic-dark-text-primary flex items-center gap-1.5">
                        <GitCompare className="w-3.5 h-3.5 text-purple-600" />
                        Multimodal Analysis Breakdown
                      </span>
                      <span className="text-[10px] text-civic-text-muted font-mono">
                        Latency: {aiResult.ai_analysis.analysis_metadata.processing_duration_ms ?? 185} ms
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      {/* Vision Prediction */}
                      <div className="p-2.5 rounded bg-white/80 dark:bg-black/20 border border-purple-200/50 dark:border-purple-800/40 space-y-1">
                        <span className="text-[10px] text-purple-800 dark:text-purple-300 font-bold uppercase tracking-wider block">
                          Vision Analysis (Photo Evidence)
                        </span>
                        <div className="flex justify-between text-[11px]">
                          <span className="text-civic-text-muted">Inferred Defect:</span>
                          <span className="font-medium text-civic-text-primary dark:text-civic-dark-text-primary">
                            {aiResult.ai_analysis.analysis_metadata.vision_prediction?.category || 'Visual Defect'}
                          </span>
                        </div>
                        <div className="flex justify-between text-[11px]">
                          <span className="text-civic-text-muted">Vision Confidence:</span>
                          <span className="font-mono font-medium text-civic-text-primary dark:text-civic-dark-text-primary">
                            {Math.round((aiResult.ai_analysis.analysis_metadata.vision_prediction?.confidence ?? 0.8) * 100)}%
                          </span>
                        </div>
                        <div className="flex justify-between text-[11px]">
                          <span className="text-civic-text-muted">Severity:</span>
                          <span className="font-medium text-civic-text-primary dark:text-civic-dark-text-primary">
                            {aiResult.ai_analysis.analysis_metadata.vision_prediction?.severity || 'MEDIUM'}
                          </span>
                        </div>
                      </div>

                      {/* Text Analysis */}
                      <div className="p-2.5 rounded bg-white/80 dark:bg-black/20 border border-purple-200/50 dark:border-purple-800/40 space-y-1">
                        <span className="text-[10px] text-purple-800 dark:text-purple-300 font-bold uppercase tracking-wider block">
                          Text Pattern Analysis (Citizen Text)
                        </span>
                        <div className="flex justify-between text-[11px]">
                          <span className="text-civic-text-muted">Inferred Defect:</span>
                          <span className="font-medium text-civic-text-primary dark:text-civic-dark-text-primary">
                            {aiResult.ai_analysis.analysis_metadata.text_prediction?.category || report.category}
                          </span>
                        </div>
                        <div className="flex justify-between text-[11px]">
                          <span className="text-civic-text-muted">Text Confidence:</span>
                          <span className="font-mono font-medium text-civic-text-primary dark:text-civic-dark-text-primary">
                            {Math.round((aiResult.ai_analysis.analysis_metadata.text_prediction?.confidence ?? 0.8) * 100)}%
                          </span>
                        </div>
                        <div className="flex justify-between text-[11px]">
                          <span className="text-civic-text-muted">Severity:</span>
                          <span className="font-medium text-civic-text-primary dark:text-civic-dark-text-primary">
                            {aiResult.ai_analysis.analysis_metadata.text_prediction?.severity || report.severity}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Matched Keywords and Agreement */}
                    {aiResult.ai_analysis.analysis_metadata.text_prediction?.matched_terms &&
                      aiResult.ai_analysis.analysis_metadata.text_prediction.matched_terms.length > 0 && (
                        <div className="text-[11px] pt-1">
                          <span className="text-civic-text-muted">Matched Linguistic Signals: </span>
                          <span className="font-mono text-purple-700 dark:text-purple-300 font-medium">
                            {aiResult.ai_analysis.analysis_metadata.text_prediction.matched_terms.join(', ')}
                          </span>
                        </div>
                      )}
                  </div>
                )}

                {/* 3. Review Required / Rationale Callout */}
                {(report.status === 'VERIFICATION_REQUIRED' ||
                  aiResult?.latest_job?.review_required ||
                  aiResult?.ai_analysis?.review_required) && (
                  <div className="p-3.5 rounded-lg border border-amber-300 bg-amber-50/60 dark:border-amber-800/60 dark:bg-amber-950/30 text-xs space-y-1">
                    <div className="flex items-center gap-1.5 text-amber-800 dark:text-amber-200 font-semibold">
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                      <span>Human Triage Review Rationale</span>
                    </div>
                    <p className="text-amber-900 dark:text-amber-300 text-[11px] pl-5">
                      {aiResult?.latest_job?.review_reason ||
                        aiResult?.ai_analysis?.analysis_metadata?.decision_rationale ||
                        'Confidence score or modality agreement falls below autonomous threshold. Officer verification required prior to municipal dispatch.'}
                    </p>
                  </div>
                )}

                {/* 4. Side-by-side Human Verification vs AI Recommendation (if verified) */}
                {(aiResult?.verification || latestVerification || ['VERIFIED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'].includes(report.status)) && (
                  <div className="p-3.5 rounded-lg border border-emerald-200 bg-emerald-50/40 dark:border-emerald-900/50 dark:bg-emerald-950/20 text-xs space-y-2">
                    <div className="flex items-center justify-between border-b border-emerald-200 dark:border-emerald-900/40 pb-1.5">
                      <span className="font-semibold text-emerald-900 dark:text-emerald-200 flex items-center gap-1.5">
                        <CheckCircle className="w-4 h-4 text-emerald-600" />
                        Human Verification vs. AI Proposal
                      </span>
                      <span className="text-[10px] text-emerald-700 dark:text-emerald-300 font-mono">
                        {aiResult?.verification?.decision || latestVerification?.decision || 'CONFIRMED'}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                      <div className="p-2 rounded bg-white/70 dark:bg-black/20 border border-emerald-200/50 dark:border-emerald-800/40">
                        <span className="text-[10px] text-civic-text-muted uppercase font-bold block mb-1">
                          Original AI Proposal
                        </span>
                        <p>Category: <strong className="font-mono">{aiResult?.ai_analysis?.predicted_category || latestAi?.predicted_category || report.category}</strong></p>
                        <p>Severity: <strong className="font-mono">{aiResult?.ai_analysis?.severity || latestAi?.severity || report.severity}</strong></p>
                      </div>

                      <div className="p-2 rounded bg-white/70 dark:bg-black/20 border border-emerald-200/50 dark:border-emerald-800/40">
                        <span className="text-[10px] text-civic-text-muted uppercase font-bold block mb-1">
                          Officer Verified Verdict
                        </span>
                        <p>Category: <strong className="font-mono">{aiResult?.verification?.verified_category || latestVerification?.verified_category || report.category}</strong></p>
                        <p>Severity: <strong className="font-mono">{aiResult?.verification?.verified_severity || latestVerification?.verified_severity || report.severity}</strong></p>
                        <p className="text-[10px] text-civic-text-muted mt-0.5">
                          Reviewer: {aiResult?.verification?.reviewer_id || latestVerification?.reviewer_id || 'Triage Officer'}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* 5. Honest AI Architecture Provenance Footnote */}
                <div className="p-3 rounded-lg border border-civic-border bg-gray-50/50 dark:border-civic-dark-border dark:bg-civic-dark-surface-elevated/30 text-[11px] text-civic-text-secondary dark:text-civic-dark-text-secondary space-y-1 font-mono">
                  <div className="flex justify-between">
                    <span>Processor Architecture:</span>
                    <strong className="text-civic-text-primary dark:text-civic-dark-text-primary">
                      {aiResult?.processor_name || 'CivicSense Deterministic Demo Processor'}
                    </strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Execution Mode:</span>
                    <span>{aiResult?.execution_mode || (env.isMock ? 'Demo Simulation' : 'API Backend')}</span>
                  </div>
                  <div className="text-[10px] text-civic-text-muted pt-1 border-t border-civic-border dark:border-civic-dark-border">
                    {aiResult?.disclaimer ||
                      'Prototype AI inference provides probabilistic operational recommendations, not certified ground truth.'}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 4. Geospatial Defect Location */}
          <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                Geospatial Defect Location
              </h2>
              <a
                href={`https://maps.google.com/?q=${report.latitude},${report.longitude}`}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-civic-green hover:underline flex items-center gap-1 font-medium"
              >
                External Maps <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            <div className="flex items-center gap-1.5 text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary mb-3">
              <MapPin className="w-3.5 h-3.5 text-civic-green shrink-0" />
              <span>{report.addressHint || 'Physical GPS coordinates recorded on citizen device'}</span>
              <span className="text-civic-text-muted font-mono">
                ({report.latitude.toFixed(5)}, {report.longitude.toFixed(5)})
              </span>
            </div>

            <div className="h-64 rounded-lg overflow-hidden border border-civic-border dark:border-civic-dark-border">
              <MapRenderer
                center={[report.latitude, report.longitude]}
                zoom={15}
                points={[
                  {
                    id: report.id,
                    trackingId: report.trackingId,
                    latitude: report.latitude,
                    longitude: report.longitude,
                    category: report.category,
                    severity: report.severity,
                    description: report.description,
                    addressHint: report.addressHint,
                  },
                ]}
                className="w-full h-full"
              />
            </div>
          </div>
        </motion.div>

        {/* RIGHT COLUMN (1 Col): Operational Actions, SLA & Department, Verification Decisions, Internal Notes, Audit Trail */}
        <motion.div variants={itemVariants} className="space-y-6">
          {/* Associated Aggregated Issue Card */}
          {report.issueId && (
            <div className="p-5 rounded-civic bg-blue-50/60 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900/60 shadow-civic-card space-y-3">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-700 dark:text-blue-300 uppercase tracking-wider">
                  <Layers className="w-3.5 h-3.5" />
                  Associated Issue
                </span>
                <span className="text-[11px] font-mono text-blue-600 dark:text-blue-400 bg-blue-100/80 dark:bg-blue-900/60 px-2 py-0.5 rounded border border-blue-200 dark:border-blue-800">
                  iss-{report.issueId.substring(0, 8)}
                </span>
              </div>

              <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                This citizen report is aggregated under a confirmed civic defect cluster.
              </p>

              <CivicButton
                variant="primary"
                size="sm"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                rightIcon={<ExternalLink className="w-3.5 h-3.5" />}
                onClick={() => navigate(`/issues/${report.issueId}`)}
              >
                View Aggregated Issue
              </CivicButton>
            </div>
          )}

          {/* 1. Operational Actions Card (State-aware for ALL 11 states) */}
          <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
            <h2 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary mb-1">
              Operational Actions
            </h2>
            <p className="text-xs text-civic-text-muted mb-4">
              State transitions enforced strictly by municipal state-machine rules.
            </p>

            <div className="space-y-2.5">
              {/* STATE: SUBMITTED */}
              {report.status === 'SUBMITTED' && (
                <>
                  <CivicButton
                    variant="primary"
                    size="md"
                    className="w-full"
                    leftIcon={<Play className="w-4 h-4" />}
                    isLoading={aiProcessMutation.isPending}
                    onClick={() => aiProcessMutation.mutate()}
                  >
                    Run AI Inference Pipeline
                  </CivicButton>

                  {canClose && (
                    <CivicButton
                      variant="outline"
                      size="md"
                      className="w-full text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20"
                      leftIcon={<XCircle className="w-4 h-4" />}
                      onClick={() => setActiveModal('REJECT')}
                    >
                      Reject / Discard (Spam or Abuse)
                    </CivicButton>
                  )}
                </>
              )}

              {/* STATE: AI_PROCESSING */}
              {report.status === 'AI_PROCESSING' && (
                <>
                  <div className="p-3 rounded-lg bg-purple-50/70 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-900/50 text-xs text-purple-900 dark:text-purple-200 flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-purple-600 animate-ping shrink-0" />
                    <div>
                      <span className="font-semibold block">Inference Pipeline Active</span>
                      <span className="text-[11px] text-purple-700 dark:text-purple-300">
                        Current Stage: {aiResult?.latest_job?.current_stage || 'PREPROCESSING'}
                      </span>
                    </div>
                  </div>

                  {env.isMock ? (
                    <CivicButton
                      variant="primary"
                      size="md"
                      className="w-full"
                      isLoading={transitionMutation.isPending}
                      onClick={() =>
                        transitionMutation.mutate({
                          nextStatus: 'AI_PROCESSED',
                          notes: 'Completed automated AI classification pipeline (Mock Demo)',
                        })
                      }
                    >
                      Complete AI Pipeline (Mock Demo)
                    </CivicButton>
                  ) : (
                    <CivicButton
                      variant="outline"
                      size="md"
                      className="w-full"
                      leftIcon={<RefreshCw className="w-4 h-4" />}
                      onClick={() => {
                        refetch();
                        refetchAI();
                      }}
                    >
                      Refresh Pipeline Status
                    </CivicButton>
                  )}

                  <CivicButton
                    variant="outline"
                    size="md"
                    className="w-full"
                    isLoading={transitionMutation.isPending}
                    onClick={() =>
                      transitionMutation.mutate({
                        nextStatus: 'VERIFICATION_REQUIRED',
                        notes: 'Escalated directly to officer triage inspection',
                      })
                    }
                  >
                    Escalate to Human Triage
                  </CivicButton>
                </>
              )}

              {/* STATE: AI_PROCESSED */}
              {report.status === 'AI_PROCESSED' && (
                <>
                  <CivicButton
                    variant="primary"
                    size="md"
                    className="w-full"
                    leftIcon={<CheckCircle className="w-4 h-4" />}
                    isLoading={transitionMutation.isPending}
                    onClick={() =>
                      transitionMutation.mutate({
                        nextStatus: 'VERIFIED',
                        notes: 'Officer confirmed AI recommendations and verified ticket authenticity',
                      })
                    }
                  >
                    Confirm AI Assessment (Mark Verified)
                  </CivicButton>

                  <CivicButton
                    variant="secondary"
                    size="md"
                    className="w-full"
                    leftIcon={<UserCheck className="w-4 h-4" />}
                    isLoading={transitionMutation.isPending}
                    onClick={() =>
                      transitionMutation.mutate({
                        nextStatus: 'VERIFICATION_REQUIRED',
                        notes: 'Routed to officer for detailed manual review',
                      })
                    }
                  >
                    Route to Manual Verification
                  </CivicButton>

                  {canPrioritize && (
                    <CivicButton
                      variant="outline"
                      size="md"
                      className="w-full"
                      leftIcon={<Send className="w-4 h-4" />}
                      onClick={() => {
                        setTargetPriority(report.priority);
                        setActiveModal('PRIORITIZE');
                      }}
                    >
                      Direct Operational Priority
                    </CivicButton>
                  )}
                </>
              )}

              {/* STATE: VERIFICATION_REQUIRED */}
              {report.status === 'VERIFICATION_REQUIRED' && (
                <>
                  {canVerify && (
                    <CivicButton
                      variant="primary"
                      size="md"
                      className="w-full"
                      leftIcon={<CheckCircle className="w-4 h-4" />}
                      onClick={() => {
                        setVerifiedCategory(report.category);
                        setVerifiedSeverity(report.severity);
                        setActiveModal('VERIFY');
                      }}
                    >
                      Verify & Confirm Report
                    </CivicButton>
                  )}

                  {canClose && (
                    <CivicButton
                      variant="danger"
                      size="md"
                      className="w-full"
                      leftIcon={<XCircle className="w-4 h-4" />}
                      onClick={() => setActiveModal('REJECT')}
                    >
                      Reject or Mark Duplicate
                    </CivicButton>
                  )}
                </>
              )}

              {/* STATE: VERIFIED */}
              {report.status === 'VERIFIED' && (
                <>
                  {canPrioritize && (
                    <CivicButton
                      variant="primary"
                      size="md"
                      className="w-full"
                      leftIcon={<Send className="w-4 h-4" />}
                      onClick={() => {
                        setTargetPriority(report.priority);
                        setActiveModal('PRIORITIZE');
                      }}
                    >
                      Set Operational Priority (SLA)
                    </CivicButton>
                  )}

                  {canAssign && (
                    <CivicButton
                      variant="secondary"
                      size="md"
                      className="w-full"
                      leftIcon={<Building className="w-4 h-4" />}
                      onClick={() => {
                        setTargetDepartment(report.department || 'Roads & Bridges');
                        setActiveModal('ASSIGN');
                      }}
                    >
                      Assign Department & Crew
                    </CivicButton>
                  )}

                  {canClose && (
                    <CivicButton
                      variant="ghost"
                      size="sm"
                      className="w-full text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20"
                      onClick={() => setActiveModal('REJECT')}
                    >
                      Decline / Close Ticket
                    </CivicButton>
                  )}
                </>
              )}

              {/* STATE: PRIORITIZED */}
              {report.status === 'PRIORITIZED' && (
                <>
                  {canAssign && (
                    <CivicButton
                      variant="primary"
                      size="md"
                      className="w-full"
                      leftIcon={<Building className="w-4 h-4" />}
                      onClick={() => {
                        setTargetDepartment(report.department || 'Roads & Bridges');
                        setActiveModal('ASSIGN');
                      }}
                    >
                      Assign Department & Crew
                    </CivicButton>
                  )}

                  {canStartWork && allowedTransitions.includes('IN_PROGRESS') && (
                    <CivicButton
                      variant="secondary"
                      size="md"
                      className="w-full"
                      leftIcon={<Flame className="w-4 h-4" />}
                      isLoading={transitionMutation.isPending}
                      onClick={() =>
                        transitionMutation.mutate({
                          nextStatus: 'IN_PROGRESS',
                          notes: 'Immediate crew mobilization dispatched',
                        })
                      }
                    >
                      Start Immediate Work
                    </CivicButton>
                  )}
                </>
              )}

              {/* STATE: ASSIGNED */}
              {report.status === 'ASSIGNED' && (
                <>
                  {canStartWork && (
                    <CivicButton
                      variant="primary"
                      size="md"
                      className="w-full bg-indigo-600 hover:bg-indigo-700"
                      isLoading={acknowledgeJobMutation.isPending}
                      leftIcon={<Flame className="w-4 h-4" />}
                      onClick={() => acknowledgeJobMutation.mutate()}
                    >
                      Acknowledge Job & Start Work
                    </CivicButton>
                  )}

                  <CivicButton
                    variant="outline"
                    size="md"
                    className="w-full text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20"
                    leftIcon={<XCircle className="w-4 h-4" />}
                    onClick={() => {
                      setDeclineReason('OUT_OF_JURISDICTION');
                      setDeclineNotes('');
                      setActiveModal('DECLINE_JOB');
                    }}
                  >
                    Decline Job & Return to Triage
                  </CivicButton>

                  {canAssign && (
                    <CivicButton
                      variant="ghost"
                      size="sm"
                      className="w-full"
                      leftIcon={<Building className="w-4 h-4" />}
                      onClick={() => {
                        setTargetDepartment(report.department || 'Roads & Bridges');
                        setActiveModal('ASSIGN');
                      }}
                    >
                      Reassign Department / Lead
                    </CivicButton>
                  )}
                </>
              )}

              {/* STATE: IN_PROGRESS */}
              {report.status === 'IN_PROGRESS' && (
                <>
                  {canResolve && (
                    <CivicButton
                      variant="primary"
                      size="md"
                      className="w-full"
                      leftIcon={<CheckCircle className="w-4 h-4" />}
                      onClick={() => setActiveModal('RESOLVE')}
                    >
                      Mark Work Resolved
                    </CivicButton>
                  )}

                  {canAssign && (
                    <CivicButton
                      variant="outline"
                      size="md"
                      className="w-full"
                      leftIcon={<Building className="w-4 h-4" />}
                      onClick={() => {
                        setTargetDepartment(report.department || 'Roads & Bridges');
                        setActiveModal('ASSIGN');
                      }}
                    >
                      Reassign Crew / Department
                    </CivicButton>
                  )}
                </>
              )}

              {/* STATE: RESOLVED */}
              {report.status === 'RESOLVED' && (
                <>
                  {canVerifyResolution && (
                    <CivicButton
                      variant="primary"
                      size="md"
                      className="w-full"
                      isLoading={transitionMutation.isPending}
                      leftIcon={<FileCheck className="w-4 h-4" />}
                      onClick={() =>
                        transitionMutation.mutate({
                          nextStatus: 'RESOLUTION_VERIFIED',
                          notes: 'Municipal inspector confirmed defect physical remediation and signed off.',
                        })
                      }
                    >
                      Verify Resolution & Sign Off
                    </CivicButton>
                  )}

                  <CivicButton
                    variant="outline"
                    size="md"
                    className="w-full"
                    isLoading={transitionMutation.isPending}
                    leftIcon={<RotateCcw className="w-4 h-4" />}
                    onClick={() =>
                      transitionMutation.mutate({
                        nextStatus: 'IN_PROGRESS',
                        notes: 'Quality inspection failed. Defect repair inadequate. Reopening work order.',
                      })
                    }
                  >
                    Reopen Work Order
                  </CivicButton>
                </>
              )}

              {/* STATE: RESOLUTION_VERIFIED */}
              {report.status === 'RESOLUTION_VERIFIED' && (
                <CivicButton
                  variant="primary"
                  size="md"
                  className="w-full"
                  isLoading={transitionMutation.isPending}
                  leftIcon={<CheckCircle className="w-4 h-4" />}
                  onClick={() =>
                    transitionMutation.mutate({
                      nextStatus: 'CLOSED',
                      notes: 'Administrative ticket archived after formal resolution verification.',
                    })
                  }
                >
                  Close & Archive Record
                </CivicButton>
              )}

              {/* STATE: CLOSED */}
              {report.status === 'CLOSED' && (
                <div className="p-4 rounded-lg bg-gray-50 dark:bg-civic-dark-surface-elevated text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary border border-civic-border dark:border-civic-dark-border text-center space-y-1.5">
                  <div className="font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                    Record Closed & Archived
                  </div>
                  <p className="text-civic-text-muted">
                    This ticket is in terminal state <strong>CLOSED</strong>. No further status changes are permitted.
                  </p>
                  {report.closureReason && (
                    <div className="mt-2 pt-2 border-t border-civic-border dark:border-civic-dark-border text-[11px] font-mono text-civic-text-secondary dark:text-civic-dark-text-secondary">
                      Closure Reason: <span className="font-bold">{report.closureReason}</span>
                    </div>
                  )}
                  {report.closureNotes && (
                    <div className="italic text-[11px] text-civic-text-muted">
                      "{report.closureNotes}"
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Citizen Reporter Information (Authorized View Only) */}
          <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary flex items-center gap-1.5">
                <User className="w-4 h-4 text-civic-green" />
                Citizen Reporter Information
              </h2>
              <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/60">
                <Lock className="w-3 h-3" />
                Authorized View Only
              </span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-gray-50 dark:bg-civic-dark-surface-elevated border border-civic-border/60 dark:border-civic-dark-border/60 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-civic-text-muted flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5" /> Full Name:
                  </span>
                  <strong className="text-civic-text-primary dark:text-civic-dark-text-primary font-medium text-right">
                    {report.citizenName || 'Unspecified Citizen'}
                  </strong>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-civic-text-muted flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5" /> Phone Number:
                  </span>
                  {report.citizenPhone ? (
                    <a
                      href={`tel:${report.citizenPhone}`}
                      className="text-civic-green hover:underline font-mono font-medium text-right"
                    >
                      {report.citizenPhone}
                    </a>
                  ) : (
                    <span className="text-civic-text-muted font-mono text-right">
                      Not provided
                    </span>
                  )}
                </div>
                <div className="flex justify-between items-center gap-2">
                  <span className="text-civic-text-muted flex items-center gap-1.5 shrink-0">
                    <Mail className="w-3.5 h-3.5" /> Email Address:
                  </span>
                  {report.citizenEmail ? (
                    <a
                      href={`mailto:${report.citizenEmail}`}
                      className="text-civic-green hover:underline font-medium text-right break-all max-w-[200px]"
                    >
                      {report.citizenEmail}
                    </a>
                  ) : (
                    <span className="text-civic-text-muted text-right">
                      Not provided
                    </span>
                  )}
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-civic-text-muted flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5" /> Postal Code:
                  </span>
                  <span className="font-mono text-civic-text-primary dark:text-civic-dark-text-primary text-right">
                    {report.citizenPostalCode || 'Not provided'}
                  </span>
                </div>
                {report.citizenId && (
                  <div className="flex justify-between items-center pt-1 border-t border-civic-border/40 dark:border-civic-dark-border/40">
                    <span className="text-civic-text-muted text-[11px]">Citizen ID:</span>
                    <span className="font-mono text-[11px] text-civic-text-secondary dark:text-civic-dark-text-secondary text-right">
                      {report.citizenId}
                    </span>
                  </div>
                )}
              </div>

              <div className="flex items-start gap-1.5 text-[11px] text-civic-text-muted">
                <ShieldCheck className="w-3.5 h-3.5 text-civic-green shrink-0 mt-0.5" />
                <span>
                  Citizen contact details are confidential and accessible solely for official municipal triage, investigation, and resolution verification.
                </span>
              </div>
            </div>
          </div>

          {/* 2. Department Assignment & Response SLA Tracking */}
          <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary flex items-center gap-1.5">
                <Building className="w-4 h-4 text-civic-green" />
                Assignment & Municipal SLA
              </h2>
              {canAssign && (
                <button
                  type="button"
                  onClick={() => {
                    setTargetDepartment(report.department || 'Roads & Bridges');
                    setActiveModal('ASSIGN');
                  }}
                  className="text-xs font-medium text-civic-green hover:underline"
                >
                  Edit
                </button>
              )}
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-lg bg-gray-50 dark:bg-civic-dark-surface-elevated border border-civic-border/60 dark:border-civic-dark-border/60 space-y-2">
                <div className="flex justify-between">
                  <span className="text-civic-text-muted">Assigned Department:</span>
                  <strong className="text-civic-text-primary dark:text-civic-dark-text-primary text-right">
                    {report.department || 'General Public Works'}
                  </strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-civic-text-muted">Lead Officer / Supervisor:</span>
                  <span className="text-civic-text-primary dark:text-civic-dark-text-primary font-medium text-right">
                    {report.assignedOfficer || 'Pending Crew Assignment'}
                  </span>
                </div>
              </div>

              {/* SLA Urgency Pill */}
              <div className="p-3 rounded-lg border border-civic-border dark:border-civic-dark-border space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-civic-text-muted">Target SLA:</span>
                  <span className="font-mono font-bold text-civic-text-primary dark:text-civic-dark-text-primary">
                    {slaInfo.targetHours} Hours Target
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-civic-text-muted">SLA Status:</span>
                  {slaInfo.isBreached ? (
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-red-100 text-red-800 dark:bg-red-950/50 dark:text-red-300">
                      <ShieldAlert className="w-3 h-3 text-red-600" /> Breached
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300">
                      <Clock className="w-3 h-3 text-emerald-600" /> {slaInfo.remainingHours}h remaining
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-civic-text-muted text-right">
                  Deadline: {formatDateTime(slaInfo.deadline)}
                </div>
              </div>
            </div>
          </div>

          {/* 3. Verification Decisions Record (if verified) */}
          {latestVerification && (
            <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
              <div className="flex items-center gap-2 mb-3">
                <UserCheck className="w-4 h-4 text-civic-green" />
                <h2 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                  Verification Verdict
                </h2>
              </div>

              <div className="p-3.5 rounded-lg bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/50 text-xs space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-civic-text-muted">Decision:</span>
                  <span className="font-bold font-mono px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 text-[11px]">
                    {latestVerification.decision}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-civic-text-muted">Reviewer:</span>
                  <strong className="text-civic-text-primary dark:text-civic-dark-text-primary">
                    {latestVerification.reviewer_id || 'Triage Officer'}
                  </strong>
                </div>
                {latestVerification.verified_category && (
                  <div className="flex justify-between">
                    <span className="text-civic-text-muted">Confirmed Category:</span>
                    <span>{latestVerification.verified_category}</span>
                  </div>
                )}
                {latestVerification.verified_severity && (
                  <div className="flex justify-between">
                    <span className="text-civic-text-muted">Confirmed Severity:</span>
                    <span className="font-semibold">{latestVerification.verified_severity}</span>
                  </div>
                )}
                {latestVerification.notes && (
                  <div className="pt-2 border-t border-emerald-100 dark:border-emerald-900/40 text-[11px] italic text-civic-text-secondary dark:text-civic-dark-text-secondary">
                    "{latestVerification.notes}"
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 4. Internal Staff Notes Section (Separate from Citizen Description) */}
          <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
            <div className="flex items-center gap-2 mb-2">
              <MessageSquare className="w-4 h-4 text-civic-green" />
              <h2 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                Internal Staff Notes
              </h2>
            </div>
            <p className="text-[11px] text-civic-text-muted mb-3">
              Confidential operational communications; strictly hidden from citizen feeds.
            </p>

            {/* Existing internal notes */}
            <div className="space-y-2.5 max-h-56 overflow-y-auto pr-1">
              {report.internalNotes && report.internalNotes.length > 0 ? (
                report.internalNotes.map((note) => (
                  <div
                    key={note.id}
                    className="p-3 rounded-lg bg-gray-50 dark:bg-civic-dark-surface-elevated border border-civic-border/70 dark:border-civic-dark-border/70 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                        {note.author} ({note.authorRole})
                      </span>
                      <span className="text-civic-text-muted font-mono" title={formatDateFull(note.createdAt)}>
                        {formatTime(note.createdAt)}
                      </span>
                    </div>
                    <p className="text-civic-text-secondary dark:text-civic-dark-text-secondary leading-relaxed">
                      {note.content}
                    </p>
                  </div>
                ))
              ) : (
                <div className="p-4 rounded-lg bg-gray-50/70 dark:bg-civic-dark-surface-elevated/40 text-center text-xs text-civic-text-muted italic">
                  No internal staff notes posted yet.
                </div>
              )}
            </div>

            {/* Add note input form */}
            <div className="mt-3 pt-3 border-t border-civic-border dark:border-civic-dark-border space-y-2">
              <textarea
                rows={2}
                value={newNoteContent}
                onChange={(e) => setNewNoteContent(e.target.value)}
                placeholder="Log internal crew dispatch note, inspection finding, or instruction..."
                className="w-full p-2.5 text-xs rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border"
              />
              <CivicButton
                variant="outline"
                size="sm"
                className="w-full"
                disabled={!newNoteContent.trim() || addNoteMutation.isPending}
                isLoading={addNoteMutation.isPending}
                leftIcon={<Plus className="w-3.5 h-3.5" />}
                onClick={() => addNoteMutation.mutate(newNoteContent.trim())}
              >
                Post Operational Note
              </CivicButton>
            </div>
          </div>

          {/* Department Assignment History */}
          <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
            <div className="flex items-center gap-2 mb-3">
              <Building className="w-4 h-4 text-civic-green" />
              <h2 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                Department Assignment History
              </h2>
            </div>

            {report.assignments && report.assignments.length > 0 ? (
              <div className="space-y-3">
                {report.assignments.map((assignment) => (
                  <div
                    key={assignment.id}
                    className="p-3 rounded-lg border border-civic-border/70 dark:border-civic-dark-border/70 bg-gray-50/50 dark:bg-civic-dark-surface-elevated/40 text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                        {assignment.department_name}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          assignment.status === 'COMPLETED'
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                            : assignment.status === 'REJECTED'
                            ? 'bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300'
                            : assignment.status === 'IN_PROGRESS'
                            ? 'bg-orange-100 text-orange-800 dark:bg-orange-950/60 dark:text-orange-300'
                            : 'bg-indigo-100 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300'
                        }`}
                      >
                        {assignment.status}
                      </span>
                    </div>

                    <div className="text-[11px] text-civic-text-muted flex justify-between">
                      <span>Assigned by: {assignment.assigned_by}</span>
                      <span title={formatDateFull(assignment.created_at)}>
                        {formatDateTime(assignment.created_at)}
                      </span>
                    </div>

                    {assignment.assigned_to_officer && (
                      <div className="text-[11px] text-civic-text-secondary dark:text-civic-dark-text-secondary">
                        Officer: {assignment.assigned_to_officer}
                      </div>
                    )}

                    {assignment.rejection_reason && (
                      <div className="mt-1 p-2 rounded bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 text-[11px] border border-red-200 dark:border-red-900/40 space-y-0.5">
                        <div className="font-bold">Declined: {assignment.rejection_reason}</div>
                        {assignment.notes && <div className="italic">"{assignment.notes}"</div>}
                      </div>
                    )}

                    {assignment.status === 'COMPLETED' && assignment.notes && (
                      <div className="mt-1 p-2 rounded bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 text-[11px] border border-emerald-200 dark:border-emerald-900/40">
                        <div className="font-medium">Completion Report:</div>
                        <div className="italic">"{assignment.notes}"</div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 rounded-lg bg-gray-50/70 dark:bg-civic-dark-surface-elevated/40 text-center text-xs text-civic-text-muted italic">
                No departmental assignments recorded yet.
              </div>
            )}
          </div>

          {/* 5. Audit Trail & Timeline */}
          <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
            <div className="flex items-center gap-2 mb-4">
              <Clock className="w-4 h-4 text-civic-green" />
              <h2 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                Audit Trail & History
              </h2>
            </div>

            <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-civic-border dark:before:bg-civic-dark-border">
              {report.auditTrail.map((ev) => (
                <div key={ev.id} className="relative text-xs">
                  <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-civic-green border-2 border-white dark:border-civic-dark-surface" />
                  <div className="flex items-center justify-between gap-1 text-[11px] text-civic-text-muted mb-0.5">
                    <span className="font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                      {ev.actor}
                    </span>
                    <span className="font-mono" title={formatDateFull(ev.timestamp)}>
                      {formatTime(ev.timestamp)}
                    </span>
                  </div>
                  <p className="text-civic-text-secondary dark:text-civic-dark-text-secondary">
                    {ev.action}
                  </p>
                  {ev.fromStatus && ev.toStatus && (
                    <div className="mt-1 flex items-center gap-1.5 text-[10px] font-mono">
                      <span className="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-civic-dark-surface-elevated text-civic-text-muted">
                        {ev.fromStatus}
                      </span>
                      <span>→</span>
                      <span className="px-1.5 py-0.5 rounded bg-civic-green/10 text-civic-green font-bold">
                        {ev.toStatus}
                      </span>
                    </div>
                  )}
                  {ev.notes && (
                    <p className="mt-1.5 p-2 rounded bg-gray-50 dark:bg-civic-dark-surface-elevated text-[11px] italic text-civic-text-muted border border-civic-border/50 dark:border-civic-dark-border/50">
                      "{ev.notes}"
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>

      {/* --- MODALS --- */}

      {/* 1. Verify Report Modal */}
      <Modal
        isOpen={activeModal === 'VERIFY'}
        onClose={() => setActiveModal(null)}
        title="Verify Citizen Report"
        description="Confirm or adjust the defect category and severity before routing to departmental dispatch."
        footer={
          <>
            <CivicButton variant="ghost" size="sm" onClick={() => setActiveModal(null)}>
              Cancel
            </CivicButton>
            <CivicButton
              variant="primary"
              size="sm"
              isLoading={verifyMutation.isPending}
              onClick={() => verifyMutation.mutate()}
            >
              Confirm Verification
            </CivicButton>
          </>
        }
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-medium text-civic-text-secondary mb-1">
              Verified Category
            </label>
            <select
              value={verifiedCategory}
              onChange={(e) => setVerifiedCategory(e.target.value as CivicCategory)}
              className="w-full h-9 px-3 rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border"
            >
              <option value="Pothole">Pothole</option>
              <option value="Garbage">Garbage</option>
              <option value="Water Leakage">Water Leakage</option>
              <option value="Streetlight">Streetlight</option>
              <option value="Road Damage">Road Damage</option>
              <option value="Drainage">Drainage</option>
              <option value="Other">Other</option>
            </select>
          </div>

          <div>
            <label className="block font-medium text-civic-text-secondary mb-1">
              Verified Physical Severity
            </label>
            <select
              value={verifiedSeverity}
              onChange={(e) => setVerifiedSeverity(e.target.value as BackendSeverityLevel)}
              className="w-full h-9 px-3 rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border"
            >
              <option value="LOW">Low (Minimal impact)</option>
              <option value="MEDIUM">Medium (Moderate traffic or hygiene disruption)</option>
              <option value="HIGH">High (Active hazard to vehicles or pedestrians)</option>
              <option value="CRITICAL">Critical (Immediate life safety or property risk)</option>
            </select>
          </div>

          <div>
            <label className="block font-medium text-civic-text-secondary mb-1">
              Reviewer Notes (Optional)
            </label>
            <textarea
              rows={3}
              value={actionNotes}
              onChange={(e) => setActionNotes(e.target.value)}
              placeholder="Add observation or verification notes for the department crew..."
              className="w-full p-2.5 rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border"
            />
          </div>
        </div>
      </Modal>

      {/* 2. Reject / Mark Duplicate Modal */}
      <Modal
        isOpen={activeModal === 'REJECT'}
        onClose={() => setActiveModal(null)}
        title="Reject or Close Report"
        description="Select a structured justification for declining this citizen submission."
        footer={
          <>
            <CivicButton variant="ghost" size="sm" onClick={() => setActiveModal(null)}>
              Cancel
            </CivicButton>
            <CivicButton
              variant="danger"
              size="sm"
              isLoading={rejectMutation.isPending}
              disabled={!actionNotes.trim()}
              onClick={() => rejectMutation.mutate()}
            >
              Confirm Closure
            </CivicButton>
          </>
        }
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-medium text-civic-text-secondary mb-1">
              Structured Closure Reason <span className="text-red-500">*</span>
            </label>
            <select
              value={closureReason}
              onChange={(e) => setClosureReason(e.target.value as ClosureReason)}
              className="w-full h-9 px-3 rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border"
            >
              <option value="INVALID_REPORT">Invalid or Spam Report</option>
              <option value="DUPLICATE">Duplicate of Existing Issue</option>
              <option value="OUT_OF_SCOPE">Out of Municipal Jurisdiction</option>
              <option value="INSUFFICIENT_EVIDENCE">Insufficient Evidence / Unlocatable</option>
              <option value="RESOLVED_EXTERNALLY">Already Resolved Externally</option>
              <option value="OTHER">Other Administrative Reason</option>
            </select>
          </div>

          <div>
            <label className="block font-medium text-civic-text-secondary mb-1">
              Closure Justification Notes <span className="text-red-500">*</span>
            </label>
            <textarea
              rows={3}
              required
              value={actionNotes}
              onChange={(e) => setActionNotes(e.target.value)}
              placeholder="Explain why this report is being rejected or marked duplicate..."
              className="w-full p-2.5 rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border"
            />
          </div>
        </div>
      </Modal>

      {/* 3. Prioritize Modal */}
      <Modal
        isOpen={activeModal === 'PRIORITIZE'}
        onClose={() => setActiveModal(null)}
        title="Set Operational Priority"
        description="Determine response SLA urgency."
        footer={
          <>
            <CivicButton variant="ghost" size="sm" onClick={() => setActiveModal(null)}>
              Cancel
            </CivicButton>
            <CivicButton
              variant="primary"
              size="sm"
              isLoading={prioritizeMutation.isPending}
              onClick={() => prioritizeMutation.mutate()}
            >
              Update Priority
            </CivicButton>
          </>
        }
      >
        <div className="space-y-3 text-xs">
          <label className="block font-medium text-civic-text-secondary">
            Operational Priority Level
          </label>
          <div className="grid grid-cols-2 gap-2">
            {(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as BackendPriorityLevel[]).map((pri) => (
              <button
                key={pri}
                type="button"
                onClick={() => setTargetPriority(pri)}
                className={`p-3 rounded-lg border text-left transition-colors ${
                  targetPriority === pri
                    ? 'border-civic-green bg-civic-green-container/30 text-civic-green font-semibold dark:bg-civic-green-container/20'
                    : 'border-civic-border hover:bg-black/5 dark:border-civic-dark-border'
                }`}
              >
                <div className="font-bold">{pri}</div>
                <div className="text-[10px] text-civic-text-muted mt-0.5">
                  {pri === 'CRITICAL' && '24-hour dispatch SLA'}
                  {pri === 'HIGH' && '48-hour response target'}
                  {pri === 'MEDIUM' && 'Standard weekly workflow'}
                  {pri === 'LOW' && 'Scheduled periodic maintenance'}
                </div>
              </button>
            ))}
          </div>
        </div>
      </Modal>

      {/* 4. Assign Department Modal */}
      <Modal
        isOpen={activeModal === 'ASSIGN'}
        onClose={() => setActiveModal(null)}
        title="Assign Municipal Department"
        description="Route work ticket to responsible civic engineering division."
        footer={
          <>
            <CivicButton variant="ghost" size="sm" onClick={() => setActiveModal(null)}>
              Cancel
            </CivicButton>
            <CivicButton
              variant="primary"
              size="sm"
              isLoading={assignMutation.isPending}
              onClick={() => assignMutation.mutate()}
            >
              Assign & Route
            </CivicButton>
          </>
        }
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-medium text-civic-text-secondary mb-1">
              Target Department
            </label>
            <select
              value={targetDepartment}
              onChange={(e) => setTargetDepartment(e.target.value as DepartmentName)}
              className="w-full h-9 px-3 rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border"
            >
              <option value="Roads & Bridges">Roads & Bridges</option>
              <option value="Solid Waste Management">Solid Waste Management</option>
              <option value="Water Supply & Sewerage">Water Supply & Sewerage</option>
              <option value="Street Lighting & Electrical">Street Lighting & Electrical</option>
              <option value="Town Planning & Enforcement">Town Planning & Enforcement</option>
              <option value="General Public Works">General Public Works</option>
            </select>
          </div>

          <div>
            <label className="block font-medium text-civic-text-secondary mb-1">
              Designated Lead Officer / Crew (Optional)
            </label>
            <input
              type="text"
              value={assignedOfficer}
              onChange={(e) => setAssignedOfficer(e.target.value)}
              placeholder="e.g. Ramesh Chandra (Supervisor)"
              className="w-full h-9 px-3 rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border"
            />
          </div>
        </div>
      </Modal>

      {/* 5. Mark Resolved Modal */}
      <Modal
        isOpen={activeModal === 'RESOLVE'}
        onClose={() => setActiveModal(null)}
        title="Mark Defect Resolved"
        description="Record field completion of physical repair work."
        footer={
          <>
            <CivicButton variant="ghost" size="sm" onClick={() => setActiveModal(null)}>
              Cancel
            </CivicButton>
            <CivicButton
              variant="primary"
              size="sm"
              isLoading={transitionMutation.isPending}
              disabled={!actionNotes.trim()}
              onClick={() =>
                transitionMutation.mutate({
                  nextStatus: 'RESOLVED',
                  notes: actionNotes,
                })
              }
            >
              Submit Resolution
            </CivicButton>
          </>
        }
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-medium text-civic-text-secondary mb-1">
              Field Completion Report / Notes <span className="text-red-500">*</span>
            </label>
            <textarea
              rows={4}
              required
              value={actionNotes}
              onChange={(e) => setActionNotes(e.target.value)}
              placeholder="Detail actions taken (e.g. Asphalt compaction completed, replacement luminaire fitted, water pipeline sealed)..."
              className="w-full p-2.5 rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border"
            />
          </div>
        </div>
      </Modal>

      {/* 6. Full Image Preview Modal */}
      <Modal
        isOpen={activeModal === 'IMAGE_PREVIEW'}
        onClose={() => setActiveModal(null)}
        title="High-Resolution Evidence"
        maxWidth="lg"
      >
        {previewImageUri && (
          <div className="rounded-lg overflow-hidden bg-black flex items-center justify-center">
            <img
              src={previewImageUri}
              alt="High resolution evidence"
              className="max-h-[70vh] w-auto object-contain"
            />
          </div>
        )}
      </Modal>

      {/* 7. Decline Job Modal */}
      <Modal
        isOpen={activeModal === 'DECLINE_JOB'}
        onClose={() => setActiveModal(null)}
        title="Decline Department Job Order"
        description={`Return work ticket ${report.trackingId} back to municipal triage with structured justification.`}
        footer={
          <>
            <CivicButton variant="ghost" size="sm" onClick={() => setActiveModal(null)}>
              Cancel
            </CivicButton>
            <CivicButton
              variant="danger"
              size="sm"
              isLoading={declineJobMutation.isPending}
              disabled={!declineNotes.trim()}
              onClick={() => declineJobMutation.mutate()}
            >
              Confirm Decline & Return to Triage
            </CivicButton>
          </>
        }
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-medium text-civic-text-secondary mb-1">
              Decline Justification Reason <span className="text-red-500">*</span>
            </label>
            <select
              value={declineReason}
              onChange={(e) =>
                setDeclineReason(e.target.value as BackendDepartmentRejectionReason)
              }
              className="w-full h-9 px-3 rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border"
            >
              <option value="OUT_OF_JURISDICTION">Outside Department Jurisdiction / Scope</option>
              <option value="INSUFFICIENT_ACCESS">Inaccessible Location / Physical Barrier</option>
              <option value="DUPLICATE_WORK_ORDER">Duplicate Existing Work Order</option>
              <option value="REQUIRES_MAJOR_BUDGET">Requires Capital Budget / Tender</option>
              <option value="INSUFFICIENT_INFORMATION">Insufficient Evidence / Unlocatable</option>
              <option value="OTHER">Other Operational Ground</option>
            </select>
          </div>

          <div>
            <label className="block font-medium text-civic-text-secondary mb-1">
              Operational Justification Notes <span className="text-red-500">*</span>
            </label>
            <textarea
              rows={4}
              required
              value={declineNotes}
              onChange={(e) => setDeclineNotes(e.target.value)}
              placeholder="Explain why this department cannot execute this job order..."
              className="w-full p-2.5 rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border"
            />
          </div>
        </div>
      </Modal>
    </motion.div>
  );
};
