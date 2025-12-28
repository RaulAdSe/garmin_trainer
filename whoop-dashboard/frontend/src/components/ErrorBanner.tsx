'use client';

import { useState, useEffect, useCallback } from 'react';
import { AppError, ErrorType } from '@/lib/errors';

interface ErrorBannerProps {
  error: AppError | null;
  onDismiss?: () => void;
  autoDismissMs?: number;
  className?: string;
}

// Styling configuration based on error severity
const ERROR_STYLES: Record<
  ErrorType,
  {
    bg: string;
    border: string;
    text: string;
    icon: string;
    isCritical: boolean;
  }
> = {
  [ErrorType.NETWORK]: {
    bg: 'bg-amber-900/20',
    border: 'border-amber-800/50',
    text: 'text-amber-400',
    icon: 'text-amber-400',
    isCritical: false,
  },
  [ErrorType.AUTH]: {
    bg: 'bg-red-900/20',
    border: 'border-red-800/50',
    text: 'text-red-400',
    icon: 'text-red-400',
    isCritical: true,
  },
  [ErrorType.API]: {
    bg: 'bg-orange-900/20',
    border: 'border-orange-800/50',
    text: 'text-orange-400',
    icon: 'text-orange-400',
    isCritical: false,
  },
  [ErrorType.STORAGE]: {
    bg: 'bg-purple-900/20',
    border: 'border-purple-800/50',
    text: 'text-purple-400',
    icon: 'text-purple-400',
    isCritical: true,
  },
  [ErrorType.UNKNOWN]: {
    bg: 'bg-zinc-800/50',
    border: 'border-zinc-700',
    text: 'text-zinc-400',
    icon: 'text-zinc-400',
    isCritical: false,
  },
};

// Icons for different error types
function ErrorIcon({ type, className }: { type: ErrorType; className?: string }) {
  const baseClass = `w-5 h-5 shrink-0 ${className || ''}`;

  switch (type) {
    case ErrorType.NETWORK:
      return (
        <svg className={baseClass} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414"
          />
        </svg>
      );
    case ErrorType.AUTH:
      return (
        <svg className={baseClass} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
          />
        </svg>
      );
    case ErrorType.API:
      return (
        <svg className={baseClass} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"
          />
        </svg>
      );
    case ErrorType.STORAGE:
      return (
        <svg className={baseClass} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
          />
        </svg>
      );
    default:
      return (
        <svg className={baseClass} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      );
  }
}

/**
 * ErrorBanner component displays error messages with appropriate styling and actions.
 *
 * Features:
 * - Displays user-friendly error messages
 * - Shows retry button for recoverable errors
 * - Auto-dismisses non-critical errors after specified time (default 5s)
 * - Color-coded by error severity
 * - Accessible dismiss button
 *
 * @example
 * const [error, setError] = useState<AppError | null>(null);
 *
 * <ErrorBanner
 *   error={error}
 *   onDismiss={() => setError(null)}
 * />
 */
export function ErrorBanner({
  error,
  onDismiss,
  autoDismissMs = 5000,
  className = '',
}: ErrorBannerProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  // Handle visibility and auto-dismiss
  useEffect(() => {
    if (error) {
      setIsVisible(true);

      const styles = ERROR_STYLES[error.type];

      // Auto-dismiss non-critical, non-recoverable errors
      if (!styles.isCritical && autoDismissMs > 0) {
        const timer = setTimeout(() => {
          setIsVisible(false);
          setTimeout(() => onDismiss?.(), 300); // Allow fade-out animation
        }, autoDismissMs);

        return () => clearTimeout(timer);
      }
    } else {
      setIsVisible(false);
    }
  }, [error, autoDismissMs, onDismiss]);

  const handleDismiss = useCallback(() => {
    setIsVisible(false);
    setTimeout(() => onDismiss?.(), 300);
  }, [onDismiss]);

  const handleRetry = useCallback(async () => {
    if (!error?.retryAction) return;

    setIsRetrying(true);
    try {
      await error.retryAction();
      handleDismiss();
    } catch {
      // Error will be re-thrown and handled by parent
    } finally {
      setIsRetrying(false);
    }
  }, [error, handleDismiss]);

  if (!error) return null;

  const styles = ERROR_STYLES[error.type];

  return (
    <div
      role="alert"
      aria-live="polite"
      className={`
        transition-all duration-300 ease-in-out
        ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-2'}
        ${className}
      `}
    >
      <div
        className={`
          flex items-start gap-3 p-4 rounded-xl border
          ${styles.bg} ${styles.border}
        `}
      >
        {/* Error icon */}
        <ErrorIcon type={error.type} className={styles.icon} />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-medium ${styles.text}`}>
            {error.userMessage}
          </p>
          {/* Show technical message in development */}
          {process.env.NODE_ENV === 'development' && error.message !== error.userMessage && (
            <p className="text-xs text-zinc-500 mt-1 truncate" title={error.message}>
              {error.message}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Retry button for recoverable errors */}
          {error.recoverable && error.retryAction && (
            <button
              onClick={handleRetry}
              disabled={isRetrying}
              className={`
                px-3 py-1.5 text-sm font-medium rounded-lg
                transition-colors
                ${styles.text} hover:bg-white/10
                disabled:opacity-50 disabled:cursor-not-allowed
              `}
              aria-label="Retry action"
            >
              {isRetrying ? (
                <svg
                  className="w-4 h-4 animate-spin"
                  fill="none"
                  viewBox="0 0 24 24"
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
              ) : (
                'Retry'
              )}
            </button>
          )}

          {/* Dismiss button */}
          <button
            onClick={handleDismiss}
            className="p-1 rounded-lg text-zinc-500 hover:text-white hover:bg-white/10 transition-colors"
            aria-label="Dismiss error"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

export default ErrorBanner;
