'use client';

import { clsx } from 'clsx';
import { ScoreCard, ScoreCardSkeleton } from './ScoreCard';
import type { WorkoutScore } from '@/lib/types';

export interface ScoreCardGridProps {
  scores: WorkoutScore[];
  size?: 'sm' | 'md' | 'lg';
  columns?: 2 | 3 | 4;
  className?: string;
}

export function ScoreCardGrid({
  scores,
  size = 'md',
  columns = 4,
  className,
}: ScoreCardGridProps) {
  // Dynamic grid classes based on columns
  const gridClasses = {
    2: 'grid-cols-2',
    3: 'grid-cols-2 sm:grid-cols-3',
    4: 'grid-cols-2 lg:grid-cols-4',
  };

  return (
    <div
      className={clsx(
        'grid gap-4 sm:gap-6',
        gridClasses[columns],
        className
      )}
    >
      {scores.map((score, index) => (
        <div
          key={score.name || index}
          className="flex justify-center"
        >
          <ScoreCard score={score} size={size} />
        </div>
      ))}
    </div>
  );
}

// Skeleton loader for the grid
export function ScoreCardGridSkeleton({
  count = 4,
  size = 'md',
  columns = 4,
}: {
  count?: number;
  size?: 'sm' | 'md' | 'lg';
  columns?: 2 | 3 | 4;
}) {
  const gridClasses = {
    2: 'grid-cols-2',
    3: 'grid-cols-2 sm:grid-cols-3',
    4: 'grid-cols-2 lg:grid-cols-4',
  };

  return (
    <div className={clsx('grid gap-4 sm:gap-6', gridClasses[columns])}>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="flex justify-center">
          <ScoreCardSkeleton size={size} />
        </div>
      ))}
    </div>
  );
}

export default ScoreCardGrid;
