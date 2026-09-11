import React from 'react';
import { Building2 } from 'lucide-react';
import { PageHeader } from '@/core/layout/PageHeader';
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

const DEPARTMENTS = [
  {
    name: 'Roads & Bridges',
    head: 'Shri K. Ramanathan (Chief Engineer)',
    activeTickets: 42,
    resolvedMonthly: 184,
    leadTime: '3.2 days',
    coverage: 'Potholes, Asphalt Fractures, Road Collapses, Bridge Joints',
  },
  {
    name: 'Solid Waste Management',
    head: 'Dr. Meenakshi Sundaram (Director)',
    activeTickets: 19,
    resolvedMonthly: 310,
    leadTime: '1.1 days',
    coverage: 'Commercial Dumping, Garbage Overflow, Debris Clearance',
  },
  {
    name: 'Water Supply & Sewerage',
    head: 'Er. Anand V. (Executive Engineer)',
    activeTickets: 28,
    resolvedMonthly: 145,
    leadTime: '1.8 days',
    coverage: 'Pipeline Bursts, Valve Leaks, Drain Desilting, Sewerage Overflows',
  },
  {
    name: 'Street Lighting & Electrical',
    head: 'P. Venkatraman (Assistant Engineer)',
    activeTickets: 14,
    resolvedMonthly: 220,
    leadTime: '2.4 days',
    coverage: 'Faulty Luminaires, Cable Faults, Pole Damage, Switchgear Failures',
  },
  {
    name: 'Town Planning & Enforcement',
    head: 'Smt. Kavitha Pillai (Zonal Commissioner)',
    activeTickets: 9,
    resolvedMonthly: 56,
    leadTime: '4.8 days',
    coverage: 'Footpath Encroachments, Unauthorized Hoardings, Public Right-of-Way',
  },
];

export const DepartmentsPage: React.FC = () => {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      <motion.div variants={itemVariants}>
        <PageHeader
          title="Municipal Departments Directory"
          description="Operational divisions responsible for physical resolution and infrastructure maintenance."
        />
      </motion.div>

      <motion.div variants={containerVariants} className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {DEPARTMENTS.map((dept) => (
          <motion.div
            key={dept.name}
            variants={itemVariants}
            className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center gap-2.5 mb-2">
                <div className="p-2 rounded-lg bg-civic-green-container text-civic-green dark:bg-civic-dark-surface-elevated dark:text-civic-green-light">
                  <Building2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                    {dept.name}
                  </h3>
                  <p className="text-xs text-civic-text-muted">{dept.head}</p>
                </div>
              </div>

              <p className="text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary mt-3 line-clamp-2">
                <strong>Scope: </strong>
                {dept.coverage}
              </p>
            </div>

            <div className="mt-5 pt-3 border-t border-civic-border dark:border-civic-dark-border grid grid-cols-3 gap-2 text-center text-xs">
              <div>
                <span className="block text-[11px] text-civic-text-muted">Active Work</span>
                <span className="font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                  {dept.activeTickets}
                </span>
              </div>
              <div>
                <span className="block text-[11px] text-civic-text-muted">Avg SLA</span>
                <span className="font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                  {dept.leadTime}
                </span>
              </div>
              <div>
                <span className="block text-[11px] text-civic-text-muted">Monthly Fixes</span>
                <span className="font-semibold text-civic-green dark:text-civic-green-light">
                  {dept.resolvedMonthly}
                </span>
              </div>
            </div>
          </motion.div>
        ))}
      </motion.div>
    </motion.div>
  );
};

