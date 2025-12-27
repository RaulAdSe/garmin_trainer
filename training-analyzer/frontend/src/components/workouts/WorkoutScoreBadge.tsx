'use client';

import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { Tooltip } from '@/components/ui/Tooltip';

interface ScoreBreakdown {
  execution: 'excellent' | 'good' | 'fair' | 'needs_improvement' | null;
  trainingEffect: number | null; // 0-5
  load: number | null; // HRSS/TRIMP
}

interface WorkoutScoreBadgeProps {
  score: number; // 0-100
  breakdown?: ScoreBreakdown;
  className?: string;
}

export function WorkoutScoreBadge({ score, breakdown, className }: WorkoutScoreBadgeProps) {
  // Determine color based on score
  const { bgColor, textColor, ringColor, label } = useMemo(() => {
    if (score >= 85) {
      return {
        bgColor: 'bg-green-900/30',
        textColor: 'text-green-400',
        ringColor: 'ring-green-500/30',
        label: 'Excellent',
      };
    } else if (score >= 70) {
      return {
        bgColor: 'bg-teal-900/30',
        textColor: 'text-teal-400',
        ringColor: 'ring-teal-500/30',
        label: 'Good',
      };
    } else if (score >= 50) {
      return {
        bgColor: 'bg-amber-900/30',
        textColor: 'text-amber-400',
        ringColor: 'ring-amber-500/30',
        label: 'Fair',
      };
    } else {
      return {
        bgColor: 'bg-red-900/30',
        textColor: 'text-red-400',
        ringColor: 'ring-red-500/30',
        label: 'Needs Work',
      };
    }
  }, [score]);

  // Build tooltip content
  const tooltipContent = useMemo(() => {
    if (!breakdown) return null;

    return (
      <div className="space-y-2 py-1">
        <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Score Breakdown</div>

        {/* Execution */}
        {breakdown.execution && (
          <ScoreRow
            label="Execution"
            value={formatExecution(breakdown.execution)}
            color={getExecutionColor(breakdown.execution)}
          />
        )}

        {/* Training Effect */}
        {breakdown.trainingEffect !== null && (
          <ScoreRow
            label="Training Effect"
            value={`${breakdown.trainingEffect.toFixed(1)} / 5.0`}
            sublabel={getTrainingEffectLabel(breakdown.trainingEffect)}
            color={getTrainingEffectColor(breakdown.trainingEffect)}
          />
        )}

        {/* Load */}
        {breakdown.load !== null && (
          <ScoreRow
            label="Training Load"
            value={breakdown.load.toString()}
            sublabel={getLoadLabel(breakdown.load)}
            color={getLoadColor(breakdown.load)}
          />
        )}
      </div>
    );
  }, [breakdown]);

  const badge = (
    <div
      className={cn(
        'inline-flex items-center gap-2 px-3 py-2 rounded-lg',
        'ring-1 cursor-default transition-all duration-150',
        bgColor,
        ringColor,
        breakdown && 'cursor-pointer hover:ring-2',
        className
      )}
    >
      {/* Score number */}
      <span className={cn('text-2xl font-bold tabular-nums', textColor)}>
        {score}
      </span>

      {/* Label and max */}
      <div className="flex flex-col">
        <span className={cn('text-xs font-medium', textColor)}>{label}</span>
        <span className="text-[10px] text-gray-500">/ 100</span>
      </div>
    </div>
  );

  if (!tooltipContent) {
    return badge;
  }

  return (
    <Tooltip content={tooltipContent} position="bottom" delay={100}>
      {badge}
    </Tooltip>
  );
}

// Helper component for score rows in tooltip
interface ScoreRowProps {
  label: string;
  value: string;
  sublabel?: string;
  color: string;
}

function ScoreRow({ label, value, sublabel, color }: ScoreRowProps) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-gray-300 text-xs">{label}</span>
      <div className="text-right">
        <span className={cn('text-xs font-medium', color)}>{value}</span>
        {sublabel && (
          <span className="text-[10px] text-gray-500 ml-1">({sublabel})</span>
        )}
      </div>
    </div>
  );
}

// Helper functions
function formatExecution(rating: string): string {
  const labels: Record<string, string> = {
    excellent: 'Excellent',
    good: 'Good',
    fair: 'Fair',
    needs_improvement: 'Needs Work',
  };
  return labels[rating] || rating;
}

function getExecutionColor(rating: string): string {
  const colors: Record<string, string> = {
    excellent: 'text-green-400',
    good: 'text-teal-400',
    fair: 'text-amber-400',
    needs_improvement: 'text-red-400',
  };
  return colors[rating] || 'text-gray-400';
}

function getTrainingEffectLabel(value: number): string {
  if (value >= 4.5) return 'Overreaching';
  if (value >= 3.5) return 'Highly Improving';
  if (value >= 2.5) return 'Improving';
  if (value >= 1.5) return 'Maintaining';
  if (value >= 0.5) return 'Minor';
  return 'Minimal';
}

function getTrainingEffectColor(value: number): string {
  if (value >= 4.5) return 'text-red-400';
  if (value >= 3.5) return 'text-green-400';
  if (value >= 2.5) return 'text-teal-400';
  if (value >= 1.5) return 'text-amber-400';
  return 'text-gray-400';
}

function getLoadLabel(value: number): string {
  if (value >= 150) return 'Very High';
  if (value >= 100) return 'High';
  if (value >= 60) return 'Moderate';
  if (value >= 30) return 'Light';
  return 'Very Light';
}

function getLoadColor(value: number): string {
  if (value >= 150) return 'text-red-400';
  if (value >= 100) return 'text-amber-400';
  if (value >= 60) return 'text-teal-400';
  return 'text-gray-400';
}

export default WorkoutScoreBadge;
