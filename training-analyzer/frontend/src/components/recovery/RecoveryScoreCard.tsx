'use client';

import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui/Card';
import type { RecoveryScoreResponse, RecoveryStatus } from '@/lib/types';
import { RECOVERY_STATUS_COLORS } from '@/lib/types';

interface RecoveryScoreCardProps {
  score?: RecoveryScoreResponse | null;
}

export function RecoveryScoreCard({ score }: RecoveryScoreCardProps) {
  const t = useTranslations('recovery');

  if (!score?.success || score.recoveryScore === undefined) {
    return (
      <Card className="p-6">
        <div className="text-center py-8">
          <p className="text-gray-400">{score?.error || t('noData')}</p>
        </div>
      </Card>
    );
  }

  const recoveryScore = score.recoveryScore;
  const status = (score.recoveryStatus || 'good') as RecoveryStatus;
  const colors = RECOVERY_STATUS_COLORS[status] || RECOVERY_STATUS_COLORS.good;

  // Calculate percentage for circular progress
  const percentage = Math.round(recoveryScore);

  return (
    <Card className={`p-6 border-2 ${colors.border}`}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-100">Recovery Score</h2>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${colors.bg} ${colors.text}`}>
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </span>
      </div>

      <div className="flex items-center gap-6">
        {/* Circular Progress */}
        <div className="relative w-24 h-24">
          <svg className="w-24 h-24 transform -rotate-90" viewBox="0 0 100 100">
            <circle
              cx="50"
              cy="50"
              r="40"
              stroke="currentColor"
              strokeWidth="8"
              fill="none"
              className="text-gray-800"
            />
            <circle
              cx="50"
              cy="50"
              r="40"
              stroke="currentColor"
              strokeWidth="8"
              fill="none"
              strokeDasharray={`${2 * Math.PI * 40}`}
              strokeDashoffset={`${2 * Math.PI * 40 * (1 - percentage / 100)}`}
              className={colors.text}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={`text-2xl font-bold ${colors.text}`}>{percentage}</span>
          </div>
        </div>

        {/* Details */}
        <div className="flex-1">
          <p className="text-gray-300 mb-2">{score.summaryMessage || t('scoreDescription')}</p>
          {score.hasData === false && (
            <p className="text-sm text-gray-500">{t('connectDevice')}</p>
          )}
        </div>
      </div>
    </Card>
  );
}

