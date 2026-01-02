'use client';

import { Link } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { useRecovery, useSleepDebt, useHRVTrend, useRecoveryScore } from '@/hooks/useRecovery';
import { Card } from '@/components/ui/Card';
import { SkeletonCard } from '@/components/ui/Skeleton';
import { RecoveryScoreCard } from '@/components/recovery/RecoveryScoreCard';
import { SleepDebtCard } from '@/components/recovery/SleepDebtCard';
import { HRVTrendChart } from '@/components/recovery/HRVTrendChart';
import { RecoveryRecommendations } from '@/components/recovery/RecoveryRecommendations';

export default function RecoveryPage() {
  const t = useTranslations('recovery');

  const { data: recoveryData, isLoading: isLoadingRecovery } = useRecovery();
  const { data: sleepDebt, isLoading: isLoadingSleepDebt } = useSleepDebt();
  const { data: hrvTrend, isLoading: isLoadingHrvTrend } = useHRVTrend();
  const { data: score, isLoading: isLoadingScore } = useRecoveryScore();

  const isLoading = isLoadingRecovery || isLoadingSleepDebt || isLoadingHrvTrend || isLoadingScore;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/"
          className="p-2 rounded-lg hover:bg-gray-800 transition-colors"
        >
          <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Recovery Dashboard</h1>
          <p className="text-sm text-gray-400 mt-1">
            Track your sleep, HRV, and recovery metrics
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-6">
          <SkeletonCard className="h-32" />
          <SkeletonCard className="h-48" />
          <SkeletonCard className="h-64" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Recovery Score Card */}
          <RecoveryScoreCard score={score} />

          {/* Sleep Debt Visualization */}
          <SleepDebtCard data={sleepDebt} />

          {/* HRV Trend Chart */}
          <HRVTrendChart data={hrvTrend} />

          {/* Recovery Recommendations */}
          <RecoveryRecommendations data={recoveryData} />
        </div>
      )}
    </div>
  );
}

