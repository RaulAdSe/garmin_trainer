/**
 * Dashboard configuration for beginner and full modes.
 *
 * Controls which components are shown based on user preferences
 * and experience level.
 */

export interface DashboardConfig {
  // Core readiness and simple metrics
  showReadinessGauge: boolean;
  showNextWorkoutSuggestion: boolean;
  showQuickActions: boolean;

  // Gamification
  showGamificationHeader: boolean;
  showStreakCounter: boolean;

  // Advanced metrics (hidden in beginner mode)
  showVO2MaxCard: boolean;
  showTrainingBalance: boolean;
  showFitnessMetrics: boolean;
  showRecoveryScore: boolean;
  showPatternInsights: boolean;
  showEconomyCard: boolean;

  // Goals and planning
  showRaceGoals: boolean;

  // Focus mode
  showFocusView: boolean;
}

/**
 * Configuration for beginner mode dashboard.
 * Shows only essential metrics to avoid overwhelming new users.
 */
export const BEGINNER_DASHBOARD_CONFIG: DashboardConfig = {
  // Essential components for beginners
  showReadinessGauge: true,
  showNextWorkoutSuggestion: true,
  showQuickActions: true,

  // Gamification keeps users engaged
  showGamificationHeader: true,
  showStreakCounter: true,

  // Hide advanced metrics
  showVO2MaxCard: false,
  showTrainingBalance: false,
  showFitnessMetrics: false,
  showRecoveryScore: false,
  showPatternInsights: false,
  showEconomyCard: false,

  // Hide complex planning
  showRaceGoals: false,

  // Focus view is great for beginners
  showFocusView: true,
};

/**
 * Configuration for full dashboard mode.
 * Shows all available metrics and features.
 */
export const FULL_DASHBOARD_CONFIG: DashboardConfig = {
  showReadinessGauge: true,
  showNextWorkoutSuggestion: true,
  showQuickActions: true,

  showGamificationHeader: true,
  showStreakCounter: true,

  showVO2MaxCard: true,
  showTrainingBalance: true,
  showFitnessMetrics: true,
  showRecoveryScore: true,
  showPatternInsights: true,
  showEconomyCard: true,

  showRaceGoals: true,

  showFocusView: true,
};

/**
 * Get the appropriate dashboard configuration based on user preferences.
 */
export function getDashboardConfig(isBeginnerMode: boolean): DashboardConfig {
  return isBeginnerMode ? BEGINNER_DASHBOARD_CONFIG : FULL_DASHBOARD_CONFIG;
}

/**
 * Level threshold for auto-enabling beginner mode.
 * Users below this level will have beginner mode suggested/enabled.
 */
export const BEGINNER_MODE_AUTO_ENABLE_LEVEL = 5;

/**
 * Check if beginner mode should be auto-enabled for a user level.
 */
export function shouldAutoEnableBeginnerMode(userLevel: number): boolean {
  return userLevel < BEGINNER_MODE_AUTO_ENABLE_LEVEL;
}
