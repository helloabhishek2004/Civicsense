import React from 'react';
import { Server, Map, Bot, Shield } from 'lucide-react';
import { PageHeader } from '@/core/layout/PageHeader';
import { env } from '@/core/config/env';
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

export const SettingsPage: React.FC = () => {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      <motion.div variants={itemVariants}>
        <PageHeader
          title="System Settings & Infrastructure"
          description="Configuration parameters, endpoint targets, tile servers, and ML model thresholds."
        />
      </motion.div>

      <motion.div variants={containerVariants} className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Environment & Data Source */}
        <motion.div variants={itemVariants} className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
          <div className="flex items-center gap-2 mb-4">
            <Server className="w-4 h-4 text-civic-green" />
            <h3 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
              Repository & Data Mode
            </h3>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between py-2 border-b border-civic-border dark:border-civic-dark-border">
              <span className="text-civic-text-secondary">VITE_DATA_MODE</span>
              <span className="font-mono font-bold px-2 py-0.5 rounded bg-black/5 dark:bg-white/10 uppercase">
                {env.dataMode}
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-civic-border dark:border-civic-dark-border">
              <span className="text-civic-text-secondary">FastAPI Base URL</span>
              <span className="font-mono text-civic-text-muted">{env.apiBaseUrl}</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-civic-text-secondary">Fail-safe Fallback</span>
              <span className="text-emerald-700 dark:text-emerald-300 font-medium">
                Disabled (Explicit Mode Required)
              </span>
            </div>
          </div>
        </motion.div>

        {/* Map & Spatial Services */}
        <motion.div variants={itemVariants} className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
          <div className="flex items-center gap-2 mb-4">
            <Map className="w-4 h-4 text-civic-green" />
            <h3 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
              Cartographic & Spatial Engine
            </h3>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between py-2 border-b border-civic-border dark:border-civic-dark-border">
              <span className="text-civic-text-secondary">Primary Map Provider</span>
              <span className="font-mono text-civic-text-primary dark:text-civic-dark-text-primary font-semibold">
                Google Maps JS API
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-civic-border dark:border-civic-dark-border">
              <span className="text-civic-text-secondary">Google Maps Key</span>
              <span className="font-mono text-emerald-700 dark:text-emerald-300">
                {env.googleMapsApiKey ? `${env.googleMapsApiKey.substring(0, 10)}... (Active)` : 'Not Configured'}
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-civic-border dark:border-civic-dark-border">
              <span className="text-civic-text-secondary">Offline / Fail-Safe Provider</span>
              <span className="font-mono text-civic-text-muted">Leaflet / OpenStreetMap</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-civic-text-secondary">Accessible List Toggle</span>
              <span className="text-emerald-700 dark:text-emerald-300 font-medium">
                Enabled (WCAG compliant)
              </span>
            </div>
          </div>
        </motion.div>

        {/* AI Inference Architecture */}
        <motion.div variants={itemVariants} className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
          <div className="flex items-center gap-2 mb-4">
            <Bot className="w-4 h-4 text-purple-600" />
            <h3 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
              AI / ML Inference Models
            </h3>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between py-2 border-b border-civic-border dark:border-civic-dark-border">
              <span className="text-civic-text-secondary">Multimodal Vision Core</span>
              <span className="font-mono text-civic-text-primary dark:text-civic-dark-text-primary font-semibold">
                CivicNet-Multimodal v1.4.2
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-civic-border dark:border-civic-dark-border">
              <span className="text-civic-text-secondary">Text Embedding Architecture</span>
              <span className="font-mono text-civic-text-muted">CivicClip-Base v1.0</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-civic-text-secondary">Human Verification Threshold</span>
              <span className="font-mono font-semibold text-amber-700 dark:text-amber-300">
                Confidence &lt; 0.70 or Agreement &lt; 0.60
              </span>
            </div>
          </div>
        </motion.div>

        {/* Workflow State Machine */}
        <motion.div variants={itemVariants} className="p-5 rounded-civic bg-civic-surface border border-civic-border shadow-civic-card dark:bg-civic-dark-surface dark:border-civic-dark-border">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-4 h-4 text-civic-green" />
            <h3 className="text-sm font-semibold text-civic-text-primary dark:text-civic-dark-text-primary">
              Lifecycle Governance
            </h3>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between py-2 border-b border-civic-border dark:border-civic-dark-border">
              <span className="text-civic-text-secondary">Canonical States</span>
              <span className="font-mono text-civic-text-primary dark:text-civic-dark-text-primary">
                11 explicit lifecycle states
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-civic-border dark:border-civic-dark-border">
              <span className="text-civic-text-secondary">State Enforcement</span>
              <span className="text-emerald-700 dark:text-emerald-300 font-medium">
                Server-Authoritative Transition Map
              </span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-civic-text-secondary">Direct Closure Justification</span>
              <span className="text-emerald-700 dark:text-emerald-300 font-medium">
                Mandatory Structured Reason
              </span>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </motion.div>
  );
};
