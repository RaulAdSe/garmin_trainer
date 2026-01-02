'use client';

import { Link } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { usePatternSummary, useTimingAnalysis, useTSBOptimalRange } from '@/hooks/usePatterns';
import { SkeletonCard } from '@/components/ui/Skeleton';
import { TimingAnalysisCard } from '@/components/patterns/TimingAnalysisCard';
import { TSBOptimalRangeCard } from '@/components/patterns/TSBOptimalRangeCard';
import { CorrelationsCard } from '@/components/patterns/CorrelationsCard';
import { FitnessPredictionCard } from '@/components/patterns/FitnessPredictionCard';

export default function PatternsPage() {
  const t = useTranslations('patterns');

  const { data: summary, isLoading: isLoadingSummary } = usePatternSummary(90);
  const { data: timing, isLoading: isLoadingTiming } = useTimingAnalysis(90);
  const { data: tsbOptimal, isLoading: isLoadingTSB } = useTSBOptimalRange(180);

  const isLoading = isLoadingSummary || isLoadingTiming || isLoadingTSB;

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
          <h1 className="text-2xl font-bold text-gray-100">Training Patterns & Insights</h1>
          <p className="text-sm text-gray-400 mt-1">
            Discover optimal training times and performance patterns
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-6">
          <SkeletonCard className="h-48" />
          <SkeletonCard className="h-64" />
          <SkeletonCard className="h-48" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Timing Analysis */}
          <TimingAnalysisCard data={timing} />

          {/* Optimal TSB Range */}
          <TSBOptimalRangeCard data={tsbOptimal} />

          {/* Performance Correlations */}
          <CorrelationsCard data={summary?.performance_correlations} />

          {/* Fitness Predictions */}
          <FitnessPredictionCard data={summary} />
        </div>
      )}
    </div>
  );
}

