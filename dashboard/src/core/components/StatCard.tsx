import React from 'react';
import { clsx } from 'clsx';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

export interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    value: number; // e.g. 12 for +12%
    label: string; // e.g. "vs last week"
    direction?: 'up' | 'down' | 'neutral';
    isPositiveGood?: boolean; // if true, down is bad, up is good
  };
  onClick?: () => void;
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  onClick,
  className,
}) => {
  const isClickable = !!onClick;

  return (
    <div
      onClick={onClick}
      className={clsx(
        'p-4 sm:p-4.5 rounded-xl bg-civic-surface border border-civic-border/90 shadow-xs transition-all duration-150',
        'dark:bg-civic-dark-surface dark:border-civic-dark-border/90',
        isClickable && 'cursor-pointer hover:border-civic-green/40 hover:shadow-civic-elevated active:scale-[0.98]',
        className
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-semibold text-civic-text-secondary dark:text-civic-dark-text-secondary uppercase tracking-wider">
          {title}
        </span>
        {icon && (
          <div className="p-1.5 rounded-lg bg-civic-green-container/40 text-civic-green dark:bg-civic-dark-surface-elevated dark:text-civic-green-light shrink-0">
            {icon}
          </div>
        )}
      </div>

      <div className="mt-1.5 flex items-baseline gap-2">
        <span className="text-2xl sm:text-[28px] font-bold tracking-tight text-civic-text-primary dark:text-civic-dark-text-primary">
          {value}
        </span>
      </div>

      {(subtitle || trend) && (
        <div className="mt-1.5 flex items-center gap-2 text-xs text-civic-text-muted dark:text-civic-dark-text-muted">
          {trend && (
            <span
              className={clsx(
                'inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded font-medium text-[11px]',
                trend.direction === 'up'
                  ? trend.isPositiveGood !== false
                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                    : 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300'
                  : trend.direction === 'down'
                  ? trend.isPositiveGood === false
                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
                    : 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300'
                  : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
              )}
            >
              {trend.direction === 'up' && <ArrowUpRight className="w-3 h-3" />}
              {trend.direction === 'down' && <ArrowDownRight className="w-3 h-3" />}
              {trend.direction === 'neutral' && <Minus className="w-3 h-3" />}
              <span>{Math.abs(trend.value)}%</span>
            </span>
          )}
          <span>{trend?.label || subtitle}</span>
        </div>
      )}
    </div>
  );
};
