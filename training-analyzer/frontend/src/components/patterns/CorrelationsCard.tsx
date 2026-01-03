'use client';

import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui/Card';
import type { PerformanceCorrelations } from '@/types/patterns';

interface CorrelationsCardProps {
  data?: PerformanceCorrelations | null;
}

export function CorrelationsCard({ data }: CorrelationsCardProps) {
  const t = useTranslations('patterns');

  if (!data || !data.correlations || data.correlations.length === 0) {
    const totalAnalyzed = data?.total_workouts_analyzed ?? 0;
    const dataQuality = data?.data_quality_score ?? 0;

    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">Performance Correlations</h3>
        <div className="text-center py-8 space-y-3">
          <p className="text-gray-400">
            {totalAnalyzed === 0
              ? "Need workouts with HR and pace data to analyze correlations."
              : totalAnalyzed < 10
              ? `Need at least 10 workouts with fitness data. Currently have ${totalAnalyzed}.`
              : "Need more variety in training data (TSB, sleep, rest days) to find correlations."}
          </p>
          <p className="text-xs text-gray-500">
            Tip: Include easy runs, tempo runs, and intervals to build correlation data.
          </p>
        </div>
      </Card>
    );
  }

  // Sort by correlation strength (absolute value)
  const sortedFactors = [...data.correlations].sort(
    (a, b) => Math.abs(b.correlation_coefficient) - Math.abs(a.correlation_coefficient)
  );

  // Get top 5 factors
  const topFactors = sortedFactors.slice(0, 5);

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold text-gray-100 mb-4">Performance Correlations</h3>

      <div className="space-y-3">
        {topFactors.map((factor, index) => {
          const correlation = factor.correlation_coefficient;
          const isPositive = correlation > 0;
          const strength = Math.abs(correlation);
          const strengthLabel = strength >= 0.5 ? 'Strong' : strength >= 0.3 ? 'Moderate' : 'Weak';

          return (
            <div key={index} className="p-3 bg-gray-800/50 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <span className="text-sm font-medium text-gray-200">{factor.factor_name}</span>
                  <span className="text-xs text-gray-500 ml-2">({factor.sample_size} workouts)</span>
                </div>
                <span
                  className={`text-sm font-bold ${
                    isPositive ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {isPositive ? '+' : ''}
                  {(correlation * 100).toFixed(1)}%
                </span>
              </div>
              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    isPositive ? 'bg-green-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${Math.max(strength * 100, 5)}%` }}
                />
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-xs text-gray-500">{strengthLabel} correlation</span>
                {factor.is_significant ? (
                  <span className="text-xs text-teal-400">Statistically significant</span>
                ) : (
                  <span className="text-xs text-gray-500">Not statistically significant</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Interpretation help */}
      <div className="mt-4 p-3 bg-gray-800/30 rounded-lg">
        <p className="text-xs text-gray-500">
          <strong className="text-green-400">Positive</strong> correlation: higher values improve performance.{' '}
          <strong className="text-red-400">Negative</strong>: higher values reduce performance.
          Need 50+ workouts for reliable patterns.
        </p>
      </div>

      {/* Key Insights */}
      {data.key_insights && data.key_insights.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-800">
          <p className="text-sm font-medium text-gray-300 mb-2">Key Insights</p>
          <ul className="space-y-1">
            {data.key_insights.map((insight, index) => (
              <li key={index} className="text-sm text-gray-400 flex items-start gap-2">
                <span className="text-teal-400 mt-1">•</span>
                <span>{insight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

