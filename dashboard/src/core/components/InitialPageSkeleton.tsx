import React from "react";
import { motion } from "motion/react";

export const InitialPageSkeleton: React.FC = () => {
  return (
    <motion.div
      initial={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } }}
      className="fixed inset-0 z-50 flex h-screen w-screen overflow-hidden bg-civic-bg dark:bg-civic-dark-bg text-civic-text-primary dark:text-civic-dark-text-primary select-none"
    >
      {/* Sidebar Skeleton */}
      <div className="hidden md:flex w-[68px] flex-col border-r border-neutral-200 dark:border-neutral-800 bg-neutral-100 dark:bg-neutral-900 p-4 justify-between shrink-0">
        <div className="space-y-6">
          {/* Logo / Brand Skeleton */}
          <div className="flex items-center gap-3 px-2 py-1">
            <div className="h-8 w-8 rounded-xl bg-neutral-200 dark:bg-neutral-800 animate-pulse shrink-0" />
          </div>

          {/* Nav Items Skeleton */}
          <div className="space-y-1.5 pt-2">
            {[1, 2, 3, 4, 5, 6, 7].map((idx) => (
              <div
                key={idx}
                className="flex items-center justify-center px-2 py-2.5 rounded-xl"
              >
                <div className="h-5 w-5 rounded-md bg-neutral-200 dark:bg-neutral-700 animate-pulse shrink-0" />
              </div>
            ))}
          </div>
        </div>

        {/* User Card Skeleton */}
        <div className="flex items-center justify-center p-2">
          <div className="h-8 w-8 rounded-full bg-neutral-200 dark:bg-neutral-800 animate-pulse shrink-0" />
        </div>
      </div>

      {/* Main Content Area Skeleton */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar Skeleton */}
        <div className="h-14 border-b border-neutral-200 dark:border-neutral-800 bg-neutral-100/90 dark:bg-neutral-900/90 px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3 w-72">
            <div className="h-8 w-full rounded-lg bg-neutral-200 dark:bg-neutral-800 animate-pulse" />
          </div>

          <div className="flex items-center gap-3">
            <div className="h-7 w-28 rounded-full bg-neutral-100 dark:bg-neutral-800 animate-pulse" />
            <div className="h-8 w-8 rounded-lg bg-neutral-100 dark:bg-neutral-800 animate-pulse" />
            <div className="h-8 w-8 rounded-lg bg-neutral-100 dark:bg-neutral-800 animate-pulse" />
            <div className="h-8 w-8 rounded-full bg-neutral-200 dark:bg-neutral-700 animate-pulse" />
          </div>
        </div>

        {/* Scrollable Viewport Skeleton */}
        <div className="flex-1 overflow-y-auto px-6 py-6 max-w-7xl w-full mx-auto space-y-6">
          {/* Header Title Skeleton */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-2">
              <div className="h-7 w-56 rounded-lg bg-neutral-200 dark:bg-neutral-800 animate-pulse" />
              <div className="h-3.5 w-80 rounded-md bg-neutral-200/60 dark:bg-neutral-800/60 animate-pulse" />
            </div>
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-24 rounded-lg bg-neutral-100 dark:bg-neutral-800 animate-pulse" />
              <div className="h-8 w-32 rounded-lg bg-neutral-200 dark:bg-neutral-700 animate-pulse" />
            </div>
          </div>

          {/* 4 Stat Cards Skeleton Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="p-4 rounded-xl border border-civic-border dark:border-civic-dark-border bg-civic-surface dark:bg-civic-dark-surface space-y-3 shadow-xs"
              >
                <div className="flex items-center justify-between">
                  <div className="h-3 w-20 rounded bg-neutral-200 dark:bg-neutral-800 animate-pulse" />
                  <div className="h-7 w-7 rounded-lg bg-neutral-100 dark:bg-neutral-800 animate-pulse" />
                </div>
                <div className="h-8 w-28 rounded-md bg-neutral-200 dark:bg-neutral-700 animate-pulse" />
                <div className="flex items-center gap-2 pt-1">
                  <div className="h-3.5 w-12 rounded-full bg-neutral-100 dark:bg-neutral-800 animate-pulse" />
                  <div className="h-3 w-24 rounded bg-neutral-200/60 dark:bg-neutral-800/60 animate-pulse" />
                </div>
              </div>
            ))}
          </div>

          {/* Split 2-Column Block Skeleton */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Chart Block Skeleton (2 cols) */}
            <div className="lg:col-span-2 p-5 rounded-xl border border-civic-border dark:border-civic-dark-border bg-civic-surface dark:bg-civic-dark-surface space-y-4 shadow-xs">
              <div className="flex items-center justify-between">
                <div className="space-y-1.5">
                  <div className="h-4 w-40 rounded bg-neutral-200 dark:bg-neutral-800 animate-pulse" />
                  <div className="h-3 w-56 rounded bg-neutral-200/60 dark:bg-neutral-800/60 animate-pulse" />
                </div>
                <div className="h-6 w-20 rounded-md bg-neutral-100 dark:bg-neutral-800 animate-pulse" />
              </div>
              <div className="h-64 rounded-lg bg-neutral-50 dark:bg-neutral-900/40 p-4 flex items-end gap-3 justify-between">
                {[45, 60, 30, 80, 55, 70, 90].map((h, idx) => (
                  <div key={idx} className="w-full flex flex-col items-center gap-2">
                    <div
                      className="w-full max-w-[28px] rounded-t-md bg-neutral-200 dark:bg-neutral-800 animate-pulse"
                      style={{ height: `${h}%` }}
                    />
                    <div className="h-2 w-6 rounded bg-neutral-200/70 dark:bg-neutral-800/70" />
                  </div>
                ))}
              </div>
            </div>

            {/* Queue List Skeleton (1 col) */}
            <div className="p-5 rounded-xl border border-civic-border dark:border-civic-dark-border bg-civic-surface dark:bg-civic-dark-surface space-y-3.5 shadow-xs">
              <div className="flex items-center justify-between pb-1">
                <div className="h-4 w-32 rounded bg-neutral-200 dark:bg-neutral-800 animate-pulse" />
                <div className="h-4 w-12 rounded-full bg-neutral-100 dark:bg-neutral-800 animate-pulse" />
              </div>
              {[1, 2, 3, 4].map((j) => (
                <div
                  key={j}
                  className="p-3 rounded-lg border border-civic-border/70 dark:border-civic-dark-border/70 bg-neutral-50/50 dark:bg-neutral-900/30 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="h-3 w-20 rounded bg-neutral-200 dark:bg-neutral-800 animate-pulse" />
                    <div className="h-3.5 w-14 rounded-full bg-neutral-200/80 dark:bg-neutral-700/80 animate-pulse" />
                  </div>
                  <div className="h-3.5 w-full rounded bg-neutral-200/70 dark:bg-neutral-800/70 animate-pulse" />
                  <div className="h-2.5 w-28 rounded bg-neutral-200/50 dark:bg-neutral-800/50 animate-pulse" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};
