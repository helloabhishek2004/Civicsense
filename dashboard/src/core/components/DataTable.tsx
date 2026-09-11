import React from 'react';
import { clsx } from 'clsx';
import { ChevronLeft, ChevronRight, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { CivicButton } from './CivicButton';
import { LoadingSkeleton } from './LoadingSkeleton';
import { EmptyState } from './EmptyState';

export interface Column<T> {
  id: string;
  header: string;
  accessorKey?: keyof T;
  cell?: (item: T) => React.ReactNode;
  sortable?: boolean;
  className?: string;
}

export interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  keyExtractor: (item: T) => string;
  isLoading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  onRowClick?: (item: T) => void;
  // Sorting
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSort?: (columnId: string) => void;
  // Pagination
  page?: number;
  totalPages?: number;
  totalItems?: number;
  pageSize?: number;
  onPageChange?: (newPage: number) => void;
  className?: string;
}

export function DataTable<T>({
  data,
  columns,
  keyExtractor,
  isLoading = false,
  emptyTitle = 'No records found',
  emptyDescription = 'There are no items matching your current view or filter criteria.',
  onRowClick,
  sortBy,
  sortOrder,
  onSort,
  page = 1,
  totalPages = 1,
  totalItems = 0,
  pageSize = 10,
  onPageChange,
  className,
}: DataTableProps<T>): React.ReactElement {
  const startItem = totalItems === 0 ? 0 : (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, totalItems);

  return (
    <div
      className={clsx(
        'rounded-civic bg-civic-surface border border-civic-border shadow-civic-card overflow-hidden flex flex-col',
        'dark:bg-civic-dark-surface dark:border-civic-dark-border',
        className
      )}
    >
      <div className="overflow-x-auto flex-1">
        <table className="w-full text-left border-collapse text-sm">
          <thead>
            <tr className="border-b border-civic-border bg-gray-50/70 dark:bg-civic-dark-surface-elevated/60 dark:border-civic-dark-border">
              {columns.map((col) => {
                const isSorted = sortBy === col.id;
                return (
                  <th
                    key={col.id}
                    scope="col"
                    className={clsx(
                      'py-3.5 px-4 text-xs font-semibold text-civic-text-secondary dark:text-civic-dark-text-secondary uppercase tracking-wider select-none',
                      col.sortable && 'cursor-pointer hover:text-civic-text-primary dark:hover:text-civic-dark-text-primary',
                      col.className
                    )}
                    onClick={() => col.sortable && onSort && onSort(col.id)}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>{col.header}</span>
                      {col.sortable && (
                        <span className="shrink-0 text-civic-text-muted">
                          {isSorted ? (
                            sortOrder === 'asc' ? (
                              <ArrowUp className="w-3.5 h-3.5 text-civic-green" />
                            ) : (
                              <ArrowDown className="w-3.5 h-3.5 text-civic-green" />
                            )
                          ) : (
                            <ArrowUpDown className="w-3 h-3 opacity-40" />
                          )}
                        </span>
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-civic-border dark:divide-civic-dark-border">
            {isLoading ? (
              Array.from({ length: pageSize > 6 ? 6 : pageSize }).map((_, rIdx) => (
                <tr key={`skeleton-${rIdx}`}>
                  {columns.map((col) => (
                    <td key={`skel-col-${col.id}`} className="py-4 px-4">
                      <LoadingSkeleton className="h-4 w-3/4" />
                    </td>
                  ))}
                </tr>
              ))
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="py-12 px-4">
                  <EmptyState title={emptyTitle} description={emptyDescription} />
                </td>
              </tr>
            ) : (
              data.map((item) => {
                const key = keyExtractor(item);
                return (
                  <tr
                    key={key}
                    onClick={() => onRowClick && onRowClick(item)}
                    className={clsx(
                      'transition-colors duration-100',
                      onRowClick
                        ? 'cursor-pointer hover:bg-gray-50/80 dark:hover:bg-civic-dark-surface-elevated/50'
                        : 'hover:bg-gray-50/40 dark:hover:bg-civic-dark-surface-elevated/20'
                    )}
                  >
                    {columns.map((col) => {
                      let cellContent: React.ReactNode = null;
                      if (col.cell) {
                        cellContent = col.cell(item);
                      } else if (col.accessorKey) {
                        cellContent = String(item[col.accessorKey] ?? '');
                      }

                      return (
                        <td
                          key={`${key}-${col.id}`}
                          className={clsx('py-3 px-4 text-civic-text-primary dark:text-civic-dark-text-primary', col.className)}
                        >
                          {cellContent}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {!isLoading && data.length > 0 && onPageChange && (
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t border-civic-border bg-civic-surface dark:border-civic-dark-border dark:bg-civic-dark-surface">
          <span className="text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary">
            Showing <strong className="font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">{startItem}</strong> to{' '}
            <strong className="font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">{endItem}</strong> of{' '}
            <strong className="font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">{totalItems}</strong> entries
          </span>

          <div className="flex items-center gap-1.5">
            <CivicButton
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              leftIcon={<ChevronLeft className="w-3.5 h-3.5" />}
            >
              Previous
            </CivicButton>

            <span className="text-xs px-2 font-medium text-civic-text-primary dark:text-civic-dark-text-primary">
              Page {page} of {totalPages}
            </span>

            <CivicButton
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              rightIcon={<ChevronRight className="w-3.5 h-3.5" />}
            >
              Next
            </CivicButton>
          </div>
        </div>
      )}
    </div>
  );
}
