import React from 'react';
import { clsx } from 'clsx';
import { BackendSeverityLevel } from '@/types/api/backendContracts';

export interface SeverityBadgeProps {
  severity: BackendSeverityLevel;
  size?: 'sm' | 'md';
  className?: string;
}

const SEVERITY_CONFIG: Record<
  BackendSeverityLevel,
  { label: string; bg: string; text: string; border: string }
> = {
  LOW: {
    label: 'Low',
    bg: 'bg-emerald-50 dark:bg-emerald-950/40',
    text: 'text-emerald-700 dark:text-emerald-300',
    border: 'border-emerald-200 dark:border-emerald-800',
  },
  MEDIUM: {
    label: 'Medium',
    bg: 'bg-amber-50 dark:bg-amber-950/40',
    text: 'text-amber-800 dark:text-amber-300',
    border: 'border-amber-200 dark:border-amber-800',
  },
  HIGH: {
    label: 'High',
    bg: 'bg-orange-50 dark:bg-orange-950/40',
    text: 'text-orange-700 dark:text-orange-300',
    border: 'border-orange-200 dark:border-orange-800',
  },
  CRITICAL: {
    label: 'Critical',
    bg: 'bg-red-50 dark:bg-red-950/40',
    text: 'text-red-700 dark:text-red-300',
    border: 'border-red-200 dark:border-red-800',
  },
};

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({
  severity,
  size = 'md',
  className,
}) => {
  const config = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.LOW;

  const sizeClasses = {
    sm: 'text-[11px] px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium rounded-md border tracking-tight',
        sizeClasses[size],
        config.bg,
        config.text,
        config.border,
        className
      )}
    >
      {config.label}
    </span>
  );
};
