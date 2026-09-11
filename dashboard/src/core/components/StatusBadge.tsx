import React from 'react';
import { clsx } from 'clsx';
import { BackendReportStatus } from '@/types/api/backendContracts';

export interface StatusBadgeProps {
  status: BackendReportStatus;
  size?: 'sm' | 'md';
  className?: string;
}

const STATUS_CONFIG: Record<
  BackendReportStatus,
  { label: string; dot: string; bg: string; text: string; border: string }
> = {
  SUBMITTED: {
    label: 'Submitted',
    dot: 'bg-gray-400',
    bg: 'bg-gray-100 dark:bg-gray-800',
    text: 'text-gray-700 dark:text-gray-300',
    border: 'border-gray-200 dark:border-gray-700',
  },
  AI_PROCESSING: {
    label: 'AI Analyzing',
    dot: 'bg-purple-500 animate-pulse',
    bg: 'bg-purple-50 dark:bg-purple-950/40',
    text: 'text-purple-700 dark:text-purple-300',
    border: 'border-purple-200 dark:border-purple-800',
  },
  AI_PROCESSED: {
    label: 'AI Processed',
    dot: 'bg-purple-500',
    bg: 'bg-purple-50 dark:bg-purple-950/40',
    text: 'text-purple-700 dark:text-purple-300',
    border: 'border-purple-200 dark:border-purple-800',
  },
  VERIFICATION_REQUIRED: {
    label: 'Needs Review',
    dot: 'bg-amber-500 animate-pulse',
    bg: 'bg-amber-50 dark:bg-amber-950/40',
    text: 'text-amber-800 dark:text-amber-300',
    border: 'border-amber-200 dark:border-amber-800',
  },
  VERIFIED: {
    label: 'Verified',
    dot: 'bg-sky-500',
    bg: 'bg-sky-50 dark:bg-sky-950/40',
    text: 'text-sky-800 dark:text-sky-300',
    border: 'border-sky-200 dark:border-sky-800',
  },
  PRIORITIZED: {
    label: 'Prioritized',
    dot: 'bg-indigo-500',
    bg: 'bg-indigo-50 dark:bg-indigo-950/40',
    text: 'text-indigo-800 dark:text-indigo-300',
    border: 'border-indigo-200 dark:border-indigo-800',
  },
  ASSIGNED: {
    label: 'Assigned',
    dot: 'bg-blue-500',
    bg: 'bg-blue-50 dark:bg-blue-950/40',
    text: 'text-blue-800 dark:text-blue-300',
    border: 'border-blue-200 dark:border-blue-800',
  },
  IN_PROGRESS: {
    label: 'In Progress',
    dot: 'bg-blue-600 animate-pulse',
    bg: 'bg-blue-50 dark:bg-blue-950/40',
    text: 'text-blue-900 dark:text-blue-200',
    border: 'border-blue-200 dark:border-blue-800',
  },
  RESOLVED: {
    label: 'Resolved',
    dot: 'bg-emerald-500',
    bg: 'bg-emerald-50 dark:bg-emerald-950/40',
    text: 'text-emerald-800 dark:text-emerald-300',
    border: 'border-emerald-200 dark:border-emerald-800',
  },
  RESOLUTION_VERIFIED: {
    label: 'Sign-off Verified',
    dot: 'bg-teal-500',
    bg: 'bg-teal-50 dark:bg-teal-950/40',
    text: 'text-teal-800 dark:text-teal-300',
    border: 'border-teal-200 dark:border-teal-800',
  },
  CLOSED: {
    label: 'Closed',
    dot: 'bg-slate-400',
    bg: 'bg-slate-100 dark:bg-slate-800',
    text: 'text-slate-600 dark:text-slate-400',
    border: 'border-slate-200 dark:border-slate-700',
  },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  className,
}) => {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.SUBMITTED;

  const sizeClasses = {
    sm: 'text-[11px] px-2 py-0.5 gap-1.5',
    md: 'text-xs px-2.5 py-1 gap-1.5',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium rounded-full border transition-colors',
        sizeClasses[size],
        config.bg,
        config.text,
        config.border,
        className
      )}
    >
      <span className={clsx('w-1.5 h-1.5 rounded-full shrink-0', config.dot)} />
      {config.label}
    </span>
  );
};
