'use client';

import { cn } from '@/lib/utils';
import { Tooltip } from '@/components/ui/Tooltip';

export interface StreakInfo {
  current: number;
  longest: number;
  freeze_tokens: number;
  protected: boolean;
  last_activity_date?: string;
}

interface StreakCounterProps {
  streakInfo: StreakInfo;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  showDetails?: boolean;
}

const sizeConfig = {
  sm: {
    container: 'px-2 py-1',
    fire: 'text-lg',
    count: 'text-lg',
    details: 'text-[10px]',
  },
  md: {
    container: 'px-3 py-2',
    fire: 'text-2xl',
    count: 'text-2xl',
    details: 'text-xs',
  },
  lg: {
    container: 'px-4 py-3',
    fire: 'text-4xl',
    count: 'text-4xl',
    details: 'text-sm',
  },
};

export function StreakCounter({
  streakInfo,
  className,
  size = 'md',
  showDetails = true,
}: StreakCounterProps) {
  const config = sizeConfig[size];
  const isActive = streakInfo.current > 0;
  const isProtected = streakInfo.protected;

  const tooltipContent = (
    <div className="space-y-2 py-1">
      <div className="text-xs text-gray-300 uppercase tracking-wide">Streak Details</div>
      <div className="space-y-1">
        <div className="flex justify-between gap-4 text-xs">
          <span className="text-gray-300">Current Streak</span>
          <span className="text-gray-100 font-medium">{streakInfo.current} days</span>
        </div>
        <div className="flex justify-between gap-4 text-xs">
          <span className="text-gray-300">Longest Streak</span>
          <span className="text-amber-400 font-medium">{streakInfo.longest} days</span>
        </div>
        {streakInfo.freeze_tokens > 0 && (
          <div className="flex justify-between gap-4 text-xs">
            <span className="text-gray-300">Freeze Tokens</span>
            <span className="text-blue-400 font-medium">{streakInfo.freeze_tokens}</span>
          </div>
        )}
        {isProtected && (
          <div className="text-xs text-green-400 mt-1">
            Rest day - streak protected!
          </div>
        )}
      </div>
    </div>
  );

  return (
    <Tooltip content={tooltipContent} position="bottom" delay={100}>
      <div
        className={cn(
          'inline-flex items-center gap-2 rounded-lg',
          'bg-gray-900 border border-gray-800',
          'transition-all duration-200 hover:border-gray-700',
          config.container,
          className
        )}
      >
        {/* Fire emoji with animation */}
        <span
          className={cn(
            config.fire,
            isActive && 'animate-pulse',
            !isActive && 'grayscale opacity-50'
          )}
        >
          {isActive ? '\u{1F525}' : '\u{1F9CA}'}
        </span>

        {/* Streak count */}
        <div className="flex flex-col">
          <div className="flex items-center gap-1">
            <span
              className={cn(
                'font-bold tabular-nums',
                config.count,
                isActive ? 'text-orange-400' : 'text-gray-500'
              )}
            >
              {streakInfo.current}
            </span>

            {/* Protected badge */}
            {isProtected && (
              <span className="px-1.5 py-0.5 text-[9px] font-medium bg-green-900/50 text-green-400 rounded border border-green-700">
                PROTECTED
              </span>
            )}
          </div>

          {/* Details row */}
          {showDetails && (
            <div className="flex items-center gap-2">
              <span className={cn('text-gray-400', config.details)}>
                day streak
              </span>

              {/* Freeze tokens */}
              {streakInfo.freeze_tokens > 0 && (
                <div className="flex items-center gap-0.5">
                  {Array.from({ length: Math.min(streakInfo.freeze_tokens, 3) }).map((_, i) => (
                    <span key={i} className="text-blue-400 text-xs">{'\u2744\uFE0F'}</span>
                  ))}
                  {streakInfo.freeze_tokens > 3 && (
                    <span className="text-blue-400 text-[10px]">+{streakInfo.freeze_tokens - 3}</span>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Longest streak */}
          {showDetails && streakInfo.longest > streakInfo.current && (
            <span className={cn('text-gray-600', config.details)}>
              Best: {streakInfo.longest}
            </span>
          )}
        </div>
      </div>
    </Tooltip>
  );
}

// Compact version for nav/header
interface StreakCounterCompactProps {
  streakInfo: StreakInfo;
  className?: string;
}

export function StreakCounterCompact({ streakInfo, className }: StreakCounterCompactProps) {
  const isActive = streakInfo.current > 0;

  return (
    <Tooltip
      content={`${streakInfo.current} day streak${streakInfo.protected ? ' (protected)' : ''}`}
      position="bottom"
      delay={100}
    >
      <div
        className={cn(
          'inline-flex items-center gap-1 px-2 py-1 rounded',
          'bg-gray-800 hover:bg-gray-700 transition-colors',
          className
        )}
      >
        <span className={cn('text-sm', !isActive && 'grayscale opacity-50')}>
          {isActive ? '\u{1F525}' : '\u{1F9CA}'}
        </span>
        <span
          className={cn(
            'text-sm font-bold tabular-nums',
            isActive ? 'text-orange-400' : 'text-gray-500'
          )}
        >
          {streakInfo.current}
        </span>
        {streakInfo.protected && (
          <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
        )}
      </div>
    </Tooltip>
  );
}

// Skeleton loader
export function StreakCounterSkeleton({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const config = sizeConfig[size];

  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 rounded-lg bg-gray-900 border border-gray-800 animate-pulse',
        config.container
      )}
    >
      <div className="w-8 h-8 rounded bg-gray-800" />
      <div className="space-y-1">
        <div className="h-6 w-12 bg-gray-800 rounded" />
        <div className="h-3 w-16 bg-gray-800 rounded" />
      </div>
    </div>
  );
}

export default StreakCounter;
