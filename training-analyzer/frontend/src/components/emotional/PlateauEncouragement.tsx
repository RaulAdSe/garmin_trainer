'use client';

import { useState, useCallback, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { Card } from '@/components/ui/Card';

// Icons
const IconTrendingUp = ({ className }: { className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
  >
    <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
    <polyline points="16 7 22 7 22 13" />
  </svg>
);

const IconMinus = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M5 12h14" />
  </svg>
);

const IconX = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M18 6 6 18" />
    <path d="m6 6 12 12" />
  </svg>
);

const IconSparkle = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
  </svg>
);

interface PlateauHistoryPoint {
  date: string;
  value: number;
  wasPlateauEnd?: boolean;
}

interface PlateauEncouragementProps {
  weeksOnPlateau: number;
  historicalData?: PlateauHistoryPoint[];
  metricName?: string;
  onDismiss?: () => void;
  className?: string;
}

/**
 * Simple mini-chart showing historical plateaus followed by breakthroughs
 */
function PlateauChart({
  data,
  metricName,
}: {
  data: PlateauHistoryPoint[];
  metricName: string;
}) {
  const t = useTranslations();

  // Normalize data for display
  const { normalizedData, minValue, maxValue } = useMemo(() => {
    const values = data.map((d) => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    return {
      normalizedData: data.map((d) => ({
        ...d,
        normalizedValue: ((d.value - min) / range) * 100,
      })),
      minValue: min,
      maxValue: max,
    };
  }, [data]);

  if (normalizedData.length < 2) return null;

  const chartHeight = 60;
  const chartWidth = 200;
  const padding = 4;

  // Create path
  const points = normalizedData.map((d, i) => {
    const x = padding + (i / (normalizedData.length - 1)) * (chartWidth - 2 * padding);
    const y = chartHeight - padding - (d.normalizedValue / 100) * (chartHeight - 2 * padding);
    return { x, y, ...d };
  });

  const pathD = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`)
    .join(' ');

  return (
    <div className="mt-3 p-3 rounded-lg bg-black/20">
      <p className="text-xs text-gray-400 mb-2">
        {t('emotional.plateau.historicalTitle', { metric: metricName })}
      </p>
      <svg
        viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        className="w-full h-16"
        preserveAspectRatio="none"
      >
        {/* Grid lines */}
        <line
          x1={padding}
          y1={chartHeight - padding}
          x2={chartWidth - padding}
          y2={chartHeight - padding}
          stroke="rgba(255,255,255,0.1)"
          strokeWidth="1"
        />

        {/* Line path */}
        <path
          d={pathD}
          fill="none"
          stroke="url(#plateauGradient)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Gradient definition */}
        <defs>
          <linearGradient id="plateauGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="50%" stopColor="#8b5cf6" />
            <stop offset="100%" stopColor="#14b8a6" />
          </linearGradient>
        </defs>

        {/* Highlight breakthrough points */}
        {points
          .filter((p) => p.wasPlateauEnd)
          .map((p, i) => (
            <g key={i}>
              <circle
                cx={p.x}
                cy={p.y}
                r="4"
                fill="#14b8a6"
                className="animate-pulse"
              />
              <circle
                cx={p.x}
                cy={p.y}
                r="6"
                fill="none"
                stroke="#14b8a6"
                strokeWidth="1"
                opacity="0.5"
              />
            </g>
          ))}
      </svg>
      <div className="flex justify-between text-[10px] text-gray-500 mt-1">
        <span>{minValue.toFixed(1)}</span>
        <span className="text-teal-400 flex items-center gap-1">
          <IconSparkle />
          {t('emotional.plateau.breakthroughPoints')}
        </span>
        <span>{maxValue.toFixed(1)}</span>
      </div>
    </div>
  );
}

export function PlateauEncouragement({
  weeksOnPlateau,
  historicalData,
  metricName = 'performance',
  onDismiss,
  className,
}: PlateauEncouragementProps) {
  const t = useTranslations();
  const [isVisible, setIsVisible] = useState(true);
  const [isAnimatingOut, setIsAnimatingOut] = useState(false);

  const handleDismiss = useCallback(() => {
    setIsAnimatingOut(true);
    setTimeout(() => {
      setIsVisible(false);
      onDismiss?.();
    }, 200);
  }, [onDismiss]);

  if (!isVisible) return null;

  // Count historical breakthroughs if data is provided
  const breakthroughCount = historicalData?.filter((d) => d.wasPlateauEnd).length || 0;

  return (
    <Card
      padding="md"
      className={cn(
        'relative overflow-hidden transition-all duration-200',
        'bg-purple-900/20 border border-purple-700/50',
        isAnimatingOut && 'opacity-0 transform translate-y-2',
        'animate-in fade-in slide-in-from-bottom-2 duration-300',
        className
      )}
    >
      {/* Dismiss button */}
      <button
        onClick={handleDismiss}
        className={cn(
          'absolute top-3 right-3 p-1.5 rounded-full',
          'text-gray-400 hover:text-gray-200',
          'hover:bg-white/10 transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-white/20'
        )}
        aria-label={t('common.close')}
      >
        <IconX />
      </button>

      {/* Header */}
      <div className="flex items-start gap-4 mb-3">
        <div
          className={cn(
            'shrink-0 w-12 h-12 rounded-full flex items-center justify-center',
            'bg-purple-800/50 text-purple-300'
          )}
        >
          <IconMinus />
        </div>
        <div className="pr-6">
          <h3 className="font-semibold text-purple-300 mb-1">
            {t('emotional.plateau.title')}
          </h3>
          <p className="text-sm text-gray-300">
            {t('emotional.plateau.precedeBreakthroughs')}
          </p>
        </div>
      </div>

      {/* Duration indicator */}
      <div className="flex items-center gap-2 mb-3 p-2 rounded-lg bg-black/20">
        <span className="text-xs text-gray-400">
          {t('emotional.plateau.duration')}:
        </span>
        <span className="text-sm font-semibold text-purple-300">
          {weeksOnPlateau} {t('common.weeks')}
        </span>
        {weeksOnPlateau >= 4 && (
          <span className="text-xs text-amber-400">
            ({t('emotional.plateau.breakthroughSoon')})
          </span>
        )}
      </div>

      {/* Main message */}
      <div className="mb-3">
        <p className="text-sm text-gray-300 leading-relaxed">
          {t('emotional.plateau.bodyConsolidating')}
        </p>
      </div>

      {/* Historical chart if data available */}
      {historicalData && historicalData.length > 5 && (
        <PlateauChart data={historicalData} metricName={metricName} />
      )}

      {/* Breakthrough stats if available */}
      {breakthroughCount > 0 && (
        <div className="mt-3 p-3 rounded-lg bg-teal-900/20 border border-teal-700/30">
          <div className="flex items-center gap-2">
            <IconTrendingUp className="text-teal-400" />
            <p className="text-xs text-teal-300">
              {t('emotional.plateau.pastBreakthroughs', { count: breakthroughCount })}
            </p>
          </div>
        </div>
      )}

      {/* Suggestions */}
      <div className="mt-4">
        <p className="text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">
          {t('emotional.plateau.suggestions')}
        </p>
        <ul className="space-y-1.5">
          <li className="flex items-start gap-2 text-xs text-gray-400">
            <span className="text-purple-400 mt-0.5">-</span>
            <span>{t('emotional.plateau.suggestion1')}</span>
          </li>
          <li className="flex items-start gap-2 text-xs text-gray-400">
            <span className="text-purple-400 mt-0.5">-</span>
            <span>{t('emotional.plateau.suggestion2')}</span>
          </li>
          <li className="flex items-start gap-2 text-xs text-gray-400">
            <span className="text-purple-400 mt-0.5">-</span>
            <span>{t('emotional.plateau.suggestion3')}</span>
          </li>
        </ul>
      </div>

      {/* Encouragement footer */}
      <p className="mt-4 text-xs text-gray-500 italic text-center">
        {t('emotional.plateau.encouragement')}
      </p>
    </Card>
  );
}

export default PlateauEncouragement;
