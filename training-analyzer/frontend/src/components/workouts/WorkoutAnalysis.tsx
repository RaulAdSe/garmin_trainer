'use client';

import { useMemo, useState } from 'react';
import type { WorkoutAnalysis as WorkoutAnalysisType, Workout } from '@/lib/types';
import { cn } from '@/lib/utils';
import { WorkoutScoreBadge } from './WorkoutScoreBadge';
import {
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  ChevronDown,
  Check,
  AlertCircle,
  Lightbulb,
} from 'lucide-react';

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
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    whatWorked: true,
    watchFor: true,
    nextSteps: false,
    context: false,
  });

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

  // Count items for summary
  const counts = useMemo(() => ({
    strengths: analysis.whatWentWell?.length || 0,
    watchFor: analysis.improvements?.length || 0,
    nextSteps: analysis.recommendations?.length || 0,
  }), [analysis]);

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

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

      {/* Say More Button with Summary Stats */}
      {hasExpandedContent && !isStreaming && (
        <button
          onClick={() => setShowMore(!showMore)}
          className={cn(
            'w-full flex items-center justify-between px-3 py-2.5 rounded-lg',
            'bg-gray-800/30 border border-gray-700/50',
            'hover:bg-gray-800/50 hover:border-gray-600/50',
            'transition-all duration-200 group'
          )}
        >
          <div className="flex items-center gap-4">
            <span className="text-sm text-teal-400 font-medium">
              {showMore ? 'Show less' : 'See details'}
            </span>
            {!showMore && (
              <div className="flex items-center gap-3 text-xs text-gray-500">
                {counts.strengths > 0 && (
                  <span className="flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-green-500" />
                    {counts.strengths}
                  </span>
                )}
                {counts.watchFor > 0 && (
                  <span className="flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3 text-amber-500" />
                    {counts.watchFor}
                  </span>
                )}
                {counts.nextSteps > 0 && (
                  <span className="flex items-center gap-1">
                    <Lightbulb className="w-3 h-3 text-purple-500" />
                    {counts.nextSteps}
                  </span>
                )}
              </div>
            )}
          </div>
          <ChevronDown
            className={cn(
              'w-4 h-4 text-gray-400 transition-transform duration-200',
              showMore && 'rotate-180'
            )}
          />
        </button>
      )}

      {/* Expanded Content - Compact Design */}
      {showMore && (
        <div className="space-y-2 animate-fadeIn">
          {/* What Worked */}
          {analysis.whatWentWell && analysis.whatWentWell.length > 0 && (
            <CollapsibleSection
              title="What Worked"
              icon={<CheckCircle2 className="w-4 h-4" />}
              color="green"
              count={analysis.whatWentWell.length}
              isExpanded={expandedSections.whatWorked}
              onToggle={() => toggleSection('whatWorked')}
            >
              <ul className="space-y-1">
                {analysis.whatWentWell.map((item, i) => (
                  <AnalysisItem
                    key={i}
                    item={item}
                    color="green"
                    icon={<Check className="w-3 h-3" />}
                    delay={i * 50}
                  />
                ))}
              </ul>
            </CollapsibleSection>
          )}

          {/* Areas to Watch */}
          {analysis.improvements && analysis.improvements.length > 0 && (
            <CollapsibleSection
              title="Watch For"
              icon={<AlertTriangle className="w-4 h-4" />}
              color="amber"
              count={analysis.improvements.length}
              isExpanded={expandedSections.watchFor}
              onToggle={() => toggleSection('watchFor')}
            >
              <ul className="space-y-1">
                {analysis.improvements.map((item, i) => (
                  <AnalysisItem
                    key={i}
                    item={item}
                    color="amber"
                    icon={<AlertCircle className="w-3 h-3" />}
                    delay={i * 50}
                  />
                ))}
              </ul>
            </CollapsibleSection>
          )}

          {/* Recommendations */}
          {analysis.recommendations && analysis.recommendations.length > 0 && (
            <CollapsibleSection
              title="Next Steps"
              icon={<Lightbulb className="w-4 h-4" />}
              color="purple"
              count={analysis.recommendations.length}
              isExpanded={expandedSections.nextSteps}
              onToggle={() => toggleSection('nextSteps')}
            >
              <ul className="space-y-1">
                {analysis.recommendations.map((item, i) => (
                  <AnalysisItem
                    key={i}
                    item={item}
                    color="purple"
                    icon={<ArrowRight className="w-3 h-3" />}
                    delay={i * 50}
                  />
                ))}
              </ul>
            </CollapsibleSection>
          )}

          {/* Training Context */}
          {(analysis.trainingContext || analysis.trainingFit) && (
            <CollapsibleSection
              title="Training Context"
              icon={<TrendingUp className="w-4 h-4" />}
              color="blue"
              isExpanded={expandedSections.context}
              onToggle={() => toggleSection('context')}
            >
              <p className="text-gray-300 text-sm leading-relaxed pl-1">
                {highlightMetrics(analysis.trainingContext || analysis.trainingFit || '', 'blue')}
              </p>
            </CollapsibleSection>
          )}
        </div>
      )}

      {/* Metadata - compact */}
      <div className="text-xs text-gray-500 pt-1">
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

// Collapsible section with accent border
interface CollapsibleSectionProps {
  title: string;
  icon: React.ReactNode;
  color: 'green' | 'amber' | 'purple' | 'blue';
  count?: number;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

function CollapsibleSection({
  title,
  icon,
  color,
  count,
  isExpanded,
  onToggle,
  children
}: CollapsibleSectionProps) {
  const colorStyles = {
    green: {
      border: 'border-l-green-500',
      icon: 'text-green-400 bg-green-500/20',
      title: 'text-green-400',
      count: 'bg-green-500/20 text-green-400',
    },
    amber: {
      border: 'border-l-amber-500',
      icon: 'text-amber-400 bg-amber-500/20',
      title: 'text-amber-400',
      count: 'bg-amber-500/20 text-amber-400',
    },
    purple: {
      border: 'border-l-purple-500',
      icon: 'text-purple-400 bg-purple-500/20',
      title: 'text-purple-400',
      count: 'bg-purple-500/20 text-purple-400',
    },
    blue: {
      border: 'border-l-blue-500',
      icon: 'text-blue-400 bg-blue-500/20',
      title: 'text-blue-400',
      count: 'bg-blue-500/20 text-blue-400',
    },
  };

  const styles = colorStyles[color];

  return (
    <div
      className={cn(
        'rounded-lg border border-gray-700/50 bg-gray-800/20',
        'border-l-[3px]',
        styles.border,
        'overflow-hidden transition-all duration-200'
      )}
    >
      {/* Header - always visible, clickable */}
      <button
        onClick={onToggle}
        className={cn(
          'w-full flex items-center justify-between px-3 py-2',
          'hover:bg-gray-800/30 transition-colors duration-150'
        )}
      >
        <div className="flex items-center gap-2">
          <div className={cn(
            'w-6 h-6 rounded-md flex items-center justify-center',
            styles.icon
          )}>
            {icon}
          </div>
          <span className={cn('text-sm font-medium', styles.title)}>
            {title}
          </span>
          {count !== undefined && (
            <span className={cn(
              'text-xs px-1.5 py-0.5 rounded-full font-medium',
              styles.count
            )}>
              {count}
            </span>
          )}
        </div>
        <ChevronDown
          className={cn(
            'w-4 h-4 text-gray-500 transition-transform duration-200',
            isExpanded && 'rotate-180'
          )}
        />
      </button>

      {/* Content - collapsible */}
      <div className={cn(
        'overflow-hidden transition-all duration-200',
        isExpanded ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
      )}>
        <div className="px-3 pb-3 pt-1">
          {children}
        </div>
      </div>
    </div>
  );
}

// Individual analysis item
interface AnalysisItemProps {
  item: string;
  color: 'green' | 'amber' | 'purple' | 'blue';
  icon: React.ReactNode;
  delay?: number;
}

// Color style maps for different contexts
const colorStyleMap = {
  green: 'text-green-400 bg-green-500/10',
  amber: 'text-amber-400 bg-amber-500/10',
  purple: 'text-purple-400 bg-purple-500/10',
  blue: 'text-blue-400 bg-blue-500/10',
};

// Shared utility to highlight metrics in text
function highlightMetrics(
  text: string,
  color: 'green' | 'amber' | 'purple' | 'blue'
): React.ReactNode[] {
  // Match patterns:
  // - Numbers with units: "140 bpm", "5%", "14.88 km", "92-minute"
  // - Time formats: "5:42/km", "6:10"
  // - Zones: "Z2", "Z3"
  // - Fractions: "11/15"
  // - CTL/ATL/TSS values: "CTL (12.1)", "ATL (15)", "TSS 85"
  // - CV percentages: "CV 7.1%"
  // - Decimal numbers in parentheses: "(12.1)", "(7.1%)"
  const metricPattern = /((?:CTL|ATL|TSS|CV|HR|HRV)\s*[\(\[]?\d+(?:\.\d+)?[\)\]]?%?|\d+(?:\/\d+)?(?:\.\d+)?(?:\s*(?:bpm|%|km|m|min|sec|hr|h|minutes?))|\d+:\d+(?:\/km)?|Z\d|\(\d+(?:\.\d+)?(?:%|bpm)?\))/gi;

  // Split with capturing group includes matches in the result array
  // Even indices are text, odd indices are matches
  const parts = text.split(metricPattern);

  return parts.map((part, i) => {
    if (!part) return null;

    // Odd indices are the captured matches
    if (i % 2 === 1) {
      return (
        <span
          key={i}
          className={cn(
            'inline-flex items-center px-1 py-0.5 rounded text-xs font-medium mx-0.5',
            colorStyleMap[color]
          )}
        >
          {part}
        </span>
      );
    }

    // Even indices are regular text
    return <span key={i}>{part}</span>;
  }).filter(Boolean);
}

function AnalysisItem({ item, color, icon, delay = 0 }: AnalysisItemProps) {
  return (
    <li
      className={cn(
        'flex items-start gap-2 py-1.5 px-1 rounded-md',
        'hover:bg-gray-800/30 transition-colors duration-150',
        'animate-fadeIn'
      )}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className={cn(
        'w-5 h-5 rounded flex items-center justify-center flex-shrink-0 mt-0.5',
        colorStyleMap[color]
      )}>
        {icon}
      </div>
      <span className="text-gray-300 text-sm leading-relaxed">
        {highlightMetrics(item, color)}
      </span>
    </li>
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

// Simplified skeleton
export function WorkoutAnalysisSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {/* Score badges */}
      <div className="flex gap-3">
        {[1, 2].map((i) => (
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
      <div className="h-10 bg-gray-700/50 rounded-lg w-full" />
    </div>
  );
}

export default WorkoutAnalysis;
