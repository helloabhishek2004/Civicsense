import React, { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'motion/react';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { InitialPageSkeleton } from '../components/InitialPageSkeleton';

export const AppShell: React.FC = () => {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const location = useLocation();

  // 2-second skeleton on first page load (session-scoped)
  const [isInitialLoading, setIsInitialLoading] = useState(() => {
    return !sessionStorage.getItem('civicsense_initial_loaded');
  });

  useEffect(() => {
    if (isInitialLoading) {
      const timer = setTimeout(() => {
        sessionStorage.setItem('civicsense_initial_loaded', 'true');
        setIsInitialLoading(false);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [isInitialLoading]);

  // Close mobile drawer on route change
  useEffect(() => {
    setIsMobileOpen(false);
  }, [location.pathname]);

  return (
    <div className="relative flex h-screen overflow-hidden bg-neutral-50 dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 transition-colors">
      {/* Initial skeleton overlay */}
      <AnimatePresence>
        {isInitialLoading && <InitialPageSkeleton key="initial-skeleton" />}
      </AnimatePresence>

      {/* Sidebar (desktop hover + mobile drawer) */}
      <Sidebar
        isMobileOpen={isMobileOpen}
        onMobileClose={() => setIsMobileOpen(false)}
      />

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Topbar onOpenMobileMenu={() => setIsMobileOpen(true)} />

        {/* Scrollable viewport with page transition animation */}
        <main className="flex-1 overflow-y-auto">
          <div className="px-4 sm:px-6 py-5 max-w-7xl w-full mx-auto">
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={location.pathname}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              >
                <Outlet />
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  );
};
