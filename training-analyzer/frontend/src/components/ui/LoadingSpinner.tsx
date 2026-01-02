'use client';

import { clsx } from 'clsx';

export type SpinnerSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

export interface LoadingSpinnerProps {
  size?: SpinnerSize;
  className?: string;
  label?: string;
}

const sizeStyles: Record<SpinnerSize, string> = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
  xl: 'w-12 h-12',
};

export function LoadingSpinner({
  size = 'md',
  className,
  label = 'Loading...',
}: LoadingSpinnerProps) {
  return (
    <div
      className={clsx('inline-flex items-center justify-center', className)}
      role="status"
      aria-label={label}
    >
      <svg
        className={clsx('animate-spin text-teal-500', sizeStyles[size])}
        fill="none"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      <span className="sr-only">{label}</span>
    </div>
  );
}

// Full page loading overlay
export function LoadingOverlay({
  message = 'Loading...',
  className,
}: {
  message?: string;
  className?: string;
}) {
  return (
    <div
      className={clsx(
        'fixed inset-0 z-50 flex items-center justify-center bg-gray-950/80 backdrop-blur-sm',
        className
      )}
      role="status"
      aria-live="polite"
    >
      <div className="flex flex-col items-center gap-4">
        <LoadingSpinner size="xl" />
        <p className="text-gray-300 text-sm font-medium">{message}</p>
      </div>
    </div>
  );
}

// Inline loading state
export function LoadingInline({
  message = 'Loading...',
  size = 'sm',
  className,
}: {
  message?: string;
  size?: SpinnerSize;
  className?: string;
}) {
  return (
    <div
      className={clsx('inline-flex items-center gap-2 text-gray-300', className)}
      role="status"
      aria-live="polite"
    >
      <LoadingSpinner size={size} />
      <span className="text-sm">{message}</span>
    </div>
  );
}

// Center loading for containers
export function LoadingCenter({
  message = 'Loading...',
  size = 'lg',
  className,
}: {
  message?: string;
  size?: SpinnerSize;
  className?: string;
}) {
  return (
    <div
      className={clsx(
        'flex flex-col items-center justify-center py-12 gap-4',
        className
      )}
      role="status"
      aria-live="polite"
    >
      <LoadingSpinner size={size} />
      <p className="text-gray-300 text-sm">{message}</p>
    </div>
  );
}

// Button loading spinner (matches button text)
export function ButtonSpinner({ className }: { className?: string }) {
  return (
    <svg
      className={clsx('animate-spin w-4 h-4', className)}
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

export default LoadingSpinner;
