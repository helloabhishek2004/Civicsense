import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Cpu,
  RefreshCw,
  AlertTriangle,
  Activity,
  ChevronRight,
  Layers,
  ExternalLink,
  Info,
  GitMerge,
  ShieldAlert,
} from 'lucide-react';
import { reportRepository } from '@/services/repository/reportRepository';
import { issueRepository } from '@/services/repository/issueRepository';
import { queryKeys } from '@/services/queryKeys';
import { AIJob, AIProcessingStage, MetricItem } from '@/types/ai';
import { CandidateMatchItem } from '@/types/issues';
import { CivicButton } from '@/core/components/CivicButton';
import { LoadingSkeleton } from '@/core/components/LoadingSkeleton';
import { DataTable, Column } from '@/core/components/DataTable';
import { Modal } from '@/core/components/Modal';
import { ErrorBanner } from '@/core/components/ErrorBanner';
import { useAuth } from '@/core/auth/AuthContext';
import { can } from '@/core/auth/permissions';
import { formatDateTime } from '@/core/utils/dateUtils';
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

const STAGES: { stage: AIProcessingStage; label: string; desc: string }[] = [
  {
    stage: 'INTAKE_VALIDATION',
    label: 'Intake Validation',
    desc: 'Schema integrity, image hash generation, GPS range checks',
  },
  {
    stage: 'PREPROCESSING',
    label: 'Preprocessing',
    desc: 'Aspect ratio normalization, EXIF cleanup, text sanitization',
  },
  {
    stage: 'VISION_ANALYSIS',
    label: 'Vision Inference',
    desc: 'Visual feature extraction, defect surface detection',
  },
  {
    stage: 'TEXT_ANALYSIS',
    label: 'Text Inference',
    desc: 'Keyword token extraction, urgency signal detection',
  },
  {
    stage: 'FUSION',
    label: 'Multimodal Fusion',
    desc: 'Cross-modal alignment, evidence agreement scoring',
  },
  {
    stage: 'DECISION',
    label: 'Decision Engine',
    desc: 'Category recommendation, severity rating, SLA priority',
  },
  {
    stage: 'HUMAN_REVIEW',
    label: 'Human Review Gate',
    desc: 'Confidence gating: flags low confidence or modality conflicts',
  },
  {
    stage: 'COMPLETED',
    label: 'Completed / Dispatched',
    desc: 'Audit event immutability, municipal triage handoff',
  },
];

const renderMetricValue = <T,>(
  metric?: MetricItem<T>,
  formatter?: (val: T) => string,
  suffix = ''
): { text: string; isInsufficient: boolean } => {
  if (!metric || metric.display_state === 'INSUFFICIENT_DATA' || metric.value === null) {
    return { text: 'INSUFFICIENT DATA', isInsufficient: true };
  }
  return {
    text: formatter ? formatter(metric.value) : `${metric.value}${suffix}`,
    isInsufficient: false,
  };
};

export const AIOperationsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const activeTab = searchParams.get('tab') === 'matches' ? 'matches' : 'pipeline';
  const { user } = useAuth();
  const canReviewMatches = can(user, 'review_matches');
  const reviewerId = user?.badgeNumber || user?.id;

  const selectedJobIdFromUrl = searchParams.get('jobId');
  const [selectedJobId, setSelectedJobId] = useState<string | null>(selectedJobIdFromUrl);
  const [stageFilter, setStageFilter] = useState<string>('ALL');
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Match review state
  const [selectedMatch, setSelectedMatch] = useState<CandidateMatchItem | null>(null);
  const [matchAction, setMatchAction] = useState<'APPROVE' | 'REJECT' | null>(null);
  const [reviewNotes, setReviewNotes] = useState('');
  const [altIssueId, setAltIssueId] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (selectedJobIdFromUrl) {
      setSelectedJobId(selectedJobIdFromUrl);
    }
  }, [selectedJobIdFromUrl]);

  // Query AI Health
  const { data: health } = useQuery({
    queryKey: queryKeys.ai.health(),
    queryFn: () => reportRepository.getAIHealth(),
    refetchInterval: autoRefresh ? 8000 : false,
  });

  // Query AI Metrics
  const { data: metrics } = useQuery({
    queryKey: queryKeys.ai.metrics(),
    queryFn: () => reportRepository.getAIMetrics(),
    refetchInterval: autoRefresh ? 8000 : false,
  });

  // Query AI Jobs List
  const {
    data: jobsData,
    isLoading: isJobsLoading,
    refetch: refetchJobs,
  } = useQuery({
    queryKey: queryKeys.ai.jobs({ stage: stageFilter !== 'ALL' ? stageFilter : undefined }),
    queryFn: () =>
      reportRepository.getAIJobs({
        page: 1,
        pageSize: 50,
        stage: stageFilter !== 'ALL' ? stageFilter : undefined,
      }),
    refetchInterval: autoRefresh ? 4000 : false,
  });

  // Query Selected Job Events
  const selectedJob = jobsData?.items.find((j) => j.id === selectedJobId) || jobsData?.items[0];

  const { data: events, isLoading: isEventsLoading } = useQuery({
    queryKey: queryKeys.ai.events(selectedJob?.report_id || ''),
    queryFn: () => reportRepository.getReportAIEvents(selectedJob!.report_id),
    enabled: !!selectedJob?.report_id,
    refetchInterval: autoRefresh && selectedJob?.status === 'PROCESSING' ? 2000 : false,
  });

  // Query Pending Matches
  const {
    data: matchesData,
    isLoading: isMatchesLoading,
    error: matchesError,
    refetch: refetchMatches,
  } = useQuery({
    queryKey: queryKeys.matches.pending(),
    queryFn: () => issueRepository.getPendingMatches(),
    refetchInterval: autoRefresh ? 6000 : false,
  });

  // Approve Match Mutation
  const approveMutation = useMutation({
    mutationFn: async ({ matchId, notes }: { matchId: string; notes?: string }) => {
      const revId = user?.badgeNumber || user?.id;
      if (!revId) {
        throw new Error('A valid municipal reviewer ID (badge number or user ID) is required to approve matches.');
      }
      return issueRepository.approveMatch(matchId, revId, notes);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.matches.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.issues.all });
      setSelectedMatch(null);
      setMatchAction(null);
      setReviewNotes('');
      setActionError(null);
    },
    onError: (err) => {
      setActionError(err instanceof Error ? err.message : 'Failed to approve candidate match.');
    },
  });

  // Reject Match Mutation
  const rejectMutation = useMutation({
    mutationFn: async ({
      matchId,
      notes,
      linkToIssueId,
    }: {
      matchId: string;
      notes?: string;
      linkToIssueId?: string;
    }) => {
      const revId = user?.badgeNumber || user?.id;
      if (!revId) {
        throw new Error('A valid municipal reviewer ID (badge number or user ID) is required to reject matches.');
      }
      return issueRepository.rejectMatch(matchId, revId, notes, linkToIssueId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.matches.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.issues.all });
      setSelectedMatch(null);
      setMatchAction(null);
      setReviewNotes('');
      setAltIssueId('');
      setActionError(null);
    },
    onError: (err) => {
      setActionError(err instanceof Error ? err.message : 'Failed to reject candidate match.');
    },
  });

  const handleSelectJob = (job: AIJob) => {
    setSelectedJobId(job.id);
    setSearchParams((prev) => {
      prev.set('jobId', job.id);
      return prev;
    });
  };

  const handleManualRefresh = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.ai.all });
    queryClient.invalidateQueries({ queryKey: queryKeys.matches.all });
    refetchJobs();
    refetchMatches();
  };

  // Calculate stage counts from active jobs
  const stageCounts: Record<string, number> = {};
  (jobsData?.items || []).forEach((j) => {
    stageCounts[j.current_stage] = (stageCounts[j.current_stage] || 0) + 1;
  });

  // Match Review Columns
  const matchColumns: Column<CandidateMatchItem>[] = [
    {
      id: 'reportId',
      header: 'Report',
      cell: (item) => (
        <div className="flex flex-col">
          <Link
            to={`/reports/${item.reportId}`}
            className="font-mono text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
          >
            <span>rep-{item.reportId.substring(0, 8)}</span>
            <ExternalLink className="w-3 h-3 opacity-60" />
          </Link>
          <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
            {formatDateTime(item.createdAt)}
          </span>
        </div>
      ),
    },
    {
      id: 'issueId',
      header: 'Target Defect Cluster',
      cell: (item) => (
        <div className="flex flex-col">
          {item.issueId ? (
            <Link
              to={`/issues/${item.issueId}`}
              className="font-mono text-xs font-semibold text-purple-600 dark:text-purple-400 hover:underline flex items-center gap-1"
            >
              <span>iss-{item.issueId.substring(0, 8)}</span>
              <ExternalLink className="w-3 h-3 opacity-60" />
            </Link>
          ) : (
            <span className="text-xs text-slate-400 italic font-mono">Unassigned Issue</span>
          )}
          <span className="text-[10px] text-slate-500 dark:text-slate-400">
            Existing defect cluster
          </span>
        </div>
      ),
    },
    {
      id: 'similarityScore',
      header: 'Match Confidence',
      cell: (item) => {
        const pct = (item.similarityScore * 100).toFixed(1);
        return (
          <div className="flex flex-col gap-1">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-bold ${
                item.similarityScore >= 0.6
                  ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-300 dark:border-amber-800'
                  : 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-300 dark:border-blue-800'
              }`}
            >
              {pct}% Confidence
            </span>
            <span className="text-[10px] text-slate-400 font-mono">Range: [45% - 70%)</span>
          </div>
        );
      },
    },
    {
      id: 'breakdown',
      header: 'Signals Breakdown',
      cell: (item) => (
        <div className="text-xs space-y-0.5">
          <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
            <span className="text-[11px] font-medium text-slate-400">Text:</span>
            <span className="font-mono font-medium">{(item.textSimilarity * 100).toFixed(1)}%</span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
            <span className="text-[11px] font-medium text-slate-400">Distance:</span>
            <span className="font-mono font-medium">{item.distanceMeters.toFixed(1)} m</span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
            <span className="text-[11px] font-medium text-slate-400">Category:</span>
            <span className="font-medium">
              {item.categoryMatch === 1.0 ? 'Exact' : item.categoryMatch === 0.5 ? 'Bridge' : 'Mismatch'}
            </span>
          </div>
        </div>
      ),
    },
    {
      id: 'reasoning',
      header: 'Engine Rationale',
      cell: (item) => (
        <div className="max-w-xs text-xs text-slate-600 dark:text-slate-400 space-y-0.5">
          {item.reasoning && item.reasoning.length > 0 ? (
            item.reasoning.map((r, i) => (
              <div key={i} className="flex items-start gap-1">
                <span className="text-purple-500 leading-none mt-1">•</span>
                <span className="text-[11px]">{r}</span>
              </div>
            ))
          ) : (
            <span className="text-[11px] text-slate-400 italic">
              Text & spatial proximity match
            </span>
          )}
          {item.embeddingModelVersion && (
            <div className="text-[10px] font-mono text-slate-400 pt-1">
              Model: {item.embeddingModelVersion}
            </div>
          )}
        </div>
      ),
    },
    {
      id: 'actions',
      header: 'Review Actions',
      cell: (item) => (
        <div className="flex items-center gap-2 justify-end">
          <CivicButton
            variant="primary"
            size="sm"
            disabled={!canReviewMatches || !reviewerId}
            onClick={() => {
              setSelectedMatch(item);
              setMatchAction('APPROVE');
              setReviewNotes('');
              setActionError(null);
            }}
            className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-2.5 py-1"
            title={
              !canReviewMatches
                ? 'Only Triage Officers and Super Admins can review matches'
                : !reviewerId
                ? 'Reviewer identity missing'
                : 'Confirm report linkage to this issue'
            }
          >
            Approve
          </CivicButton>

          <CivicButton
            variant="outline"
            size="sm"
            disabled={!canReviewMatches || !reviewerId}
            onClick={() => {
              setSelectedMatch(item);
              setMatchAction('REJECT');
              setReviewNotes('');
              setAltIssueId('');
              setActionError(null);
            }}
            className="text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 text-xs px-2.5 py-1 border-red-200 dark:border-red-900"
            title={
              !canReviewMatches
                ? 'Only Triage Officers and Super Admins can review matches'
                : !reviewerId
                ? 'Reviewer identity missing'
                : 'Reject this candidate match'
            }
          >
            Reject
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
      className="space-y-6 pb-12"
    >
      {/* 1. Header & Live Worker Status */}
      <motion.div variants={itemVariants} className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-civic-border dark:border-civic-dark-border pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-purple-600 text-white shadow-civic-subtle">
              <Cpu className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-civic-text-primary dark:text-civic-dark-text-primary">
                AI Operations & Pipeline Center
              </h1>
              <p className="text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary mt-0.5">
                Deterministic Multimodal Inference, Decision Confidence Gating & Audit Transparency
              </p>
            </div>
          </div>
        </div>

        {/* Worker Health, Processor Disclosure & Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Worker Health Pill */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border border-civic-border bg-civic-surface dark:bg-civic-dark-surface dark:border-civic-dark-border shadow-civic-card">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                health?.status === 'available'
                  ? 'bg-emerald-500 animate-pulse'
                  : health?.status === 'degraded'
                  ? 'bg-amber-500'
                  : 'bg-red-500'
              }`}
            />
            <span className="text-civic-text-primary dark:text-civic-dark-text-primary">
              Pipeline: {health?.status === 'available' ? 'Operational' : 'Degraded'}
            </span>
            <span className="text-[10px] text-civic-text-muted font-mono hidden sm:inline">
              ({health?.execution_mode || 'API Mode'})
            </span>
          </div>

          {/* Auto Refresh Toggle */}
          <button
            type="button"
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors flex items-center gap-1.5 ${
              autoRefresh
                ? 'border-purple-300 bg-purple-50 text-purple-800 dark:border-purple-800 dark:bg-purple-950/40 dark:text-purple-300'
                : 'border-civic-border bg-civic-surface text-civic-text-secondary dark:border-civic-dark-border dark:bg-civic-dark-surface'
            }`}
          >
            <Activity className={`w-3.5 h-3.5 ${autoRefresh ? 'text-purple-600 dark:text-purple-400' : ''}`} />
            Auto-Sync {autoRefresh ? 'ON' : 'OFF'}
          </button>

          {/* Manual Refresh */}
          <CivicButton
            variant="outline"
            size="sm"
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            onClick={handleManualRefresh}
          >
            Refresh
          </CivicButton>
        </div>
      </motion.div>

      {/* 2. Navigation Tabs */}
      <motion.div variants={itemVariants} className="flex border-b border-civic-border dark:border-civic-dark-border gap-6">
        <button
          type="button"
          onClick={() => {
            setSearchParams((prev) => {
              prev.delete('tab');
              return prev;
            });
          }}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
            activeTab !== 'matches'
              ? 'border-purple-600 text-purple-600 dark:text-purple-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
        >
          <Cpu className="w-4 h-4" />
          Pipeline Stages & Execution
        </button>

        <button
          type="button"
          onClick={() => {
            setSearchParams((prev) => {
              prev.set('tab', 'matches');
              return prev;
            });
          }}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === 'matches'
              ? 'border-purple-600 text-purple-600 dark:text-purple-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
        >
          <GitMerge className="w-4 h-4" />
          Candidate Duplicate Reviews
          {(matchesData?.total ?? 0) > 0 && (
            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300">
              {matchesData?.total}
            </span>
          )}
        </button>
      </motion.div>

      {activeTab === 'matches' ? (
        <motion.div variants={itemVariants} className="space-y-6">
          {/* Reviewer Identity Notice */}
          {!reviewerId && (
            <div className="p-4 rounded-xl border border-red-300 bg-red-50 dark:bg-red-950/40 dark:border-red-900/60 text-xs text-red-800 dark:text-red-300 flex items-start gap-3">
              <ShieldAlert className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block text-sm">Reviewer Identity Required</span>
                <span>
                  You must be authenticated with a valid badge number or officer ID to review candidate duplicate matches.
                  Review actions fail closed without an authenticated officer identity.
                </span>
              </div>
            </div>
          )}

          {!canReviewMatches && reviewerId && (
            <div className="p-4 rounded-xl border border-amber-300 bg-amber-50 dark:bg-amber-950/40 dark:border-amber-900/60 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-3">
              <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block text-sm">Read-Only Permission</span>
                <span>
                  Your role does not have authorization to approve or reject duplicate linkages.
                  Only Triage Officers and Super Administrators may execute duplicate decisions.
                </span>
              </div>
            </div>
          )}

          {/* Context Banner */}
          <div className="p-4 rounded-xl border border-purple-200 dark:border-purple-900/60 bg-purple-50/50 dark:bg-purple-950/20 text-xs text-purple-900 dark:text-purple-300 flex items-start gap-3">
            <Info className="w-4 h-4 text-purple-600 dark:text-purple-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Candidate Duplicate Triage: </span>
              Candidate matches are identified when incoming reports match an existing defect cluster with confidence in the
              operational candidate window <strong className="font-mono">[45%, 70%)</strong>. Approving a match links the report to the issue.
              Rejecting creates an independent issue or links to an alternate issue.
            </div>
          </div>

          {/* Matches Data Table */}
          <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border space-y-4">
            <div className="flex items-center justify-between border-b border-civic-border dark:border-civic-dark-border pb-3">
              <h2 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary uppercase tracking-wider flex items-center gap-2">
                <GitMerge className="w-4 h-4 text-purple-600" />
                Pending Duplicate Matches ({matchesData?.total || 0})
              </h2>
              <CivicButton
                variant="ghost"
                size="sm"
                onClick={() => refetchMatches()}
                className="text-xs"
              >
                Refresh Queue
              </CivicButton>
            </div>

            {matchesError && (
              <ErrorBanner
                title="Failed to fetch candidate matches"
                message={matchesError instanceof Error ? matchesError.message : 'Unknown error'}
                onRetry={() => refetchMatches()}
              />
            )}

            <DataTable<CandidateMatchItem>
              data={matchesData?.items || []}
              columns={matchColumns}
              keyExtractor={(item) => item.id}
              isLoading={isMatchesLoading}
              emptyTitle="No Pending Matches"
              emptyDescription="There are currently no candidate duplicate matches requiring municipal officer review."
            />
          </div>
        </motion.div>
      ) : (
        <div className="space-y-6">
          {/* 2. Honest System Architecture Banner */}
          <motion.div variants={itemVariants} className="p-4 rounded-civic bg-purple-50/70 border border-purple-200 dark:bg-purple-950/30 dark:border-purple-900/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-start gap-3">
          <Info className="w-4 h-4 text-purple-700 dark:text-purple-300 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="font-semibold text-purple-900 dark:text-purple-200 block">
              Active Processing Engine: {health?.processor_name || 'CivicSense Deterministic Demo Processor'}
            </span>
            <p className="text-[11px] text-purple-800 dark:text-purple-300">
              {health?.disclaimer ||
                'Running prototype deterministic rule and pattern engines with persistent audit event emission. Model inferences provide probabilistic suggestions, not ground truth.'}
            </p>
          </div>
        </div>
        <div className="shrink-0 flex items-center gap-2">
          <span className="px-2.5 py-1 rounded bg-purple-100 text-purple-900 dark:bg-purple-900/60 dark:text-purple-200 text-[10px] font-mono font-medium">
            Threshold: 70% Confidence
          </span>
          <span className="px-2.5 py-1 rounded bg-purple-100 text-purple-900 dark:bg-purple-900/60 dark:text-purple-200 text-[10px] font-mono font-medium">
            Agreement: 60% Min
          </span>
        </div>
      </motion.div>

      {/* 3. Operational KPIs Grid (with INSUFFICIENT_DATA Handling) */}
      <motion.div variants={itemVariants} className="grid grid-cols-2 lg:grid-cols-6 gap-3">
        {/* Active Jobs */}
        <div className="p-3.5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
          <span className="text-[10px] uppercase font-bold tracking-wider text-civic-text-muted block">
            Active Jobs
          </span>
          <span className="text-2xl font-bold font-mono text-purple-600 dark:text-purple-400 mt-1 block">
            {metrics?.active_jobs?.value ?? 0}
          </span>
          <span className="text-[10px] text-civic-text-muted mt-0.5 block">Queued & Processing</span>
        </div>

        {/* Total Ingested Jobs */}
        <div className="p-3.5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
          <span className="text-[10px] uppercase font-bold tracking-wider text-civic-text-muted block">
            Completed Inferences
          </span>
          <span className="text-2xl font-bold font-mono text-civic-text-primary dark:text-civic-dark-text-primary mt-1 block">
            {metrics?.completed_jobs?.value ?? 0}
          </span>
          <span className="text-[10px] text-civic-text-muted mt-0.5 block">
            Sample: {metrics?.completed_jobs?.sample_size ?? 0} tickets
          </span>
        </div>

        {/* Human Triage Escalation Rate */}
        {(() => {
          const formatted = renderMetricValue(
            metrics?.awaiting_human_review,
            (val) => `${val}`,
            ''
          );
          return (
            <div className="p-3.5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
              <span className="text-[10px] uppercase font-bold tracking-wider text-civic-text-muted block">
                Flagged for Review
              </span>
              <span
                className={`text-2xl font-bold font-mono mt-1 block ${
                  formatted.isInsufficient
                    ? 'text-xs text-civic-text-muted pt-2'
                    : 'text-amber-600 dark:text-amber-400'
                }`}
              >
                {formatted.text}
              </span>
              <span className="text-[10px] text-civic-text-muted mt-0.5 block">Confidence &lt; 0.70</span>
            </div>
          );
        })()}

        {/* Modality Disagreement Rate */}
        {(() => {
          const formatted = renderMetricValue(
            metrics?.modality_disagreement_rate,
            (val) => `${Math.round(val * 100)}%`
          );
          return (
            <div className="p-3.5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
              <span className="text-[10px] uppercase font-bold tracking-wider text-civic-text-muted block">
                Modality Conflicts
              </span>
              <span
                className={`text-2xl font-bold font-mono mt-1 block ${
                  formatted.isInsufficient
                    ? 'text-xs text-civic-text-muted pt-2'
                    : 'text-orange-600 dark:text-orange-400'
                }`}
              >
                {formatted.text}
              </span>
              <span className="text-[10px] text-civic-text-muted mt-0.5 block">Vision vs. Text</span>
            </div>
          );
        })()}

        {/* Human Override Rate */}
        {(() => {
          const formatted = renderMetricValue(
            metrics?.human_override_rate,
            (val) => `${Math.round(val * 100)}%`
          );
          return (
            <div className="p-3.5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
              <span className="text-[10px] uppercase font-bold tracking-wider text-civic-text-muted block">
                Officer Override Rate
              </span>
              <span
                className={`text-2xl font-bold font-mono mt-1 block ${
                  formatted.isInsufficient
                    ? 'text-xs text-civic-text-muted pt-2'
                    : 'text-blue-600 dark:text-blue-400'
                }`}
              >
                {formatted.text}
              </span>
              <span className="text-[10px] text-civic-text-muted mt-0.5 block">Category corrected</span>
            </div>
          );
        })()}

        {/* Avg Latency */}
        {(() => {
          const formatted = renderMetricValue(
            metrics?.avg_processing_latency_ms,
            (val) => `${Math.round(val)} ms`
          );
          return (
            <div className="p-3.5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
              <span className="text-[10px] uppercase font-bold tracking-wider text-civic-text-muted block">
                Avg Latency
              </span>
              <span
                className={`text-2xl font-bold font-mono mt-1 block ${
                  formatted.isInsufficient
                    ? 'text-xs text-civic-text-muted pt-2'
                    : 'text-civic-text-primary dark:text-civic-dark-text-primary'
                }`}
              >
                {formatted.text}
              </span>
              <span className="text-[10px] text-civic-text-muted mt-0.5 block">End-to-end stages</span>
            </div>
          );
        })()}
      </motion.div>

      {/* 4. Conveyor-Belt Pipeline Visualizer (8 Real Stages) */}
      <motion.div variants={itemVariants} className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-civic-text-primary dark:text-civic-dark-text-primary flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-600" />
              8-Stage Deterministic Pipeline Topology
            </h2>
            <p className="text-xs text-civic-text-muted mt-0.5">
              Strictly sequenced execution graph with persisted event emission at every boundary
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] text-civic-text-muted font-medium">Filter by Stage:</span>
            <select
              value={stageFilter}
              onChange={(e) => setStageFilter(e.target.value)}
              className="h-8 px-2.5 text-xs rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border"
            >
              <option value="ALL">All Stages (Topology View)</option>
              {STAGES.map((s) => (
                <option key={s.stage} value={s.stage}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Visual Pipeline Conveyor */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {STAGES.map((s, idx) => {
            const count = stageCounts[s.stage] || 0;
            const isSelected = selectedJob?.current_stage === s.stage;

            return (
              <div
                key={s.stage}
                onClick={() => setStageFilter(s.stage)}
                className={`p-3.5 rounded-lg border transition-all cursor-pointer relative overflow-hidden ${
                  isSelected
                    ? 'border-purple-500 bg-purple-50/50 dark:border-purple-700 dark:bg-purple-950/40 shadow-sm'
                    : count > 0
                    ? 'border-civic-border bg-gray-50/70 hover:border-purple-300 dark:border-civic-dark-border dark:bg-civic-dark-surface-elevated/40'
                    : 'border-civic-border bg-civic-surface hover:bg-gray-50/50 dark:border-civic-dark-border dark:bg-civic-dark-surface'
                }`}
              >
                <div className="flex items-center justify-between gap-1 mb-1">
                  <span className="text-[10px] font-mono font-bold text-purple-700 dark:text-purple-300">
                    STAGE {idx + 1}
                  </span>
                  {count > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-800 dark:bg-purple-900/60 dark:text-purple-200 text-[10px] font-bold font-mono">
                      {count} active
                    </span>
                  )}
                </div>
                <h3 className="text-xs font-semibold text-civic-text-primary dark:text-civic-dark-text-primary truncate">
                  {s.label}
                </h3>
                <p className="text-[11px] text-civic-text-muted mt-1 line-clamp-2">
                  {s.desc}
                </p>

                {/* Flow connector dot */}
                {idx < STAGES.length - 1 && (
                  <div className="hidden lg:block absolute right-0 top-1/2 -translate-y-1/2 translate-x-1.5 z-10">
                    <ChevronRight className="w-3.5 h-3.5 text-gray-300 dark:text-gray-600" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </motion.div>

      {/* 5. Main Content Columns: Active Jobs (Left) & Persisted Event Audit Log (Right) */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT (7 cols): AI Processing Jobs Table */}
        <div className="lg:col-span-7 space-y-4">
          <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-bold text-civic-text-primary dark:text-civic-dark-text-primary">
                  AI Inference Jobs Feed
                </h2>
                <span className="text-xs text-civic-text-muted">
                  Total recorded jobs: {jobsData?.total ?? 0}
                </span>
              </div>
              {stageFilter !== 'ALL' && (
                <button
                  type="button"
                  onClick={() => setStageFilter('ALL')}
                  className="text-xs text-purple-600 dark:text-purple-400 font-medium hover:underline"
                >
                  Clear Filter
                </button>
              )}
            </div>

            {isJobsLoading ? (
              <div className="space-y-2 py-4">
                <LoadingSkeleton className="h-10 w-full" />
                <LoadingSkeleton className="h-10 w-full" />
                <LoadingSkeleton className="h-10 w-full" />
              </div>
            ) : !jobsData?.items || jobsData.items.length === 0 ? (
              <div className="p-8 text-center text-xs text-civic-text-muted border border-dashed border-civic-border dark:border-civic-dark-border rounded-lg">
                No AI inference jobs found for current filter.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-civic-border dark:border-civic-dark-border text-civic-text-muted text-[11px] font-medium">
                      <th className="py-2.5 px-3">Job ID</th>
                      <th className="py-2.5 px-3">Current Stage</th>
                      <th className="py-2.5 px-3">Review Flag</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3 text-right">Inspect</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-civic-border dark:divide-civic-dark-border">
                    {jobsData.items.map((job) => {
                      const isSelected = selectedJob?.id === job.id;
                      return (
                        <tr
                          key={job.id}
                          onClick={() => handleSelectJob(job)}
                          className={`cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-purple-50/70 dark:bg-purple-950/40'
                              : 'hover:bg-gray-50 dark:hover:bg-civic-dark-surface-elevated'
                          }`}
                        >
                          <td className="py-2.5 px-3 font-mono">
                            <span className="font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                              {job.id.slice(0, 8)}...
                            </span>
                            <span className="block text-[10px] text-civic-text-muted">
                              Rep: {job.report_id.slice(0, 8)}
                            </span>
                          </td>

                          <td className="py-2.5 px-3">
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-gray-100 text-gray-800 dark:bg-civic-dark-surface-elevated dark:text-gray-200">
                              {job.current_stage}
                            </span>
                          </td>

                          <td className="py-2.5 px-3">
                            {job.review_required ? (
                              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-700 dark:text-amber-300">
                                <AlertTriangle className="w-3 h-3" />
                                Review
                              </span>
                            ) : (
                              <span className="text-[10px] text-civic-text-muted">Auto Pass</span>
                            )}
                          </td>

                          <td className="py-2.5 px-3">
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                                job.status === 'COMPLETED'
                                  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                                  : job.status === 'PROCESSING'
                                  ? 'bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300 animate-pulse'
                                  : job.status === 'FAILED'
                                  ? 'bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300'
                                  : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                              }`}
                            >
                              {job.status}
                            </span>
                          </td>

                          <td className="py-2.5 px-3 text-right">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(`/reports/${job.report_id}`);
                              }}
                              className="text-xs text-civic-green dark:text-civic-green-light hover:underline inline-flex items-center gap-1 font-medium"
                              title="Open Report Detail Workspace"
                            >
                              Report <ExternalLink className="w-3 h-3" />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT (5 cols): Selected Job Timeline & Event Stream */}
        <div className="lg:col-span-5 space-y-4">
          <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
            <div className="flex items-center justify-between mb-4 border-b border-civic-border dark:border-civic-dark-border pb-3">
              <div>
                <h2 className="text-sm font-bold text-civic-text-primary dark:text-civic-dark-text-primary flex items-center gap-2">
                  <Activity className="w-4 h-4 text-purple-600" />
                  Persisted Job Event Stream
                </h2>
                <span className="text-[11px] text-civic-text-muted font-mono">
                  {selectedJob ? `Job ID: ${selectedJob.id}` : 'Select a job to view trace'}
                </span>
              </div>
              {selectedJob && (
                <Link
                  to={`/reports/${selectedJob.report_id}`}
                  className="text-xs text-civic-green dark:text-civic-green-light hover:underline flex items-center gap-1"
                >
                  View Ticket <ExternalLink className="w-3 h-3" />
                </Link>
              )}
            </div>

            {/* Selected Job Metadata Overview */}
            {selectedJob && (
              <div className="p-3 rounded-lg bg-gray-50/80 dark:bg-civic-dark-surface-elevated/40 border border-civic-border dark:border-civic-dark-border text-xs space-y-1.5 font-mono mb-4">
                <div className="flex justify-between">
                  <span className="text-civic-text-muted">Status:</span>
                  <strong className="text-civic-text-primary dark:text-civic-dark-text-primary">
                    {selectedJob.status}
                  </strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-civic-text-muted">Current Stage:</span>
                  <span>{selectedJob.current_stage}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-civic-text-muted">Review Required:</span>
                  <span className={selectedJob.review_required ? 'text-amber-600 font-bold' : 'text-emerald-600'}>
                    {selectedJob.review_required ? 'YES (Human Gate Triggered)' : 'NO (Automated Flow)'}
                  </span>
                </div>
                {selectedJob.review_reason && (
                  <div className="text-[11px] text-amber-700 dark:text-amber-300 pt-1 border-t border-civic-border dark:border-civic-dark-border">
                    Review Reason: {selectedJob.review_reason}
                  </div>
                )}
              </div>
            )}

            {/* Event Timeline */}
            {isEventsLoading ? (
              <div className="space-y-2 py-4">
                <LoadingSkeleton className="h-8 w-full" />
                <LoadingSkeleton className="h-8 w-full" />
              </div>
            ) : !events || events.length === 0 ? (
              <div className="p-6 text-center text-xs text-civic-text-muted border border-dashed border-civic-border dark:border-civic-dark-border rounded-lg">
                No events emitted for this job yet.
              </div>
            ) : (
              <div className="relative pl-4 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-civic-border dark:before:bg-civic-dark-border">
                {events.map((evt) => (
                  <div key={evt.id} className="relative pl-3 text-xs space-y-1">
                    {/* Circle Node */}
                    <div
                      className={`absolute -left-[17px] top-1 w-2.5 h-2.5 rounded-full border-2 border-white dark:border-civic-dark-surface ${
                        evt.status === 'COMPLETED'
                          ? 'bg-emerald-500'
                          : evt.status === 'FAILED'
                          ? 'bg-red-500'
                          : 'bg-purple-600 animate-ping'
                      }`}
                    />

                    <div className="flex items-center justify-between">
                      <span className="font-mono font-semibold text-civic-text-primary dark:text-civic-dark-text-primary text-[11px]">
                        {evt.stage}
                      </span>
                      <span className="text-[10px] text-civic-text-muted font-mono">
                        {evt.duration_ms ? `${evt.duration_ms} ms` : 'In progress'}
                      </span>
                    </div>

                    <p className="text-civic-text-secondary dark:text-civic-dark-text-secondary text-[11px]">
                      {evt.message}
                    </p>

                    {/* Metadata JSON Drawer if available */}
                    {evt.metadata_json && Object.keys(evt.metadata_json).length > 0 && (
                      <div className="mt-1 p-2 rounded bg-gray-50 dark:bg-black/20 border border-civic-border dark:border-civic-dark-border text-[10px] font-mono text-civic-text-muted overflow-x-auto">
                        <pre>{JSON.stringify(evt.metadata_json, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  )}

      {/* Approve Candidate Match Modal */}
      <Modal
        isOpen={matchAction === 'APPROVE' && !!selectedMatch}
        onClose={() => {
          if (!approveMutation.isPending) {
            setMatchAction(null);
            setSelectedMatch(null);
            setActionError(null);
          }
        }}
        title="Approve Candidate Duplicate Match"
        description="Confirm that this incoming citizen report represents an instance of the existing defect cluster."
        footer={
          <div className="flex items-center justify-end gap-3 w-full">
            <CivicButton
              variant="outline"
              size="sm"
              disabled={approveMutation.isPending}
              onClick={() => {
                setMatchAction(null);
                setSelectedMatch(null);
                setActionError(null);
              }}
            >
              Cancel
            </CivicButton>
            <CivicButton
              variant="primary"
              size="sm"
              isLoading={approveMutation.isPending}
              disabled={!reviewerId}
              onClick={() => {
                if (selectedMatch) {
                  approveMutation.mutate({
                    matchId: selectedMatch.id,
                    notes: reviewNotes.trim() || undefined,
                  });
                }
              }}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              Confirm Linkage
            </CivicButton>
          </div>
        }
      >
        {selectedMatch && (
          <div className="space-y-4 text-xs">
            {actionError && (
              <ErrorBanner title="Approval Failed" message={actionError} />
            )}

            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-500 font-medium">Incoming Report:</span>
                <span className="font-mono font-semibold text-blue-600 dark:text-blue-400">
                  rep-{selectedMatch.reportId.slice(0, 8)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-medium">Target Defect Cluster:</span>
                <span className="font-mono font-semibold text-purple-600 dark:text-purple-400">
                  iss-{selectedMatch.issueId.slice(0, 8)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-medium">Model Similarity:</span>
                <span className="font-mono font-bold text-amber-600 dark:text-amber-400">
                  {(selectedMatch.similarityScore * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-medium">Spatial Proximity:</span>
                <span className="font-mono">{selectedMatch.distanceMeters.toFixed(1)} m</span>
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="approve-review-notes" className="font-semibold text-slate-700 dark:text-slate-300 block">
                Reviewer Notes (Optional)
              </label>
              <textarea
                id="approve-review-notes"
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Reason for confirming this duplicate match..."
                rows={3}
                className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div className="p-2.5 rounded bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/50 text-[11px] text-emerald-800 dark:text-emerald-300">
              <strong>Reviewer Authentication:</strong> Signed as Officer{' '}
              <span className="font-mono font-bold">{reviewerId || 'UNAUTHENTICATED'}</span>
            </div>
          </div>
        )}
      </Modal>

      {/* Reject Candidate Match Modal */}
      <Modal
        isOpen={matchAction === 'REJECT' && !!selectedMatch}
        onClose={() => {
          if (!rejectMutation.isPending) {
            setMatchAction(null);
            setSelectedMatch(null);
            setActionError(null);
          }
        }}
        title="Reject Candidate Duplicate Match"
        description="Reject linking this report to the candidate defect cluster. The report will remain an independent defect entity unless an alternate issue is provided."
        footer={
          <div className="flex items-center justify-end gap-3 w-full">
            <CivicButton
              variant="outline"
              size="sm"
              disabled={rejectMutation.isPending}
              onClick={() => {
                setMatchAction(null);
                setSelectedMatch(null);
                setActionError(null);
              }}
            >
              Cancel
            </CivicButton>
            <CivicButton
              variant="primary"
              size="sm"
              isLoading={rejectMutation.isPending}
              disabled={!reviewerId}
              onClick={() => {
                if (selectedMatch) {
                  const cleanedAltId = altIssueId.trim();
                  const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
                  if (cleanedAltId && !UUID_REGEX.test(cleanedAltId)) {
                    setActionError('Alternate issue ID must be a valid 36-character UUID string (e.g. 123e4567-e89b-12d3-a456-426614174000).');
                    return;
                  }
                  rejectMutation.mutate({
                    matchId: selectedMatch.id,
                    notes: reviewNotes.trim() || undefined,
                    linkToIssueId: cleanedAltId || undefined,
                  });
                }
              }}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              Confirm Rejection
            </CivicButton>
          </div>
        }
      >
        {selectedMatch && (
          <div className="space-y-4 text-xs">
            {actionError && (
              <ErrorBanner title="Rejection Failed" message={actionError} />
            )}

            <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-500 font-medium">Incoming Report:</span>
                <span className="font-mono font-semibold text-blue-600 dark:text-blue-400">
                  rep-{selectedMatch.reportId.slice(0, 8)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-medium">Candidate Issue:</span>
                <span className="font-mono font-semibold text-purple-600 dark:text-purple-400">
                  iss-{selectedMatch.issueId.slice(0, 8)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-medium">Suggested Confidence:</span>
                <span className="font-mono font-bold text-amber-600 dark:text-amber-400">
                  {(selectedMatch.similarityScore * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="reject-alt-issue-id" className="font-semibold text-slate-700 dark:text-slate-300 block">
                Link to Alternate Issue UUID (Optional)
              </label>
              <input
                id="reject-alt-issue-id"
                type="text"
                value={altIssueId}
                onChange={(e) => setAltIssueId(e.target.value)}
                placeholder="Leave blank to treat report as separate issue..."
                className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-mono focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
              <p className="text-[10px] text-slate-500">
                If provided, the report will be redirected and linked to this alternate issue UUID instead of creating a standalone issue.
              </p>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="reject-review-notes" className="font-semibold text-slate-700 dark:text-slate-300 block">
                Rejection Reason / Notes (Optional)
              </label>
              <textarea
                id="reject-review-notes"
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Explain why this report does not match the candidate cluster..."
                rows={3}
                className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <div className="p-2.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-[11px] text-slate-700 dark:text-slate-300">
              <strong>Reviewer Authentication:</strong> Signed as Officer{' '}
              <span className="font-mono font-bold">{reviewerId || 'UNAUTHENTICATED'}</span>
            </div>
          </div>
        )}
      </Modal>
    </motion.div>
  );
};
