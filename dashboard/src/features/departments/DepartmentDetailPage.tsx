import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Building2,
  Phone,
  Mail,
  Clock,
  CheckCircle,
  XCircle,
  Flame,
  Eye,
  RefreshCw,
} from 'lucide-react';
import { departmentRepository } from '@/services/repository/DepartmentRepository';
import { reportRepository } from '@/services/repository/reportRepository';
import { queryKeys } from '@/services/queryKeys';
import { DataTable, Column } from '@/core/components/DataTable';
import { StatusBadge } from '@/core/components/StatusBadge';
import { SeverityBadge } from '@/core/components/SeverityBadge';
import { PriorityBadge } from '@/core/components/PriorityBadge';
import { CivicButton } from '@/core/components/CivicButton';
import { Modal } from '@/core/components/Modal';
import { ErrorBanner } from '@/core/components/ErrorBanner';
import { LoadingSkeleton } from '@/core/components/LoadingSkeleton';
import { formatDateShort, formatDateFull, formatRelativeTime } from '@/core/utils/dateUtils';
import {
  ReportItem,
} from '@/types/models';
import { BackendDepartmentRejectionReason } from '@/types/api/backendContracts';
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

type DepartmentJobTab = 'ALL' | 'ASSIGNED' | 'IN_PROGRESS' | 'RESOLVED';

const REJECTION_REASONS: Array<{ value: BackendDepartmentRejectionReason; label: string }> = [
  { value: 'OUT_OF_JURISDICTION', label: 'Outside Department Jurisdiction / Scope' },
  { value: 'INSUFFICIENT_ACCESS', label: 'Inaccessible Location / Physical Barrier' },
  { value: 'DUPLICATE_WORK_ORDER', label: 'Duplicate Existing Work Order' },
  { value: 'REQUIRES_MAJOR_BUDGET', label: 'Requires Capital Budget / Tender' },
  { value: 'INSUFFICIENT_INFORMATION', label: 'Insufficient Evidence / Unlocatable' },
  { value: 'OTHER', label: 'Other Operational Ground' },
];

export const DepartmentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<DepartmentJobTab>('ALL');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Modals for actions
  const [declineReport, setDeclineReport] = useState<ReportItem | null>(null);
  const [declineReason, setDeclineReason] =
    useState<BackendDepartmentRejectionReason>('OUT_OF_JURISDICTION');
  const [declineNotes, setDeclineNotes] = useState('');

  const [completeReport, setCompleteReport] = useState<ReportItem | null>(null);
  const [completionNotes, setCompletionNotes] = useState('');

  // 1. Fetch Department Info
  const {
    data: department,
    isLoading: isDeptLoading,
    isError: isDeptError,
    error: deptError,
  } = useQuery({
    queryKey: queryKeys.departments.detail(id || ''),
    queryFn: () => departmentRepository.getDepartmentById(id || ''),
    enabled: !!id,
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });

  // 2. Fetch Department Stats
  const { data: stats } = useQuery({
    queryKey: queryKeys.departments.stats(id || ''),
    queryFn: () => departmentRepository.getDepartmentStats(id || ''),
    enabled: !!id,
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });

  // 3. Fetch Assigned Reports
  const statusParam = activeTab === 'ALL' ? undefined : activeTab;
  const priParam = priorityFilter === 'ALL' ? undefined : priorityFilter;

  const {
    data: reportsData,
    isLoading: isReportsLoading,
    isError: isReportsError,
    error: reportsError,
    refetch: refetchReports,
    isFetching,
  } = useQuery({
    queryKey: queryKeys.departments.reports(id || '', {
      status: statusParam,
      priority: priParam,
      page,
      pageSize,
    }),
    queryFn: () =>
      departmentRepository.getDepartmentReports(id || '', {
        status: statusParam,
        priority: priParam,
        page,
        pageSize,
      }),
    enabled: !!id,
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });

  // Action Mutations
  const acknowledgeMutation = useMutation({
    mutationFn: async (reportId: string) => {
      return reportRepository.acknowledgeJob(
        reportId,
        department?.head_name || 'Department Officer',
        'Acknowledged by municipal operations team'
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.departments.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
    },
  });

  const declineMutation = useMutation({
    mutationFn: async () => {
      if (!declineReport) return;
      return reportRepository.rejectJob(
        declineReport.id,
        declineReason,
        declineNotes
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.departments.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      setDeclineReport(null);
      setDeclineNotes('');
    },
  });

  const completeMutation = useMutation({
    mutationFn: async () => {
      if (!completeReport) return;
      return reportRepository.completeJob(
        completeReport.id,
        completionNotes,
        department?.head_name || 'Department Crew Lead'
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.departments.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      setCompleteReport(null);
      setCompletionNotes('');
    },
  });

  if (isDeptLoading) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton className="h-8 w-64" />
        <LoadingSkeleton className="h-36 w-full rounded-civic" />
        <LoadingSkeleton className="h-80 w-full rounded-civic" />
      </div>
    );
  }

  if (isDeptError || !department) {
    return (
      <div className="space-y-4">
        <CivicButton
          variant="outline"
          size="sm"
          onClick={() => navigate('/departments')}
          leftIcon={<ArrowLeft className="w-4 h-4" />}
        >
          Back to Departments
        </CivicButton>
        <ErrorBanner
          title="Department Not Found"
          message={
            deptError instanceof Error
              ? deptError.message
              : 'The requested department could not be retrieved from the repository.'
          }
        />
      </div>
    );
  }

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
          {item.reassignmentRequired && (
            <span className="text-[10px] text-amber-600 dark:text-amber-400 font-semibold">
              Reassignment Req
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
      header: 'Defect Description',
      cell: (item) => (
        <p className="text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary line-clamp-1 max-w-xs">
          {item.description}
        </p>
      ),
    },
    {
      id: 'priority',
      header: 'Priority',
      sortable: true,
      cell: (item) => <PriorityBadge priority={item.priority} size="sm" />,
    },
    {
      id: 'severity',
      header: 'Severity',
      sortable: true,
      cell: (item) => <SeverityBadge severity={item.severity} size="sm" />,
    },
    {
      id: 'status',
      header: 'Status',
      sortable: true,
      cell: (item) => <StatusBadge status={item.status} size="sm" />,
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
      cell: (item) => (
        <div className="flex items-center justify-end gap-1.5 flex-wrap">
          {item.status === 'ASSIGNED' && (
            <>
              <CivicButton
                variant="primary"
                size="sm"
                className="h-7 text-xs px-2.5 bg-indigo-600 hover:bg-indigo-700"
                isLoading={acknowledgeMutation.isPending}
                leftIcon={<Flame className="w-3 h-3" />}
                onClick={(e) => {
                  e.stopPropagation();
                  acknowledgeMutation.mutate(item.id);
                }}
              >
                Acknowledge
              </CivicButton>
              <CivicButton
                variant="outline"
                size="sm"
                className="h-7 text-xs px-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20"
                leftIcon={<XCircle className="w-3 h-3" />}
                onClick={(e) => {
                  e.stopPropagation();
                  setDeclineReport(item);
                  setDeclineReason('OUT_OF_JURISDICTION');
                  setDeclineNotes('');
                }}
              >
                Decline
              </CivicButton>
            </>
          )}

          {item.status === 'IN_PROGRESS' && (
            <CivicButton
              variant="primary"
              size="sm"
              className="h-7 text-xs px-2.5 bg-teal-600 hover:bg-teal-700"
              leftIcon={<CheckCircle className="w-3 h-3" />}
              onClick={(e) => {
                e.stopPropagation();
                setCompleteReport(item);
                setCompletionNotes('');
              }}
            >
              Complete
            </CivicButton>
          )}

          <CivicButton
            variant="ghost"
            size="sm"
            className="h-7 text-xs px-2"
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/reports/${item.id}`);
            }}
            rightIcon={<Eye className="w-3 h-3" />}
          >
            View
          </CivicButton>
        </div>
      ),
    },
  ];

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      {/* Navigation & Header */}
      <motion.div variants={itemVariants} className="space-y-3">
        <CivicButton
          variant="outline"
          size="sm"
          onClick={() => navigate('/departments')}
          leftIcon={<ArrowLeft className="w-4 h-4" />}
        >
          Back to Directory
        </CivicButton>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-civic-green-container text-civic-green dark:bg-civic-dark-surface-elevated dark:text-civic-green-light">
              <Building2 className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-civic-text-primary dark:text-civic-dark-text-primary">
                  {department.name}
                </h1>
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-civic-dark-surface-elevated text-civic-text-secondary border border-civic-border dark:border-civic-dark-border">
                  {department.code}
                </span>
                {department.is_active && (
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                    Active Operations
                  </span>
                )}
              </div>
              <p className="text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary mt-0.5">
                {department.description || 'Municipal engineering division responsible for field execution.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary shrink-0">
            {department.contact_phone && (
              <div className="flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5 text-civic-green" />
                <span className="font-mono">{department.contact_phone}</span>
              </div>
            )}
            {department.contact_email && (
              <div className="flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-civic-green" />
                <span>{department.contact_email}</span>
              </div>
            )}
            <div className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-civic-green" />
              <span>SLA Target: <strong>{department.sla_hours_default}h</strong></span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Stats Cards Row */}
      <motion.div variants={itemVariants} className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="p-3.5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
          <span className="text-[11px] text-civic-text-muted font-medium uppercase tracking-wider block">
            Total Assigned
          </span>
          <span className="text-xl font-bold text-civic-text-primary dark:text-civic-dark-text-primary font-mono mt-0.5 block">
            {stats?.total_assigned ?? 0}
          </span>
        </div>

        <div className="p-3.5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
          <span className="text-[11px] text-civic-text-muted font-medium uppercase tracking-wider block">
            Pending Ack
          </span>
          <div className="flex items-center justify-between mt-0.5">
            <span className="text-xl font-bold text-civic-text-primary dark:text-civic-dark-text-primary font-mono">
              {stats?.pending_acknowledgment ?? 0}
            </span>
            {(stats?.pending_acknowledgment ?? 0) > 0 && (
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            )}
          </div>
        </div>

        <div className="p-3.5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
          <span className="text-[11px] text-civic-text-muted font-medium uppercase tracking-wider block">
            In Progress
          </span>
          <span className="text-xl font-bold text-orange-600 dark:text-orange-400 font-mono mt-0.5 block">
            {stats?.in_progress ?? 0}
          </span>
        </div>

        <div className="p-3.5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
          <span className="text-[11px] text-civic-text-muted font-medium uppercase tracking-wider block">
            Completed
          </span>
          <span className="text-xl font-bold text-civic-green dark:text-civic-green-light font-mono mt-0.5 block">
            {stats?.resolved ?? 0}
          </span>
        </div>

        <div className="p-3.5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
          <span className="text-[11px] text-civic-text-muted font-medium uppercase tracking-wider block">
            Declined / Reassign
          </span>
          <span className="text-xl font-bold text-red-600 dark:text-red-400 font-mono mt-0.5 block">
            {stats?.reassignment_required ?? stats?.rejected_assignments ?? 0}
          </span>
        </div>
      </motion.div>

      {/* Operational Work Queue */}
      <motion.div
        variants={itemVariants}
        className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border space-y-4"
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-civic-border dark:border-civic-dark-border">
          {/* Status Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto">
            {(
              [
                { tab: 'ALL', label: 'All Jobs' },
                { tab: 'ASSIGNED', label: 'Pending Acknowledgment' },
                { tab: 'IN_PROGRESS', label: 'In Progress' },
                { tab: 'RESOLVED', label: 'Completed' },
              ] as Array<{ tab: DepartmentJobTab; label: string }>
            ).map(({ tab, label }) => {
              const isActive = activeTab === tab;
              return (
                <button
                  key={tab}
                  type="button"
                  onClick={() => {
                    setActiveTab(tab);
                    setPage(1);
                  }}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
                    isActive
                      ? 'bg-civic-green text-white shadow-civic-subtle'
                      : 'text-civic-text-secondary hover:text-civic-text-primary hover:bg-black/5 dark:text-civic-dark-text-secondary dark:hover:text-white'
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>

          {/* Priority Filter & Live Refetch Status */}
          <div className="flex items-center gap-2">
            <select
              value={priorityFilter}
              onChange={(e) => {
                setPriorityFilter(e.target.value);
                setPage(1);
              }}
              className="h-8 px-2.5 text-xs rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 dark:bg-civic-dark-surface dark:border-civic-dark-border cursor-pointer"
            >
              <option value="ALL">All Priorities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>

            <CivicButton
              variant="outline"
              size="sm"
              className="h-8 px-2"
              onClick={() => refetchReports()}
              title="Refresh Queue"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
            </CivicButton>
          </div>
        </div>

        {/* Error state if reports failed */}
        {isReportsError && (
          <ErrorBanner
            title="Failed to load department work queue"
            message={
              reportsError instanceof Error
                ? reportsError.message
                : 'An unexpected error occurred.'
            }
            onRetry={() => refetchReports()}
          />
        )}

        {/* Reports Table */}
        <DataTable
          data={reportsData?.items || []}
          columns={columns}
          keyExtractor={(item) => item.id}
          isLoading={isReportsLoading}
          onRowClick={(item) => navigate(`/reports/${item.id}`)}
          page={reportsData?.page || 1}
          pageSize={reportsData?.pageSize || pageSize}
          totalItems={reportsData?.total || 0}
          totalPages={reportsData?.totalPages || 1}
          onPageChange={(newPage: number) => setPage(newPage)}
          emptyTitle="No assigned jobs found in this queue."
        />
      </motion.div>

      {/* Decline Job Modal */}
      <Modal
        isOpen={!!declineReport}
        onClose={() => setDeclineReport(null)}
        title="Decline Department Job Order"
        description={`Return work ticket ${declineReport?.trackingId} back to municipal triage with structured justification.`}
        footer={
          <>
            <CivicButton
              variant="ghost"
              size="sm"
              onClick={() => setDeclineReport(null)}
            >
              Cancel
            </CivicButton>
            <CivicButton
              variant="danger"
              size="sm"
              isLoading={declineMutation.isPending}
              disabled={!declineNotes.trim()}
              onClick={() => declineMutation.mutate()}
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
              {REJECTION_REASONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
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
              placeholder="Explain why this department cannot execute this job order (e.g. Defect is on private property, electrical feeder belongs to state power corporation, etc.)..."
              className="w-full p-2.5 rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border"
            />
          </div>
        </div>
      </Modal>

      {/* Complete Job Modal */}
      <Modal
        isOpen={!!completeReport}
        onClose={() => setCompleteReport(null)}
        title="Complete Field Job Order"
        description={`Record completion of physical remediation work for ${completeReport?.trackingId}.`}
        footer={
          <>
            <CivicButton
              variant="ghost"
              size="sm"
              onClick={() => setCompleteReport(null)}
            >
              Cancel
            </CivicButton>
            <CivicButton
              variant="primary"
              size="sm"
              isLoading={completeMutation.isPending}
              disabled={!completionNotes.trim()}
              onClick={() => completeMutation.mutate()}
            >
              Submit Completion Report
            </CivicButton>
          </>
        }
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-medium text-civic-text-secondary mb-1">
              Field Remediation Report / Notes <span className="text-red-500">*</span>
            </label>
            <textarea
              rows={4}
              required
              value={completionNotes}
              onChange={(e) => setCompletionNotes(e.target.value)}
              placeholder="Describe physical remediation performed (materials used, crew dispatch, test results)..."
              className="w-full p-2.5 rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border"
            />
          </div>
        </div>
      </Modal>
    </motion.div>
  );
};
