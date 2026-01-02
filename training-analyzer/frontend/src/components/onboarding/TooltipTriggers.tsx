'use client';

import { useEffect, useRef, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { ContextualTooltip, type TooltipPosition } from './ContextualTooltip';
import {
  useContextualTooltips,
  useOnboardingProgress,
  type TooltipId,
} from '@/hooks/useContextualTooltips';

// Tooltip content configuration
interface TooltipConfig {
  id: TooltipId;
  title: string;
  content: string;
  dismissText?: string;
  position?: TooltipPosition;
  targetSelector?: string;
  action?: {
    text: string;
    href?: string;
    onClick?: () => void;
  };
}

interface TooltipTriggersProps {
  /** Whether the user has no workouts */
  hasNoWorkouts?: boolean;
  /** Number of workouts the user has */
  workoutCount?: number;
  /** User's current level */
  currentLevel?: number;
  /** Number of achievements earned */
  achievementCount?: number;
  /** Whether user is viewing an analysis */
  isViewingAnalysis?: boolean;
  /** Features unlocked at the current level */
  unlockedFeatures?: string[];
  /** Custom target refs for specific tooltips */
  targetRefs?: {
    readinessGauge?: React.RefObject<HTMLElement>;
    connectButton?: React.RefObject<HTMLElement>;
    xpCounter?: React.RefObject<HTMLElement>;
    achievementBadge?: React.RefObject<HTMLElement>;
    levelBadge?: React.RefObject<HTMLElement>;
  };
}

export function TooltipTriggers({
  hasNoWorkouts = false,
  workoutCount = 0,
  currentLevel = 1,
  achievementCount = 0,
  isViewingAnalysis = false,
  unlockedFeatures = [],
  targetRefs = {},
}: TooltipTriggersProps) {
  const t = useTranslations('onboarding');
  const router = useRouter();
  const { progress, updateProgress, isLoaded } = useOnboardingProgress();

  const {
    activeTooltip,
    dismissTooltip,
    updateConditions,
  } = useContextualTooltips();

  // Track previous values to detect changes
  const prevWorkoutCount = useRef(workoutCount);
  const prevAchievementCount = useRef(achievementCount);
  const prevLevel = useRef(currentLevel);

  // Update conditions based on props
  useEffect(() => {
    if (!isLoaded) return;

    const justSyncedFirstWorkout =
      workoutCount > 0 &&
      prevWorkoutCount.current === 0 &&
      progress.workoutCountAtFirstSync === 0;

    const justEarnedFirstAchievement =
      achievementCount > 0 &&
      prevAchievementCount.current === 0 &&
      !progress.hasEarnedFirstAchievement;

    const justLeveledUp =
      currentLevel > prevLevel.current && currentLevel > progress.lastSeenLevel;

    const viewingFirstAnalysis =
      isViewingAnalysis && !progress.hasViewedFirstAnalysis;

    updateConditions({
      hasNoWorkouts,
      justSyncedFirstWorkout,
      viewingFirstAnalysis,
      justEarnedFirstAchievement,
      justLeveledUp,
      currentLevel,
      unlockedFeatures,
    });

    // Update refs for next comparison
    prevWorkoutCount.current = workoutCount;
    prevAchievementCount.current = achievementCount;
    prevLevel.current = currentLevel;

    // Update progress when milestones are reached
    if (justSyncedFirstWorkout) {
      updateProgress({ workoutCountAtFirstSync: workoutCount });
    }
    if (justEarnedFirstAchievement) {
      updateProgress({ hasEarnedFirstAchievement: true });
    }
    if (justLeveledUp) {
      updateProgress({ lastSeenLevel: currentLevel });
    }
    if (viewingFirstAnalysis) {
      updateProgress({ hasViewedFirstAnalysis: true });
    }
  }, [
    hasNoWorkouts,
    workoutCount,
    currentLevel,
    achievementCount,
    isViewingAnalysis,
    unlockedFeatures,
    isLoaded,
    progress,
    updateConditions,
    updateProgress,
  ]);

  // Build tooltip configurations with translations
  const tooltipConfigs: TooltipConfig[] = useMemo(
    () => [
      {
        id: 'no_workouts' as TooltipId,
        title: t('noWorkouts.title'),
        content: t('noWorkouts.content'),
        dismissText: t('common.gotIt'),
        position: 'bottom' as TooltipPosition,
        targetSelector: '[data-onboarding="connect-button"]',
        action: {
          text: t('noWorkouts.action'),
          href: '/connect',
        },
      },
      {
        id: 'first_workout_synced' as TooltipId,
        title: t('firstWorkoutSynced.title'),
        content: t('firstWorkoutSynced.content'),
        dismissText: t('common.gotIt'),
        position: 'bottom' as TooltipPosition,
        targetSelector: '[data-onboarding="readiness-gauge"]',
      },
      {
        id: 'first_analysis_viewed' as TooltipId,
        title: t('firstAnalysisViewed.title'),
        content: t('firstAnalysisViewed.content'),
        dismissText: t('common.gotIt'),
        position: 'top' as TooltipPosition,
        targetSelector: '[data-onboarding="xp-counter"]',
      },
      {
        id: 'first_achievement_earned' as TooltipId,
        title: t('firstAchievementEarned.title'),
        content: t('firstAchievementEarned.content'),
        dismissText: t('common.awesome'),
        position: 'left' as TooltipPosition,
        targetSelector: '[data-onboarding="achievement-badge"]',
        action: {
          text: t('firstAchievementEarned.action'),
          href: '/achievements',
        },
      },
      {
        id: 'level_up' as TooltipId,
        title: t('levelUp.title', { level: currentLevel }),
        content: t('levelUp.content', {
          features: unlockedFeatures.length > 0 ? unlockedFeatures.join(', ') : t('levelUp.noNewFeatures'),
        }),
        dismissText: t('common.gotIt'),
        position: 'bottom' as TooltipPosition,
        targetSelector: '[data-onboarding="level-badge"]',
        action: {
          text: t('levelUp.action'),
          href: '/achievements',
        },
      },
    ],
    [t, currentLevel, unlockedFeatures]
  );

  // Get active tooltip config
  const activeConfig = useMemo(
    () => tooltipConfigs.find((config) => config.id === activeTooltip),
    [tooltipConfigs, activeTooltip]
  );

  // Handle action click
  const handleAction = (config: TooltipConfig) => {
    if (config.action?.href) {
      router.push(config.action.href);
    } else if (config.action?.onClick) {
      config.action.onClick();
    }
  };

  // Don't render if no active tooltip
  if (!activeConfig) {
    return null;
  }

  // Get the target ref for the active tooltip
  const getTargetRef = () => {
    switch (activeConfig.id) {
      case 'first_workout_synced':
        return targetRefs.readinessGauge;
      case 'no_workouts':
        return targetRefs.connectButton;
      case 'first_analysis_viewed':
        return targetRefs.xpCounter;
      case 'first_achievement_earned':
        return targetRefs.achievementBadge;
      case 'level_up':
        return targetRefs.levelBadge;
      default:
        return undefined;
    }
  };

  return (
    <ContextualTooltip
      id={activeConfig.id}
      title={activeConfig.title}
      content={activeConfig.content}
      position={activeConfig.position}
      isVisible={true}
      onDismiss={() => dismissTooltip(activeConfig.id)}
      targetRef={getTargetRef()}
      targetSelector={activeConfig.targetSelector}
      dismissText={activeConfig.dismissText}
      action={
        activeConfig.action
          ? {
              text: activeConfig.action.text,
              onClick: () => handleAction(activeConfig),
            }
          : undefined
      }
    />
  );
}

// Provider component that wraps pages to enable onboarding tooltips
interface OnboardingProviderProps {
  children: React.ReactNode;
  /** Props for tooltip triggers */
  triggerProps?: TooltipTriggersProps;
}

export function OnboardingProvider({
  children,
  triggerProps = {},
}: OnboardingProviderProps) {
  return (
    <>
      {children}
      <TooltipTriggers {...triggerProps} />
    </>
  );
}

export default TooltipTriggers;
