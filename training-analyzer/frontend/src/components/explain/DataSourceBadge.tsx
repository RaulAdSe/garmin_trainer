'use client';

import type { ReactNode } from 'react';
import type { DataSource } from '@/lib/types';

interface DataSourceBadgeProps {
  source: DataSource;
  size?: 'sm' | 'md';
}

// Map source types to colors and icons
const SOURCE_CONFIG: Record<string, { color: string; icon: string }> = {
  garmin_hrv: { color: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400', icon: 'heart' },
  garmin_sleep: { color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400', icon: 'moon' },
  garmin_stress: { color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400', icon: 'activity' },
  garmin_body_battery: { color: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400', icon: 'battery' },
  calculated_tsb: { color: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400', icon: 'calculator' },
  calculated_acwr: { color: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400', icon: 'calculator' },
  calculated_ctl: { color: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400', icon: 'calculator' },
  calculated_atl: { color: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400', icon: 'calculator' },
  activity_history: { color: 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-400', icon: 'list' },
  user_profile: { color: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300', icon: 'user' },
  training_plan: { color: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400', icon: 'calendar' },
};

function getIcon(iconName: string) {
  const icons: Record<string, ReactNode> = {
    heart: (
      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
      </svg>
    ),
    moon: (
      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
      </svg>
    ),
    activity: (
      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    battery: (
      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7h16a1 1 0 011 1v8a1 1 0 01-1 1H4a1 1 0 01-1-1V8a1 1 0 011-1zm16 3h2" />
        <rect x="5" y="9" width="6" height="6" fill="currentColor" opacity="0.5" />
      </svg>
    ),
    calculator: (
      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
      </svg>
    ),
    list: (
      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
      </svg>
    ),
    user: (
      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ),
    calendar: (
      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    ),
  };
  return icons[iconName] || icons.calculator;
}

export function DataSourceBadge({ source, size = 'sm' }: DataSourceBadgeProps) {
  const config = SOURCE_CONFIG[source.source_type] || SOURCE_CONFIG.calculated_tsb;
  const sizeClasses = size === 'sm' ? 'text-xs px-1.5 py-0.5' : 'text-sm px-2 py-1';

  // Format confidence as percentage
  const confidencePercent = Math.round(source.confidence * 100);

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium ${config.color} ${sizeClasses}`}
      title={`${source.source_name} (${confidencePercent}% confidence)${source.last_updated ? ` - Updated: ${source.last_updated}` : ''}`}
    >
      {getIcon(config.icon)}
      <span className="truncate max-w-[100px]">{source.source_name}</span>
      {source.confidence < 1 && (
        <span className="opacity-70">{confidencePercent}%</span>
      )}
    </span>
  );
}

interface DataSourceListProps {
  sources: DataSource[];
  size?: 'sm' | 'md';
}

export function DataSourceList({ sources, size = 'sm' }: DataSourceListProps) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1">
      {sources.map((source, index) => (
        <DataSourceBadge key={`${source.source_type}-${index}`} source={source} size={size} />
      ))}
    </div>
  );
}

export default DataSourceBadge;
