import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { clsx } from 'clsx';

export interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  width?: 'sm' | 'md' | 'lg' | 'xl';
  footer?: React.ReactNode;
}

export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  width = 'md',
  footer,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const widthClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-xl',
    xl: 'max-w-2xl',
  };

  return createPortal(
    <div className="fixed inset-0 z-50 overflow-hidden" role="dialog" aria-modal="true">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-sm transition-opacity duration-300"
        onClick={onClose}
        aria-hidden="true"
      />

      <div className="fixed inset-y-0 right-0 flex max-w-full pl-10">
        <div
          className={clsx(
            'w-screen bg-civic-surface border-l border-civic-border shadow-civic-modal flex flex-col',
            'dark:bg-civic-dark-surface dark:border-civic-dark-border',
            'transform transition-transform duration-300 ease-out',
            widthClasses[width]
          )}
        >
          {/* Drawer Header */}
          <div className="flex items-center justify-between p-5 border-b border-civic-border dark:border-civic-dark-border">
            <div>
              <h3 className="text-base font-semibold text-civic-text-primary dark:text-civic-dark-text-primary tracking-tight">
                {title}
              </h3>
              {subtitle && (
                <p className="mt-0.5 text-xs text-civic-text-secondary dark:text-civic-dark-text-secondary">
                  {subtitle}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-civic-text-muted hover:text-civic-text-primary hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
              aria-label="Close drawer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Drawer Body */}
          <div className="flex-1 overflow-y-auto p-5">{children}</div>

          {/* Drawer Footer */}
          {footer && (
            <div className="p-4 border-t border-civic-border bg-gray-50/50 dark:border-civic-dark-border dark:bg-civic-dark-surface-elevated/40">
              {footer}
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
};
