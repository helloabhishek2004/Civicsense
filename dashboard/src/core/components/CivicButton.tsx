import React from 'react';
import { clsx } from 'clsx';
import { Loader2 } from 'lucide-react';

export interface CivicButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const CivicButton = React.forwardRef<HTMLButtonElement, CivicButtonProps>(
  (
    {
      children,
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      disabled,
      leftIcon,
      rightIcon,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-150 select-none cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-civic-green/40 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none disabled:active:scale-100';

    const sizeStyles = {
      sm: 'h-8 px-3 text-xs gap-1.5',
      md: 'h-9 px-4 text-sm gap-2',
      lg: 'h-11 px-5 text-base gap-2.5',
    };

    const variantStyles = {
      primary:
        'bg-civic-green text-white hover:bg-civic-green-dark shadow-civic-subtle active:bg-civic-green-dark',
      secondary:
        'bg-civic-green-container text-civic-on-green-container hover:bg-[#d6e2d3] dark:bg-civic-green-container/20 dark:text-civic-green-light dark:hover:bg-civic-green-container/30',
      outline:
        'border border-civic-border bg-civic-surface text-civic-text-primary hover:bg-gray-50 dark:bg-civic-dark-surface dark:border-civic-dark-border dark:text-civic-dark-text-primary dark:hover:bg-civic-dark-surface-elevated shadow-civic-subtle',
      danger:
        'bg-red-600 text-white hover:bg-red-700 shadow-civic-subtle active:bg-red-800',
      ghost:
        'bg-transparent text-civic-text-primary hover:bg-black/5 dark:text-civic-dark-text-primary dark:hover:bg-white/5',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={clsx(
          baseStyles,
          sizeStyles[size],
          variantStyles[variant],
          className
        )}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin shrink-0" />
        ) : (
          leftIcon && <span className="shrink-0">{leftIcon}</span>
        )}
        <span>{children}</span>
        {!isLoading && rightIcon && <span className="shrink-0">{rightIcon}</span>}
      </button>
    );
  }
);

CivicButton.displayName = 'CivicButton';
