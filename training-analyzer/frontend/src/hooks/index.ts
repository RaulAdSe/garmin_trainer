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

// Re-export onboarding context hook for convenience
export { useOnboarding } from '@/contexts/onboarding-context';
export type {
  OnboardingStep,
  OnboardingProfile,
  OnboardingState,
  FeatureIntroState,
} from '@/contexts/onboarding-context';
