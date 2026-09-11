import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import {
  Bot,
  UserCheck,
  Clock,
  AlertTriangle,
  Info,
} from 'lucide-react';
import { PageHeader } from '@/core/layout/PageHeader';
import { StatCard } from '@/core/components/StatCard';
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

const DEPARTMENT_VELOCITY_DATA = [
  { department: 'Roads & Bridges', avgDays: 3.2, slaDays: 3.0 },
  { department: 'Solid Waste', avgDays: 1.1, slaDays: 1.5 },
  { department: 'Water Supply', avgDays: 1.8, slaDays: 2.0 },
  { department: 'Street Lighting', avgDays: 2.4, slaDays: 2.0 },
  { department: 'Town Planning', avgDays: 4.8, slaDays: 5.0 },
];

const CONFIDENCE_DISTRIBUTION_DATA = [
  { range: '50-60%', count: 4, reviewRequired: true },
  { range: '60-70%', count: 7, reviewRequired: true },
  { range: '70-80%', count: 18, reviewRequired: false },
  { range: '80-90%', count: 46, reviewRequired: false },
  { range: '90-100%', count: 68, reviewRequired: false },
];

export const AnalyticsPage: React.FC = () => {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      <motion.div variants={itemVariants}>
        <PageHeader
          title="Civic Intelligence & Operational Analytics"
          description="Empirical resolution metrics, departmental SLAs, and transparent human-in-the-loop AI performance."
        />
      </motion.div>

      {/* Governance & Explainability Notice */}
      <motion.div
        variants={itemVariants}
        className="p-4 rounded-civic bg-blue-50/70 border border-blue-200 text-blue-900 dark:bg-blue-950/30 dark:border-blue-900/50 dark:text-blue-200 flex items-start gap-3"
      >
        <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <p className="font-semibold">Human-in-the-Loop AI Governance</p>
          <p className="leading-relaxed opacity-90">
            Model predictions and severity ratings represent probabilistic estimates, not authoritative facts.
            All high-severity and low-confidence reports are routed to human verification officers before departmental work dispatch.
          </p>
        </div>
      </motion.div>

      {/* 4 Core Honest Metrics */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="AI Agreement Rate"
          value="91.2%"
          subtitle="Human review confirmation"
          icon={<Bot className="w-4 h-4 text-purple-600" />}
          trend={{ value: 2.1, label: 'vs last month', direction: 'up', isPositiveGood: true }}
        />
        <StatCard
          title="Human Override Rate"
          value="8.8%"
          subtitle="Officer corrections applied"
          icon={<UserCheck className="w-4 h-4 text-civic-green" />}
          trend={{ value: 1.4, label: 'calibration delta', direction: 'down', isPositiveGood: true }}
        />
        <StatCard
          title="Manual Review Load"
          value="24.5%"
          subtitle="Reports routed to verification"
          icon={<AlertTriangle className="w-4 h-4 text-amber-600" />}
        />
        <StatCard
          title="Avg Resolution Time"
          value="2.3 Days"
          subtitle="From intake to completion"
          icon={<Clock className="w-4 h-4 text-emerald-600" />}
          trend={{ value: 8.5, label: 'faster turnaround', direction: 'down', isPositiveGood: false }}
        />
      </motion.div>

      {/* Charts Grid */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Department Resolution Velocity vs SLA */}
        <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
          <h3 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary mb-1">
            Department Turnaround Time (Days) vs SLA Target
          </h3>
          <p className="text-xs text-civic-text-muted mb-4">
            Comparison of actual average resolution duration against municipal SLA thresholds
          </p>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={DEPARTMENT_VELOCITY_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.15} />
                <XAxis dataKey="department" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} unit="d" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderRadius: '8px',
                    border: '1px solid #E6E8E3',
                    fontSize: '12px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Bar dataKey="avgDays" name="Actual Turnaround (Days)" fill="#526B55" radius={[4, 4, 0, 0]} />
                <Bar dataKey="slaDays" name="SLA Target (Days)" fill="#D1D5DB" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AI Confidence Distribution */}
        <div className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
          <h3 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary mb-1">
            AI Model Confidence Distribution
          </h3>
          <p className="text-xs text-civic-text-muted mb-4">
            Frequency of prediction confidence across the model inference pool (threshold &lt; 70% requires review)
          </p>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={CONFIDENCE_DISTRIBUTION_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.15} />
                <XAxis dataKey="range" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderRadius: '8px',
                    border: '1px solid #E6E8E3',
                    fontSize: '12px',
                  }}
                />
                <Bar
                  dataKey="count"
                  name="Reports Processed"
                  fill="#7C3AED"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

