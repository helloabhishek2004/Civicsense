"use client";
import React, { useState, createContext, useContext } from "react";
import { NavLink } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import { IconMenu2, IconX } from "@tabler/icons-react";
import { cn } from "@/lib/utils";

export interface SidebarLinkItem {
  label: string;
  href?: string;
  to?: string;
  icon: React.JSX.Element | React.ReactNode;
  onClick?: () => void;
}

interface SidebarContextProps {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  animate: boolean;
}

const SidebarContext = createContext<SidebarContextProps | undefined>(
  undefined
);

export const useSidebar = () => {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error("useSidebar must be used within a SidebarProvider");
  }
  return context;
};

export const SidebarProvider = ({
  children,
  open: openProp,
  setOpen: setOpenProp,
  animate = true,
}: {
  children: React.ReactNode;
  open?: boolean;
  setOpen?: React.Dispatch<React.SetStateAction<boolean>>;
  animate?: boolean;
}) => {
  const [openState, setOpenState] = useState(false);

  const open = openProp !== undefined ? openProp : openState;
  const setOpen = setOpenProp !== undefined ? setOpenProp : setOpenState;

  return (
    <SidebarContext.Provider value={{ open, setOpen, animate }}>
      {children}
    </SidebarContext.Provider>
  );
};

export const Sidebar = ({
  children,
  open,
  setOpen,
  animate = true,
}: {
  children: React.ReactNode;
  open?: boolean;
  setOpen?: React.Dispatch<React.SetStateAction<boolean>>;
  animate?: boolean;
}) => {
  return (
    <SidebarProvider open={open} setOpen={setOpen} animate={animate}>
      {children}
    </SidebarProvider>
  );
};

export const SidebarBody = (props: React.ComponentProps<typeof motion.div>) => {
  return (
    <>
      <DesktopSidebar {...props} />
      <MobileSidebar {...(props as React.ComponentProps<"div">)} />
    </>
  );
};

export const DesktopSidebar = ({
  className,
  children,
  collapsedWidth = "68px",
  expandedWidth = "260px",
  ...props
}: React.ComponentProps<typeof motion.div> & {
  collapsedWidth?: string;
  expandedWidth?: string;
}) => {
  const { open, setOpen, animate } = useSidebar();
  return (
    <motion.aside
      className={cn(
        "h-full px-3 py-4 hidden md:flex md:flex-col shrink-0 select-none overflow-hidden",
        "bg-civic-surface border-r border-civic-border dark:bg-civic-dark-surface dark:border-civic-dark-border transition-colors",
        className
      )}
      animate={{
        width: animate ? (open ? expandedWidth : collapsedWidth) : expandedWidth,
      }}
      transition={{
        duration: 0.28,
        ease: [0.16, 1, 0.3, 1], // Apple critically damped curve
      }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      {...props}
    >
      {children}
    </motion.aside>
  );
};

export const MobileSidebar = ({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) => {
  const { open, setOpen } = useSidebar();
  return (
    <>
      <div
        className={cn(
          "h-10 px-4 py-4 flex flex-row md:hidden items-center justify-between bg-civic-surface dark:bg-civic-dark-surface border-b border-civic-border dark:border-civic-dark-border w-full"
        )}
        {...props}
      >
        <div className="flex justify-end z-20 w-full">
          <IconMenu2
            className="text-civic-text-primary dark:text-civic-dark-text-primary cursor-pointer w-5 h-5"
            onClick={() => setOpen(!open)}
          />
        </div>
        <AnimatePresence>
          {open && (
            <div className="fixed inset-0 z-50 md:hidden flex">
              {/* Backdrop */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="fixed inset-0 bg-black/40 backdrop-blur-sm"
                onClick={() => setOpen(false)}
                aria-hidden="true"
              />

              {/* Drawer Container */}
              <motion.div
                initial={{ x: "-100%" }}
                animate={{ x: 0 }}
                exit={{ x: "-100%" }}
                transition={{
                  duration: 0.3,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className={cn(
                  "relative z-50 h-full w-[280px] max-w-[85vw] p-5 flex flex-col justify-between shadow-2xl",
                  "bg-civic-surface border-r border-civic-border dark:bg-civic-dark-surface dark:border-civic-dark-border",
                  className
                )}
              >
                <div
                  className="absolute right-4 top-4 z-50 p-1.5 rounded-lg text-civic-text-secondary hover:text-civic-text-primary hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer transition-colors"
                  onClick={() => setOpen(false)}
                  aria-label="Close navigation"
                >
                  <IconX className="w-5 h-5" />
                </div>
                {children}
              </motion.div>
            </div>
          )}
        </AnimatePresence>
      </div>
    </>
  );
};

export const SidebarLink = ({
  link,
  className,
  ...props
}: {
  link: SidebarLinkItem;
  className?: string;
}) => {
  const { open, animate } = useSidebar();

  const content = (
    <>
      <div className="shrink-0 flex items-center justify-center">
        {link.icon}
      </div>

      <motion.span
        animate={{
          display: animate ? (open ? "inline-block" : "none") : "inline-block",
          opacity: animate ? (open ? 1 : 0) : 1,
        }}
        transition={{
          duration: 0.18,
          ease: [0.16, 1, 0.3, 1],
        }}
        className="text-inherit text-xs sm:text-sm font-inherit group-hover/sidebar:translate-x-0.5 transition duration-150 whitespace-pre inline-block truncate !p-0 !m-0"
      >
        {link.label}
      </motion.span>
    </>
  );

  if (link.to) {
    return (
      <NavLink
        to={link.to}
        onClick={link.onClick}
        className={({ isActive }) =>
          cn(
            "flex items-center justify-start gap-3 rounded-lg px-3 py-2 text-xs sm:text-sm font-medium transition-colors group/sidebar select-none",
            isActive
              ? "bg-civic-green-container text-civic-on-green-container font-semibold dark:bg-civic-green-container/25 dark:text-civic-green-light"
              : "text-civic-text-secondary hover:text-civic-text-primary hover:bg-black/5 dark:text-civic-dark-text-secondary dark:hover:text-civic-dark-text-primary dark:hover:bg-white/5",
            !open && "justify-center px-2",
            className
          )
        }
        title={!open ? link.label : undefined}
      >
        {content}
      </NavLink>
    );
  }

  return (
    <a
      href={link.href || "#"}
      onClick={link.onClick}
      className={cn(
        "flex items-center justify-start gap-3 rounded-lg px-3 py-2 text-xs sm:text-sm font-medium transition-colors group/sidebar select-none",
        "text-civic-text-secondary hover:text-civic-text-primary hover:bg-black/5 dark:text-civic-dark-text-secondary dark:hover:text-civic-dark-text-primary dark:hover:bg-white/5",
        !open && "justify-center px-2",
        className
      )}
      title={!open ? link.label : undefined}
      {...props}
    >
      {content}
    </a>
  );
};
