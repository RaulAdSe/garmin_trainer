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

export {
  useDataFreshness,
  type DataFreshnessState,
  type FreshnessStatus,
} from './useDataFreshness';

export { useTouchChart } from './useTouchChart';

export {
  useChartComparison,
  useQuickSelectionLabel,
  comparisonKeys,
} from './useChartComparison';
export type { UseChartComparisonOptions, UseChartComparisonReturn } from './useChartComparison';

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

export {
  useSocialProof,
  useInvalidateSocialProof,
  socialProofKeys,
} from './useSocialProof';

export {
  useIdentity,
  useIdentityStatement,
  useIdentityTemplates,
  useCreateIdentityStatement,
  useReinforceIdentity,
  useReinforcementCheck,
  useDeleteIdentityStatement,
  identityKeys,
  type IdentityStatement,
  type IdentityTemplate,
  type ReinforcementCheck,
} from './useIdentity';

export {
  useEmotionalMessage,
  useEmotionalMessageAPI,
  useDetectEmotionalContext,
  useAvailableContexts,
  useRecoveryMessage,
  emotionalMessageKeys,
  type EmotionalMessageResponse,
  type DetectedContextResponse,
  type DismissedMessage,
} from './useEmotionalMessage';

export {
  usePRHistory,
  useRecentPRs,
  usePRSummary,
  useCompareToPRs,
  useDetectPRs,
  usePRCelebration,
  useAutoDetectPRs,
  prKeys,
} from './usePRDetection';

export {
  useComebackChallenge,
  useRecordComebackWorkout,
  useTriggerComebackChallenge,
  useComebackChallengeHistory,
  useCancelComebackChallenge,
  comebackChallengeKeys,
  type ComebackChallenge,
  type RecordWorkoutResponse,
  type ChallengeHistoryResponse,
} from './useComebackChallenge';

export {
  useAvailableStrategies,
  useGeneratePacingPlan,
  useCalculateWeatherAdjustment,
  useQuickPacingPlan,
  formatPace,
  formatTime,
  parseTimeString,
  getTimeComponents,
  racePacingKeys,
  type PacingPlan,
  type GeneratePacingPlanRequest,
  type WeatherAdjustment,
  type WeatherAdjustmentRequest,
  type AvailableStrategiesResponse,
} from './useRacePacing';

export {
  useSafetyAlerts,
  useLoadAnalysis,
  useActiveAlerts,
  useCriticalAlerts,
  safetyKeys,
  type UseSafetyAlertsOptions,
  type UseSafetyAlertsReturn,
  type UseLoadAnalysisReturn,
} from './useSafetyAlerts';

// Re-export onboarding context hook for convenience
export { useOnboarding } from '@/contexts/onboarding-context';
export type {
  OnboardingStep,
  OnboardingProfile,
  OnboardingState,
  FeatureIntroState,
} from '@/contexts/onboarding-context';
