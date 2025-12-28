'use client';

import { useState } from 'react';
import type { ExplainedRecommendation } from '@/lib/types';
import { FactorList } from './FactorBar';

interface ExplainPanelProps {
  recommendation: ExplainedRecommendation;
  title?: string;
  defaultExpanded?: boolean;
  showCalculation?: boolean;
}

export function ExplainPanel({
  recommendation,
  title = 'Why this recommendation?',
  defaultExpanded = false,
  showCalculation = true,
}: ExplainPanelProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [showRawData, setShowRawData] = useState(false);

  // Format confidence as percentage
  const confidencePercent = Math.round(recommendation.confidence * 100);

  // Get confidence color
  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.85) return 'text-green-400';
    if (conf >= 0.70) return 'text-yellow-400';
    return 'text-orange-400';
  };

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg overflow-hidden">
      {/* Collapsible header */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 flex items-center justify-between hover:bg-gray-800 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          {/* Question mark icon */}
          <div className="p-2 bg-teal-500/20 rounded-lg">
            <svg
              className="w-5 h-5 text-teal-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <div>
            <h3 className="font-medium text-gray-100">{title}</h3>
            <p className="text-sm text-gray-400">
              {recommendation.key_driver && `Key driver: ${recommendation.key_driver}`}
            </p>
          </div>
        </div>

        {/* Confidence badge and expand icon */}
        <div className="flex items-center gap-3">
          <span
            className={`text-sm font-medium ${getConfidenceColor(recommendation.confidence)}`}
            title={recommendation.confidence_explanation}
          >
            {confidencePercent}% confident
          </span>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="border-t border-gray-700 p-4 space-y-6">
          {/* Recommendation summary */}
          <div className="bg-gray-900/50 rounded-lg p-3">
            <p className="text-gray-200">{recommendation.recommendation}</p>
            <p className="text-sm text-gray-400 mt-2">{recommendation.confidence_explanation}</p>
          </div>

          {/* Factor breakdown */}
          {recommendation.factors.length > 0 && (
            <FactorList factors={recommendation.factors} title="Contributing Factors" />
          )}

          {/* Alternatives considered */}
          {recommendation.alternatives_considered.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-300">Alternatives Considered</h4>
              <div className="flex flex-wrap gap-2">
                {recommendation.alternatives_considered.map((alt, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-gray-700 rounded-full text-sm text-gray-300"
                  >
                    {alt}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Calculation summary */}
          {showCalculation && recommendation.calculation_summary && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-300">Calculation Details</h4>
              <pre className="bg-gray-900 rounded-lg p-3 text-xs text-gray-400 overflow-x-auto font-mono whitespace-pre-wrap">
                {recommendation.calculation_summary}
              </pre>
            </div>
          )}

          {/* Raw data toggle */}
          <div className="border-t border-gray-700 pt-4">
            <button
              type="button"
              onClick={() => setShowRawData(!showRawData)}
              className="text-sm text-teal-400 hover:text-teal-300 flex items-center gap-2"
            >
              <svg
                className={`w-4 h-4 transition-transform ${showRawData ? 'rotate-90' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
              {showRawData ? 'Hide raw data' : 'Show raw data'}
            </button>

            {showRawData && (
              <pre className="mt-3 bg-gray-900 rounded-lg p-3 text-xs text-gray-400 overflow-x-auto font-mono">
                {JSON.stringify(recommendation.data_points, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Compact "Why?" button that can be added to cards
interface WhyButtonProps {
  onClick: () => void;
  className?: string;
}

export function WhyButton({ onClick, className = '' }: WhyButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-teal-400 hover:text-teal-300 bg-teal-500/10 hover:bg-teal-500/20 rounded-lg transition-colors ${className}`}
      title="See why this recommendation was made"
    >
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      Why?
    </button>
  );
}

export default ExplainPanel;
