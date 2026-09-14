import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  MapPin,
  Eye,
  ExternalLink,
  Layers,
  X,
  Bot,
  CheckCircle,
  Building,
  Send,
  XCircle,
  MoreHorizontal,
  AlertCircle,
  ShieldAlert,
  RotateCcw,
} from 'lucide-react';
import { reportRepository } from '@/services/repository/reportRepository';
import { queryKeys } from '@/services/queryKeys';
import { useAuth } from '@/core/auth/AuthContext';
import { can } from '@/core/auth/permissions';
import {
  ReportFilterParams,
  ReportItem,
  BackendSeverityLevel,
  BackendPriorityLevel,
  CivicCategory,
  ClosureReason,
  DepartmentName,
} from '@/types/models';
import { PageHeader } from '@/core/layout/PageHeader';
import { FilterBar } from '@/core/components/FilterBar';
import { DataTable, Column } from '@/core/components/DataTable';
import { StatusBadge } from '@/core/components/StatusBadge';
import { SeverityBadge } from '@/core/components/SeverityBadge';
import { PriorityBadge } from '@/core/components/PriorityBadge';
import { CivicButton } from '@/core/components/CivicButton';
import { Modal } from '@/core/components/Modal';
import { ErrorBanner } from '@/core/components/ErrorBanner';
import { formatDateShort, formatDateFull, formatRelativeTime } from '@/core/utils/dateUtils';
import { motion, type Variants } from 'motion/react';
import { clsx } from 'clsx';

const CIVIC_CATEGORIES: CivicCategory[] = [
  'Pothole',
  'Garbage',
  'Water Leakage',
  'Streetlight',
  'Road Damage',
  'Drainage',
  'Infrastructure',
  'Other',
];

const SEVERITY_LEVELS: BackendSeverityLevel[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

const PRIORITY_LEVELS: BackendPriorityLevel[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

const DEPARTMENTS: DepartmentName[] = [
  'Roads & Bridges',
  'Solid Waste Management',
  'Water Supply & Sewerage',
  'Street Lighting & Electrical',
  'Town Planning & Enforcement',
  'General Public Works',
];

const CLOSURE_REASONS: { value: ClosureReason; label: string }[] = [
  { value: 'INVALID_REPORT', label: 'Invalid / Unverifiable Report' },
  { value: 'DUPLICATE', label: 'Duplicate Citizen Report' },
  { value: 'OUT_OF_SCOPE', label: 'Out of Municipal Jurisdiction' },
  { value: 'INSUFFICIENT_EVIDENCE', label: 'Insufficient Evidence / Low Quality Media' },
  { value: 'RESOLVED_EXTERNALLY', label: 'Already Resolved Externally' },
  { value: 'OTHER', label: 'Other Administrative Closure' },
];

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
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

export const ReportsPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const urlIssueId = searchParams.get('issue_id') || searchParams.get('issueId') || undefined;

  // Permissions
  const canVerify = can(user, 'verify_report');
  const canPrioritize = can(user, 'prioritize_report');
  const canAssign = can(user, 'assign_department');
  const canClose = can(user, 'close_report');

  const [filters, setFilters] = useState<ReportFilterParams>({
    phase: 'ALL',
    category: 'ALL',
    severity: 'ALL',
    priority: 'ALL',
    issueId: urlIssueId,
    search: '',
    page: 1,
    pageSize: 10,
    sortBy: 'createdAt',
    sortOrder: 'desc',
  });

  // Action states
  const [activeDropdownId, setActiveDropdownId] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [runningAiId, setRunningAiId] = useState<string | null>(null);

  // Modal states
  const [activeModal, setActiveModal] = useState<
    'REJECT' | 'VERIFY' | 'ASSIGN' | 'PRIORITIZE' | null
  >(null);
  const [selectedReport, setSelectedReport] = useState<ReportItem | null>(null);

  // Modal Form states
  const [verifiedCategory, setVerifiedCategory] = useState<CivicCategory>('Pothole');
  const [verifiedSeverity, setVerifiedSeverity] = useState<BackendSeverityLevel>('MEDIUM');
  const [closureReason, setClosureReason] = useState<ClosureReason>('INVALID_REPORT');
  const [targetDepartment, setTargetDepartment] = useState<DepartmentName>('Roads & Bridges');
  const [targetPriority, setTargetPriority] = useState<BackendPriorityLevel>('MEDIUM');
  const [assignedOfficer, setAssignedOfficer] = useState('');
  const [actionNotes, setActionNotes] = useState('');

  // Operational feedback toast/banner
  const [feedback, setFeedback] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  // Auto-dismiss feedback after 4.5 seconds
  useEffect(() => {
    if (!feedback) return;
    const timer = setTimeout(() => {
      setFeedback(null);
    }, 4500);
    return () => clearTimeout(timer);
  }, [feedback]);

  // Keep filters.issueId synchronized when URL changes
  useEffect(() => {
    setFilters((prev) => {
      if (prev.issueId !== urlIssueId) {
        return { ...prev, issueId: urlIssueId, page: 1 };
      }
      return prev;
    });
  }, [urlIssueId]);

  // Outside click and Escape key listeners for the actions dropdown
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setActiveDropdownId(null);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setActiveDropdownId(null);
      }
    };
    if (activeDropdownId) {
      document.addEventListener('mousedown', handleOutsideClick);
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [activeDropdownId]);

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: queryKeys.reports.list(filters),
    queryFn: () => reportRepository.getReports(filters),
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });

  // --- Mutations ---

  // AI Pipeline Trigger
  const aiProcessMutation = useMutation({
    mutationFn: async (reportId: string) => {
      setRunningAiId(reportId);
      return reportRepository.triggerAIProcess(reportId);
    },
    onSuccess: (job, reportId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.detail(reportId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.stats() });
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.all });
      setFeedback({
        type: 'success',
        message: `AI analysis successfully triggered (Job ID: ${job.id.substring(0, 8)}).`,
      });
    },
    onError: (err) => {
      setFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to execute AI analysis.',
      });
    },
    onSettled: () => {
      setRunningAiId(null);
    },
  });

  // Verify & Set Severity Mutation
  const verifyMutation = useMutation({
    mutationFn: async () => {
      if (!selectedReport) return;
      return reportRepository.verifyReport(
        selectedReport.id,
        'CONFIRMED',
        verifiedCategory,
        verifiedSeverity,
        actionNotes,
        user ? `${user.name} (${user.role})` : 'Triage Officer'
      );
    },
    onSuccess: (updated) => {
      if (!updated) return;
      queryClient.setQueryData(queryKeys.reports.detail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.stats() });
      setActiveModal(null);
      setActionNotes('');
      setFeedback({
        type: 'success',
        message: `Report ${updated.trackingId} verified successfully as ${updated.category} with ${updated.severity} severity.`,
      });
    },
    onError: (err) => {
      setFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Verification failed.',
      });
    },
  });

  // Reject / Close Report Mutation
  const rejectMutation = useMutation({
    mutationFn: async () => {
      if (!selectedReport) return;
      return reportRepository.verifyReport(
        selectedReport.id,
        closureReason === 'DUPLICATE' ? 'DUPLICATE' : 'REJECTED',
        undefined,
        undefined,
        actionNotes,
        user ? `${user.name} (${user.role})` : 'Triage Officer'
      );
    },
    onSuccess: (updated) => {
      if (!updated) return;
      queryClient.setQueryData(queryKeys.reports.detail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.stats() });
      setActiveModal(null);
      setActionNotes('');
      setFeedback({
        type: 'success',
        message: `Report ${updated.trackingId} has been closed (${closureReason}).`,
      });
    },
    onError: (err) => {
      setFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to reject report.',
      });
    },
  });

  // Assign Department Mutation
  const assignMutation = useMutation({
    mutationFn: async () => {
      if (!selectedReport) return;
      return reportRepository.assignDepartment(
        selectedReport.id,
        targetDepartment,
        assignedOfficer || undefined,
        user ? `${user.name} (${user.role})` : 'Department Manager'
      );
    },
    onSuccess: (updated) => {
      if (!updated) return;
      queryClient.setQueryData(queryKeys.reports.detail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.stats() });
      queryClient.invalidateQueries({ queryKey: queryKeys.departments.all });
      setActiveModal(null);
      setActionNotes('');
      setFeedback({
        type: 'success',
        message: `Report ${updated.trackingId} successfully assigned to ${targetDepartment}.`,
      });
    },
    onError: (err) => {
      setFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to assign department.',
      });
    },
  });

  // Set Operational Priority Mutation
  const prioritizeMutation = useMutation({
    mutationFn: async () => {
      if (!selectedReport) return;
      return reportRepository.prioritizeReport(
        selectedReport.id,
        targetPriority,
        user ? `${user.name} (${user.role})` : 'Triage Officer'
      );
    },
    onSuccess: (updated) => {
      if (!updated) return;
      queryClient.setQueryData(queryKeys.reports.detail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.stats() });
      setActiveModal(null);
      setActionNotes('');
      setFeedback({
        type: 'success',
        message: `Report ${updated.trackingId} priority updated to ${targetPriority}.`,
      });
    },
    onError: (err) => {
      setFeedback({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to update priority.',
      });
    },
  });

  // --- Handlers to Open Modals ---

  const handleRunAI = (item: ReportItem) => {
    aiProcessMutation.mutate(item.id);
  };

  const openVerifyModal = (item: ReportItem) => {
    setSelectedReport(item);
    setVerifiedCategory(item.category);
    setVerifiedSeverity(item.severity);
    setActionNotes('');
    setActiveModal('VERIFY');
  };

  const openAssignModal = (item: ReportItem) => {
    setSelectedReport(item);
    setTargetDepartment(item.department || 'Roads & Bridges');
    setAssignedOfficer(item.assignedOfficer || '');
    setActionNotes('');
    setActiveModal('ASSIGN');
  };

  const openRejectModal = (item: ReportItem) => {
    setSelectedReport(item);
    setClosureReason('INVALID_REPORT');
    setActionNotes('');
    setActiveModal('REJECT');
  };

  const openPrioritizeModal = (item: ReportItem) => {
    setSelectedReport(item);
    setTargetPriority(item.priority);
    setActionNotes('');
    setActiveModal('PRIORITIZE');
  };

  const handleFilterChange = (newFilters: Partial<ReportFilterParams>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  };

  const handleResetFilters = () => {
    setFilters({
      phase: 'ALL',
      category: 'ALL',
      severity: 'ALL',
      priority: 'ALL',
      search: '',
      page: 1,
      pageSize: 10,
      sortBy: 'createdAt',
      sortOrder: 'desc',
    });
  };

  const handleStartFresh = async () => {
    try {
      if (reportRepository.resetReports) {
        await reportRepository.resetReports();
      }
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.stats() });
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.all });
      handleResetFilters();
      setFeedback({
        type: 'success',
        message: 'Reports work queue reset to fresh, calibrated dataset.',
      });
    } catch {
      setFeedback({
        type: 'error',
        message: 'Failed to reset reports dataset.',
      });
    }
  };

  const handleSort = (columnId: string) => {
    const isAsc = filters.sortBy === columnId && filters.sortOrder === 'asc';
    setFilters((prev) => ({
      ...prev,
      sortBy: columnId as ReportFilterParams['sortBy'],
      sortOrder: isAsc ? 'desc' : 'asc',
      page: 1,
    }));
  };

  const columns: Column<ReportItem>[] = [
    {
      id: 'trackingId',
      header: 'Tracking ID',
      sortable: true,
      cell: (item) => (
        <div className="flex flex-col">
          <span className="font-mono font-semibold text-civic-text-primary dark:text-civic-dark-text-primary text-xs">
            {item.trackingId}
          </span>
          {item.reviewRequired && (
            <span className="text-[10px] text-amber-600 dark:text-amber-400 font-medium">
              Review Required
            </span>
          )}
        </div>
      ),
    },
    {
      id: 'category',
      header: 'Category',
      sortable: true,
      cell: (item) => (
        <span className="font-medium text-xs text-civic-text-primary dark:text-civic-dark-text-primary">
          {item.category}
        </span>
      ),
    },
    {
      id: 'description',
      header: 'Description',
      cell: (item) => (
        <p className="text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary line-clamp-1 max-w-xs">
          {item.description}
        </p>
      ),
    },
    {
      id: 'addressHint',
      header: 'Locality',
      sortable: true,
      cell: (item) => (
        <div className="flex items-center gap-1.5 text-xs text-civic-text-muted max-w-[200px]">
          <MapPin className="w-3.5 h-3.5 text-civic-green shrink-0" />
          <span className="truncate">{item.addressHint || `${item.latitude.toFixed(4)}, ${item.longitude.toFixed(4)}`}</span>
        </div>
      ),
    },
    {
      id: 'severity',
      header: 'Severity',
      sortable: true,
      cell: (item) => <SeverityBadge severity={item.severity} size="sm" />,
    },
    {
      id: 'priority',
      header: 'Priority',
      sortable: true,
      cell: (item) => <PriorityBadge priority={item.priority} size="sm" />,
    },
    {
      id: 'status',
      header: 'Status',
      sortable: true,
      cell: (item) => <StatusBadge status={item.status} size="sm" />,
    },
    {
      id: 'issueId',
      header: 'Issue',
      cell: (item) =>
        item.issueId ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/issues/${item.issueId}`);
            }}
            className="inline-flex items-center gap-1 font-mono text-[11px] font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 hover:bg-blue-100 dark:hover:bg-blue-900/60 px-2 py-0.5 rounded border border-blue-200 dark:border-blue-800 transition-colors"
            title={`View Aggregated Issue: ${item.issueId}`}
          >
            <span>iss-{item.issueId.substring(0, 6)}</span>
            <ExternalLink className="w-2.5 h-2.5 opacity-70" />
          </button>
        ) : (
          <span className="text-slate-400 dark:text-slate-600 text-xs font-mono">—</span>
        ),
    },
    {
      id: 'createdAt',
      header: 'Submitted',
      sortable: true,
      cell: (item) => {
        const shortDate = formatDateShort(item.createdAt);
        const fullTooltip = formatDateFull(item.createdAt);
        const relative = formatRelativeTime(item.createdAt);
        return (
          <div className="flex flex-col" title={fullTooltip}>
            <span className="text-xs font-medium text-civic-text-primary">
              {shortDate}
            </span>
            <span className="text-[10px] text-civic-text-muted">
              {relative}
            </span>
          </div>
        );
      },
    },
    {
      id: 'actions',
      header: 'Actions',
      className: 'text-right',
      cell: (item) => {
        const isMenuOpen = activeDropdownId === item.id;
        const isRunningAi = runningAiId === item.id;

        return (
          <div
            className="relative flex items-center justify-end gap-1.5"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 1. Contextual Primary Quick Action Button */}
            {item.status === 'SUBMITTED' && (
              <CivicButton
                variant="secondary"
                size="sm"
                className="text-xs h-7 px-2.5 bg-purple-50 text-purple-700 hover:bg-purple-100 border-purple-200 dark:bg-purple-950/40 dark:text-purple-300 dark:border-purple-800"
                leftIcon={<Bot className="w-3.5 h-3.5" />}
                isLoading={isRunningAi}
                onClick={() => handleRunAI(item)}
                title="Manually Start AI Multimodal Analysis"
              >
                Run AI
              </CivicButton>
            )}

            {(item.status === 'AI_PROCESSED' || item.status === 'VERIFICATION_REQUIRED') && canVerify && (
              <CivicButton
                variant="primary"
                size="sm"
                className="text-xs h-7 px-2.5"
                leftIcon={<CheckCircle className="w-3.5 h-3.5" />}
                onClick={() => openVerifyModal(item)}
                title="Verify Report & Set Severity"
              >
                Verify
              </CivicButton>
            )}

            {(item.status === 'VERIFIED' || item.status === 'PRIORITIZED') && canAssign && (
              <CivicButton
                variant="primary"
                size="sm"
                className="text-xs h-7 px-2.5 bg-blue-600 hover:bg-blue-700 text-white"
                leftIcon={<Building className="w-3.5 h-3.5" />}
                onClick={() => openAssignModal(item)}
                title="Assign Department & Crew"
              >
                Assign
              </CivicButton>
            )}

            {['ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'RESOLUTION_VERIFIED', 'CLOSED'].includes(
              item.status
            ) && (
              <CivicButton
                variant="ghost"
                size="sm"
                className="text-xs h-7 px-2"
                leftIcon={<Eye className="w-3.5 h-3.5" />}
                onClick={() => navigate(`/reports/${item.id}`)}
                title="View Report Details"
              >
                View
              </CivicButton>
            )}

            {/* 2. More Actions Dropdown Menu */}
            <div className="relative">
              <button
                type="button"
                data-testid={`actions-menu-${item.id}`}
                onClick={() => setActiveDropdownId(isMenuOpen ? null : item.id)}
                className={clsx(
                  'p-1.5 rounded-md text-civic-text-muted hover:text-civic-text-primary hover:bg-black/5 dark:hover:bg-white/5 transition-colors border',
                  isMenuOpen
                    ? 'border-civic-green text-civic-green bg-civic-green/10'
                    : 'border-transparent hover:border-civic-border dark:hover:border-civic-dark-border'
                )}
                title="More Administrative Actions"
                aria-label="More Administrative Actions"
              >
                <MoreHorizontal className="w-4 h-4" />
              </button>

              {isMenuOpen && (
                <div
                  ref={dropdownRef}
                  className="absolute right-0 top-full mt-1.5 w-56 z-50 bg-white dark:bg-civic-dark-surface-elevated rounded-xl shadow-xl border border-civic-border dark:border-civic-dark-border py-1.5 divide-y divide-civic-border/50 dark:divide-civic-dark-border/50 text-left animate-in fade-in zoom-in-95 duration-150"
                >
                  {/* Primary group */}
                  <div className="py-1">
                    <button
                      type="button"
                      onClick={() => {
                        setActiveDropdownId(null);
                        navigate(`/reports/${item.id}`);
                      }}
                      className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-civic-text-primary dark:text-civic-dark-text-primary hover:bg-gray-50 dark:hover:bg-civic-dark-surface transition-colors"
                    >
                      <Eye className="w-3.5 h-3.5 text-civic-text-muted" />
                      <span>View Full Details</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        setActiveDropdownId(null);
                        handleRunAI(item);
                      }}
                      disabled={isRunningAi}
                      className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-950/30 transition-colors"
                    >
                      <Bot className="w-3.5 h-3.5" />
                      <span>
                        {item.status === 'SUBMITTED'
                          ? 'Start AI Analysis'
                          : 'Re-run AI Analysis'}
                      </span>
                    </button>
                  </div>

                  {/* Triage & Management group */}
                  <div className="py-1">
                    {canVerify && (
                      <button
                        type="button"
                        onClick={() => {
                          setActiveDropdownId(null);
                          openVerifyModal(item);
                        }}
                        className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-civic-text-primary dark:text-civic-dark-text-primary hover:bg-gray-50 dark:hover:bg-civic-dark-surface transition-colors"
                      >
                        <CheckCircle className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                        <span>Verify & Set Severity</span>
                      </button>
                    )}

                    {canAssign && (
                      <button
                        type="button"
                        onClick={() => {
                          setActiveDropdownId(null);
                          openAssignModal(item);
                        }}
                        className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-civic-text-primary dark:text-civic-dark-text-primary hover:bg-gray-50 dark:hover:bg-civic-dark-surface transition-colors"
                      >
                        <Building className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                        <span>Assign Department</span>
                      </button>
                    )}

                    {canPrioritize && (
                      <button
                        type="button"
                        onClick={() => {
                          setActiveDropdownId(null);
                          openPrioritizeModal(item);
                        }}
                        className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-civic-text-primary dark:text-civic-dark-text-primary hover:bg-gray-50 dark:hover:bg-civic-dark-surface transition-colors"
                      >
                        <Send className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                        <span>Set Priority (SLA)</span>
                      </button>
                    )}
                  </div>

                  {/* Destructive group */}
                  {canClose && item.status !== 'CLOSED' && (
                    <div className="py-1">
                      <button
                        type="button"
                        onClick={() => {
                          setActiveDropdownId(null);
                          openRejectModal(item);
                        }}
                        className="w-full flex items-center gap-2.5 px-3 py-1.5 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        <span>Reject Report</span>
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      },
    },
  ];

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-4"
    >
      <motion.div variants={itemVariants}>
        <PageHeader
          title="Reports Work Queue"
          description="Review incoming citizen reports, execute AI intelligence, assign municipal divisions, and verify severity."
          actions={
            <CivicButton
              variant="outline"
              size="sm"
              leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
              onClick={handleStartFresh}
              title="Reset work queue to clean, fresh dataset"
            >
              Reset to Fresh Data
            </CivicButton>
          }
        />
      </motion.div>

      {/* Action Feedback Banner */}
      {feedback && (
        <motion.div
          variants={itemVariants}
          className={clsx(
            'flex items-center justify-between px-4 py-3 rounded-xl text-xs border shadow-sm transition-all',
            feedback.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-900 dark:text-emerald-200 border-emerald-200 dark:border-emerald-800'
              : 'bg-red-50 dark:bg-red-950/40 text-red-900 dark:text-red-200 border-red-200 dark:border-red-800'
          )}
        >
          <div className="flex items-center gap-2">
            {feedback.type === 'success' ? (
              <CheckCircle className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0" />
            )}
            <span className="font-medium">{feedback.message}</span>
          </div>
          <button
            type="button"
            onClick={() => setFeedback(null)}
            className="p-1 rounded hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
            aria-label="Dismiss message"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </motion.div>
      )}

      {isError && (
        <motion.div variants={itemVariants} className="mb-4">
          <ErrorBanner
            title="Failed to load reports"
            message={error instanceof Error ? error.message : 'An error occurred while communicating with the data repository.'}
            onRetry={() => refetch()}
            isRetrying={isFetching}
          />
        </motion.div>
      )}

      {/* Filter and Search Bar */}
      <motion.div
        variants={itemVariants}
        className="p-4 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border"
      >
        <FilterBar
          filters={filters}
          onChange={handleFilterChange}
          onReset={handleResetFilters}
          totalResults={data?.total}
        />
      </motion.div>

      {/* Active Issue Filter Banner */}
      {filters.issueId && (
        <motion.div
          variants={itemVariants}
          className="flex items-center justify-between px-4 py-2.5 bg-blue-50/80 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800/80 rounded-xl text-xs text-blue-900 dark:text-blue-200"
        >
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0" />
            <span>
              Active Filter: Showing reports linked to Aggregated Issue{' '}
              <strong className="font-mono">{filters.issueId}</strong>
            </span>
          </div>
          <button
            type="button"
            onClick={() => {
              setSearchParams((prev) => {
                prev.delete('issueId');
                prev.delete('issue_id');
                return prev;
              });
              setFilters((prev) => ({ ...prev, issueId: undefined, page: 1 }));
            }}
            className="inline-flex items-center gap-1 font-semibold text-blue-700 dark:text-blue-300 hover:text-blue-900 dark:hover:text-white px-2 py-1 rounded hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
            Clear Issue Filter
          </button>
        </motion.div>
      )}

      {/* Reports Data Table */}
      <motion.div variants={itemVariants}>
        <DataTable
          data={data?.items || []}
          columns={columns}
          keyExtractor={(item) => item.id}
          isLoading={isLoading}
          onRowClick={(item) => navigate(`/reports/${item.id}`)}
          sortBy={filters.sortBy}
          sortOrder={filters.sortOrder}
          onSort={handleSort}
          page={filters.page || 1}
          totalPages={data?.totalPages || 1}
          totalItems={data?.total || 0}
          pageSize={filters.pageSize || 10}
          onPageChange={(p) => setFilters((prev) => ({ ...prev, page: p }))}
        />
      </motion.div>

      {/* ========================================================================= */}
      {/* ACTION MODALS                                                             */}
      {/* ========================================================================= */}

      {/* 1. VERIFY & ASSIGN SEVERITY MODAL */}
      <Modal
        isOpen={activeModal === 'VERIFY'}
        onClose={() => setActiveModal(null)}
        title={`Verify Report & Set Severity (${selectedReport?.trackingId || ''})`}
        description="Verify defect authenticity, assign canonical issue category, and determine operational severity."
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
            <label className="block font-medium text-civic-text-primary dark:text-civic-dark-text-primary mb-1">
              Confirmed Category
            </label>
            <select
              value={verifiedCategory}
              onChange={(e) => setVerifiedCategory(e.target.value as CivicCategory)}
              className="w-full px-3 py-2 rounded-lg border border-civic-border dark:border-civic-dark-border bg-white dark:bg-civic-dark-surface text-civic-text-primary dark:text-civic-dark-text-primary"
            >
              {CIVIC_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-medium text-civic-text-primary dark:text-civic-dark-text-primary mb-1">
              Operational Severity Level
            </label>
            <div className="grid grid-cols-2 gap-2">
              {SEVERITY_LEVELS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setVerifiedSeverity(s)}
                  className={clsx(
                    'flex items-center justify-between p-2.5 rounded-lg border text-left transition-all',
                    verifiedSeverity === s
                      ? 'border-civic-green bg-civic-green/10 text-civic-green font-semibold shadow-sm'
                      : 'border-civic-border dark:border-civic-dark-border hover:bg-gray-50 dark:hover:bg-civic-dark-surface-elevated text-civic-text-primary dark:text-civic-dark-text-primary'
                  )}
                >
                  <span>{s}</span>
                  <SeverityBadge severity={s} size="sm" />
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block font-medium text-civic-text-primary dark:text-civic-dark-text-primary mb-1">
              Verification Notes
            </label>
            <textarea
              value={actionNotes}
              onChange={(e) => setActionNotes(e.target.value)}
              placeholder="State verification observations, ground findings, or severity rationale..."
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-civic-border dark:border-civic-dark-border bg-white dark:bg-civic-dark-surface text-civic-text-primary dark:text-civic-dark-text-primary focus:outline-none focus:ring-1 focus:ring-civic-green"
            />
          </div>
        </div>
      </Modal>

      {/* 2. ASSIGN DEPARTMENT MODAL */}
      <Modal
        isOpen={activeModal === 'ASSIGN'}
        onClose={() => setActiveModal(null)}
        title={`Assign Department (${selectedReport?.trackingId || ''})`}
        description="Dispatch work ticket to the responsible municipal department and assign field crew."
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
              Assign Department
            </CivicButton>
          </>
        }
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-medium text-civic-text-primary dark:text-civic-dark-text-primary mb-1">
              Target Municipal Division
            </label>
            <select
              value={targetDepartment}
              onChange={(e) => setTargetDepartment(e.target.value as DepartmentName)}
              className="w-full px-3 py-2 rounded-lg border border-civic-border dark:border-civic-dark-border bg-white dark:bg-civic-dark-surface text-civic-text-primary dark:text-civic-dark-text-primary"
            >
              {DEPARTMENTS.map((dept) => (
                <option key={dept} value={dept}>
                  {dept}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-medium text-civic-text-primary dark:text-civic-dark-text-primary mb-1">
              Assigned Field Inspector / Crew Lead (Optional)
            </label>
            <input
              type="text"
              value={assignedOfficer}
              onChange={(e) => setAssignedOfficer(e.target.value)}
              placeholder="e.g. Officer Ramesh or Squad B"
              className="w-full px-3 py-2 rounded-lg border border-civic-border dark:border-civic-dark-border bg-white dark:bg-civic-dark-surface text-civic-text-primary dark:text-civic-dark-text-primary focus:outline-none focus:ring-1 focus:ring-civic-green"
            />
          </div>

          <div>
            <label className="block font-medium text-civic-text-primary dark:text-civic-dark-text-primary mb-1">
              Dispatch Instructions
            </label>
            <textarea
              value={actionNotes}
              onChange={(e) => setActionNotes(e.target.value)}
              placeholder="Provide job instructions, access details, or site precautions..."
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-civic-border dark:border-civic-dark-border bg-white dark:bg-civic-dark-surface text-civic-text-primary dark:text-civic-dark-text-primary focus:outline-none focus:ring-1 focus:ring-civic-green"
            />
          </div>
        </div>
      </Modal>

      {/* 3. SET PRIORITY MODAL */}
      <Modal
        isOpen={activeModal === 'PRIORITIZE'}
        onClose={() => setActiveModal(null)}
        title={`Set Operational Priority (${selectedReport?.trackingId || ''})`}
        description="Update the operational dispatch priority and SLA target for this issue."
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
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-medium text-civic-text-primary dark:text-civic-dark-text-primary mb-2">
              Select Priority (SLA Standard)
            </label>
            <div className="space-y-2">
              {PRIORITY_LEVELS.map((p) => {
                const slaMap: Record<BackendPriorityLevel, string> = {
                  CRITICAL: '24 Hours SLA',
                  HIGH: '48 Hours SLA',
                  MEDIUM: '5 Days SLA',
                  LOW: '14 Days SLA',
                };
                return (
                  <button
                    key={p}
                    type="button"
                    onClick={() => setTargetPriority(p)}
                    className={clsx(
                      'w-full flex items-center justify-between p-3 rounded-lg border text-left transition-all',
                      targetPriority === p
                        ? 'border-civic-green bg-civic-green/10 text-civic-green font-semibold shadow-sm'
                        : 'border-civic-border dark:border-civic-dark-border hover:bg-gray-50 dark:hover:bg-civic-dark-surface-elevated text-civic-text-primary dark:text-civic-dark-text-primary'
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <PriorityBadge priority={p} size="sm" />
                      <span className="font-semibold">{p}</span>
                    </div>
                    <span className="text-[11px] text-civic-text-muted">{slaMap[p]}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </Modal>

      {/* 4. REJECT REPORT MODAL */}
      <Modal
        isOpen={activeModal === 'REJECT'}
        onClose={() => setActiveModal(null)}
        title={`Reject / Close Report (${selectedReport?.trackingId || ''})`}
        description="Rejecting will immediately mark this report as Closed. This action is auditable."
        footer={
          <>
            <CivicButton variant="ghost" size="sm" onClick={() => setActiveModal(null)}>
              Cancel
            </CivicButton>
            <CivicButton
              variant="danger"
              size="sm"
              isLoading={rejectMutation.isPending}
              onClick={() => rejectMutation.mutate()}
            >
              Confirm Rejection
            </CivicButton>
          </>
        }
      >
        <div className="space-y-4 text-xs">
          <div className="p-3 bg-red-50/70 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50 rounded-lg text-red-900 dark:text-red-200 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0" />
            <span>
              Closing this ticket removes it from active municipal resolution workflows.
            </span>
          </div>

          <div>
            <label className="block font-medium text-civic-text-primary dark:text-civic-dark-text-primary mb-1">
              Rejection / Closure Reason
            </label>
            <select
              value={closureReason}
              onChange={(e) => setClosureReason(e.target.value as ClosureReason)}
              className="w-full px-3 py-2 rounded-lg border border-civic-border dark:border-civic-dark-border bg-white dark:bg-civic-dark-surface text-civic-text-primary dark:text-civic-dark-text-primary"
            >
              {CLOSURE_REASONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-medium text-civic-text-primary dark:text-civic-dark-text-primary mb-1">
              Officer Justification Notes (Required)
            </label>
            <textarea
              value={actionNotes}
              onChange={(e) => setActionNotes(e.target.value)}
              placeholder="State why this report was rejected or closed..."
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-civic-border dark:border-civic-dark-border bg-white dark:bg-civic-dark-surface text-civic-text-primary dark:text-civic-dark-text-primary focus:outline-none focus:ring-1 focus:ring-red-500"
            />
          </div>
        </div>
      </Modal>
    </motion.div>
  );
};
