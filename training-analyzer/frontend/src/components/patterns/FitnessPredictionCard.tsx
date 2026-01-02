'use client';

import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui/Card';
import type { PatternSummary } from '@/types/patterns';

interface FitnessPredictionCardProps {
  data?: PatternSummary | null;
}

export function FitnessPredictionCard({ data }: FitnessPredictionCardProps) {
  const t = useTranslations('patterns');

  const prediction = data?.fitness_prediction;

  if (!prediction) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">Fitness Predictions</h3>
        <div className="text-center py-8">
          <p className="text-gray-400">{t('noData')}</p>
        </div>
      </Card>
    );
  }

  const peakDate = prediction.natural_peak_date
    ? new Date(prediction.natural_peak_date)
    : null;
  const currentCTL = prediction.current_ctl;
  const projectedCTL = prediction.natural_peak_ctl;

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold text-gray-100 mb-4">Fitness Predictions</h3>

      <div className="space-y-4">
        {/* Current vs Projected CTL */}
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-gray-800/50 rounded-lg">
            <p className="text-sm text-gray-400 mb-1">Current CTL</p>
            <p className="text-2xl font-bold text-gray-200">
              {currentCTL?.toFixed(1) || '--'}
            </p>
          </div>
          <div className="p-4 bg-gray-800/50 rounded-lg">
            <p className="text-sm text-gray-400 mb-1">Peak CTL</p>
            <p className="text-2xl font-bold text-teal-400">
              {projectedCTL?.toFixed(1) || '--'}
            </p>
          </div>
        </div>

        {/* Peak Fitness Date */}
        {peakDate && (
          <div className="p-4 bg-teal-500/10 border border-teal-500/30 rounded-lg">
            <p className="text-sm text-gray-400 mb-1">Peak Fitness Date</p>
            <p className="text-xl font-bold text-teal-400">
              {peakDate.toLocaleDateString('en-US', {
                month: 'long',
                day: 'numeric',
                year: 'numeric',
              })}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Confidence: {(prediction.prediction_confidence * 100).toFixed(0)}%
            </p>
          </div>
        )}

        {/* CTL Projections */}
        {prediction.ctl_projection && prediction.ctl_projection.length > 0 && (
          <div>
            <p className="text-sm font-medium text-gray-300 mb-2">CTL Projections</p>
            <div className="space-y-2">
              {prediction.ctl_projection.slice(0, 5).map((proj, index) => (
                <div key={index} className="flex items-center justify-between p-2 bg-gray-800/50 rounded">
                  <span className="text-sm text-gray-400">
                    {proj.date}
                  </span>
                  <span className="text-sm font-medium text-gray-200">
                    {proj.projected_ctl.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

