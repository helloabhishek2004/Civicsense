import React from 'react';
import { clsx } from 'clsx';

export interface LoadingSkeletonProps {
  className?: string;
  count?: number;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  className,
  count = 1,
}) => {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={clsx(
            'animate-pulse rounded bg-gray-200/80 dark:bg-gray-800/80',
            className
          )}
        />
      ))}
    </>
  );
};
