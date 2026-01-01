'use client';

import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { Tooltip } from '@/components/ui/Tooltip';
import { useTranslations } from 'next-intl';

// Feature unlock levels mapping (mirrors LEVEL_REWARDS from achievement_service.py)
export const FEATURE_UNLOCK_LEVELS: Record<string, number> = {
  trend_analysis: 3,
  advanced_metrics: 5,
  ai_coach_chat: 8,
  personalized_tips: 8,
  training_plans: 10,
  training_plan_generation: 10,
  race_predictions: 10,
  workout_design: 15,
  custom_workout_design: 15,
  garmin_fit_export: 15,
  periodization: 20,
  periodization_planner: 20,
  peak_optimization: 20,
  coach_mode: 25,
  athlete_management: 25,
  beta_access: 30,
};

/**
 * Check if a feature is unlocked based on current level
 */
export function isFeatureUnlocked(feature: string, level: number): boolean {
  return level >= (FEATURE_UNLOCK_LEVELS[feature] ?? 0);
}

/**
 * Get the required level for a feature
 */
export function getFeatureRequiredLevel(feature: string): number {
  return FEATURE_UNLOCK_LEVELS[feature] ?? 0;
}

/**
 * Calculate XP needed to unlock a feature (approximation based on level progression)
 * Uses the formula: XP = 100 * (level^1.5)
 */
function getXPForLevel(level: number): number {
  return Math.floor(100 * Math.pow(level, 1.5));
}

interface LockedFeatureGateProps {
  feature: string;
  currentLevel: number;
  requiredLevel: number;
  children: React.ReactNode;
  /**
   * Optional: Current XP (used for "almost unlocked" state XP calculation)
   */
  currentXP?: number;
  /**
   * Optional: Timestamp when the feature was unlocked (for "NEW" badge)
   */
  unlockedAt?: string;
  /**
   * Optional: Additional CSS classes for the container
   */
  className?: string;
}

type FeatureState = 'locked' | 'almost_unlocked' | 'unlocked' | 'newly_unlocked';

export function LockedFeatureGate({
  feature,
  currentLevel,
  requiredLevel,
  children,
  currentXP,
  unlockedAt,
  className,
}: LockedFeatureGateProps) {
  const t = useTranslations('achievements.levelRewards');
  const [showCelebration, setShowCelebration] = useState(false);
  const [hasCelebrated, setHasCelebrated] = useState(false);

  // Determine the feature state
  const getFeatureState = (): FeatureState => {
    const isUnlocked = currentLevel >= requiredLevel;

    if (!isUnlocked) {
      // Check if within 1 level of unlocking
      const levelsAway = requiredLevel - currentLevel;
      if (levelsAway === 1) {
        return 'almost_unlocked';
      }
      return 'locked';
    }

    // Check if newly unlocked (within 7 days)
    if (unlockedAt) {
      const unlockDate = new Date(unlockedAt);
      const now = new Date();
      const daysSinceUnlock = Math.floor(
        (now.getTime() - unlockDate.getTime()) / (1000 * 60 * 60 * 24)
      );
      if (daysSinceUnlock <= 7) {
        return 'newly_unlocked';
      }
    }

    return 'unlocked';
  };

  const featureState = getFeatureState();

  // Trigger celebration animation on first unlock
  useEffect(() => {
    if (featureState === 'newly_unlocked' && !hasCelebrated) {
      setShowCelebration(true);
      setHasCelebrated(true);
      const timer = setTimeout(() => setShowCelebration(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [featureState, hasCelebrated]);

  // Calculate XP to unlock for "almost there" message
  const calculateXPToUnlock = (): number => {
    if (currentXP === undefined) return 0;
    const requiredXP = getXPForLevel(requiredLevel);
    return Math.max(0, requiredXP - currentXP);
  };

  // Render unlocked state
  if (featureState === 'unlocked') {
    return <>{children}</>;
  }

  // Render newly unlocked state with NEW badge
  if (featureState === 'newly_unlocked') {
    return (
      <div className={cn('relative', className)}>
        {/* Celebration animation */}
        {showCelebration && (
          <div className="absolute inset-0 z-20 pointer-events-none overflow-hidden rounded-lg">
            <div className="absolute inset-0 animate-celebration-burst bg-gradient-to-r from-amber-500/20 via-yellow-500/30 to-amber-500/20" />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="animate-celebration-scale">
                <span className="text-4xl">🎉</span>
              </div>
            </div>
          </div>
        )}

        {/* NEW badge */}
        <div className="absolute -top-2 -right-2 z-10">
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-gradient-to-r from-amber-500 to-yellow-500 text-white shadow-lg animate-pulse">
            {t('newBadge')}
          </span>
        </div>

        {children}
      </div>
    );
  }

  // Calculate progress for locked states
  const progress = Math.min((currentLevel / requiredLevel) * 100, 99);

  // Render almost unlocked state
  if (featureState === 'almost_unlocked') {
    const xpToUnlock = calculateXPToUnlock();
    const tooltipContent = currentXP !== undefined
      ? t('almostUnlocked', { xp: xpToUnlock })
      : t('lockedFeature', { level: requiredLevel });

    return (
      <Tooltip content={tooltipContent} position="top">
        <div
          className={cn(
            'relative opacity-70 cursor-not-allowed',
            'ring-2 ring-orange-500/50 rounded-lg',
            'almost-unlocked-container',
            className
          )}
        >
          {/* Pulsing glow effect via CSS animation */}
          <style jsx>{`
            .almost-unlocked-container {
              animation: almostUnlockedGlow 2s ease-in-out infinite;
            }
            @keyframes almostUnlockedGlow {
              0%, 100% {
                box-shadow: 0 0 5px 0 rgba(249, 115, 22, 0.3),
                            0 0 10px 0 rgba(249, 115, 22, 0.2);
              }
              50% {
                box-shadow: 0 0 15px 5px rgba(249, 115, 22, 0.4),
                            0 0 25px 10px rgba(249, 115, 22, 0.2);
              }
            }
          `}</style>

          {/* Content with reduced interactivity */}
          <div className="pointer-events-none">
            {children}
          </div>

          {/* Lock overlay */}
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900/40 rounded-lg">
            {/* Pulsing lock icon */}
            <div className="flex items-center gap-2 animate-pulse">
              <LockIcon className="w-6 h-6 text-orange-400" />
              <span className="text-sm font-medium text-orange-400">
                {t('lockedFeature', { level: requiredLevel })}
              </span>
            </div>

            {/* Progress bar */}
            <div className="mt-3 w-3/4 max-w-[200px]">
              <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-orange-500 to-amber-500 rounded-full transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-xs text-gray-500">
                  {t('levelProgress', { current: currentLevel, required: requiredLevel })}
                </span>
              </div>
            </div>
          </div>
        </div>
      </Tooltip>
    );
  }

  // Render locked state
  const tooltipContent = t('lockedFeature', { level: requiredLevel });

  return (
    <Tooltip content={tooltipContent} position="top">
      <div
        className={cn(
          'relative opacity-50 cursor-not-allowed',
          className
        )}
      >
        {/* Content with reduced interactivity */}
        <div className="pointer-events-none grayscale">
          {children}
        </div>

        {/* Lock overlay */}
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-900/60 rounded-lg">
          <LockIcon className="w-8 h-8 text-gray-400" />
          <span className="mt-2 text-sm font-medium text-gray-400">
            {t('lockedFeature', { level: requiredLevel })}
          </span>

          {/* Progress bar */}
          <div className="mt-3 w-3/4 max-w-[200px]">
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-gray-600 to-gray-500 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-xs text-gray-500">
                {t('levelProgress', { current: currentLevel, required: requiredLevel })}
              </span>
            </div>
          </div>
        </div>
      </div>
    </Tooltip>
  );
}

// Lock icon component
function LockIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
      />
    </svg>
  );
}

// Wrapper component that uses the feature name to look up required level
interface LockedFeatureProps {
  feature: keyof typeof FEATURE_UNLOCK_LEVELS;
  currentLevel: number;
  children: React.ReactNode;
  currentXP?: number;
  unlockedAt?: string;
  className?: string;
}

export function LockedFeature({
  feature,
  currentLevel,
  children,
  currentXP,
  unlockedAt,
  className,
}: LockedFeatureProps) {
  const requiredLevel = FEATURE_UNLOCK_LEVELS[feature];

  return (
    <LockedFeatureGate
      feature={feature}
      currentLevel={currentLevel}
      requiredLevel={requiredLevel}
      currentXP={currentXP}
      unlockedAt={unlockedAt}
      className={className}
    >
      {children}
    </LockedFeatureGate>
  );
}

export default LockedFeatureGate;
