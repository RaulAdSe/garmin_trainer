'use client';

import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui/Card';
import type { RecoveryModuleResponse } from '@/lib/types';

interface RecoveryRecommendationsProps {
  data?: RecoveryModuleResponse | null;
}

export function RecoveryRecommendations({ data }: RecoveryRecommendationsProps) {
  const t = useTranslations('recovery');

  if (!data?.success || !data.data) {
    return null;
  }

  const recoveryData = data.data;
  const recommendations = recoveryData.recommendations || [];

  if (recommendations.length === 0) {
    return null;
  }

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold text-gray-100 mb-4">Recovery Recommendations</h3>

      <div className="space-y-3">
        {recommendations.map((rec, index) => (
          <div
            key={index}
            className="flex items-start gap-3 p-3 bg-gray-800/50 rounded-lg"
          >
            <svg
              className="w-5 h-5 text-teal-400 flex-shrink-0 mt-0.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-sm text-gray-300 flex-1">{rec}</p>
          </div>
        ))}
      </div>

      {/* Summary Message */}
      {recoveryData.summaryMessage && (
        <div className="mt-4 p-4 bg-teal-500/10 border border-teal-500/30 rounded-lg">
          <p className="text-sm text-teal-300">{recoveryData.summaryMessage}</p>
        </div>
      )}
    </Card>
  );
}

