import React from 'react';
import { Search, X, RotateCcw } from 'lucide-react';
import { clsx } from 'clsx';
import {
  LifecyclePhase,
  CivicCategory,
  DepartmentName,
  ReportFilterParams,
} from '@/types/models';
import { BackendSeverityLevel, BackendPriorityLevel } from '@/types/api/backendContracts';
import { CivicButton } from './CivicButton';

export interface FilterBarProps {
  filters: ReportFilterParams;
  onChange: (newFilters: Partial<ReportFilterParams>) => void;
  onReset: () => void;
  totalResults?: number;
  className?: string;
}

const PHASE_TABS: Array<{ phase: LifecyclePhase; label: string }> = [
  { phase: 'ALL', label: 'All Reports' },
  { phase: 'INTAKE', label: 'Intake & AI' },
  { phase: 'VERIFICATION', label: 'Verification' },
  { phase: 'WORKFLOW', label: 'In Progress' },
  { phase: 'RESOLUTION', label: 'Resolved' },
];

const CATEGORIES: CivicCategory[] = [
  'Pothole',
  'Garbage',
  'Water Leakage',
  'Streetlight',
  'Road Damage',
  'Drainage',
  'Infrastructure',
  'Other',
];

const SEVERITIES: BackendSeverityLevel[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
const PRIORITIES: BackendPriorityLevel[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
const DEPARTMENTS: DepartmentName[] = [
  'Roads & Bridges',
  'Solid Waste Management',
  'Water Supply & Sewerage',
  'Street Lighting & Electrical',
  'Town Planning & Enforcement',
  'General Public Works',
];

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onChange,
  onReset,
  totalResults,
  className,
}) => {
  const hasActiveFilters =
    (filters.phase && filters.phase !== 'ALL') ||
    (filters.category && filters.category !== 'ALL') ||
    (filters.severity && filters.severity !== 'ALL') ||
    (filters.priority && filters.priority !== 'ALL') ||
    (filters.department && filters.department !== 'ALL') ||
    (filters.search && filters.search.trim().length > 0);

  return (
    <div className={clsx('space-y-3', className)}>
      {/* Lifecycle Phase Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-civic-border dark:border-civic-dark-border">
        {PHASE_TABS.map((tab) => {
          const isActive = (filters.phase || 'ALL') === tab.phase;
          return (
            <button
              key={tab.phase}
              type="button"
              onClick={() => onChange({ phase: tab.phase, page: 1 })}
              className={clsx(
                'px-3.5 py-2 text-xs font-medium rounded-lg whitespace-nowrap transition-all duration-150 select-none cursor-pointer',
                isActive
                  ? 'bg-civic-green text-white shadow-civic-subtle'
                  : 'text-civic-text-secondary hover:text-civic-text-primary hover:bg-black/5 dark:text-civic-dark-text-secondary dark:hover:text-civic-dark-text-primary dark:hover:bg-white/5'
              )}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Controls Bar: Search & Selects */}
      <div className="flex flex-wrap items-center justify-between gap-2.5">
        {/* Search */}
        <div className="relative flex-1 min-w-[240px] max-w-md">
          <Search className="w-4 h-4 text-civic-text-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={filters.search || ''}
            onChange={(e) => onChange({ search: e.target.value, page: 1 })}
            placeholder="Search by ID, keyword, locality, citizen..."
            className="w-full h-9 pl-9 pr-8 text-xs rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary placeholder:text-civic-text-muted focus:outline-none focus:ring-2 focus:ring-civic-green/30 focus:border-civic-green dark:bg-civic-dark-surface dark:border-civic-dark-border dark:text-civic-dark-text-primary transition-colors"
          />
          {filters.search && (
            <button
              type="button"
              onClick={() => onChange({ search: '', page: 1 })}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 text-civic-text-muted hover:text-civic-text-primary"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Filter Dropdowns */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Category Dropdown */}
          <select
            value={filters.category || 'ALL'}
            onChange={(e) =>
              onChange({ category: e.target.value as CivicCategory | 'ALL', page: 1 })
            }
            aria-label="Filter by category"
            className="h-9 px-3 text-xs rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 focus:border-civic-green dark:bg-civic-dark-surface dark:border-civic-dark-border dark:text-civic-dark-text-primary cursor-pointer"
          >
            <option value="ALL">All Categories</option>
            {CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>

          {/* Severity Dropdown */}
          <select
            value={filters.severity || 'ALL'}
            onChange={(e) =>
              onChange({
                severity: e.target.value as BackendSeverityLevel | 'ALL',
                page: 1,
              })
            }
            aria-label="Filter by severity"
            className="h-9 px-3 text-xs rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 focus:border-civic-green dark:bg-civic-dark-surface dark:border-civic-dark-border dark:text-civic-dark-text-primary cursor-pointer"
          >
            <option value="ALL">All Severities</option>
            {SEVERITIES.map((sev) => (
              <option key={sev} value={sev}>
                {sev} Severity
              </option>
            ))}
          </select>

          {/* Priority Dropdown */}
          <select
            value={filters.priority || 'ALL'}
            onChange={(e) =>
              onChange({
                priority: e.target.value as BackendPriorityLevel | 'ALL',
                page: 1,
              })
            }
            aria-label="Filter by priority"
            className="h-9 px-3 text-xs rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 focus:border-civic-green dark:bg-civic-dark-surface dark:border-civic-dark-border dark:text-civic-dark-text-primary cursor-pointer"
          >
            <option value="ALL">All Priorities</option>
            {PRIORITIES.map((pri) => (
              <option key={pri} value={pri}>
                {pri} Priority
              </option>
            ))}
          </select>

          {/* Department Dropdown */}
          <select
            value={filters.department || 'ALL'}
            onChange={(e) =>
              onChange({
                department: e.target.value as DepartmentName | 'ALL',
                page: 1,
              })
            }
            aria-label="Filter by department"
            className="h-9 px-3 text-xs rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 focus:border-civic-green dark:bg-civic-dark-surface dark:border-civic-dark-border dark:text-civic-dark-text-primary cursor-pointer"
          >
            <option value="ALL">All Departments</option>
            {DEPARTMENTS.map((dept) => (
              <option key={dept} value={dept}>
                {dept}
              </option>
            ))}
          </select>

          {/* Reset button if filtered */}
          {hasActiveFilters && (
            <CivicButton
              variant="ghost"
              size="sm"
              onClick={onReset}
              leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
              className="text-civic-text-muted hover:text-civic-text-primary"
            >
              Reset
            </CivicButton>
          )}

          {typeof totalResults === 'number' && (
            <span className="text-xs text-civic-text-muted dark:text-civic-dark-text-muted ml-1 pl-2 border-l border-civic-border dark:border-civic-dark-border hidden sm:inline">
              {totalResults} {totalResults === 1 ? 'result' : 'results'}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
