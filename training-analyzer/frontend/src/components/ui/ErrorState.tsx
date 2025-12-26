'use client';

import { type ReactNode } from 'react';
import { clsx } from 'clsx';
import { Button } from './Button';

export interface ErrorStateProps {
  title?: string;
  message?: string;
  error?: Error | null;
  onRetry?: () => void;
  retryLabel?: string;
  onBack?: () => void;
  backLabel?: string;
  icon?: ReactNode;
  className?: string;
  variant?: 'inline' | 'card' | 'fullPage';
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  error,
  onRetry,
  retryLabel = 'Try Again',
  onBack,
  backLabel = 'Go Back',
  icon,
  className,
  variant = 'card',
}: ErrorStateProps) {
  const errorMessage = message || error?.message || 'An unexpected error occurred.';

  const defaultIcon = (
    <svg
      className="w-6 h-6 text-red-400"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );

  if (variant === 'inline') {
    return (
      <div
        className={clsx(
          'flex items-center gap-3 p-4 bg-red-900/20 border border-red-800 rounded-lg',
          className
        )}
        role="alert"
      >
        <div className="shrink-0">
          {icon || defaultIcon}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-red-400">{title}</p>
          <p className="text-sm text-red-300/80 mt-0.5">{errorMessage}</p>
        </div>
        {onRetry && (
          <Button variant="ghost" size="sm" onClick={onRetry}>
            {retryLabel}
          </Button>
        )}
      </div>
    );
  }

  if (variant === 'fullPage') {
    return (
      <div
        className={clsx(
          'min-h-[50vh] flex items-center justify-center p-4',
          className
        )}
        role="alert"
      >
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-6 flex items-center justify-center rounded-full bg-red-900/50">
            <svg
              className="w-8 h-8 text-red-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-100 mb-2">{title}</h2>
          <p className="text-gray-400 mb-6">{errorMessage}</p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            {onRetry && (
              <Button variant="primary" onClick={onRetry}>
                {retryLabel}
              </Button>
            )}
            {onBack && (
              <Button variant="secondary" onClick={onBack}>
                {backLabel}
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Card variant (default)
  return (
    <div
      className={clsx(
        'bg-red-900/20 border border-red-800 rounded-xl p-6 text-center',
        className
      )}
      role="alert"
    >
      <div className="w-12 h-12 mx-auto mb-4 flex items-center justify-center rounded-full bg-red-900/50">
        {icon || (
          <svg
            className="w-6 h-6 text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        )}
      </div>
      <h3 className="text-lg font-medium text-red-300 mb-1">{title}</h3>
      <p className="text-sm text-red-400/80 mb-4">{errorMessage}</p>
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        {onRetry && (
          <Button
            variant="danger"
            size="sm"
            onClick={onRetry}
            leftIcon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            }
          >
            {retryLabel}
          </Button>
        )}
        {onBack && (
          <Button variant="ghost" size="sm" onClick={onBack}>
            {backLabel}
          </Button>
        )}
      </div>
    </div>
  );
}

// Network error state
export function NetworkErrorState({ onRetry }: { onRetry?: () => void }) {
  return (
    <ErrorState
      title="Connection Error"
      message="Unable to connect to the server. Please check your internet connection and try again."
      onRetry={onRetry}
      icon={
        <svg
          className="w-6 h-6 text-red-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414"
          />
        </svg>
      }
    />
  );
}

// Not found error state
export function NotFoundState({
  resourceName = 'Resource',
  onBack,
}: {
  resourceName?: string;
  onBack?: () => void;
}) {
  return (
    <ErrorState
      variant="fullPage"
      title={`${resourceName} Not Found`}
      message={`The ${resourceName.toLowerCase()} you're looking for doesn't exist or has been removed.`}
      onBack={onBack}
      backLabel="Go Back"
      icon={
        <svg
          className="w-8 h-8 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      }
    />
  );
}

export default ErrorState;
