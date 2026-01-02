'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';

// Tooltip identifiers
export type TooltipId =
  | 'no_workouts'
  | 'first_workout_synced'
  | 'first_analysis_viewed'
  | 'first_achievement_earned'
  | 'level_up';

// Tooltip trigger conditions
export interface TooltipConditions {
  /** User has no workouts */
  hasNoWorkouts: boolean;
  /** User just synced their first workout */
  justSyncedFirstWorkout: boolean;
  /** User is viewing their first analysis */
  viewingFirstAnalysis: boolean;
  /** User just earned their first achievement */
  justEarnedFirstAchievement: boolean;
  /** User just leveled up */
  justLeveledUp: boolean;
  /** User's current level (for level up tooltip) */
  currentLevel?: number;
  /** Features unlocked at current level */
  unlockedFeatures?: string[];
}

// LocalStorage key for dismissed tooltips
const STORAGE_KEY = 'training_analyzer_onboarding_tooltips';

// Get dismissed tooltips from localStorage
function getDismissedTooltips(): Set<TooltipId> {
  if (typeof window === 'undefined') return new Set();

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return new Set(parsed as TooltipId[]);
    }
  } catch (error) {
    console.error('Error reading dismissed tooltips:', error);
  }
  return new Set();
}

// Save dismissed tooltips to localStorage
function saveDismissedTooltips(dismissed: Set<TooltipId>): void {
  if (typeof window === 'undefined') return;

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(dismissed)));
  } catch (error) {
    console.error('Error saving dismissed tooltips:', error);
  }
}

export interface UseContextualTooltipsResult {
  /** Currently active tooltip (if any) */
  activeTooltip: TooltipId | null;
  /** Whether a specific tooltip has been dismissed */
  isTooltipDismissed: (id: TooltipId) => boolean;
  /** Dismiss a tooltip */
  dismissTooltip: (id: TooltipId) => void;
  /** Trigger a specific tooltip (will show if not already dismissed) */
  triggerTooltip: (id: TooltipId) => void;
  /** Reset all dismissed tooltips (for testing) */
  resetAllTooltips: () => void;
  /** Update conditions that might trigger tooltips */
  updateConditions: (conditions: Partial<TooltipConditions>) => void;
  /** Current conditions */
  conditions: TooltipConditions;
}

export function useContextualTooltips(
  initialConditions?: Partial<TooltipConditions>
): UseContextualTooltipsResult {
  const [dismissedTooltips, setDismissedTooltips] = useState<Set<TooltipId>>(new Set());
  const [activeTooltip, setActiveTooltip] = useState<TooltipId | null>(null);
  const [conditions, setConditions] = useState<TooltipConditions>({
    hasNoWorkouts: false,
    justSyncedFirstWorkout: false,
    viewingFirstAnalysis: false,
    justEarnedFirstAchievement: false,
    justLeveledUp: false,
    currentLevel: undefined,
    unlockedFeatures: undefined,
    ...initialConditions,
  });
  const [isInitialized, setIsInitialized] = useState(false);

  // Load dismissed tooltips from localStorage on mount
  useEffect(() => {
    const dismissed = getDismissedTooltips();
    setDismissedTooltips(dismissed);
    setIsInitialized(true);
  }, []);

  // Check if a tooltip has been dismissed
  const isTooltipDismissed = useCallback(
    (id: TooltipId): boolean => dismissedTooltips.has(id),
    [dismissedTooltips]
  );

  // Dismiss a tooltip
  const dismissTooltip = useCallback((id: TooltipId) => {
    setDismissedTooltips((prev) => {
      const newSet = new Set(prev);
      newSet.add(id);
      saveDismissedTooltips(newSet);
      return newSet;
    });

    // Clear active tooltip if it matches
    setActiveTooltip((current) => (current === id ? null : current));
  }, []);

  // Trigger a specific tooltip
  const triggerTooltip = useCallback(
    (id: TooltipId) => {
      if (!isTooltipDismissed(id)) {
        setActiveTooltip(id);
      }
    },
    [isTooltipDismissed]
  );

  // Reset all dismissed tooltips
  const resetAllTooltips = useCallback(() => {
    setDismissedTooltips(new Set());
    saveDismissedTooltips(new Set());
    setActiveTooltip(null);
  }, []);

  // Update conditions
  const updateConditions = useCallback((newConditions: Partial<TooltipConditions>) => {
    setConditions((prev) => ({ ...prev, ...newConditions }));
  }, []);

  // Determine which tooltip to show based on conditions (priority order)
  useEffect(() => {
    if (!isInitialized) return;

    // Don't change active tooltip if one is already showing
    if (activeTooltip) return;

    // Priority 1: Level up (highest priority - celebration moment)
    if (conditions.justLeveledUp && !isTooltipDismissed('level_up')) {
      setActiveTooltip('level_up');
      return;
    }

    // Priority 2: First achievement earned
    if (conditions.justEarnedFirstAchievement && !isTooltipDismissed('first_achievement_earned')) {
      setActiveTooltip('first_achievement_earned');
      return;
    }

    // Priority 3: First workout synced (readiness explanation)
    if (conditions.justSyncedFirstWorkout && !isTooltipDismissed('first_workout_synced')) {
      setActiveTooltip('first_workout_synced');
      return;
    }

    // Priority 4: First analysis viewed
    if (conditions.viewingFirstAnalysis && !isTooltipDismissed('first_analysis_viewed')) {
      setActiveTooltip('first_analysis_viewed');
      return;
    }

    // Priority 5: No workouts (prompt to connect)
    if (conditions.hasNoWorkouts && !isTooltipDismissed('no_workouts')) {
      setActiveTooltip('no_workouts');
      return;
    }
  }, [conditions, isInitialized, isTooltipDismissed, activeTooltip]);

  return useMemo(
    () => ({
      activeTooltip,
      isTooltipDismissed,
      dismissTooltip,
      triggerTooltip,
      resetAllTooltips,
      updateConditions,
      conditions,
    }),
    [
      activeTooltip,
      isTooltipDismissed,
      dismissTooltip,
      triggerTooltip,
      resetAllTooltips,
      updateConditions,
      conditions,
    ]
  );
}

// Hook for tracking onboarding progress
const ONBOARDING_PROGRESS_KEY = 'training_analyzer_onboarding_progress';

export interface OnboardingProgress {
  hasViewedFirstAnalysis: boolean;
  hasEarnedFirstAchievement: boolean;
  lastSeenLevel: number;
  workoutCountAtFirstSync: number;
}

const defaultProgress: OnboardingProgress = {
  hasViewedFirstAnalysis: false,
  hasEarnedFirstAchievement: false,
  lastSeenLevel: 1,
  workoutCountAtFirstSync: 0,
};

export function useOnboardingProgress() {
  const [progress, setProgress] = useState<OnboardingProgress>(defaultProgress);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load progress from localStorage
  useEffect(() => {
    if (typeof window === 'undefined') return;

    try {
      const stored = localStorage.getItem(ONBOARDING_PROGRESS_KEY);
      if (stored) {
        setProgress(JSON.parse(stored));
      }
    } catch (error) {
      console.error('Error loading onboarding progress:', error);
    }
    setIsLoaded(true);
  }, []);

  // Update progress
  const updateProgress = useCallback((updates: Partial<OnboardingProgress>) => {
    setProgress((prev) => {
      const newProgress = { ...prev, ...updates };

      if (typeof window !== 'undefined') {
        try {
          localStorage.setItem(ONBOARDING_PROGRESS_KEY, JSON.stringify(newProgress));
        } catch (error) {
          console.error('Error saving onboarding progress:', error);
        }
      }

      return newProgress;
    });
  }, []);

  // Reset progress
  const resetProgress = useCallback(() => {
    setProgress(defaultProgress);
    if (typeof window !== 'undefined') {
      localStorage.removeItem(ONBOARDING_PROGRESS_KEY);
    }
  }, []);

  return useMemo(
    () => ({
      progress,
      isLoaded,
      updateProgress,
      resetProgress,
    }),
    [progress, isLoaded, updateProgress, resetProgress]
  );
}

export default useContextualTooltips;
