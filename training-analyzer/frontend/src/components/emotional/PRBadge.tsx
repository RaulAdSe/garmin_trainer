'use client';

import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import type { PRType } from './PRCelebrationModal';

interface PRBadgeProps {
  prType: PRType;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

/**
 * Get icon and color for each PR type
 */
function getPRTypeConfig(prType: PRType): {
  icon: React.ReactNode;
  bgColor: string;
  textColor: string;
  borderColor: string;
} {
  switch (prType) {
    case 'pace':
      return {
        icon: (
          <svg className="w-full h-full" fill="currentColor" viewBox="0 0 24 24">
            <path d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        ),
        bgColor: 'bg-amber-500/20',
        textColor: 'text-amber-400',
        borderColor: 'border-amber-500/30',
      };
    case 'distance':
      return {
        icon: (
          <svg className="w-full h-full" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l5.447 2.724A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
        ),
        bgColor: 'bg-blue-500/20',
        textColor: 'text-blue-400',
        borderColor: 'border-blue-500/30',
      };
    case 'duration':
      return {
        icon: (
          <svg className="w-full h-full" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        ),
        bgColor: 'bg-purple-500/20',
        textColor: 'text-purple-400',
        borderColor: 'border-purple-500/30',
      };
    case 'elevation':
      return {
        icon: (
          <svg className="w-full h-full" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2L2 22h20L12 2zm0 4l6 12H6l6-12z" />
          </svg>
        ),
        bgColor: 'bg-green-500/20',
        textColor: 'text-green-400',
        borderColor: 'border-green-500/30',
      };
    case 'power':
      return {
        icon: (
          <svg className="w-full h-full" fill="currentColor" viewBox="0 0 24 24">
            <path d="M11 21h-1l1-7H7.5c-.88 0-.33-.75-.31-.78C8.48 10.94 10.42 7.54 13.01 3h1l-1 7h3.51c.4 0 .62.19.4.66C12.97 17.55 11 21 11 21z" />
          </svg>
        ),
        bgColor: 'bg-orange-500/20',
        textColor: 'text-orange-400',
        borderColor: 'border-orange-500/30',
      };
    default:
      return {
        icon: (
          <svg className="w-full h-full" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
          </svg>
        ),
        bgColor: 'bg-gray-500/20',
        textColor: 'text-gray-400',
        borderColor: 'border-gray-500/30',
      };
  }
}

/**
 * Size configurations
 */
const sizeConfig = {
  sm: {
    badge: 'w-6 h-6',
    icon: 'w-3 h-3',
    text: 'text-xs',
    padding: 'px-2 py-1',
  },
  md: {
    badge: 'w-8 h-8',
    icon: 'w-4 h-4',
    text: 'text-sm',
    padding: 'px-3 py-1.5',
  },
  lg: {
    badge: 'w-10 h-10',
    icon: 'w-5 h-5',
    text: 'text-base',
    padding: 'px-4 py-2',
  },
};

/**
 * PRBadge Component
 *
 * A small badge to display on workout cards that have associated personal records.
 * Shows a trophy icon with the PR type indicator.
 */
export function PRBadge({
  prType,
  size = 'md',
  showLabel = false,
  className,
}: PRBadgeProps) {
  const t = useTranslations('personalRecords');
  const config = getPRTypeConfig(prType);
  const sizes = sizeConfig[size];

  if (showLabel) {
    return (
      <div
        className={cn(
          'inline-flex items-center gap-1.5 rounded-full border',
          config.bgColor,
          config.borderColor,
          sizes.padding,
          className
        )}
      >
        {/* Trophy icon */}
        <div className={cn(sizes.icon, config.textColor)}>
          <svg fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
          </svg>
        </div>

        {/* Label */}
        <span className={cn('font-medium', config.textColor, sizes.text)}>
          {t(`badge.${prType}`)}
        </span>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'inline-flex items-center justify-center rounded-full border',
        config.bgColor,
        config.borderColor,
        sizes.badge,
        className
      )}
      title={t(`badge.${prType}`)}
    >
      <div className={cn(sizes.icon, config.textColor)}>
        <svg fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
      </div>
    </div>
  );
}

/**
 * PRBadgeGroup Component
 *
 * Displays multiple PR badges in a compact group format.
 * Used when a workout has multiple PRs.
 */
interface PRBadgeGroupProps {
  prTypes: PRType[];
  size?: 'sm' | 'md' | 'lg';
  maxVisible?: number;
  className?: string;
}

export function PRBadgeGroup({
  prTypes,
  size = 'sm',
  maxVisible = 3,
  className,
}: PRBadgeGroupProps) {
  const t = useTranslations('personalRecords');

  if (prTypes.length === 0) {
    return null;
  }

  const visiblePRs = prTypes.slice(0, maxVisible);
  const remainingCount = prTypes.length - maxVisible;

  return (
    <div className={cn('flex items-center -space-x-1', className)}>
      {visiblePRs.map((prType, index) => (
        <PRBadge
          key={prType}
          prType={prType}
          size={size}
          className={cn(
            'ring-2 ring-gray-900',
            index > 0 && '-ml-2'
          )}
        />
      ))}

      {remainingCount > 0 && (
        <div
          className={cn(
            'inline-flex items-center justify-center rounded-full',
            'bg-amber-500/20 border border-amber-500/30 ring-2 ring-gray-900',
            'text-amber-400 font-medium',
            size === 'sm' && 'w-6 h-6 text-xs',
            size === 'md' && 'w-8 h-8 text-sm',
            size === 'lg' && 'w-10 h-10 text-base'
          )}
          title={t('badge.more', { count: remainingCount })}
        >
          +{remainingCount}
        </div>
      )}
    </div>
  );
}

export default PRBadge;
