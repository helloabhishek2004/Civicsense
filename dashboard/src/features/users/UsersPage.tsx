import React from 'react';
import { PageHeader } from '@/core/layout/PageHeader';
import { DEMO_OFFICERS } from '@/core/auth/AuthContext';
import { motion, type Variants } from 'motion/react';

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
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

export const UsersPage: React.FC = () => {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      <motion.div variants={itemVariants}>
        <PageHeader
          title="Staff & Role Governance"
          description="Authorized municipal triage officers, department managers, and field supervisors."
        />
      </motion.div>

      <motion.div
        variants={itemVariants}
        className="rounded-civic bg-civic-surface border border-civic-border shadow-civic-card overflow-hidden dark:bg-civic-dark-surface dark:border-civic-dark-border"
      >
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-civic-border bg-gray-50/70 dark:bg-civic-dark-surface-elevated/60 dark:border-civic-dark-border text-civic-text-secondary">
              <th className="py-3 px-4">Officer Name</th>
              <th className="py-3 px-4">Badge Number</th>
              <th className="py-3 px-4">Role Designation</th>
              <th className="py-3 px-4">Department</th>
              <th className="py-3 px-4">Contact Email</th>
              <th className="py-3 px-4">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-civic-border dark:divide-civic-dark-border">
            {DEMO_OFFICERS.map((officer) => (
              <tr key={officer.id} className="hover:bg-gray-50/50 dark:hover:bg-civic-dark-surface-elevated/30">
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded-full bg-civic-green-container text-civic-green flex items-center justify-center font-bold text-xs">
                      {officer.name.charAt(0)}
                    </div>
                    <span className="font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
                      {officer.name}
                    </span>
                  </div>
                </td>
                <td className="py-3 px-4 font-mono text-civic-text-secondary">{officer.badgeNumber}</td>
                <td className="py-3 px-4">
                  <span className="inline-block px-2 py-0.5 rounded font-mono text-[11px] bg-civic-green-container/40 text-civic-on-green-container dark:bg-civic-dark-surface-elevated dark:text-civic-green-light">
                    {officer.role.replace('_', ' ')}
                  </span>
                </td>
                <td className="py-3 px-4 text-civic-text-secondary">{officer.department}</td>
                <td className="py-3 px-4 text-civic-text-muted font-mono">{officer.email}</td>
                <td className="py-3 px-4">
                  <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 dark:text-emerald-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Active
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </motion.div>
    </motion.div>
  );
};
