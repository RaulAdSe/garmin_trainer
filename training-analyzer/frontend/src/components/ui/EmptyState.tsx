'use client';

import { type ReactNode } from 'react';
import { clsx } from 'clsx';
import { Button } from './Button';

export interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary';
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

const sizeStyles = {
  sm: {
    container: 'py-8',
    icon: 'w-10 h-10',
    iconWrapper: 'w-14 h-14 mb-3',
    title: 'text-base',
    description: 'text-sm',
  },
  md: {
    container: 'py-12',
    icon: 'w-12 h-12',
    iconWrapper: 'w-16 h-16 mb-4',
    title: 'text-lg',
    description: 'text-sm',
  },
  lg: {
    container: 'py-16',
    icon: 'w-16 h-16',
    iconWrapper: 'w-20 h-20 mb-5',
    title: 'text-xl',
    description: 'text-base',
  },
};

export function EmptyState({
  icon,
  title,
  description,
  action,
  secondaryAction,
  className,
  size = 'md',
}: EmptyStateProps) {
  const styles = sizeStyles[size];

  const defaultIcon = (
    <svg
      className={clsx('text-gray-500', styles.icon)}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
      />
    </svg>
  );

  return (
    <div
      className={clsx(
        'flex flex-col items-center justify-center text-center px-4',
        styles.container,
        className
      )}
    >
      <div
        className={clsx(
          'flex items-center justify-center rounded-full bg-gray-800',
          styles.iconWrapper
        )}
      >
        {icon || defaultIcon}
      </div>
      <h3 className={clsx('font-semibold text-gray-100', styles.title)}>
        {title}
      </h3>
      {description && (
        <p
          className={clsx(
            'mt-2 text-gray-400 max-w-md',
            styles.description
          )}
        >
          {description}
        </p>
      )}
      {(action || secondaryAction) && (
        <div className="mt-6 flex flex-col sm:flex-row gap-3">
          {action && (
            <Button
              variant={action.variant || 'primary'}
              onClick={action.onClick}
            >
              {action.label}
            </Button>
          )}
          {secondaryAction && (
            <Button variant="ghost" onClick={secondaryAction.onClick}>
              {secondaryAction.label}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

// Specialized empty states for common use cases
export function NoWorkoutsState({ onCreateClick }: { onCreateClick?: () => void }) {
  return (
    <EmptyState
      icon={
        <svg
          className="w-12 h-12 text-teal-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M13 10V3L4 14h7v7l9-11h-7z"
          />
        </svg>
      }
      title="No workouts yet"
      description="Start tracking your training to see your workouts here. Import from Garmin or sync your activities."
      action={
        onCreateClick
          ? { label: 'Import Workouts', onClick: onCreateClick }
          : undefined
      }
    />
  );
}

export function NoPlansState({ onCreateClick }: { onCreateClick?: () => void }) {
  return (
    <EmptyState
      icon={
        <svg
          className="w-12 h-12 text-teal-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
          />
        </svg>
      }
      title="No training plans"
      description="Create an AI-powered training plan tailored to your goals and fitness level."
      action={
        onCreateClick
          ? { label: 'Create Training Plan', onClick: onCreateClick }
          : undefined
      }
    />
  );
}

export function NoResultsState({
  searchTerm,
  onClearSearch,
}: {
  searchTerm?: string;
  onClearSearch?: () => void;
}) {
  return (
    <EmptyState
      icon={
        <svg
          className="w-12 h-12 text-gray-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      }
      title="No results found"
      description={
        searchTerm
          ? `No results for "${searchTerm}". Try adjusting your search or filters.`
          : 'No items match your current filters.'
      }
      action={
        onClearSearch
          ? { label: 'Clear Search', onClick: onClearSearch, variant: 'secondary' }
          : undefined
      }
    />
  );
}

export default EmptyState;
