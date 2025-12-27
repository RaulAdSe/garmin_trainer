'use client';

import { clsx } from 'clsx';
import { ScoreCard, ScoreCardSkeleton } from './ScoreCard';
import { ScoreCardGrid, ScoreCardGridSkeleton } from './ScoreCardGrid';
import type { WorkoutScore, WorkoutScores as WorkoutScoresType } from '@/lib/types';
import { SCORE_COLOR_MAP, SCORE_LABEL_MAP } from '@/lib/types';

export interface WorkoutScoresProps {
  scores: WorkoutScoresType;
  className?: string;
}

export function WorkoutScores({ scores, className }: WorkoutScoresProps) {
  // Extract secondary scores (excluding overall quality)
  const secondaryScores: WorkoutScore[] = [
    scores.trainingEffect,
    scores.loadManagement,
    scores.recoveryImpact,
  ];

  const overallColorConfig = SCORE_COLOR_MAP[scores.overallQuality.color];

  return (
    <div className={clsx('space-y-6', className)}>
      {/* Hero Section - Overall Workout Quality */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-4 text-center">
          Workout Quality
        </h3>

        <div className="flex flex-col items-center">
          {/* Large Primary Score */}
          <ScoreCard
            score={scores.overallQuality}
            size="lg"
            showLabel={true}
          />

          {/* Overall quality description */}
          {scores.overallQuality.description && (
            <p className="mt-4 text-sm text-gray-400 text-center max-w-md">
              {scores.overallQuality.description}
            </p>
          )}
        </div>
      </div>

      {/* Secondary Scores Grid */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <h4 className="text-sm font-medium text-gray-400 mb-4 text-center uppercase tracking-wide">
          Score Breakdown
        </h4>
        <ScoreCardGrid
          scores={secondaryScores}
          size="sm"
          columns={3}
        />
      </div>
    </div>
  );
}

// Alternative compact layout for sidebar or smaller spaces
export interface WorkoutScoresCompactProps {
  scores: WorkoutScoresType;
  className?: string;
}

export function WorkoutScoresCompact({ scores, className }: WorkoutScoresCompactProps) {
  const allScores: WorkoutScore[] = [
    scores.overallQuality,
    scores.trainingEffect,
    scores.loadManagement,
    scores.recoveryImpact,
  ];

  return (
    <div className={clsx('bg-gray-900 rounded-xl border border-gray-800 p-4', className)}>
      <h3 className="text-sm font-semibold text-gray-100 mb-4 text-center">
        Workout Scores
      </h3>

      <div className="space-y-3">
        {allScores.map((score) => (
          <ScoreBarItem key={score.name} score={score} />
        ))}
      </div>
    </div>
  );
}

// Horizontal bar-style score item for compact layouts
interface ScoreBarItemProps {
  score: WorkoutScore;
}

function ScoreBarItem({ score }: ScoreBarItemProps) {
  const colorConfig = SCORE_COLOR_MAP[score.color];
  const percentage = Math.min((score.value / score.maxValue) * 100, 100);

  return (
    <div className="group relative">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-gray-400">{score.name}</span>
        <span className={clsx('text-sm font-semibold', colorConfig.text)}>
          {Math.round(score.value)}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all duration-500', colorConfig.bg)}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Label badge */}
      <div className="flex justify-end mt-1">
        <span className={clsx('text-xs', colorConfig.text)}>
          {SCORE_LABEL_MAP[score.label]}
        </span>
      </div>

      {/* Tooltip on hover */}
      {score.description && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-gray-800 border border-gray-700 rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
          <p className="text-xs text-gray-300 text-center">
            {score.description}
          </p>
        </div>
      )}
    </div>
  );
}

// Skeleton loader for WorkoutScores
export function WorkoutScoresSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Hero section skeleton */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <div className="h-6 bg-gray-700 rounded w-32 mx-auto mb-4" />
        <div className="flex flex-col items-center">
          <ScoreCardSkeleton size="lg" />
          <div className="mt-4 h-4 bg-gray-700 rounded w-64" />
        </div>
      </div>

      {/* Secondary scores skeleton */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <div className="h-4 bg-gray-700 rounded w-28 mx-auto mb-4" />
        <ScoreCardGridSkeleton count={3} size="sm" columns={3} />
      </div>
    </div>
  );
}

// Skeleton for compact version
export function WorkoutScoresCompactSkeleton() {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 animate-pulse">
      <div className="h-5 bg-gray-700 rounded w-28 mx-auto mb-4" />

      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i}>
            <div className="flex items-center justify-between mb-1">
              <div className="h-3 bg-gray-700 rounded w-20" />
              <div className="h-4 bg-gray-700 rounded w-8" />
            </div>
            <div className="h-2 bg-gray-700 rounded-full" />
            <div className="flex justify-end mt-1">
              <div className="h-3 bg-gray-700 rounded w-12" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default WorkoutScores;
