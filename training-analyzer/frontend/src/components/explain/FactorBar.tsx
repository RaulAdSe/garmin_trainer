'use client';

import { useState } from 'react';
import type { ExplanationFactor, ImpactType } from '@/lib/types';
import { DataSourceList } from './DataSourceBadge';

interface FactorBarProps {
  factor: ExplanationFactor;
  maxContribution?: number;
  showDetails?: boolean;
}

// Get color based on impact type
function getImpactColor(impact: ImpactType): {
  bar: string;
  text: string;
  bg: string;
  icon: string;
} {
  switch (impact) {
    case 'positive':
      return {
        bar: 'bg-green-500',
        text: 'text-green-400',
        bg: 'bg-green-500/10',
        icon: '+',
      };
    case 'negative':
      return {
        bar: 'bg-red-500',
        text: 'text-red-400',
        bg: 'bg-red-500/10',
        icon: '-',
      };
    case 'neutral':
    default:
      return {
        bar: 'bg-yellow-500',
        text: 'text-yellow-400',
        bg: 'bg-yellow-500/10',
        icon: '~',
      };
  }
}

// Get impact icon
function ImpactIcon({ impact }: { impact: ImpactType }) {
  const colors = getImpactColor(impact);

  if (impact === 'positive') {
    return (
      <svg className={`w-4 h-4 ${colors.text}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
      </svg>
    );
  } else if (impact === 'negative') {
    return (
      <svg className={`w-4 h-4 ${colors.text}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
      </svg>
    );
  }
  return (
    <svg className={`w-4 h-4 ${colors.text}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
    </svg>
  );
}

export function FactorBar({ factor, maxContribution = 30, showDetails = true }: FactorBarProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const colors = getImpactColor(factor.impact);

  // Calculate bar width as percentage of max contribution
  const barWidth = Math.min(100, Math.max(0, (Math.abs(factor.contribution_points) / maxContribution) * 100));

  return (
    <div className={`rounded-lg border border-gray-700 overflow-hidden ${colors.bg}`}>
      {/* Header row */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-3 flex items-center gap-3 hover:bg-gray-800/50 transition-colors text-left"
      >
        {/* Impact indicator */}
        <ImpactIcon impact={factor.impact} />

        {/* Factor name and value */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-100 text-sm">{factor.name}</span>
            <span className={`text-sm ${colors.text}`}>{factor.display_value}</span>
          </div>

          {/* Progress bar */}
          <div className="mt-1.5 h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full ${colors.bar} transition-all duration-500 ease-out`}
              style={{ width: `${barWidth}%` }}
            />
          </div>
        </div>

        {/* Contribution points */}
        <div className="text-right shrink-0">
          <div className={`text-sm font-mono ${colors.text}`}>
            {factor.contribution_points > 0 ? '+' : ''}
            {factor.contribution_points.toFixed(1)}
          </div>
          <div className="text-xs text-gray-500">
            {(factor.weight * 100).toFixed(0)}% weight
          </div>
        </div>

        {/* Expand indicator */}
        {showDetails && (
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        )}
      </button>

      {/* Expanded details */}
      {showDetails && isExpanded && (
        <div className="px-3 pb-3 border-t border-gray-700/50 pt-3 space-y-3">
          {/* Explanation */}
          <p className="text-sm text-gray-300">{factor.explanation}</p>

          {/* Threshold and baseline */}
          {(factor.threshold || factor.baseline !== undefined) && (
            <div className="flex flex-wrap gap-2 text-xs">
              {factor.threshold && (
                <span className="px-2 py-1 bg-gray-700 rounded text-gray-300">
                  {factor.threshold}
                </span>
              )}
              {factor.baseline !== undefined && factor.baseline !== null && (
                <span className="px-2 py-1 bg-gray-700 rounded text-gray-300">
                  Baseline: {typeof factor.baseline === 'object' ? JSON.stringify(factor.baseline) : String(factor.baseline)}
                </span>
              )}
            </div>
          )}

          {/* Data sources */}
          {factor.data_sources.length > 0 && (
            <div className="pt-2 border-t border-gray-700/50">
              <div className="text-xs text-gray-500 mb-1">Data Sources:</div>
              <DataSourceList sources={factor.data_sources} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface FactorListProps {
  factors: ExplanationFactor[];
  title?: string;
}

export function FactorList({ factors, title }: FactorListProps) {
  if (!factors || factors.length === 0) return null;

  // Find max contribution for scaling bars
  const maxContribution = Math.max(...factors.map(f => Math.abs(f.contribution_points)), 10);

  // Sort by absolute contribution
  const sortedFactors = [...factors].sort(
    (a, b) => Math.abs(b.contribution_points) - Math.abs(a.contribution_points)
  );

  return (
    <div className="space-y-3">
      {title && (
        <h4 className="text-sm font-medium text-gray-300">{title}</h4>
      )}
      <div className="space-y-2">
        {sortedFactors.map((factor, index) => (
          <FactorBar key={`${factor.name}-${index}`} factor={factor} maxContribution={maxContribution} />
        ))}
      </div>
    </div>
  );
}

export default FactorBar;
