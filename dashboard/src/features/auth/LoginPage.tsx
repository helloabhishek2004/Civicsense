import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ShieldCheck, ArrowRight, UserCheck } from 'lucide-react';
import { useAuth } from '@/core/auth/AuthContext';
import { CivicButton } from '@/core/components/CivicButton';
import { UserRole } from '@/core/auth/authTypes';

export const LoginPage: React.FC = () => {
  const { login, availableOfficers } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('priya.sharma@civicsense.gov.in');
  const [selectedRole, setSelectedRole] = useState<UserRole>('TRIAGE_OFFICER');
  const [isLoading, setIsLoading] = useState(false);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await login(email, selectedRole);
      navigate(from, { replace: true });
    } finally {
      setIsLoading(false);
    }
  };

  const selectPersona = (officer: (typeof availableOfficers)[0]) => {
    setEmail(officer.email);
    setSelectedRole(officer.role);
  };

  return (
    <div className="min-h-screen bg-civic-bg dark:bg-civic-dark-bg flex flex-col justify-center items-center p-4 transition-colors">
      <div className="w-full max-w-md">
        {/* Brand Card */}
        <div className="rounded-civic-lg bg-civic-surface border border-civic-border shadow-civic-modal p-6 sm:p-8 dark:bg-civic-dark-surface dark:border-civic-dark-border">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-civic-green flex items-center justify-center text-white shadow-civic-subtle">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-civic-text-primary dark:text-civic-dark-text-primary tracking-tight">
                CivicSense Authority
              </h1>
              <p className="text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary">
                Municipal Management & AI Triage
              </p>
            </div>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label
                htmlFor="officer-email"
                className="block text-xs font-medium text-civic-text-secondary dark:text-civic-dark-text-secondary mb-1"
              >
                Officer Email Address
              </label>
              <input
                id="officer-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="officer@civicsense.gov.in"
                className="w-full h-10 px-3 text-xs rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 focus:border-civic-green dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border dark:text-civic-dark-text-primary"
              />
            </div>

            <div>
              <label
                htmlFor="officer-role"
                className="block text-xs font-medium text-civic-text-secondary dark:text-civic-dark-text-secondary mb-1"
              >
                Access Role
              </label>
              <select
                id="officer-role"
                value={selectedRole}
                onChange={(e) => setSelectedRole(e.target.value as UserRole)}
                className="w-full h-10 px-3 text-xs rounded-lg border border-civic-border bg-civic-surface text-civic-text-primary focus:outline-none focus:ring-2 focus:ring-civic-green/30 focus:border-civic-green dark:bg-civic-dark-surface-elevated dark:border-civic-dark-border dark:text-civic-dark-text-primary"
              >
                <option value="TRIAGE_OFFICER">Triage Officer (Review & Prioritize)</option>
                <option value="DEPARTMENT_MANAGER">Department Manager (Assign & Coordinate)</option>
                <option value="FIELD_INSPECTOR">Field Inspector (Execute & Resolve)</option>
                <option value="SUPER_ADMIN">Super Administrator (Full Governance)</option>
              </select>
            </div>

            <div className="pt-2">
              <CivicButton
                type="submit"
                variant="primary"
                size="lg"
                isLoading={isLoading}
                rightIcon={<ArrowRight className="w-4 h-4" />}
                className="w-full"
              >
                Sign In to Dashboard
              </CivicButton>
            </div>
          </form>

          {/* Quick Persona Selector */}
          <div className="mt-8 pt-6 border-t border-civic-border dark:border-civic-dark-border">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-civic-text-muted uppercase tracking-wider mb-3">
              <UserCheck className="w-3.5 h-3.5" />
              <span>Quick Test Personas</span>
            </div>
            <div className="grid grid-cols-1 gap-2">
              {availableOfficers.map((off) => (
                <button
                  key={off.id}
                  type="button"
                  onClick={() => selectPersona(off)}
                  className="flex items-center justify-between p-2.5 rounded-lg border border-civic-border bg-gray-50/60 hover:bg-civic-green-container/30 hover:border-civic-green/40 dark:bg-civic-dark-surface-elevated/40 dark:border-civic-dark-border text-left transition-colors cursor-pointer"
                >
                  <div>
                    <p className="text-xs font-medium text-civic-text-primary dark:text-civic-dark-text-primary">
                      {off.name}
                    </p>
                    <p className="text-[11px] text-civic-text-muted">
                      {off.badgeNumber} � {off.department}
                    </p>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-black/5 dark:bg-white/10 text-civic-text-secondary dark:text-civic-dark-text-secondary">
                    {off.role.replace('_', ' ')}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="mt-4 text-center text-xs text-civic-text-muted">
          CivicSense Municipal Operations — Secure Government Portal
        </p>

        {/* Prototype Authentication Disclosure */}
        <div className="mt-3 p-3 rounded-lg border border-amber-200 bg-amber-50/80 dark:bg-amber-950/30 dark:border-amber-900/50 text-center">
          <p className="text-[11px] text-amber-800 dark:text-amber-300 leading-relaxed">
            <span className="font-semibold">Prototype Mode:</span> Authentication is simulated for controlled demonstrations only.
            Production deployment requires authenticated role-based access control (RBAC).
          </p>
        </div>
      </div>
    </div>
  );
};
