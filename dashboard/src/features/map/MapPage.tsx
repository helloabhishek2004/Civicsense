import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Map as MapIcon, List, Eye, Filter } from 'lucide-react';
import { reportRepository } from '@/services/repository/reportRepository';
import { queryKeys } from '@/services/queryKeys';
import { StatusBadge } from '@/core/components/StatusBadge';
import { SeverityBadge } from '@/core/components/SeverityBadge';
import { CivicButton } from '@/core/components/CivicButton';
import { LoadingSkeleton } from '@/core/components/LoadingSkeleton';
import { CivicCategory } from '@/types/models';
import { BackendSeverityLevel } from '@/types/api/backendContracts';
import { MapRenderer } from './MapRenderer';
import { motion, type Variants } from 'motion/react';

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
      delayChildren: 0.02,
    },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.35,
      ease: [0.16, 1, 0.3, 1],
    },
  },
};

export const MapPage: React.FC = () => {
  const navigate = useNavigate();

  const [viewMode, setViewMode] = useState<'map' | 'list'>('map');
  const [selectedCategory, setSelectedCategory] = useState<CivicCategory | 'ALL'>('ALL');
  const [selectedSeverity, setSelectedSeverity] = useState<BackendSeverityLevel | 'ALL'>('ALL');

  const { data: reports, isLoading } = useQuery({
    queryKey: queryKeys.reports.mapPoints(),
    queryFn: () => reportRepository.getMapPoints(),
    refetchInterval: 15000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });

  const filteredReports = (reports || []).filter((r) => {
    if (selectedCategory !== 'ALL' && r.category !== selectedCategory) return false;
    if (selectedSeverity !== 'ALL' && r.severity !== selectedSeverity) return false;
    return true;
  });

  // Preserve initial center across polls so map viewport is not reset
  const initialCenterRef = useRef<[number, number] | null>(null);
  if (!initialCenterRef.current && filteredReports.length > 0) {
    initialCenterRef.current = [filteredReports[0].latitude, filteredReports[0].longitude];
  }
  const mapCenter = initialCenterRef.current || [12.9716, 77.5946];

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-4 flex flex-col h-[calc(100vh-7rem)]"
    >
      <motion.div variants={itemVariants} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 shrink-0">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold tracking-tight text-civic-text-primary dark:text-civic-dark-text-primary">
            City Geospatial Defect Map
          </h1>
          <p className="text-xs sm:text-sm text-civic-text-secondary dark:text-civic-dark-text-secondary mt-0.5">
            Geographic distribution of active civic reports, hazardous hotspots, and repair operations.
          </p>
        </div>

        {/* View Toggle (Apple Accessibility: Never rely solely on visual map) */}
        <div className="flex items-center gap-2">
          <div className="flex items-center p-0.5 rounded-lg border border-civic-border bg-civic-surface dark:bg-civic-dark-surface dark:border-civic-dark-border">
            <button
              type="button"
              onClick={() => setViewMode('map')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                viewMode === 'map'
                  ? 'bg-civic-green text-white shadow-civic-subtle'
                  : 'text-civic-text-secondary hover:text-civic-text-primary'
              }`}
            >
              <MapIcon className="w-3.5 h-3.5" /> Map View
            </button>
            <button
              type="button"
              onClick={() => setViewMode('list')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                viewMode === 'list'
                  ? 'bg-civic-green text-white shadow-civic-subtle'
                  : 'text-civic-text-secondary hover:text-civic-text-primary'
              }`}
            >
              <List className="w-3.5 h-3.5" /> List View
            </button>
          </div>
        </div>
      </motion.div>

      {/* Filter Chips Bar */}
      <motion.div variants={itemVariants} className="flex flex-wrap items-center justify-between gap-2.5 p-3 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border shrink-0">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="flex items-center gap-1 text-civic-text-muted mr-1 font-medium">
            <Filter className="w-3.5 h-3.5" /> Filter Pin Layer:
          </div>

          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value as CivicCategory | 'ALL')}
            className="h-8 px-2.5 text-xs rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border"
          >
            <option value="ALL">All Categories</option>
            <option value="Pothole">Pothole</option>
            <option value="Garbage">Garbage</option>
            <option value="Water Leakage">Water Leakage</option>
            <option value="Streetlight">Streetlight</option>
            <option value="Road Damage">Road Damage</option>
            <option value="Drainage">Drainage</option>
          </select>

          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value as BackendSeverityLevel | 'ALL')}
            className="h-8 px-2.5 text-xs rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-[11px] text-civic-text-muted">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-600" />
            <span>Critical</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-orange-600" />
            <span>High</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            <span>Medium</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-600" />
            <span>Low</span>
          </div>
        </div>
      </motion.div>

      {/* Main Map / List Container */}
      <motion.div variants={itemVariants} className="flex-1 rounded-civic overflow-hidden border border-civic-border shadow-civic-card dark:border-civic-dark-border relative">
        {isLoading ? (
          <div className="h-full w-full flex items-center justify-center bg-gray-50 dark:bg-civic-dark-surface">
            <LoadingSkeleton className="h-full w-full" />
          </div>
        ) : viewMode === 'map' ? (
          <MapRenderer
            center={mapCenter}
            zoom={13}
            points={filteredReports}
            onSelectPoint={(selectedId) => navigate(`/reports/${selectedId}`)}
          />
        ) : (
          /* Accessible Table Alternative */
          <div className="h-full overflow-y-auto bg-civic-surface dark:bg-civic-dark-surface p-4">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-civic-border dark:border-civic-dark-border text-civic-text-secondary">
                  <th className="py-2.5 px-3">Tracking ID</th>
                  <th className="py-2.5 px-3">Category</th>
                  <th className="py-2.5 px-3">Locality / Coordinates</th>
                  <th className="py-2.5 px-3">Severity</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-civic-border dark:divide-civic-dark-border">
                {filteredReports.map((report) => (
                  <tr
                    key={report.id}
                    onClick={() => navigate(`/reports/${report.id}`)}
                    className="hover:bg-gray-50 dark:hover:bg-civic-dark-surface-elevated cursor-pointer"
                  >
                    <td className="py-2.5 px-3 font-mono font-semibold">{report.trackingId}</td>
                    <td className="py-2.5 px-3 font-medium">{report.category}</td>
                    <td className="py-2.5 px-3 text-civic-text-muted">
                      {report.addressHint || `${report.latitude.toFixed(4)}, ${report.longitude.toFixed(4)}`}
                    </td>
                    <td className="py-2.5 px-3">
                      <SeverityBadge severity={report.severity} size="sm" />
                    </td>
                    <td className="py-2.5 px-3">
                      <StatusBadge status={report.status} size="sm" />
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <CivicButton variant="ghost" size="sm" rightIcon={<Eye className="w-3.5 h-3.5" />}>
                        Inspect
                      </CivicButton>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
};

