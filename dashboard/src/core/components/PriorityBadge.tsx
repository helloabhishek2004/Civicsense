import React from 'react';
import { clsx } from 'clsx';
import { BackendPriorityLevel } from '@/types/api/backendContracts';

export interface PriorityBadgeProps {
  priority?: BackendPriorityLevel | 'UNRANKED' | null;
  size?: 'sm' | 'md';
  className?: string;
}

const PRIORITY_CONFIG: Record<
  BackendPriorityLevel,
  { code: string; label: string; bg: string; text: string; border: string }
> = {
  CRITICAL: {
    code: 'P1',
    label: 'Critical',
    bg: 'bg-red-100 dark:bg-red-950/60',
    text: 'text-red-800 dark:text-red-200',
    border: 'border-red-300 dark:border-red-800',
  },
  HIGH: {
    code: 'P2',
    label: 'High',
    bg: 'bg-orange-100 dark:bg-orange-950/60',
    text: 'text-orange-800 dark:text-orange-200',
    border: 'border-orange-300 dark:border-orange-800',
  },
  MEDIUM: {
    code: 'P3',
    label: 'Medium',
    bg: 'bg-yellow-100 dark:bg-yellow-950/60',
    text: 'text-yellow-800 dark:text-yellow-200',
    border: 'border-yellow-300 dark:border-yellow-800',
  },
  LOW: {
    code: 'P4',
    label: 'Low',
    bg: 'bg-slate-100 dark:bg-slate-800',
    text: 'text-slate-700 dark:text-slate-300',
    border: 'border-slate-300 dark:border-slate-700',
  },
};

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({
  priority,
  size = 'md',
  className,
}) => {
  const sizeClasses = {
    sm: 'text-[11px] px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5',
  };

  if (!priority || priority === 'UNRANKED' || !(priority in PRIORITY_CONFIG)) {
    return (
      <span
        className={clsx(
          'inline-flex items-center font-medium rounded-md border font-mono tracking-tight bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700',
          sizeClasses[size],
          className
        )}
        title="Priority Level: Unranked"
      >
        <span className="font-bold">--</span>
        <span className="font-sans font-normal opacity-80">UNRANKED</span>
      </span>
    );
  }

  const config = PRIORITY_CONFIG[priority];

  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium rounded-md border font-mono tracking-tight',
        sizeClasses[size],
        config.bg,
        config.text,
        config.border,
        className
      )}
      title={`Priority Level: ${config.label}`}
    >
      <span className="font-bold">{config.code}</span>
      <span className="font-sans font-normal opacity-80">{config.label}</span>
    </span>
  );
};
