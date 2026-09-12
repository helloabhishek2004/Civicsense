import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Building2, ArrowRight, Clock, AlertTriangle } from 'lucide-react';
import { PageHeader } from '@/core/layout/PageHeader';
import { departmentRepository } from '@/services/repository/DepartmentRepository';
import { queryKeys } from '@/services/queryKeys';
import { ErrorBanner } from '@/core/components/ErrorBanner';
import { LoadingSkeleton } from '@/core/components/LoadingSkeleton';
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

export const DepartmentsPage: React.FC = () => {
  const navigate = useNavigate();

  const {
    data: departments,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.departments.list(true),
    queryFn: () => departmentRepository.getDepartments(true),
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      <motion.div variants={itemVariants}>
        <PageHeader
          title="Municipal Departments Directory"
          description="Operational divisions responsible for physical resolution and infrastructure maintenance."
        />
      </motion.div>

      {isError && (
        <motion.div variants={itemVariants}>
          <ErrorBanner
            title="Failed to load departments"
            message={
              error instanceof Error
                ? error.message
                : 'Could not fetch municipal department directory.'
            }
            onRetry={() => refetch()}
          />
        </motion.div>
      )}

      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <LoadingSkeleton key={i} className="h-48 w-full rounded-civic" />
          ))}
        </div>
      )}

      {!isLoading && !isError && departments && (
        <motion.div variants={containerVariants} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {departments.map((dept) => {
            const stats = dept.stats;
            const pendingAck = stats?.pending_acknowledgment ?? 0;
            const inProgress = stats?.in_progress ?? 0;
            const resolved = stats?.resolved ?? 0;
            const reassignmentReq = stats?.reassignment_required ?? 0;

            return (
              <motion.div
                key={dept.id}
                variants={itemVariants}
                onClick={() => navigate(`/departments/${dept.code}`)}
                className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border flex flex-col justify-between cursor-pointer hover:border-civic-green/60 hover:shadow-md transition-all group"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg bg-civic-green-container text-civic-green dark:bg-civic-dark-surface-elevated dark:text-civic-green-light group-hover:bg-civic-green group-hover:text-white transition-colors">
                        <Building2 className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                            {dept.name}
                          </h3>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-gray-100 dark:bg-civic-dark-surface-elevated text-civic-text-secondary border border-civic-border dark:border-civic-dark-border">
                            {dept.code}
                          </span>
                        </div>
                        <p className="text-xs text-civic-text-muted mt-0.5">
                          {dept.head_name || 'Department Lead'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 text-[11px] text-civic-text-muted font-mono">
                      <Clock className="w-3.5 h-3.5 text-civic-green" />
                      <span>{dept.sla_hours_default}h SLA</span>
                    </div>
                  </div>

                  <p className="text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary mt-3 line-clamp-2">
                    {dept.description || 'Physical infrastructure resolution division.'}
                  </p>

                  {reassignmentReq > 0 && (
                    <div className="mt-2.5 p-2 rounded-lg bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-300 text-[11px] flex items-center gap-1.5 border border-red-200 dark:border-red-900/40">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-red-600" />
                      <span>{reassignmentReq} job order(s) declined — reassignment needed</span>
                    </div>
                  )}
                </div>

                <div className="mt-5 pt-3 border-t border-civic-border dark:border-civic-dark-border">
                  <div className="grid grid-cols-4 gap-2 text-center text-xs mb-3">
                    <div>
                      <span className="block text-[11px] text-civic-text-muted">In Progress</span>
                      <span className="font-semibold text-orange-600 dark:text-orange-400">
                        {inProgress}
                      </span>
                    </div>
                    <div>
                      <span className="block text-[11px] text-civic-text-muted">Pending Ack</span>
                      <span className={`font-semibold ${pendingAck > 0 ? 'text-amber-600 font-bold' : 'text-civic-text-primary dark:text-civic-dark-text-primary'}`}>
                        {pendingAck}
                      </span>
                    </div>
                    <div>
                      <span className="block text-[11px] text-civic-text-muted">Resolved</span>
                      <span className="font-semibold text-civic-green dark:text-civic-green-light">
                        {resolved}
                      </span>
                    </div>
                    <div>
                      <span className="block text-[11px] text-civic-text-muted">Total</span>
                      <span className="font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                        {stats?.total_assigned ?? 0}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs font-medium text-civic-green group-hover:underline pt-1">
                    <span>View Work Queue & Operations</span>
                    <ArrowRight className="w-4 h-4 transform group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </div>
              </motion.div>
            );
          })}
        </motion.div>
      )}
    </motion.div>
  );
};
