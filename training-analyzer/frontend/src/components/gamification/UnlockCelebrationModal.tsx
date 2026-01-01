'use client';

import { useEffect, useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { LevelBadge } from './LevelBadge';

// Feature information for celebration modal
export interface UnlockableFeature {
  id: string;
  name: string;
  icon: string;
  description: string;
  navigateTo?: string; // Route to navigate to when "Try it now" is clicked
}

// Map feature IDs to their details and navigation routes
export const FEATURE_DETAILS: Record<string, UnlockableFeature> = {
  trend_analysis: {
    id: 'trend_analysis',
    name: 'Trend Analysis',
    icon: '📈',
    description: 'View 7/30/90 day trends for your training metrics',
    navigateTo: '/workouts',
  },
  advanced_metrics: {
    id: 'advanced_metrics',
    name: 'Advanced Metrics',
    icon: '📊',
    description: 'Access TSB charts, fatigue modeling, and more',
    navigateTo: '/',
  },
  ai_coach_chat: {
    id: 'ai_coach_chat',
    name: 'AI Coach Chat',
    icon: '🤖',
    description: 'Chat with your personal AI training coach',
    navigateTo: '/chat',
  },
  personalized_tips: {
    id: 'personalized_tips',
    name: 'Personalized Tips',
    icon: '💡',
    description: 'Receive personalized training recommendations',
    navigateTo: '/',
  },
  training_plan_generation: {
    id: 'training_plan_generation',
    name: 'Training Plan Generation',
    icon: '📋',
    description: 'Generate AI-powered training plans tailored to your goals',
    navigateTo: '/plans',
  },
  race_predictions: {
    id: 'race_predictions',
    name: 'Race Predictions',
    icon: '🏁',
    description: 'Get AI predictions for your race performance',
    navigateTo: '/goals',
  },
  custom_workout_design: {
    id: 'custom_workout_design',
    name: 'Custom Workout Design',
    icon: '🎯',
    description: 'Design custom workouts with interval structure',
    navigateTo: '/design',
  },
  garmin_fit_export: {
    id: 'garmin_fit_export',
    name: 'Garmin FIT Export',
    icon: '⌚',
    description: 'Export workouts to Garmin devices',
    navigateTo: '/design',
  },
  periodization_planner: {
    id: 'periodization_planner',
    name: 'Periodization Planner',
    icon: '🗓️',
    description: 'Plan training phases and periodization cycles',
    navigateTo: '/plans',
  },
  peak_optimization: {
    id: 'peak_optimization',
    name: 'Peak Optimization',
    icon: '⚡',
    description: 'Optimize your training for peak performance',
    navigateTo: '/plans',
  },
  coach_mode: {
    id: 'coach_mode',
    name: 'Coach Mode',
    icon: '👨‍🏫',
    description: 'Manage multiple athletes as a coach',
    navigateTo: '/coach',
  },
  athlete_management: {
    id: 'athlete_management',
    name: 'Athlete Management',
    icon: '👥',
    description: 'Manage your team of athletes',
    navigateTo: '/coach',
  },
  beta_access: {
    id: 'beta_access',
    name: 'Beta Access',
    icon: '🚀',
    description: 'Early access to new features before release',
    navigateTo: '/',
  },
};

// localStorage key for tracking seen unlocks
const SEEN_UNLOCKS_KEY = 'trainer_seen_feature_unlocks';
const UNLOCK_TIMESTAMPS_KEY = 'trainer_feature_unlock_timestamps';

// Helper functions for localStorage
export function getSeenUnlocks(): string[] {
  if (typeof window === 'undefined') return [];
  try {
    const stored = localStorage.getItem(SEEN_UNLOCKS_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

export function markUnlockAsSeen(featureId: string): void {
  if (typeof window === 'undefined') return;
  try {
    const seen = getSeenUnlocks();
    if (!seen.includes(featureId)) {
      seen.push(featureId);
      localStorage.setItem(SEEN_UNLOCKS_KEY, JSON.stringify(seen));
    }
  } catch {
    // Silently fail if localStorage is not available
  }
}

export function getUnlockTimestamp(featureId: string): number | null {
  if (typeof window === 'undefined') return null;
  try {
    const stored = localStorage.getItem(UNLOCK_TIMESTAMPS_KEY);
    const timestamps: Record<string, number> = stored ? JSON.parse(stored) : {};
    return timestamps[featureId] || null;
  } catch {
    return null;
  }
}

export function setUnlockTimestamp(featureId: string): void {
  if (typeof window === 'undefined') return;
  try {
    const stored = localStorage.getItem(UNLOCK_TIMESTAMPS_KEY);
    const timestamps: Record<string, number> = stored ? JSON.parse(stored) : {};
    if (!timestamps[featureId]) {
      timestamps[featureId] = Date.now();
      localStorage.setItem(UNLOCK_TIMESTAMPS_KEY, JSON.stringify(timestamps));
    }
  } catch {
    // Silently fail if localStorage is not available
  }
}

export function isNewlyUnlocked(featureId: string): boolean {
  const timestamp = getUnlockTimestamp(featureId);
  if (!timestamp) return false;
  const sevenDaysMs = 7 * 24 * 60 * 60 * 1000;
  return Date.now() - timestamp < sevenDaysMs;
}

export function hasSeenUnlock(featureId: string): boolean {
  return getSeenUnlocks().includes(featureId);
}

interface UnlockCelebrationModalProps {
  featureId: string;
  levelReached: number;
  onClose: () => void;
  className?: string;
}

export function UnlockCelebrationModal({
  featureId,
  levelReached,
  onClose,
  className,
}: UnlockCelebrationModalProps) {
  const t = useTranslations('achievements.unlockCelebration');
  const tFeatures = useTranslations('achievements.levelRewards.features');
  const router = useRouter();

  const [isVisible, setIsVisible] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  const [isExiting, setIsExiting] = useState(false);

  const feature = FEATURE_DETAILS[featureId];
  const featureName = feature?.name || tFeatures(featureId);

  // Animate in on mount
  useEffect(() => {
    const showTimer = setTimeout(() => {
      setIsVisible(true);
      setShowConfetti(true);
    }, 50);

    return () => clearTimeout(showTimer);
  }, []);

  // Hide confetti after animation
  useEffect(() => {
    if (showConfetti) {
      const confettiTimer = setTimeout(() => {
        setShowConfetti(false);
      }, 3000);

      return () => clearTimeout(confettiTimer);
    }
  }, [showConfetti]);

  // Mark as seen and set timestamp when modal opens
  useEffect(() => {
    markUnlockAsSeen(featureId);
    setUnlockTimestamp(featureId);
  }, [featureId]);

  const handleClose = useCallback(() => {
    setIsExiting(true);
    setTimeout(() => {
      onClose();
    }, 300);
  }, [onClose]);

  const handleTryNow = useCallback(() => {
    setIsExiting(true);
    setTimeout(() => {
      onClose();
      if (feature?.navigateTo) {
        router.push(feature.navigateTo);
      }
    }, 300);
  }, [onClose, router, feature]);

  if (!feature) {
    return null;
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 z-50 bg-black/70 backdrop-blur-sm',
          'transition-opacity duration-300',
          isVisible && !isExiting ? 'opacity-100' : 'opacity-0'
        )}
        onClick={handleClose}
      />

      {/* Modal */}
      <div
        className={cn(
          'fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none'
        )}
      >
        <div
          className={cn(
            'relative bg-gray-900 rounded-2xl border border-gray-800 shadow-2xl',
            'max-w-md w-full pointer-events-auto overflow-hidden',
            'transition-all duration-300 ease-out',
            isVisible && !isExiting
              ? 'scale-100 opacity-100 translate-y-0'
              : 'scale-95 opacity-0 translate-y-4',
            className
          )}
        >
          {/* Confetti effect */}
          {showConfetti && (
            <div className="absolute inset-0 pointer-events-none overflow-hidden">
              {Array.from({ length: 30 }).map((_, i) => (
                <div
                  key={i}
                  className={cn(
                    'absolute w-3 h-3 rounded-full animate-celebration-confetti',
                    i % 5 === 0 && 'bg-amber-400',
                    i % 5 === 1 && 'bg-teal-400',
                    i % 5 === 2 && 'bg-purple-400',
                    i % 5 === 3 && 'bg-blue-400',
                    i % 5 === 4 && 'bg-green-400'
                  )}
                  style={{
                    left: `${Math.random() * 100}%`,
                    animationDelay: `${Math.random() * 0.8}s`,
                    animationDuration: `${1.5 + Math.random() * 1}s`,
                  }}
                />
              ))}
            </div>
          )}

          {/* Glow effect at top */}
          <div className="absolute top-0 left-0 right-0 h-32 bg-gradient-to-b from-teal-500/20 to-transparent pointer-events-none" />

          {/* Close button */}
          <button
            onClick={handleClose}
            className="absolute top-4 right-4 text-gray-500 hover:text-gray-300 transition-colors p-1 z-10"
            aria-label={t('close')}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>

          {/* Content */}
          <div className="relative px-6 pt-8 pb-6 text-center">
            {/* Header with celebration emoji */}
            <div className="mb-4">
              <span className="text-4xl animate-celebration-bounce inline-block">🎉</span>
            </div>

            <h2 className="text-xl font-bold text-white mb-2">
              {t('title')}
            </h2>

            {/* Feature icon and name */}
            <div className="flex flex-col items-center gap-4 my-6">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-teal-500/30 to-teal-600/10 flex items-center justify-center border border-teal-500/30 animate-celebration-glow">
                <span className="text-4xl">{feature.icon}</span>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-teal-400">
                  {featureName}
                </h3>
                <p className="text-sm text-gray-400 mt-1 max-w-xs mx-auto">
                  {feature.description}
                </p>
              </div>
            </div>

            {/* Level badge */}
            <div className="flex items-center justify-center gap-2 mb-6">
              <span className="text-sm text-gray-400">
                {t('levelReached', { level: levelReached })}
              </span>
              <LevelBadge level={levelReached} size="sm" showTooltip={false} />
            </div>

            {/* Action buttons */}
            <div className="flex flex-col sm:flex-row gap-3">
              {feature.navigateTo && (
                <Button
                  variant="primary"
                  onClick={handleTryNow}
                  className="flex-1"
                >
                  {t('tryNow')}
                </Button>
              )}
              <Button
                variant={feature.navigateTo ? 'secondary' : 'primary'}
                onClick={handleClose}
                className="flex-1"
              >
                {t('maybeLater')}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Inline keyframes for animations */}
      <style jsx>{`
        @keyframes celebration-confetti {
          0% {
            transform: translateY(-20px) rotate(0deg) scale(1);
            opacity: 1;
          }
          100% {
            transform: translateY(400px) rotate(1080deg) scale(0.5);
            opacity: 0;
          }
        }
        .animate-celebration-confetti {
          animation: celebration-confetti 2s ease-out forwards;
        }
        @keyframes celebration-bounce {
          0%, 100% { transform: translateY(0) scale(1); }
          25% { transform: translateY(-8px) scale(1.1); }
          50% { transform: translateY(0) scale(1); }
          75% { transform: translateY(-4px) scale(1.05); }
        }
        .animate-celebration-bounce {
          animation: celebration-bounce 1s ease-in-out 2;
        }
        @keyframes celebration-glow {
          0%, 100% { box-shadow: 0 0 20px rgba(20, 184, 166, 0.3); }
          50% { box-shadow: 0 0 40px rgba(20, 184, 166, 0.5); }
        }
        .animate-celebration-glow {
          animation: celebration-glow 2s ease-in-out infinite;
        }
      `}</style>
    </>
  );
}

// NEW badge component for recently unlocked features
interface NewBadgeProps {
  featureId: string;
  className?: string;
}

export function NewBadge({ featureId, className }: NewBadgeProps) {
  const t = useTranslations('achievements.unlockCelebration');
  const [isNew, setIsNew] = useState(false);

  useEffect(() => {
    setIsNew(isNewlyUnlocked(featureId));
  }, [featureId]);

  if (!isNew) {
    return null;
  }

  return (
    <span
      className={cn(
        'inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium',
        'bg-teal-500/20 text-teal-400 border border-teal-500/30',
        'animate-pulse',
        className
      )}
    >
      {t('newBadge')}
    </span>
  );
}

export default UnlockCelebrationModal;
