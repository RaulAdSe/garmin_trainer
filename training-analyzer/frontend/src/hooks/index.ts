// Hooks barrel export

export {
  useWorkouts,
  useWorkout,
  useWorkoutAnalysis,
  useInfiniteWorkouts,
  workoutKeys,
} from './useWorkouts';

export {
  useLLMStream,
  useTypingStream,
  useMultiLLMStream,
} from './useLLMStream';

export {
  useAchievements,
  useRecentAchievements,
  useUserProgress,
  useCheckAchievements,
  achievementKeys,
} from './useAchievements';

export {
  useAthleteContext,
  useReadiness,
  useFitnessMetrics,
  useVO2MaxTrend,
} from './useAthleteContext';

export { useDataFreshness } from './useDataFreshness';

export { useTouchChart } from './useTouchChart';

export { usePurpose, type PurposeType, type UserPurpose } from './usePurpose';

export {
  useContextualTooltips,
  useOnboardingProgress,
  type TooltipId,
  type TooltipConditions,
  type OnboardingProgress,
} from './useContextualTooltips';

export {
  useMileageCap,
  useCheckPlannedRun,
  useWeeklyComparison,
  useTenPercentRuleInfo,
  useMileageCapComplete,
  mileageCapKeys,
  type MileageCapData,
  type PlannedRunCheckData,
  type WeeklyComparisonData,
  type TenPercentRuleInfo,
} from './useMileageCap';

export {
  useRunWalkTimer,
  type UseRunWalkTimerOptions,
  type UseRunWalkTimerReturn,
} from './useRunWalkTimer';

// Re-export onboarding context hook for convenience
export { useOnboarding } from '@/contexts/onboarding-context';
export type {
  OnboardingStep,
  OnboardingProfile,
  OnboardingState,
  FeatureIntroState,
} from '@/contexts/onboarding-context';
