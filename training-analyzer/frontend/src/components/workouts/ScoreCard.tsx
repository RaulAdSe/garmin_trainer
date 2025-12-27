'use client';

import { useState } from 'react';
import {
  RadialBarChart,
  RadialBar,
  ResponsiveContainer,
  PolarAngleAxis,
} from 'recharts';
import { clsx } from 'clsx';
import type { WorkoutScore, ScoreColor } from '@/lib/types';
import { SCORE_COLOR_MAP, SCORE_LABEL_MAP } from '@/lib/types';

export interface ScoreCardProps {
  score: WorkoutScore;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

const sizeConfig = {
  sm: {
    container: 'w-24 h-24',
    chart: 100,
    innerRadius: 32,
    outerRadius: 42,
    fontSize: 'text-xl',
    labelSize: 'text-xs',
    nameSize: 'text-xs',
  },
  md: {
    container: 'w-32 h-32',
    chart: 130,
    innerRadius: 42,
    outerRadius: 54,
    fontSize: 'text-2xl',
    labelSize: 'text-xs',
    nameSize: 'text-sm',
  },
  lg: {
    container: 'w-44 h-44',
    chart: 180,
    innerRadius: 60,
    outerRadius: 76,
    fontSize: 'text-4xl',
    labelSize: 'text-sm',
    nameSize: 'text-base',
  },
};

export function ScoreCard({
  score,
  size = 'md',
  showLabel = true,
  className,
}: ScoreCardProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const config = sizeConfig[size];
  const colorConfig = SCORE_COLOR_MAP[score.color];

  // Calculate percentage for the radial bar
  const percentage = Math.min((score.value / score.maxValue) * 100, 100);

  // Chart data - we need a full circle background and the actual value
  const data = [
    {
      name: score.name,
      value: percentage,
      fill: colorConfig.fill,
    },
  ];

  return (
    <div
      className={clsx(
        'relative flex flex-col items-center group',
        className
      )}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {/* Score name above the chart */}
      <div className={clsx('text-gray-400 mb-1 font-medium text-center', config.nameSize)}>
        {score.name}
      </div>

      {/* Radial Chart Container */}
      <div className={clsx('relative', config.container)}>
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius={config.innerRadius}
            outerRadius={config.outerRadius}
            barSize={config.outerRadius - config.innerRadius}
            data={data}
            startAngle={90}
            endAngle={-270}
          >
            {/* Background circle */}
            <PolarAngleAxis
              type="number"
              domain={[0, 100]}
              angleAxisId={0}
              tick={false}
            />
            {/* Gray background track */}
            <RadialBar
              background={{ fill: '#374151' }}
              dataKey="value"
              cornerRadius={10}
              isAnimationActive={true}
              animationDuration={800}
              animationEasing="ease-out"
            />
          </RadialBarChart>
        </ResponsiveContainer>

        {/* Center value display */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={clsx('font-bold', config.fontSize, colorConfig.text)}>
            {Math.round(score.value)}
          </span>
        </div>
      </div>

      {/* Label below the chart */}
      {showLabel && (
        <div
          className={clsx(
            'mt-1 px-2 py-0.5 rounded-full font-medium',
            config.labelSize,
            colorConfig.bg,
            'text-white'
          )}
        >
          {SCORE_LABEL_MAP[score.label]}
        </div>
      )}

      {/* Tooltip on hover */}
      {showTooltip && score.description && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-gray-800 border border-gray-700 rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
          <p className="text-xs text-gray-300 text-center">
            {score.description}
          </p>
          {/* Arrow */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
        </div>
      )}
    </div>
  );
}

// Skeleton loader for ScoreCard
export function ScoreCardSkeleton({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const config = sizeConfig[size];

  return (
    <div className="flex flex-col items-center animate-pulse">
      <div className={clsx('bg-gray-700 rounded h-4 w-20 mb-1', config.nameSize)} />
      <div className={clsx('rounded-full bg-gray-800 border-4 border-gray-700', config.container)} />
      <div className="mt-1 h-5 w-16 bg-gray-700 rounded-full" />
    </div>
  );
}

export default ScoreCard;
