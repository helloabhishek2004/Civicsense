import React from 'react';
import { clsx } from 'clsx';
import { Inbox } from 'lucide-react';
import { CivicButton } from './CivicButton';

export interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon = <Inbox className="w-10 h-10 stroke-[1.5]" />,
  actionLabel,
  onAction,
  className,
}) => {
  return (
    <div
      className={clsx(
        'flex flex-col items-center justify-center p-12 text-center rounded-civic border border-dashed border-civic-border bg-civic-surface/50 dark:bg-civic-dark-surface/50 dark:border-civic-dark-border',
        className
      )}
    >
      <div className="p-3 rounded-full bg-civic-green-container/50 text-civic-green dark:bg-civic-dark-surface-elevated dark:text-civic-green-light mb-4">
        {icon}
      </div>
      <h3 className="text-base font-medium text-civic-text-primary dark:text-civic-dark-text-primary tracking-tight">
        {title}
      </h3>
      <p className="mt-1 text-sm text-civic-text-secondary dark:text-civic-dark-text-secondary max-w-sm">
        {description}
      </p>
      {actionLabel && onAction && (
        <div className="mt-5">
          <CivicButton variant="secondary" size="sm" onClick={onAction}>
            {actionLabel}
          </CivicButton>
        </div>
      )}
    </div>
  );
};
