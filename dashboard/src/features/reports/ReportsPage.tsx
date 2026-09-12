import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { MapPin, Eye } from 'lucide-react';
import { reportRepository } from '@/services/repository/reportRepository';
import { queryKeys } from '@/services/queryKeys';
import { ReportFilterParams, ReportItem } from '@/types/models';
import { PageHeader } from '@/core/layout/PageHeader';
import { FilterBar } from '@/core/components/FilterBar';
import { DataTable, Column } from '@/core/components/DataTable';
import { StatusBadge } from '@/core/components/StatusBadge';
import { SeverityBadge } from '@/core/components/SeverityBadge';
import { PriorityBadge } from '@/core/components/PriorityBadge';
import { CivicButton } from '@/core/components/CivicButton';
import { ErrorBanner } from '@/core/components/ErrorBanner';
import { formatDateShort, formatDateFull, formatRelativeTime } from '@/core/utils/dateUtils';
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

export const ReportsPage: React.FC = () => {
  const navigate = useNavigate();

  const [filters, setFilters] = useState<ReportFilterParams>({
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
      header: '',
      cell: (item) => (
        <div className="flex items-center justify-end gap-1">
          <CivicButton
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/reports/${item.id}`);
            }}
            rightIcon={<Eye className="w-3.5 h-3.5" />}
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
      className="space-y-4"
    >
      <motion.div variants={itemVariants}>
        <PageHeader
          title="Reports Work Queue"
          description="Review incoming citizen reports, verify AI intelligence, and coordinate departmental resolution."
        />
      </motion.div>

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
    </motion.div>
  );
};
