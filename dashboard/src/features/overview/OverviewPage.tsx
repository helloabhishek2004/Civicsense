import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import {
  Inbox,
  AlertTriangle,
  Activity,
  CheckCircle2,
  ArrowRight,
  MapPin,
  Sparkles,
} from 'lucide-react';
import { reportRepository } from '@/services/repository/reportRepository';
import { queryKeys } from '@/services/queryKeys';
import { PageHeader } from '@/core/layout/PageHeader';
import { StatCard } from '@/core/components/StatCard';
import { StatusBadge } from '@/core/components/StatusBadge';
import { SeverityBadge } from '@/core/components/SeverityBadge';
import { CivicButton } from '@/core/components/CivicButton';
import { LoadingSkeleton } from '@/core/components/LoadingSkeleton';
import { motion, type Variants } from 'motion/react';

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.07,
      delayChildren: 0.03,
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

const CATEGORY_COLORS: Record<string, string> = {
  Pothole: '#526B55',
  'Water Leakage': '#1A73E8',
  Garbage: '#E37400',
  Streetlight: '#9333EA',
  'Road Damage': '#D93025',
  Drainage: '#0D9488',
  Infrastructure: '#2563EB',
  Other: '#6B7280',
};

export const OverviewPage: React.FC = () => {
  const navigate = useNavigate();

  const { data: stats, isLoading: isStatsLoading } = useQuery({
    queryKey: queryKeys.reports.stats(),
    queryFn: () => reportRepository.getStats(),
    refetchInterval: 10000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });

  const { data: allReportsData } = useQuery({
    queryKey: queryKeys.reports.list({ pageSize: 100 }),
    queryFn: () => reportRepository.getReports({ pageSize: 100 }),
    refetchInterval: 10000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });

  const { data: urgentReports, isLoading: isUrgentLoading } = useQuery({
    queryKey: queryKeys.reports.list({ pageSize: 5, sortBy: 'priority', sortOrder: 'desc' }),
    queryFn: () => reportRepository.getReports({ pageSize: 5, sortBy: 'priority', sortOrder: 'desc' }),
    refetchInterval: 10000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });

  // Dynamically calculate category breakdown from actual report data
  const categoryBreakdown = useMemo(() => {
    const items = allReportsData?.items || [];
    if (items.length === 0) return [];

    const counts: Record<string, number> = {};
    items.forEach((r) => {
      const cat = r.category || 'Other';
      counts[cat] = (counts[cat] || 0) + 1;
    });

    return Object.entries(counts)
      .map(([name, count]) => ({
        name,
        count,
        percentage: Math.round((count / items.length) * 100),
        color: CATEGORY_COLORS[name] || '#526B55',
      }))
      .sort((a, b) => b.count - a.count);
  }, [allReportsData?.items]);

  // Dynamically calculate 7-day intake and resolution velocity from actual report timestamps
  const weeklyVelocityData = useMemo(() => {
    const items = allReportsData?.items || [];
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const orderedDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const buckets: Record<string, { intake: number; resolved: number }> = {
      Mon: { intake: 0, resolved: 0 },
      Tue: { intake: 0, resolved: 0 },
      Wed: { intake: 0, resolved: 0 },
      Thu: { intake: 0, resolved: 0 },
      Fri: { intake: 0, resolved: 0 },
      Sat: { intake: 0, resolved: 0 },
      Sun: { intake: 0, resolved: 0 },
    };

    items.forEach((r) => {
      const createdDate = new Date(r.createdAt);
      if (!isNaN(createdDate.getTime())) {
        const dayName = days[createdDate.getDay()];
        if (buckets[dayName]) {
          buckets[dayName].intake += 1;
        }
      }
      if (['RESOLVED', 'RESOLUTION_VERIFIED', 'CLOSED'].includes(r.status)) {
        const resolvedDate = new Date(r.resolvedAt || r.updatedAt);
        if (!isNaN(resolvedDate.getTime())) {
          const dayName = days[resolvedDate.getDay()];
          if (buckets[dayName]) {
            buckets[dayName].resolved += 1;
          }
        }
      }
    });

    return orderedDays.map((day) => ({
      day,
      intake: buckets[day].intake,
      resolved: buckets[day].resolved,
    }));
  }, [allReportsData?.items]);

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-4 sm:space-y-4.5"
    >
      <motion.div variants={itemVariants}>
        <PageHeader
          title="Municipal Operations Command"
          description="Real-time citizen reporting intelligence, triage bottlenecks, and departmental progress."
          actions={
            <CivicButton
              variant="primary"
              size="sm"
              onClick={() => navigate('/reports')}
              rightIcon={<ArrowRight className="w-4 h-4" />}
            >
              Open Work Queue
            </CivicButton>
          }
        />
      </motion.div>

      {/* KPI Metric Cards */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-3.5">
        {isStatsLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="p-4 rounded-xl bg-civic-surface border border-civic-border/90 dark:bg-civic-dark-surface dark:border-civic-dark-border/90 shadow-xs"
            >
              <LoadingSkeleton className="h-3 w-20 mb-2" />
              <LoadingSkeleton className="h-7 w-16 mb-2" />
              <LoadingSkeleton className="h-2.5 w-28" />
            </div>
          ))
        ) : (
          <>
            <StatCard
              title="Total Citizen Intake"
              value={stats?.totalReports || 0}
              subtitle="Registered city defects"
              icon={<Inbox className="w-4 h-4" />}
              trend={{ value: 14, label: 'vs last week', direction: 'up', isPositiveGood: true }}
              onClick={() => navigate('/reports')}
            />
            <StatCard
              title="Pending Verification"
              value={stats?.pendingReview || 0}
              subtitle="Requires officer review"
              icon={<AlertTriangle className="w-4 h-4 text-amber-600" />}
              trend={{ value: 5, label: 'queue velocity', direction: 'down', isPositiveGood: true }}
              onClick={() => navigate('/reports')}
            />
            <StatCard
              title="Active Workflows"
              value={stats?.inProgress || 0}
              subtitle="Assigned to field crews"
              icon={<Activity className="w-4 h-4 text-blue-600" />}
              onClick={() => navigate('/reports')}
            />
            <StatCard
              title="Resolved Today"
              value={stats?.resolvedToday || 0}
              subtitle="Verified municipal fixes"
              icon={<CheckCircle2 className="w-4 h-4 text-emerald-600" />}
              trend={{ value: 8, label: 'daily target', direction: 'up', isPositiveGood: true }}
              onClick={() => navigate('/reports')}
            />
          </>
        )}
      </motion.div>

      {/* Two Column Layout: Charts & Urgent Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-4.5">
        {/* Left 2 Cols: Intake Trend & Category Distribution */}
        <motion.div variants={itemVariants} className="lg:col-span-2 space-y-4">
          {/* Intake vs Resolution Chart */}
          <div className="p-4 sm:p-4.5 rounded-xl bg-civic-surface border border-civic-border/90 shadow-xs dark:bg-civic-dark-surface dark:border-civic-dark-border/90">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                  Weekly Report Velocity
                </h3>
                <p className="text-xs text-civic-text-muted">
                  New incoming reports vs completed municipal repairs
                </p>
              </div>
            </div>

            <div className="h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={weeklyVelocityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.15} />
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderRadius: '8px',
                      border: '1px solid #E6E8E3',
                      fontSize: '12px',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  <Bar dataKey="intake" name="New Reports" fill="#526B55" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="resolved" name="Resolved Issues" fill="#A4C2A8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Category Breakdown */}
          <div className="p-4 sm:p-4.5 rounded-xl bg-civic-surface border border-civic-border/90 shadow-xs dark:bg-civic-dark-surface dark:border-civic-dark-border/90">
            <h3 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary mb-0.5">
              Defect Distribution by Category
            </h3>
            <p className="text-xs text-civic-text-muted mb-3">
              Breakdown of city issues submitted across municipal divisions
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 items-center">
              <div className="h-48 w-full flex items-center justify-center">
                {categoryBreakdown.length === 0 ? (
                  <div className="text-xs text-civic-text-muted text-center py-6">
                    No defect categories recorded yet
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={categoryBreakdown}
                        dataKey="count"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={46}
                        outerRadius={70}
                        paddingAngle={3}
                      >
                        {categoryBreakdown.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#FFFFFF',
                          borderRadius: '8px',
                          border: '1px solid #E6E8E3',
                          fontSize: '12px',
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>

              <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                {categoryBreakdown.length === 0 ? (
                  <div className="text-xs text-civic-text-muted py-4 text-center">
                    No category data available
                  </div>
                ) : (
                  categoryBreakdown.map((cat) => (
                    <div key={cat.name} className="flex items-center justify-between text-xs py-0.5">
                      <div className="flex items-center gap-2 truncate pr-2">
                        <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: cat.color }} />
                        <span className="text-civic-text-secondary dark:text-civic-dark-text-secondary truncate">{cat.name}</span>
                      </div>
                      <span className="font-semibold text-civic-text-primary dark:text-civic-dark-text-primary shrink-0">
                        {cat.percentage}% <span className="text-[10px] font-normal text-civic-text-muted">({cat.count})</span>
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Right Col: Urgent Triage Queue & AI Provenance */}
        <motion.div variants={itemVariants} className="space-y-4">
          {/* Urgent Triage Queue */}
          <div className="p-4 sm:p-4.5 rounded-xl bg-civic-surface border border-civic-border/90 shadow-xs dark:bg-civic-dark-surface dark:border-civic-dark-border/90">
            <div className="flex items-center justify-between mb-2.5">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-orange-600" />
                <h3 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                  Urgent Triage Queue
                </h3>
              </div>
              <button
                type="button"
                onClick={() => navigate('/reports')}
                className="text-xs text-civic-green dark:text-civic-green-light font-semibold hover:underline"
              >
                View all
              </button>
            </div>

            {isUrgentLoading ? (
              <div className="space-y-2.5">
                <LoadingSkeleton className="h-12 w-full rounded-lg" count={3} />
              </div>
            ) : urgentReports?.items && urgentReports.items.length > 0 ? (
              <div className="divide-y divide-civic-border/80 dark:divide-civic-dark-border/80">
                {urgentReports.items.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => navigate(`/reports/${item.id}`)}
                    className="py-2.5 first:pt-0 last:pb-0 cursor-pointer hover:opacity-80 transition-opacity"
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-mono text-xs font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                        {item.trackingId}
                      </span>
                      <SeverityBadge severity={item.severity} size="sm" />
                    </div>
                    <p className="text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary line-clamp-1 mb-1">
                      {item.description}
                    </p>
                    <div className="flex items-center justify-between text-[11px] text-civic-text-muted">
                      <div className="flex items-center gap-1 truncate max-w-[150px]">
                        <MapPin className="w-3 h-3 text-civic-green shrink-0" />
                        <span className="truncate">{item.addressHint || 'Coordinates recorded'}</span>
                      </div>
                      <StatusBadge status={item.status} size="sm" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-civic-text-muted py-4 text-center">
                All triage queues are currently clear.
              </p>
            )}
          </div>

          {/* AI Multimodal Intelligence Summary */}
          <div className="p-4 sm:p-4.5 rounded-xl bg-gradient-to-br from-civic-green/10 to-purple-500/10 border border-civic-green/20 shadow-xs dark:border-civic-green/30">
            <div className="flex items-center gap-2 mb-1.5">
              <Sparkles className="w-4 h-4 text-civic-green" />
              <h3 className="text-[11px] font-bold uppercase tracking-wider text-civic-text-primary dark:text-civic-dark-text-primary">
                AI Engine Health
              </h3>
            </div>
            <p className="text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary mb-2.5 leading-relaxed">
              Multimodal fusion pipeline operating with <strong>91.2%</strong> human review confirmation agreement.
            </p>
            <div className="space-y-1.5 text-xs text-civic-text-muted font-mono">
              <div className="flex justify-between">
                <span>Vision Model:</span>
                <span className="text-civic-text-primary dark:text-civic-dark-text-primary font-semibold">CivicNet v1.4.2</span>
              </div>
              <div className="flex justify-between">
                <span>Embedding Model:</span>
                <span>CivicClip-Base</span>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
};
