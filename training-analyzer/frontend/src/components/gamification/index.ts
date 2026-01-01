// Gamification Components
// Achievement and progress tracking UI components

// Badge Components
export {
  AchievementBadge,
  AchievementBadgeSkeleton,
  type Achievement,
  type AchievementRarity,
} from './AchievementBadge';

// Card Components
export { AchievementCard, AchievementCardSkeleton } from './AchievementCard';

// Progress Components
export {
  ProgressBar,
  ProgressBarCompact,
  ProgressBarSkeleton,
  type LevelInfo,
} from './ProgressBar';

// Streak Components
export {
  StreakCounter,
  StreakCounterCompact,
  StreakCounterSkeleton,
  type StreakInfo,
} from './StreakCounter';

// Level Components
export {
  LevelBadge,
  LevelBadgeInline,
  LevelBadgeSkeleton,
} from './LevelBadge';

// Notification Components
export {
  AchievementNotification,
  AchievementNotificationContainer,
} from './AchievementNotification';

// Grid Components
export {
  AchievementGrid,
  AchievementGridCompact,
  type AchievementCategory,
} from './AchievementGrid';

// Feature Gating Components
export {
  LockedFeatureGate,
  LockedFeature,
  isFeatureUnlocked,
  getFeatureRequiredLevel,
  FEATURE_UNLOCK_LEVELS,
} from './LockedFeatureGate';
