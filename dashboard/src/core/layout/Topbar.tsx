import React, { useState, useEffect, useRef } from 'react';
import { Menu, Sun, Moon, Laptop, LogOut, RefreshCw, ChevronDown, Check } from 'lucide-react';
import { clsx } from 'clsx';
import { useAuth } from '../auth/AuthContext';
import { useTheme } from '../theme/ThemeContext';
import { env } from '../config/env';
import { apiClient } from '@/services/api/apiClient';
import { UserRole } from '../auth/authTypes';
import { CivicSenseLogo } from '../components/CivicSenseLogo';
import { AnimatePresence, motion } from 'motion/react';
import { useNavigate } from 'react-router-dom';

const DROPDOWN_ANIM = {
  initial:  { opacity: 0, scale: 0.95, y: -4 },
  animate:  { opacity: 1, scale: 1,    y: 0   },
  exit:     { opacity: 0, scale: 0.95, y: -4  },
  transition: { duration: 0.15, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] },
};

export interface TopbarProps {
  onOpenMobileMenu: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({ onOpenMobileMenu }) => {
  const { user, logout, switchRole, availableOfficers } = useAuth();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const navigate = useNavigate();

  const [isApiHealthy, setIsApiHealthy]     = useState<boolean | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [isThemeMenuOpen,   setIsThemeMenuOpen]   = useState(false);

  // Outside-click refs
  const profileRef = useRef<HTMLDivElement>(null);
  const themeRef   = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setIsProfileMenuOpen(false);
      }
      if (themeRef.current && !themeRef.current.contains(e.target as Node)) {
        setIsThemeMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Close on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsProfileMenuOpen(false);
        setIsThemeMenuOpen(false);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  const checkApiHealth = async () => {
    if (!env.isApi) return;
    setIsCheckingHealth(true);
    try {
      const ok = await apiClient.checkHealth();
      setIsApiHealthy(ok);
    } catch {
      setIsApiHealthy(false);
    } finally {
      setIsCheckingHealth(false);
    }
  };

  useEffect(() => {
    if (env.isApi) {
      checkApiHealth();
      const interval = setInterval(checkApiHealth, 30000);
      return () => clearInterval(interval);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLogout = () => {
    setIsProfileMenuOpen(false);
    logout();
    navigate('/login');
  };

  return (
    <header className="h-14 border-b border-neutral-200/80 dark:border-neutral-800/80 bg-neutral-100/90 dark:bg-neutral-900/90 backdrop-blur-xl px-4 sm:px-5 flex items-center justify-between sticky top-0 z-30 transition-colors">

      {/* ── Left: Mobile menu + breadcrumb ─────────────────────────── */}
      <div className="flex items-center gap-2.5">
        <button
          type="button"
          onClick={onOpenMobileMenu}
          className="p-2 -ml-1 rounded-xl text-neutral-600 hover:text-neutral-900 hover:bg-neutral-200/70 dark:text-neutral-400 dark:hover:text-neutral-100 dark:hover:bg-neutral-700/60 transition-colors md:hidden"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Mobile brand */}
        <div className="flex items-center gap-2 md:hidden">
          <CivicSenseLogo size={22} showBadge={false} />
          <span className="font-bold text-sm tracking-tight text-neutral-900 dark:text-neutral-100">
            CivicSense
          </span>
        </div>

        {/* Desktop breadcrumb */}
        <div className="hidden md:flex items-center gap-2 text-xs">
          <CivicSenseLogo size={18} showBadge={false} />
          <span className="font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500">
            City Municipality
          </span>
          <span className="text-neutral-300 dark:text-neutral-600">/</span>
          <span className="font-medium text-neutral-700 dark:text-neutral-300">
            Central Command Triage
          </span>
        </div>
      </div>

      {/* ── Right: Status + Theme + Profile ────────────────────────── */}
      <div className="flex items-center gap-2 sm:gap-3">

        {/* Connection status */}
        {env.isMock ? (
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800 border border-amber-200/80 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800/60"
            title="Operating with local mock data (VITE_DATA_MODE=mock)"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
            <span className="hidden sm:inline text-amber-700 dark:text-amber-400">Demo</span>
            <span className="font-semibold">Mock</span>
          </div>
        ) : (
          <div
            className={clsx(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors',
              isApiHealthy === true
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800/60'
                : isApiHealthy === false
                ? 'bg-red-50 text-red-700 border-red-200 dark:bg-red-950/50 dark:text-red-300 dark:border-red-800/60'
                : 'bg-neutral-100 text-neutral-600 border-neutral-200 dark:bg-neutral-800 dark:text-neutral-400 dark:border-neutral-700'
            )}
          >
            <span
              className={clsx(
                'w-1.5 h-1.5 rounded-full shrink-0',
                isApiHealthy === true  ? 'bg-emerald-500'
                : isApiHealthy === false ? 'bg-red-500 animate-pulse'
                : 'bg-neutral-400'
              )}
            />
            <span className="hidden sm:inline">
              {isApiHealthy === true  ? 'Live API'
               : isApiHealthy === false ? 'Offline'
               : 'Checking…'}
            </span>
            {isApiHealthy === false && (
              <button
                type="button"
                onClick={checkApiHealth}
                disabled={isCheckingHealth}
                className="ml-0.5 hover:opacity-70"
                title="Retry"
              >
                <RefreshCw className={clsx('w-3 h-3', isCheckingHealth && 'animate-spin')} />
              </button>
            )}
          </div>
        )}

        {/* ── Theme Switcher ──────────────────────────────────────── */}
        <div className="relative" ref={themeRef}>
          <button
            type="button"
            onClick={() => { setIsThemeMenuOpen(p => !p); setIsProfileMenuOpen(false); }}
            className="p-2 rounded-xl text-neutral-600 hover:text-neutral-900 hover:bg-neutral-200/70 dark:text-neutral-400 dark:hover:text-neutral-100 dark:hover:bg-neutral-700/60 transition-colors"
            aria-label="Toggle theme"
            aria-expanded={isThemeMenuOpen}
          >
            {resolvedTheme === 'dark' ? (
              <Moon className="w-4 h-4" />
            ) : (
              <Sun className="w-4 h-4" />
            )}
          </button>

          <AnimatePresence>
            {isThemeMenuOpen && (
              <motion.div
                {...DROPDOWN_ANIM}
                className="absolute right-0 top-full mt-2 w-40 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 shadow-xl shadow-black/10 dark:shadow-black/40 z-50 py-1.5 overflow-hidden"
              >
                {(
                  [
                    { value: 'light',  label: 'Light',  Icon: Sun    },
                    { value: 'dark',   label: 'Dark',   Icon: Moon   },
                    { value: 'system', label: 'System', Icon: Laptop },
                  ] as const
                ).map(({ value, label, Icon }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => { setTheme(value); setIsThemeMenuOpen(false); }}
                    className={clsx(
                      'w-full flex items-center justify-between gap-2 px-4 py-2 text-sm transition-colors',
                      theme === value
                        ? 'text-civic-green dark:text-civic-green-light bg-civic-green/8 dark:bg-civic-green/15 font-semibold'
                        : 'text-neutral-700 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-700/60'
                    )}
                  >
                    <span className="flex items-center gap-2.5">
                      <Icon className="w-3.5 h-3.5 shrink-0" />
                      {label}
                    </span>
                    {theme === value && <Check className="w-3.5 h-3.5 shrink-0" />}
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ── Officer Profile Menu ────────────────────────────────── */}
        {user && (
          <div className="relative" ref={profileRef}>
            <button
              type="button"
              onClick={() => { setIsProfileMenuOpen(p => !p); setIsThemeMenuOpen(false); }}
              className="flex items-center gap-2 p-1 sm:px-2.5 sm:py-1.5 rounded-xl hover:bg-neutral-200/70 dark:hover:bg-neutral-700/60 transition-colors select-none"
              aria-expanded={isProfileMenuOpen}
            >
              <div className="w-7 h-7 rounded-full bg-civic-green-container text-civic-green dark:bg-civic-green/20 dark:text-civic-green-light flex items-center justify-center font-bold text-xs shrink-0">
                {user.name.charAt(0)}
              </div>
              <div className="hidden sm:flex flex-col text-left">
                <span className="text-xs font-semibold text-neutral-900 dark:text-neutral-100 leading-tight">
                  {user.name}
                </span>
                <span className="text-[10px] text-neutral-500 dark:text-neutral-400 leading-tight">
                  {user.badgeNumber}
                </span>
              </div>
              <ChevronDown className={clsx(
                'w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500 hidden sm:block transition-transform duration-200',
                isProfileMenuOpen && 'rotate-180'
              )} />
            </button>

            <AnimatePresence>
              {isProfileMenuOpen && (
                <motion.div
                  {...DROPDOWN_ANIM}
                  className="absolute right-0 top-full mt-2 w-72 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 shadow-xl shadow-black/10 dark:shadow-black/40 z-50 overflow-hidden"
                >
                  {/* Profile header */}
                  <div className="px-4 py-3 border-b border-neutral-100 dark:border-neutral-700">
                    <p className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                      {user.name}
                    </p>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400 truncate mt-0.5">
                      {user.email}
                    </p>
                    <div className="mt-2 flex items-center gap-2">
                      <span className="inline-block px-2 py-0.5 rounded-md text-[11px] font-mono font-medium bg-civic-green/10 text-civic-green dark:bg-civic-green/20 dark:text-civic-green-light">
                        {user.role}
                      </span>
                      <span className="text-[11px] text-neutral-500 dark:text-neutral-400 truncate">
                        {user.department}
                      </span>
                    </div>
                  </div>

                  {/* Switch persona */}
                  <div className="py-1.5">
                    <span className="block px-4 py-1 text-[10px] font-bold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider">
                      Switch Test Persona
                    </span>
                    {availableOfficers.map((officer) => (
                      <button
                        key={officer.id}
                        type="button"
                        onClick={() => { switchRole(officer.role as UserRole); setIsProfileMenuOpen(false); }}
                        className={clsx(
                          'w-full flex items-center justify-between px-4 py-2 text-sm transition-colors',
                          user.id === officer.id
                            ? 'bg-civic-green/8 dark:bg-civic-green/15 text-civic-green dark:text-civic-green-light font-semibold'
                            : 'text-neutral-700 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-700/60'
                        )}
                      >
                        <span className="truncate">{officer.name}</span>
                        <span className="text-[10px] opacity-60 font-mono ml-2 shrink-0">
                          {officer.role.replace(/_/g, ' ')}
                        </span>
                      </button>
                    ))}
                  </div>

                  {/* Logout */}
                  <div className="border-t border-neutral-100 dark:border-neutral-700 py-1.5">
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
                    >
                      <LogOut className="w-4 h-4 shrink-0" />
                      Sign Out
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>
    </header>
  );
};
