'use client';

import { useEffect, useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { AchievementBadge, type Achievement, type AchievementRarity } from './AchievementBadge';

interface AchievementNotificationProps {
  achievement: Achievement;
  onClose: () => void;
  autoClose?: number; // milliseconds, default 5000
  className?: string;
  isFirstAchievement?: boolean; // Triggers extra celebration with full confetti
  isEarlyWin?: boolean; // Early win achievements get special styling
}

const rarityColors: Record<AchievementRarity, { border: string; glow: string; text: string }> = {
  common: {
    border: 'border-gray-600',
    glow: '',
    text: 'text-gray-300',
  },
  rare: {
    border: 'border-blue-500',
    glow: 'shadow-blue-500/30',
    text: 'text-blue-400',
  },
  epic: {
    border: 'border-purple-500',
    glow: 'shadow-purple-500/30',
    text: 'text-purple-400',
  },
  legendary: {
    border: 'border-amber-500',
    glow: 'shadow-amber-500/40',
    text: 'text-amber-400',
  },
};

export function AchievementNotification({
  achievement,
  onClose,
  autoClose = 5000,
  className,
  isFirstAchievement = false,
  isEarlyWin = false,
}: AchievementNotificationProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  const [showFullConfetti, setShowFullConfetti] = useState(false);

  const rarityStyle = rarityColors[achievement.rarity];
  // Show confetti for rare+ OR first achievement OR early win achievements
  const shouldShowConfetti = isFirstAchievement || isEarlyWin ||
    achievement.rarity === 'rare' || achievement.rarity === 'epic' || achievement.rarity === 'legendary';
  // Full screen confetti only for first achievement ever
  const shouldShowFullConfetti = isFirstAchievement;

  const handleClose = useCallback(() => {
    setIsExiting(true);
    setTimeout(() => {
      onClose();
    }, 300);
  }, [onClose]);

  // Animate in on mount
  useEffect(() => {
    const showTimer = setTimeout(() => {
      setIsVisible(true);
      if (shouldShowConfetti) {
        setShowConfetti(true);
      }
      if (shouldShowFullConfetti) {
        setShowFullConfetti(true);
      }
    }, 50);

    return () => clearTimeout(showTimer);
  }, [shouldShowConfetti, shouldShowFullConfetti]);

  // Auto close timer
  useEffect(() => {
    if (autoClose > 0) {
      const closeTimer = setTimeout(() => {
        handleClose();
      }, autoClose);

      return () => clearTimeout(closeTimer);
    }
  }, [autoClose, handleClose]);

  // Hide confetti after animation
  useEffect(() => {
    if (showConfetti) {
      const confettiTimer = setTimeout(() => {
        setShowConfetti(false);
      }, 2000);

      return () => clearTimeout(confettiTimer);
    }
  }, [showConfetti]);

  // Hide full screen confetti after longer animation
  useEffect(() => {
    if (showFullConfetti) {
      const fullConfettiTimer = setTimeout(() => {
        setShowFullConfetti(false);
      }, 4000);

      return () => clearTimeout(fullConfettiTimer);
    }
  }, [showFullConfetti]);

  return (
    <>
      {/* Full screen confetti for first achievement - celebration burst */}
      {showFullConfetti && (
        <div className="fixed inset-0 pointer-events-none z-[100] overflow-hidden">
          {/* Confetti particles across full screen */}
          {Array.from({ length: 100 }).map((_, i) => (
            <div
              key={`full-${i}`}
              className={cn(
                'absolute rounded-full animate-confetti-full',
                i % 6 === 0 && 'bg-amber-400 w-3 h-3',
                i % 6 === 1 && 'bg-purple-400 w-2 h-2',
                i % 6 === 2 && 'bg-blue-400 w-3 h-3',
                i % 6 === 3 && 'bg-green-400 w-2 h-2',
                i % 6 === 4 && 'bg-pink-400 w-2 h-2',
                i % 6 === 5 && 'bg-teal-400 w-3 h-3'
              )}
              style={{
                left: `${Math.random() * 100}%`,
                top: '-10px',
                animationDelay: `${Math.random() * 1.5}s`,
                animationDuration: `${2 + Math.random() * 2}s`,
              }}
            />
          ))}
          {/* Sparkle stars */}
          {Array.from({ length: 30 }).map((_, i) => (
            <div
              key={`star-${i}`}
              className="absolute animate-sparkle text-yellow-300"
              style={{
                left: `${10 + Math.random() * 80}%`,
                top: `${10 + Math.random() * 80}%`,
                animationDelay: `${Math.random() * 2}s`,
                fontSize: `${12 + Math.random() * 16}px`,
              }}
            >
              *
            </div>
          ))}
        </div>
      )}

      <div
        className={cn(
          'fixed top-4 right-4 z-50 max-w-sm',
          'transition-all duration-300 ease-out',
          isVisible && !isExiting
            ? 'translate-x-0 opacity-100'
            : 'translate-x-full opacity-0',
          className
        )}
      >
        {/* Confetti effect for rare+ achievements or early wins */}
        {showConfetti && (
          <div className="absolute inset-0 pointer-events-none overflow-hidden">
            {Array.from({ length: 20 }).map((_, i) => (
              <div
                key={i}
                className={cn(
                  'absolute w-2 h-2 rounded-full animate-confetti',
                  i % 4 === 0 && 'bg-amber-400',
                  i % 4 === 1 && 'bg-purple-400',
                  i % 4 === 2 && 'bg-blue-400',
                  i % 4 === 3 && 'bg-green-400'
                )}
                style={{
                  left: `${Math.random() * 100}%`,
                  animationDelay: `${Math.random() * 0.5}s`,
                  animationDuration: `${1 + Math.random()}s`,
                }}
              />
            ))}
          </div>
        )}

        {/* Notification card */}
        <div
          className={cn(
            'relative bg-gray-900 rounded-xl border-2 shadow-xl overflow-hidden',
            rarityStyle.border,
            shouldShowConfetti && 'shadow-lg',
            shouldShowConfetti && rarityStyle.glow,
            isFirstAchievement && 'border-teal-400 shadow-teal-400/30',
            isEarlyWin && !isFirstAchievement && 'border-green-500 shadow-green-500/20'
          )}
        >
          {/* Header */}
          <div className={cn(
            "flex items-center justify-between px-4 py-2 border-b border-gray-800",
            isFirstAchievement ? 'bg-teal-900/30' : 'bg-gray-800/50'
          )}>
            <span className={cn(
              "text-xs font-medium uppercase tracking-wide",
              isFirstAchievement ? 'text-teal-300' : 'text-teal-400'
            )}>
              {isFirstAchievement ? 'First Achievement Unlocked!' :
               isEarlyWin ? 'Early Win!' : 'Achievement Unlocked!'}
            </span>
            <button
              onClick={handleClose}
              className="text-gray-500 hover:text-gray-300 transition-colors p-1"
              aria-label="Close notification"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="flex items-center gap-4 p-4">
            {/* Badge */}
            <div className={cn(
              "shrink-0",
              isFirstAchievement ? 'animate-bounce-celebrate' : 'animate-bounce-subtle'
            )}>
              <AchievementBadge
                achievement={achievement}
                size="lg"
                showTooltip={false}
              />
            </div>

            {/* Details */}
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-gray-100 truncate">
                {achievement.name}
              </h3>
              <p className="text-sm text-gray-400 line-clamp-2 mt-0.5">
                {achievement.description}
              </p>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-sm font-medium text-teal-400">
                  +{achievement.xp_value} XP
                </span>
                <span className={cn('text-xs font-medium', rarityStyle.text)}>
                  {achievement.rarity.charAt(0).toUpperCase() + achievement.rarity.slice(1)}
                </span>
                {isEarlyWin && (
                  <span className="text-[10px] font-medium text-green-400 bg-green-900/30 px-1.5 py-0.5 rounded">
                    QUICK WIN
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Progress bar for auto-close */}
          {autoClose > 0 && (
            <div className="h-1 bg-gray-800">
              <div
                className={cn(
                  "h-full transition-all ease-linear",
                  isFirstAchievement ? 'bg-teal-400' : 'bg-teal-500'
                )}
                style={{
                  width: '100%',
                  animation: `shrink ${autoClose}ms linear forwards`,
                }}
              />
            </div>
          )}
        </div>

        {/* Inline keyframes for animations */}
        <style jsx>{`
          @keyframes shrink {
            from { width: 100%; }
            to { width: 0%; }
          }
          @keyframes confetti {
            0% {
              transform: translateY(-10px) rotate(0deg);
              opacity: 1;
            }
            100% {
              transform: translateY(200px) rotate(720deg);
              opacity: 0;
            }
          }
          .animate-confetti {
            animation: confetti 1.5s ease-out forwards;
          }
          @keyframes confetti-full {
            0% {
              transform: translateY(0) rotate(0deg);
              opacity: 1;
            }
            100% {
              transform: translateY(100vh) rotate(720deg);
              opacity: 0;
            }
          }
          .animate-confetti-full {
            animation: confetti-full 3s ease-out forwards;
          }
          @keyframes sparkle {
            0%, 100% { opacity: 0; transform: scale(0); }
            50% { opacity: 1; transform: scale(1); }
          }
          .animate-sparkle {
            animation: sparkle 1.5s ease-in-out infinite;
          }
          @keyframes bounce-subtle {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-4px); }
          }
          .animate-bounce-subtle {
            animation: bounce-subtle 0.6s ease-in-out 2;
          }
          @keyframes bounce-celebrate {
            0%, 100% { transform: translateY(0) scale(1); }
            25% { transform: translateY(-8px) scale(1.1); }
            50% { transform: translateY(0) scale(1); }
            75% { transform: translateY(-4px) scale(1.05); }
          }
          .animate-bounce-celebrate {
            animation: bounce-celebrate 1s ease-in-out 3;
          }
        `}</style>
      </div>
    </>
  );
}

// Notification container for multiple achievements
interface AchievementNotificationContainerProps {
  achievements: Achievement[];
  onDismiss: (id: string) => void;
  isFirstAchievement?: boolean; // First achievement in the list gets special treatment
  isEarlyWin?: boolean; // All are early win achievements
}

export function AchievementNotificationContainer({
  achievements,
  onDismiss,
  isFirstAchievement = false,
  isEarlyWin = false,
}: AchievementNotificationContainerProps) {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-3">
      {achievements.map((achievement, index) => (
        <div
          key={achievement.id}
          style={{ marginTop: index > 0 ? '0.75rem' : '0' }}
        >
          <AchievementNotification
            achievement={achievement}
            onClose={() => onDismiss(achievement.id)}
            autoClose={5000 + index * 1000} // Stagger auto-close times
            isFirstAchievement={isFirstAchievement && index === 0} // Only first in list gets full celebration
            isEarlyWin={isEarlyWin}
          />
        </div>
      ))}
    </div>
  );
}

// Early win achievement type for API responses
export interface EarlyAchievementResponse {
  newAchievements: Array<{
    achievement: Achievement;
    unlockedAt: string;
    isNew: boolean;
  }>;
  xpEarned: number;
  levelUp: boolean;
  newLevel: number | null;
  isFirstAchievement: boolean;
  totalAchievementsUnlocked: number;
}

export default AchievementNotification;
