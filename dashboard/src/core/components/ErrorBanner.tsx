import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { CivicButton } from './CivicButton';

export interface ErrorBannerProps {
  title?: string;
  message: string;
  requestId?: string;
  onRetry?: () => void;
  isRetrying?: boolean;
  className?: string;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  title = 'Unable to complete request',
  message,
  requestId,
  onRetry,
  isRetrying = false,
  className = '',
}) => {
  return (
    <div
      className={`p-4 rounded-civic bg-red-50/80 border border-red-200 text-red-900 dark:bg-red-950/40 dark:border-red-900/60 dark:text-red-200 ${className}`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold tracking-tight">{title}</h4>
          <p className="mt-0.5 text-xs text-red-800 dark:text-red-300 break-words">
            {message}
          </p>
          {requestId && (
            <div className="mt-2 text-[11px] font-mono opacity-75">
              <span>Trace ID: </span>
              <code className="px-1 py-0.5 rounded bg-red-100 dark:bg-red-900/60 select-all">
                {requestId}
              </code>
            </div>
          )}
        </div>
        {onRetry && (
          <CivicButton
            variant="outline"
            size="sm"
            onClick={onRetry}
            isLoading={isRetrying}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            className="shrink-0 text-red-700 dark:text-red-300 border-red-300 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-950/60"
          >
            Retry
          </CivicButton>
        )}
      </div>
    </div>
  );
};
