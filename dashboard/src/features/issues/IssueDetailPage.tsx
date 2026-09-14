import React, { useState, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  Layers,
  MapPin,
  Clock,
  FileText,
  AlertTriangle,
  ExternalLink,
  Copy,
  Check,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  RotateCcw,
} from 'lucide-react';
import { issueRepository } from '@/services/repository/issueRepository';
import { queryKeys } from '@/services/queryKeys';
import { ReportItem } from '@/types/models';
import { Column, DataTable } from '@/core/components/DataTable';
import { CivicButton } from '@/core/components/CivicButton';
import { StatCard } from '@/core/components/StatCard';
import { StatusBadge } from '@/core/components/StatusBadge';
import { PriorityBadge } from '@/core/components/PriorityBadge';
import { SeverityBadge } from '@/core/components/SeverityBadge';
import { LoadingSkeleton } from '@/core/components/LoadingSkeleton';
import { EmptyState } from '@/core/components/EmptyState';
import { ErrorBanner } from '@/core/components/ErrorBanner';
import { MapRenderer } from '@/features/map/MapRenderer';
import { MapPoint } from '@/features/map/types';
import { formatDateTime } from '@/core/utils/dateUtils';
import { resolveMediaUrl } from '@/core/utils/mediaUtils';
import { motion, type Variants } from 'motion/react';

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

export const IssueDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);
  const [activePhotoIndex, setActivePhotoIndex] = useState(0);
  const [reportPage, setReportPage] = useState(1);
  const reportPageSize = 10;

  // 1. Fetch Issue Details
  const {
    data: issue,
    isLoading: isLoadingIssue,
    error: issueError,
    refetch: refetchIssue,
  } = useQuery({
    queryKey: queryKeys.issues.detail(id || ''),
    queryFn: () => issueRepository.getIssueById(id || ''),
    enabled: Boolean(id),
  });

  // 2. Fetch Priority Breakdown
  const { data: priorityData } = useQuery({
    queryKey: queryKeys.issues.priority(id || ''),
    queryFn: () => issueRepository.getIssuePriority(id || ''),
    enabled: Boolean(id),
  });

  // 3. Fetch Linked Reports
  const {
    data: reportsData,
    isLoading: isLoadingReports,
    error: reportsError,
  } = useQuery({
    queryKey: queryKeys.issues.reports(id || '', reportPage, reportPageSize),
    queryFn: () => issueRepository.getIssueReports(id || '', reportPage, reportPageSize),
    enabled: Boolean(id),
  });

  const handleCopyId = () => {
    if (issue?.id) {
      navigator.clipboard.writeText(issue.id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Aggregate photographic evidence from all linked reports
  const allEvidences = useMemo(() => {
    return (reportsData?.items || []).flatMap((report) =>
      (report.evidences || [])
        .filter((ev) => ev.evidence_type === 'IMAGE' && ev.storage_uri)
        .map((ev) => ({
          ...ev,
          reportId: report.id,
          trackingId: report.trackingId,
          submittedAt: report.createdAt,
        }))
    );
  }, [reportsData?.items]);

  // Map markers for MapRenderer
  const mapPoints: MapPoint[] = useMemo(() => {
    return (reportsData?.items || []).map((r) => ({
      id: r.id,
      trackingId: r.trackingId,
      latitude: r.latitude,
      longitude: r.longitude,
      category: r.category,
      severity: r.severity,
      description: r.description,
      addressHint: r.addressHint,
    }));
  }, [reportsData?.items]);

  // If issue has coordinates, ensure map center is on the issue centroid
  const mapCenter: [number, number] = useMemo(() => {
    return [issue?.latitude ?? 0, issue?.longitude ?? 0];
  }, [issue?.latitude, issue?.longitude]);

  if (isLoadingIssue) {
    return (
      <div className="p-6 space-y-6 max-w-7xl mx-auto">
        <div className="flex items-center gap-4">
          <LoadingSkeleton className="h-9 w-28" />
          <LoadingSkeleton className="h-9 w-64" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <LoadingSkeleton className="h-28 rounded-xl" />
          <LoadingSkeleton className="h-28 rounded-xl" />
          <LoadingSkeleton className="h-28 rounded-xl" />
          <LoadingSkeleton className="h-28 rounded-xl" />
        </div>
        <LoadingSkeleton className="h-80 rounded-xl" />
      </div>
    );
  }

  if (issueError || !issue) {
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <EmptyState
          icon={<AlertTriangle className="w-12 h-12 text-amber-500" />}
          title="Aggregated Issue Not Found"
          description={
            issueError instanceof Error
              ? issueError.message
              : `The requested issue with ID "${id}" could not be retrieved.`
          }
          actionLabel="Return to Reports Queue"
          onAction={() => navigate('/reports')}
        />
      </div>
    );
  }

  // Linked reports table columns
  const reportColumns: Column<ReportItem>[] = [
    {
      id: 'trackingId',
      header: 'Tracking ID',
      cell: (item) => (
        <div className="flex items-center gap-1.5 font-mono font-medium text-blue-600 dark:text-blue-400">
          <Link
            to={`/reports/${item.id}`}
            className="hover:underline flex items-center gap-1"
          >
            {item.trackingId}
            <ExternalLink className="w-3 h-3 opacity-60" />
          </Link>
        </div>
      ),
    },
    {
      id: 'submitted',
      header: 'Submitted',
      cell: (item) => (
        <span className="text-xs text-slate-600 dark:text-slate-400">
          {formatDateTime(item.createdAt)}
        </span>
      ),
    },
    {
      id: 'category',
      header: 'Category',
      cell: (item) => (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700">
          {item.category}
        </span>
      ),
    },
    {
      id: 'severity',
      header: 'Severity',
      cell: (item) => <SeverityBadge severity={item.severity} size="sm" />,
    },
    {
      id: 'status',
      header: 'Report Status',
      cell: (item) => <StatusBadge status={item.status} size="sm" />,
    },
    {
      id: 'department',
      header: 'Department / Officer',
      cell: (item) => (
        <div className="text-xs">
          <div className="font-medium text-slate-900 dark:text-slate-100">
            {item.department || 'Unassigned'}
          </div>
          {item.assignedOfficer && (
            <div className="text-slate-500 dark:text-slate-400 text-[11px]">
              {item.assignedOfficer}
            </div>
          )}
        </div>
      ),
    },
    {
      id: 'actions',
      header: '',
      cell: (item) => (
        <CivicButton
          variant="secondary"
          size="sm"
          onClick={() => navigate(`/reports/${item.id}`)}
        >
          View
        </CivicButton>
      ),
    },
  ];

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-4 sm:space-y-4.5"
    >
      {/* 1. Header & Navigation */}
      <motion.div variants={itemVariants} className="space-y-3">
        <div className="flex items-center justify-between">
          <CivicButton
            variant="ghost"
            size="sm"
            onClick={() => navigate(-1)}
            className="flex items-center gap-1.5 text-civic-text-secondary hover:text-civic-text-primary"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back
          </CivicButton>

          <div className="flex items-center gap-2">
            <Link
              to={`/reports?issueId=${issue.id}`}
              className="inline-flex items-center gap-1 text-xs font-medium text-civic-green dark:text-civic-green-light hover:underline"
            >
              <span>View in Reports Queue</span>
              <ExternalLink className="w-3 h-3" />
            </Link>
            <CivicButton
              variant="outline"
              size="sm"
              onClick={() => refetchIssue()}
              leftIcon={<RotateCcw className="w-3 h-3" />}
            >
              Refresh
            </CivicButton>
          </div>
        </div>

        <div className="p-4 sm:p-4.5 rounded-xl bg-civic-surface border border-civic-border/90 dark:bg-civic-dark-surface dark:border-civic-dark-border/90 shadow-xs">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold uppercase tracking-wider bg-civic-green/10 dark:bg-civic-green/20 text-civic-green dark:text-civic-green-light border border-civic-green/25">
                  <Layers className="w-3 h-3" />
                  Aggregated Issue
                </span>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-civic-surface-elevated dark:bg-civic-dark-surface-elevated text-civic-text-secondary dark:text-civic-dark-text-secondary border border-civic-border dark:border-civic-dark-border">
                  {issue.category}
                </span>
                <PriorityBadge priority={issue.priorityLevel} size="sm" />
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                  {issue.status}
                </span>
              </div>

              <h1 className="text-xl sm:text-2xl font-bold text-civic-text-primary dark:text-civic-dark-text-primary tracking-tight">
                {issue.title}
              </h1>

              <div className="flex items-center gap-2 text-xs text-civic-text-muted font-mono">
                <span>Issue ID: {issue.id}</span>
                <button
                  type="button"
                  onClick={handleCopyId}
                  className="hover:text-civic-text-primary transition-colors"
                  title="Copy Issue ID"
                >
                  {copied ? (
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Notice Banner explaining Domain Concept */}
      <motion.div
        variants={itemVariants}
        className="p-3.5 sm:p-4 rounded-xl border border-civic-green/20 bg-civic-green/5 dark:bg-civic-green/10 text-xs text-civic-text-primary dark:text-civic-dark-text-primary flex items-start gap-3"
      >
        <Layers className="w-4 h-4 text-civic-green shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <span className="font-semibold">Defect Cluster Workspace: </span>
          This entity represents an aggregated physical problem identified across{' '}
          <span className="font-semibold">{issue.reportCount}</span> citizen submission
          {issue.reportCount === 1 ? '' : 's'}. Priority scoring and triage are computed
          at the issue level, while individual reports preserve original evidence, GPS data, and citizen contact records.
        </div>
      </motion.div>

      {/* 2. Key Metrics Row */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-3.5">
        <StatCard
          title="Linked Citizen Reports"
          value={issue.reportCount}
          icon={<FileText className="w-4 h-4 text-blue-600" />}
          subtitle="Citizen submissions aggregated"
        />

        <StatCard
          title="Priority Score"
          value={
            issue.priorityScore !== null && issue.priorityScore !== undefined
              ? `${issue.priorityScore.toFixed(1)} / 100`
              : 'Uncalculated'
          }
          icon={<TrendingUp className="w-4 h-4 text-amber-600" />}
          subtitle={
            issue.priorityLevel
              ? `Ranked Level: ${issue.priorityLevel}`
              : 'Pending calculation'
          }
        />

        <StatCard
          title="Centroid Coordinates"
          value={`${issue.latitude.toFixed(4)}, ${issue.longitude.toFixed(4)}`}
          icon={<MapPin className="w-4 h-4 text-civic-green" />}
          subtitle="Primary defect focal point"
        />

        <StatCard
          title="Last Reported"
          value={formatDateTime(issue.updatedAt)}
          icon={<Clock className="w-4 h-4 text-indigo-600" />}
          subtitle={`First: ${formatDateTime(issue.createdAt)}`}
        />
      </motion.div>

      {/* 3. Media Carousel & Map Visualization */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-2 gap-3.5 sm:gap-4">
        {/* Evidence Photos Carousel */}
        <div className="p-4 sm:p-4.5 rounded-xl bg-civic-surface border border-civic-border/90 shadow-xs dark:bg-civic-dark-surface dark:border-civic-dark-border/90 flex flex-col justify-between space-y-3">
          <div className="flex items-center justify-between border-b border-civic-border/50 dark:border-civic-dark-border/50 pb-2.5">
            <h2 className="text-xs font-semibold text-civic-text-primary dark:text-civic-dark-text-primary uppercase tracking-wider flex items-center gap-2">
              <FileText className="w-3.5 h-3.5 text-civic-green" />
              Citizen Evidence Gallery ({allEvidences.length})
            </h2>
            {allEvidences.length > 1 && (
              <div className="flex items-center gap-1.5">
                <CivicButton
                  variant="ghost"
                  size="sm"
                  aria-label="Previous evidence photo"
                  disabled={activePhotoIndex === 0}
                  onClick={() => setActivePhotoIndex((i) => Math.max(0, i - 1))}
                  className="p-1 h-6 w-6"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </CivicButton>
                <span className="text-[11px] font-medium text-civic-text-muted">
                  {activePhotoIndex + 1} / {allEvidences.length}
                </span>
                <CivicButton
                  variant="ghost"
                  size="sm"
                  aria-label="Next evidence photo"
                  disabled={activePhotoIndex === allEvidences.length - 1}
                  onClick={() =>
                    setActivePhotoIndex((i) => Math.min(allEvidences.length - 1, i + 1))
                  }
                  className="p-1 h-6 w-6"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </CivicButton>
              </div>
            )}
          </div>

          {allEvidences.length > 0 ? (
            <div className="space-y-2.5">
              <div className="relative aspect-video w-full rounded-lg overflow-hidden bg-black/5 dark:bg-black/40 flex items-center justify-center border border-civic-border/80 dark:border-civic-dark-border/80">
                <img
                  src={resolveMediaUrl(allEvidences[activePhotoIndex]?.storage_uri) || ''}
                  alt={`Evidence for ${allEvidences[activePhotoIndex]?.trackingId}`}
                  loading="lazy"
                  className="max-h-full max-w-full object-contain transition-opacity duration-200"
                  onError={(e) => {
                    e.currentTarget.src =
                      'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="%23888" stroke-width="2"><rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>';
                  }}
                />
              </div>

              <div className="flex items-center justify-between text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary bg-civic-surface-elevated/70 dark:bg-civic-dark-surface-elevated/60 p-2.5 rounded-lg border border-civic-border/70 dark:border-civic-dark-border/70">
                <div>
                  Originating Report:{' '}
                  <Link
                    to={`/reports/${allEvidences[activePhotoIndex]?.reportId}`}
                    className="font-mono font-semibold text-civic-green dark:text-civic-green-light hover:underline"
                  >
                    {allEvidences[activePhotoIndex]?.trackingId}
                  </Link>
                </div>
                <div className="text-civic-text-muted">{formatDateTime(allEvidences[activePhotoIndex]?.submittedAt)}</div>
              </div>
            </div>
          ) : (
            <div className="py-12 text-center text-civic-text-muted space-y-1">
              <p className="text-xs font-medium">No Photographic Evidence</p>
              <p className="text-[11px]">
                No visual evidence has been submitted with the reports linked to this issue.
              </p>
            </div>
          )}
        </div>

        {/* Spatial Map View */}
        <div className="p-4 sm:p-4.5 rounded-xl bg-civic-surface border border-civic-border/90 shadow-xs dark:bg-civic-dark-surface dark:border-civic-dark-border/90 flex flex-col justify-between space-y-3">
          <div className="flex items-center justify-between border-b border-civic-border/50 dark:border-civic-dark-border/50 pb-2.5">
            <h2 className="text-xs font-semibold text-civic-text-primary dark:text-civic-dark-text-primary uppercase tracking-wider flex items-center gap-2">
              <MapPin className="w-3.5 h-3.5 text-civic-green" />
              Spatial Distribution & Centroid
            </h2>
            <span className="text-[11px] text-civic-text-muted font-mono">
              {mapPoints.length} Point{mapPoints.length === 1 ? '' : 's'}
            </span>
          </div>

          <div className="h-64 w-full rounded-lg overflow-hidden border border-civic-border/80 dark:border-civic-dark-border/80">
            <MapRenderer
              points={mapPoints}
              center={mapCenter}
              zoom={15}
              onSelectPoint={(pointId) => navigate(`/reports/${pointId}`)}
              className="h-full w-full"
            />
          </div>

          <div className="text-[11px] text-civic-text-muted flex items-center gap-1.5">
            <MapPin className="w-3 h-3 text-civic-green shrink-0" />
            <span>
              Primary Centroid at {issue.latitude.toFixed(5)}, {issue.longitude.toFixed(5)}.
              Click markers to inspect constituent reports.
            </span>
          </div>
        </div>
      </motion.div>

      {/* 4. Priority Scorecard & Algorithmic Breakdown */}
      {priorityData && (
        <motion.div
          variants={itemVariants}
          className="p-4 sm:p-4.5 rounded-xl bg-civic-surface border border-civic-border/90 shadow-xs dark:bg-civic-dark-surface dark:border-civic-dark-border/90 space-y-3.5"
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-civic-border/50 dark:border-civic-dark-border/50 pb-2.5">
            <div>
              <h2 className="text-xs font-semibold text-civic-text-primary dark:text-civic-dark-text-primary uppercase tracking-wider flex items-center gap-2">
                <TrendingUp className="w-3.5 h-3.5 text-amber-500" />
                Priority Scorecard Breakdown
              </h2>
              <p className="text-xs text-civic-text-muted">
                Multi-factor operational ranking calculated by the CivicSense Priority Engine
              </p>
            </div>
            {priorityData.priorityComputedAt && (
              <span className="text-[11px] text-civic-text-muted font-mono">
                Computed: {formatDateTime(priorityData.priorityComputedAt)}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
            <div className="p-3 rounded-xl bg-civic-surface-elevated/70 dark:bg-civic-dark-surface-elevated/60 border border-civic-border/80 dark:border-civic-dark-border/80 space-y-1">
              <span className="text-[11px] text-civic-text-muted font-medium">
                Overall Priority
              </span>
              <div className="flex items-baseline gap-1.5">
                <span className="text-xl font-bold font-mono text-civic-text-primary dark:text-civic-dark-text-primary">
                  {priorityData.priorityScore !== null && priorityData.priorityScore !== undefined
                    ? priorityData.priorityScore.toFixed(1)
                    : '--'}
                </span>
                <span className="text-[11px] text-civic-text-muted font-mono">/ 100</span>
              </div>
              <span className="text-[10px] text-civic-text-muted font-mono block">
                Level: {priorityData.priorityLevel || 'UNSET'}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-civic-surface-elevated/70 dark:bg-civic-dark-surface-elevated/60 border border-civic-border/80 dark:border-civic-dark-border/80 space-y-1">
              <span className="text-[11px] text-civic-text-muted font-medium">
                Severity Factor
              </span>
              <div className="text-lg font-bold font-mono text-civic-text-primary dark:text-civic-dark-text-primary">
                {priorityData.breakdown?.severity_score !== undefined
                  ? (priorityData.breakdown.severity_score * 100).toFixed(0)
                  : '--'}%
              </div>
              <span className="text-[10px] text-civic-text-muted block">
                Weight: 30% | {priorityData.breakdown?.max_severity || 'LOW'}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-civic-surface-elevated/70 dark:bg-civic-dark-surface-elevated/60 border border-civic-border/80 dark:border-civic-dark-border/80 space-y-1">
              <span className="text-[11px] text-civic-text-muted font-medium">
                Volume Factor
              </span>
              <div className="text-lg font-bold font-mono text-civic-text-primary dark:text-civic-dark-text-primary">
                {priorityData.breakdown?.report_volume_score !== undefined
                  ? (priorityData.breakdown.report_volume_score * 100).toFixed(0)
                  : '--'}%
              </div>
              <span className="text-[10px] text-civic-text-muted block">
                Weight: 25% | {priorityData.breakdown?.report_count ?? issue.reportCount} rpts
              </span>
            </div>

            <div className="p-3 rounded-xl bg-civic-surface-elevated/70 dark:bg-civic-dark-surface-elevated/60 border border-civic-border/80 dark:border-civic-dark-border/80 space-y-1">
              <span className="text-[11px] text-civic-text-muted font-medium">
                Reporter Diversity
              </span>
              <div className="text-lg font-bold font-mono text-civic-text-primary dark:text-civic-dark-text-primary">
                {priorityData.breakdown?.unique_reporter_score !== undefined
                  ? (priorityData.breakdown.unique_reporter_score * 100).toFixed(0)
                  : '--'}%
              </div>
              <span className="text-[10px] text-civic-text-muted block">
                Weight: 20% | {priorityData.breakdown?.unique_reporter_count ?? 1} citizens
              </span>
            </div>

            <div className="p-3 rounded-xl bg-civic-surface-elevated/70 dark:bg-civic-dark-surface-elevated/60 border border-civic-border/80 dark:border-civic-dark-border/80 space-y-1">
              <span className="text-[11px] text-civic-text-muted font-medium">
                Recency & Aging
              </span>
              <div className="text-lg font-bold font-mono text-civic-text-primary dark:text-civic-dark-text-primary">
                {priorityData.breakdown?.recency_score !== undefined
                  ? (priorityData.breakdown.recency_score * 100).toFixed(0)
                  : '--'}%
              </div>
              <span className="text-[10px] text-civic-text-muted block">
                Weight: 25% (15% rec, 10% age)
              </span>
            </div>
          </div>
          <p className="text-[11px] text-civic-text-muted italic">
            Priority score is an automated decision-support estimate based on 5 weighted signals (Formula v{priorityData.breakdown?.formula_version || '1.0'}).
          </p>
        </motion.div>
      )}

      {/* 5. Linked Reports Data Table */}
      <motion.div
        variants={itemVariants}
        className="p-4 sm:p-4.5 rounded-xl bg-civic-surface border border-civic-border/90 shadow-xs dark:bg-civic-dark-surface dark:border-civic-dark-border/90 space-y-3.5"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-civic-border/50 dark:border-civic-dark-border/50 pb-2.5">
          <div>
            <h2 className="text-xs font-semibold text-civic-text-primary dark:text-civic-dark-text-primary uppercase tracking-wider flex items-center gap-2">
              <FileText className="w-3.5 h-3.5 text-civic-green" />
              Constituent Citizen Reports ({reportsData?.total || 0})
            </h2>
            <p className="text-xs text-civic-text-muted">
              Individual citizen submissions deduplicated and linked under this aggregated issue
            </p>
          </div>

          <Link
            to={`/reports?issueId=${issue.id}`}
            className="text-xs font-medium text-civic-green dark:text-civic-green-light hover:underline flex items-center gap-1 self-start sm:self-auto"
          >
            View in Reports Queue
            <ExternalLink className="w-3 h-3" />
          </Link>
        </div>

        {reportsError && (
          <ErrorBanner
            message="Failed to load linked citizen reports."
            onRetry={() => window.location.reload()}
          />
        )}

        <DataTable<ReportItem>
          data={reportsData?.items || []}
          columns={reportColumns}
          keyExtractor={(item) => item.id}
          isLoading={isLoadingReports}
          emptyTitle="No Reports Linked"
          emptyDescription="No citizen reports are currently linked to this aggregated issue."
          page={reportPage}
          totalPages={reportsData?.totalPages || 1}
          totalItems={reportsData?.total || 0}
          pageSize={reportPageSize}
          onPageChange={setReportPage}
          onRowClick={(item) => navigate(`/reports/${item.id}`)}
        />
      </motion.div>
    </motion.div>
  );
};
