import React, { useState, createContext, useContext } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'motion/react';
import {
  IconBrandTabler,
  IconFileText,
  IconCpu,
  IconMapPin,
  IconChartBar,
  IconBuilding,
  IconUsers,
  IconSettings,
  IconMenu2,
  IconX,
  IconLogout,
} from '@tabler/icons-react';
import { cn } from '@/lib/utils';
import { useAuth } from '../auth/AuthContext';
import { CivicSenseLogo } from '../components/CivicSenseLogo';

// ── Context ────────────────────────────────────────────────────────────────────

interface SidebarContextProps {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  animate: boolean;
}

const SidebarContext = createContext<SidebarContextProps | undefined>(undefined);

export const useSidebar = () => {
  const ctx = useContext(SidebarContext);
  if (!ctx) throw new Error('useSidebar must be used within Sidebar');
  return ctx;
};

// ── Types ──────────────────────────────────────────────────────────────────────

interface NavItem {
  label: string;
  to: string;
  icon: React.ReactNode;
}

// ── Nav Items ──────────────────────────────────────────────────────────────────

const OPERATIONS_NAV: NavItem[] = [
  { label: 'Overview',      to: '/',              icon: <IconBrandTabler className="w-5 h-5 shrink-0" /> },
  { label: 'Reports Queue', to: '/reports',       icon: <IconFileText    className="w-5 h-5 shrink-0" /> },
  { label: 'AI Operations', to: '/ai-operations', icon: <IconCpu         className="w-5 h-5 shrink-0" /> },
  { label: 'Live Map',      to: '/map',           icon: <IconMapPin      className="w-5 h-5 shrink-0" /> },
  { label: 'Analytics',     to: '/analytics',     icon: <IconChartBar    className="w-5 h-5 shrink-0" /> },
];

const ADMINISTRATION_NAV: NavItem[] = [
  { label: 'Departments', to: '/departments', icon: <IconBuilding className="w-5 h-5 shrink-0" /> },
  { label: 'Staff & Roles', to: '/users',     icon: <IconUsers    className="w-5 h-5 shrink-0" /> },
  { label: 'Settings',    to: '/settings',    icon: <IconSettings className="w-5 h-5 shrink-0" /> },
];

// ── NavLink Item (shared by desktop + mobile) ──────────────────────────────────

const NavItem: React.FC<{
  item: NavItem;
  onNavigate?: () => void;
  collapsed?: boolean;
}> = ({ item, onNavigate, collapsed = false }) => {
  const { open, animate } = useSidebar();
  const isExpanded = !collapsed && (animate ? open : true);

  return (
    <NavLink
      to={item.to}
      end={item.to === '/'}
      onClick={onNavigate}
      title={!isExpanded ? item.label : undefined}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 group/navitem select-none whitespace-nowrap overflow-hidden',
          isActive
            ? 'bg-civic-green/15 text-civic-green dark:bg-civic-green/20 dark:text-civic-green-light font-semibold'
            : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-200/60 dark:text-neutral-400 dark:hover:text-neutral-100 dark:hover:bg-neutral-700/60',
          !isExpanded && 'justify-center px-0'
        )
      }
    >
      <span className="shrink-0 flex items-center justify-center">{item.icon}</span>
      <motion.span
        animate={{
          display: isExpanded ? 'inline-block' : 'none',
          opacity: isExpanded ? 1 : 0,
        }}
        transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
        className="truncate group-hover/navitem:translate-x-0.5 transition-transform duration-150"
      >
        {item.label}
      </motion.span>
    </NavLink>
  );
};

// ── Desktop Sidebar ────────────────────────────────────────────────────────────

const DesktopSidebar: React.FC = () => {
  const { open, setOpen, animate } = useSidebar();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const isExpanded = animate ? open : true;

  return (
    <motion.aside
      className={cn(
        'hidden md:flex md:flex-col h-full shrink-0 select-none overflow-hidden border-r z-40 transition-colors',
        'bg-neutral-100 dark:bg-neutral-900 border-neutral-200 dark:border-neutral-800'
      )}
      animate={{ width: isExpanded ? '280px' : '68px' }}
      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center px-4 border-b border-neutral-200 dark:border-neutral-800 gap-3 shrink-0">
        <CivicSenseLogo size={28} />
        <motion.div
          animate={{ display: isExpanded ? 'flex' : 'none', opacity: isExpanded ? 1 : 0 }}
          transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col min-w-0 overflow-hidden"
        >
          <span className="font-bold text-sm tracking-tight text-neutral-900 dark:text-neutral-100 truncate whitespace-nowrap">
            CivicSense
          </span>
          <span className="text-[10px] font-semibold text-civic-green dark:text-civic-green-light tracking-wide uppercase truncate whitespace-nowrap">
            Authority Portal
          </span>
        </motion.div>
      </div>

      {/* Navigation */}
      <div className="flex-1 py-4 px-2 space-y-6 overflow-y-auto overflow-x-hidden">
        {/* Operations */}
        <div className="space-y-1">
          <motion.p
            animate={{ display: isExpanded ? 'block' : 'none', opacity: isExpanded ? 1 : 0 }}
            transition={{ duration: 0.14 }}
            className="px-3 mb-1 text-[10px] font-bold text-neutral-400 dark:text-neutral-500 uppercase tracking-widest whitespace-nowrap"
          >
            Operations
          </motion.p>
          <nav className="space-y-0.5">
            {OPERATIONS_NAV.map((item) => (
              <NavItem key={item.to} item={item} />
            ))}
          </nav>
        </div>

        {/* Administration */}
        <div className="space-y-1">
          <motion.p
            animate={{ display: isExpanded ? 'block' : 'none', opacity: isExpanded ? 1 : 0 }}
            transition={{ duration: 0.14 }}
            className="px-3 mb-1 text-[10px] font-bold text-neutral-400 dark:text-neutral-500 uppercase tracking-widest whitespace-nowrap"
          >
            Administration
          </motion.p>
          <nav className="space-y-0.5">
            {ADMINISTRATION_NAV.map((item) => (
              <NavItem key={item.to} item={item} />
            ))}
          </nav>
        </div>
      </div>

      {/* Footer: Officer Profile + Logout */}
      <div className="p-3 border-t border-neutral-200 dark:border-neutral-800 shrink-0">
        {user && (
          <div
            className={cn(
              'flex items-center gap-2.5 min-w-0 overflow-hidden',
              !isExpanded && 'justify-center'
            )}
          >
            {/* Avatar */}
            <div
              className="w-8 h-8 rounded-full bg-civic-green-container text-civic-green dark:bg-civic-green/20 dark:text-civic-green-light flex items-center justify-center font-bold text-xs shrink-0 ring-1 ring-neutral-200 dark:ring-neutral-700"
              title={!isExpanded ? `${user.name} (${user.role})` : undefined}
            >
              {user.name.charAt(0)}
            </div>

            {/* Name + Role (hidden when collapsed) */}
            <motion.div
              animate={{ display: isExpanded ? 'flex' : 'none', opacity: isExpanded ? 1 : 0 }}
              transition={{ duration: 0.18 }}
              className="flex flex-col min-w-0 flex-1"
            >
              <span className="text-xs font-semibold text-neutral-900 dark:text-neutral-100 truncate whitespace-nowrap">
                {user.name}
              </span>
              <span className="text-[10px] text-neutral-500 dark:text-neutral-400 truncate whitespace-nowrap">
                {user.role.replace(/_/g, ' ')}
              </span>
            </motion.div>

            {/* Logout button — only visible when expanded */}
            <motion.button
              type="button"
              animate={{ display: isExpanded ? 'flex' : 'none', opacity: isExpanded ? 1 : 0 }}
              transition={{ duration: 0.18 }}
              onClick={() => {
                logout();
                navigate('/login');
              }}
              className="p-1.5 rounded-lg text-neutral-400 hover:text-red-500 hover:bg-red-50 dark:hover:text-red-400 dark:hover:bg-red-950/40 transition-colors shrink-0"
              title="Sign out"
              aria-label="Sign out"
            >
              <IconLogout className="w-4 h-4" />
            </motion.button>
          </div>
        )}
      </div>
    </motion.aside>
  );
};

// ── Mobile Sidebar ─────────────────────────────────────────────────────────────

const MobileSidebar: React.FC<{
  isMobileOpen: boolean;
  onMobileClose: () => void;
}> = ({ isMobileOpen, onMobileClose }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleNavigate = () => {
    onMobileClose();
  };

  const handleLogout = () => {
    onMobileClose();
    logout();
    navigate('/login');
  };

  return (
    <AnimatePresence>
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm"
            onClick={onMobileClose}
            aria-hidden="true"
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: '-100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '-100%', opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="relative z-50 h-full w-[280px] max-w-[85vw] flex flex-col bg-neutral-100 dark:bg-neutral-900 border-r border-neutral-200 dark:border-neutral-800 shadow-2xl"
          >
            {/* Header */}
            <div className="h-16 flex items-center justify-between px-5 border-b border-neutral-200 dark:border-neutral-800 shrink-0">
              <div className="flex items-center gap-3">
                <CivicSenseLogo size={28} />
                <div className="flex flex-col">
                  <span className="font-bold text-sm text-neutral-900 dark:text-neutral-100">CivicSense</span>
                  <span className="text-[10px] font-semibold text-civic-green dark:text-civic-green-light uppercase tracking-wide">
                    Authority Portal
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={onMobileClose}
                className="p-1.5 rounded-lg text-neutral-500 hover:text-neutral-900 hover:bg-neutral-200 dark:hover:text-neutral-100 dark:hover:bg-neutral-700 transition-colors"
                aria-label="Close navigation"
              >
                <IconX className="w-5 h-5" />
              </button>
            </div>

            {/* Nav */}
            <div className="flex-1 py-5 px-3 overflow-y-auto space-y-6">
              {/* Operations */}
              <div className="space-y-1">
                <p className="px-3 mb-2 text-[10px] font-bold text-neutral-400 dark:text-neutral-500 uppercase tracking-widest">
                  Operations
                </p>
                <nav className="space-y-0.5">
                  {OPERATIONS_NAV.map((item) => (
                    <MobileNavItem key={item.to} item={item} onNavigate={handleNavigate} />
                  ))}
                </nav>
              </div>

              {/* Administration */}
              <div className="space-y-1">
                <p className="px-3 mb-2 text-[10px] font-bold text-neutral-400 dark:text-neutral-500 uppercase tracking-widest">
                  Administration
                </p>
                <nav className="space-y-0.5">
                  {ADMINISTRATION_NAV.map((item) => (
                    <MobileNavItem key={item.to} item={item} onNavigate={handleNavigate} />
                  ))}
                </nav>
              </div>
            </div>

            {/* Footer */}
            {user && (
              <div className="p-4 border-t border-neutral-200 dark:border-neutral-800 shrink-0 flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-civic-green-container text-civic-green dark:bg-civic-green/20 dark:text-civic-green-light flex items-center justify-center font-bold text-sm shrink-0">
                  {user.name.charAt(0)}
                </div>
                <div className="flex flex-col min-w-0 flex-1">
                  <span className="text-xs font-semibold text-neutral-900 dark:text-neutral-100 truncate">{user.name}</span>
                  <span className="text-[10px] text-neutral-500 dark:text-neutral-400 truncate">{user.role.replace(/_/g, ' ')}</span>
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="p-2 rounded-lg text-neutral-400 hover:text-red-500 hover:bg-red-50 dark:hover:text-red-400 dark:hover:bg-red-950/40 transition-colors"
                  aria-label="Sign out"
                >
                  <IconLogout className="w-4 h-4" />
                </button>
              </div>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

// ── Mobile NavLink (no context dependency) ─────────────────────────────────────

const MobileNavItem: React.FC<{ item: NavItem; onNavigate: () => void }> = ({ item, onNavigate }) => (
  <NavLink
    to={item.to}
    end={item.to === '/'}
    onClick={onNavigate}
    className={({ isActive }) =>
      cn(
        'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors',
        isActive
          ? 'bg-civic-green/15 text-civic-green dark:bg-civic-green/20 dark:text-civic-green-light font-semibold'
          : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-200/60 dark:text-neutral-400 dark:hover:text-neutral-100 dark:hover:bg-neutral-700/60'
      )
    }
  >
    <span className="shrink-0">{item.icon}</span>
    <span className="truncate">{item.label}</span>
  </NavLink>
);

// ── Mobile Topbar Trigger ──────────────────────────────────────────────────────

export const MobileMenuButton: React.FC<{ onClick: () => void }> = ({ onClick }) => (
  <button
    type="button"
    onClick={onClick}
    className="p-2 rounded-xl text-neutral-600 hover:text-neutral-900 hover:bg-neutral-200/60 dark:text-neutral-400 dark:hover:text-neutral-100 dark:hover:bg-neutral-700/60 transition-colors md:hidden"
    aria-label="Open navigation"
  >
    <IconMenu2 className="w-5 h-5" />
  </button>
);

// ── Main Exported Sidebar Component ───────────────────────────────────────────

export interface SidebarProps {
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  isMobileOpen?: boolean;
  onMobileClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isMobileOpen = false,
  onMobileClose = () => {},
}) => {
  const [open, setOpen] = useState(false);

  return (
    <SidebarContext.Provider value={{ open, setOpen, animate: true }}>
      {/* Desktop hover-expandable sidebar */}
      <DesktopSidebar />

      {/* Mobile slide-in drawer */}
      <MobileSidebar isMobileOpen={isMobileOpen} onMobileClose={onMobileClose} />
    </SidebarContext.Provider>
  );
};
