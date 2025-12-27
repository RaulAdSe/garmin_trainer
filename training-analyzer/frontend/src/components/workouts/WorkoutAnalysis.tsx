'use client';

import { useMemo, useState } from 'react';
import type { WorkoutAnalysis as WorkoutAnalysisType, Workout } from '@/lib/types';
import { cn } from '@/lib/utils';
import { WorkoutScoreBadge } from './WorkoutScoreBadge';

interface WorkoutAnalysisProps {
  analysis: WorkoutAnalysisType;
  workout?: Workout;
  className?: string;
  isStreaming?: boolean;
}

export function WorkoutAnalysis({
  analysis,
  workout,
  className,
  isStreaming = false,
}: WorkoutAnalysisProps) {
  const [showMore, setShowMore] = useState(false);

  // Calculate overall score (use backend score or derive from execution rating)
  const overallScore = useMemo(() => {
    if (analysis.overallScore) return analysis.overallScore;
    // Fallback: derive from execution rating
    const ratingScores: Record<string, number> = {
      excellent: 92,
      good: 78,
      fair: 55,
      needs_improvement: 35,
    };
    return analysis.executionRating ? ratingScores[analysis.executionRating] || 70 : 70;
  }, [analysis.overallScore, analysis.executionRating]);

  // Build score breakdown for tooltip
  const scoreBreakdown = useMemo(() => ({
    execution: analysis.executionRating || null,
    trainingEffect: analysis.trainingEffectScore ?? workout?.metrics?.trainingEffect ?? null,
    load: analysis.loadScore ?? null,
  }), [analysis, workout]);

  // Build the expanded content
  const hasExpandedContent = useMemo(() => {
    return (
      (analysis.whatWentWell && analysis.whatWentWell.length > 0) ||
      (analysis.improvements && analysis.improvements.length > 0) ||
      (analysis.recommendations && analysis.recommendations.length > 0) ||
      analysis.trainingContext ||
      analysis.trainingFit
    );
  }, [analysis]);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Score + Duration Row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Primary Score Badge with hover breakdown */}
        <WorkoutScoreBadge
          score={overallScore}
          breakdown={scoreBreakdown}
        />

        {/* Duration - simple info */}
        {workout?.duration && (
          <MetricBadge
            label="Duration"
            value={formatDurationShort(workout.duration)}
            sublabel={workout.distance ? `${(workout.distance / 1000).toFixed(1)} km` : undefined}
          />
        )}
      </div>

      {/* Main Summary - Single Paragraph */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
        <p className="text-gray-200 text-sm leading-relaxed">
          {analysis.summary}
          {isStreaming && <span className="inline-block w-2 h-4 ml-1 bg-teal-400 animate-pulse" />}
        </p>
      </div>

      {/* Say More Button */}
      {hasExpandedContent && !isStreaming && (
        <button
          onClick={() => setShowMore(!showMore)}
          className={cn(
            'flex items-center gap-2 text-sm text-teal-400 hover:text-teal-300',
            'transition-colors duration-150'
          )}
        >
          <span>{showMore ? 'Show less' : 'Say more'}</span>
          <ChevronIcon className={cn('w-4 h-4 transition-transform', showMore && 'rotate-180')} />
        </button>
      )}

      {/* Expanded Content */}
      {showMore && (
        <div className="space-y-4 animate-fadeIn">
          {/* What Worked */}
          {analysis.whatWentWell && analysis.whatWentWell.length > 0 && (
            <ExpandedSection title="What Worked" icon="✓" color="green">
              <ul className="space-y-1.5">
                {analysis.whatWentWell.map((item, i) => (
                  <li key={i} className="text-gray-300 text-sm flex items-start gap-2">
                    <span className="text-green-400 mt-0.5">•</span>
                    {item}
                  </li>
                ))}
              </ul>
            </ExpandedSection>
          )}

          {/* Areas to Watch */}
          {analysis.improvements && analysis.improvements.length > 0 && (
            <ExpandedSection title="Watch For" icon="!" color="amber">
              <ul className="space-y-1.5">
                {analysis.improvements.map((item, i) => (
                  <li key={i} className="text-gray-300 text-sm flex items-start gap-2">
                    <span className="text-amber-400 mt-0.5">•</span>
                    {item}
                  </li>
                ))}
              </ul>
            </ExpandedSection>
          )}

          {/* Recommendations */}
          {analysis.recommendations && analysis.recommendations.length > 0 && (
            <ExpandedSection title="Next Steps" icon="→" color="purple">
              <ul className="space-y-1.5">
                {analysis.recommendations.map((item, i) => (
                  <li key={i} className="text-gray-300 text-sm flex items-start gap-2">
                    <span className="text-purple-400 mt-0.5">→</span>
                    {item}
                  </li>
                ))}
              </ul>
            </ExpandedSection>
          )}

          {/* Training Context */}
          {(analysis.trainingContext || analysis.trainingFit) && (
            <ExpandedSection title="Training Context" icon="📊" color="blue">
              <p className="text-gray-300 text-sm">
                {analysis.trainingContext || analysis.trainingFit}
              </p>
            </ExpandedSection>
          )}
        </div>
      )}

      {/* Metadata - compact */}
      <div className="text-xs text-gray-500 pt-2">
        {new Date(analysis.generatedAt || analysis.createdAt || new Date().toISOString()).toLocaleString()}
        {analysis.modelUsed && <span className="ml-2">• {analysis.modelUsed}</span>}
      </div>
    </div>
  );
}

// Simple metric badge (for duration, etc.)
interface MetricBadgeProps {
  label: string;
  value: string | number;
  sublabel?: string;
}

function MetricBadge({ label, value, sublabel }: MetricBadgeProps) {
  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/50 px-3 py-2">
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className="text-lg font-semibold text-gray-100">
        {value}
        {sublabel && <span className="text-xs text-gray-500 ml-1 font-normal">{sublabel}</span>}
      </p>
    </div>
  );
}

// Expanded section wrapper
interface ExpandedSectionProps {
  title: string;
  icon: string;
  color: 'green' | 'amber' | 'purple' | 'blue';
  children: React.ReactNode;
}

function ExpandedSection({ title, icon, color, children }: ExpandedSectionProps) {
  const colorMap = {
    green: 'border-green-800/30 bg-green-900/10',
    amber: 'border-amber-800/30 bg-amber-900/10',
    purple: 'border-purple-800/30 bg-purple-900/10',
    blue: 'border-blue-800/30 bg-blue-900/10',
  };

  const headerColorMap = {
    green: 'text-green-400',
    amber: 'text-amber-400',
    purple: 'text-purple-400',
    blue: 'text-blue-400',
  };

  return (
    <div className={cn('rounded-lg border p-3', colorMap[color])}>
      <h4 className={cn('text-xs font-medium uppercase tracking-wide mb-2', headerColorMap[color])}>
        <span className="mr-1">{icon}</span> {title}
      </h4>
      {children}
    </div>
  );
}

// Helper functions
function formatDurationShort(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-4 h-4', className)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  );
}

// Simplified skeleton
export function WorkoutAnalysisSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {/* Score badges */}
      <div className="flex gap-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="rounded-lg border border-gray-700 bg-gray-800/50 px-3 py-2">
            <div className="h-3 bg-gray-700 rounded w-12 mb-1" />
            <div className="h-5 bg-gray-700 rounded w-16" />
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
        <div className="space-y-2">
          <div className="h-4 bg-gray-700 rounded w-full" />
          <div className="h-4 bg-gray-700 rounded w-5/6" />
          <div className="h-4 bg-gray-700 rounded w-4/6" />
        </div>
      </div>

      {/* Say more button */}
      <div className="h-4 bg-gray-700 rounded w-20" />
    </div>
  );
}

export default WorkoutAnalysis;
