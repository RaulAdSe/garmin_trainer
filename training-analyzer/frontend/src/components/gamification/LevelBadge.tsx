'use client';

import { cn } from '@/lib/utils';
import { Tooltip } from '@/components/ui/Tooltip';

interface LevelBadgeProps {
  level: number;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  showTooltip?: boolean;
  title?: string;
}

const sizeConfig = {
  sm: {
    container: 'w-8 h-8',
    text: 'text-xs',
    ring: 'ring-2',
  },
  md: {
    container: 'w-10 h-10',
    text: 'text-sm',
    ring: 'ring-2',
  },
  lg: {
    container: 'w-14 h-14',
    text: 'text-lg',
    ring: 'ring-3',
  },
};

// Tier colors based on level ranges
function getTierColors(level: number): {
  bg: string;
  text: string;
  ring: string;
  glow: string;
  tierName: string;
} {
  if (level >= 20) {
    return {
      bg: 'bg-gradient-to-br from-amber-500 to-yellow-600',
      text: 'text-amber-900',
      ring: 'ring-amber-400',
      glow: 'shadow-amber-400/50',
      tierName: 'Legendary',
    };
  }
  if (level >= 15) {
    return {
      bg: 'bg-gradient-to-br from-purple-500 to-purple-700',
      text: 'text-white',
      ring: 'ring-purple-400',
      glow: 'shadow-purple-400/40',
      tierName: 'Epic',
    };
  }
  if (level >= 10) {
    return {
      bg: 'bg-gradient-to-br from-blue-500 to-blue-700',
      text: 'text-white',
      ring: 'ring-blue-400',
      glow: 'shadow-blue-400/40',
      tierName: 'Advanced',
    };
  }
  if (level >= 5) {
    return {
      bg: 'bg-gradient-to-br from-teal-500 to-teal-700',
      text: 'text-white',
      ring: 'ring-teal-400',
      glow: 'shadow-teal-400/40',
      tierName: 'Intermediate',
    };
  }
  return {
    bg: 'bg-gradient-to-br from-gray-500 to-gray-700',
    text: 'text-white',
    ring: 'ring-gray-400',
    glow: 'shadow-gray-400/30',
    tierName: 'Beginner',
  };
}

export function LevelBadge({
  level,
  size = 'md',
  className,
  showTooltip = true,
  title,
}: LevelBadgeProps) {
  const config = sizeConfig[size];
  const tierColors = getTierColors(level);

  const badge = (
    <div
      className={cn(
        'relative inline-flex items-center justify-center rounded-full',
        'font-bold shadow-lg transition-transform duration-200 hover:scale-105',
        config.container,
        config.text,
        config.ring,
        tierColors.bg,
        tierColors.text,
        tierColors.ring,
        tierColors.glow,
        className
      )}
    >
      {level}

      {/* Shine effect for higher tiers */}
      {level >= 10 && (
        <div className="absolute inset-0 rounded-full overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/20 to-transparent" />
        </div>
      )}
    </div>
  );

  if (!showTooltip) {
    return badge;
  }

  const tooltipContent = (
    <div className="text-center">
      <div className="font-medium text-gray-100">Level {level}</div>
      {title && <div className="text-xs text-gray-400">{title}</div>}
      <div className={cn('text-xs mt-1', getTierTextColor(level))}>
        {tierColors.tierName} Tier
      </div>
    </div>
  );

  return (
    <Tooltip content={tooltipContent} position="top" delay={100}>
      {badge}
    </Tooltip>
  );
}

// Helper function for tooltip tier text color
function getTierTextColor(level: number): string {
  if (level >= 20) return 'text-amber-400';
  if (level >= 15) return 'text-purple-400';
  if (level >= 10) return 'text-blue-400';
  if (level >= 5) return 'text-teal-400';
  return 'text-gray-400';
}

// Inline level display (for headers, nav, etc.)
interface LevelBadgeInlineProps {
  level: number;
  title?: string;
  className?: string;
}

export function LevelBadgeInline({ level, title, className }: LevelBadgeInlineProps) {
  const tierColors = getTierColors(level);

  return (
    <div className={cn('inline-flex items-center gap-2', className)}>
      <LevelBadge level={level} size="sm" showTooltip={false} />
      {title && (
        <span className={cn('text-sm font-medium', getTierTextColor(level))}>
          {title}
        </span>
      )}
    </div>
  );
}

// Skeleton loader
export function LevelBadgeSkeleton({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const config = sizeConfig[size];

  return (
    <div
      className={cn(
        'rounded-full bg-gray-800 animate-pulse',
        config.container
      )}
    />
  );
}

export default LevelBadge;
