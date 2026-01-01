'use client';

import { useEffect, useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { AchievementBadge, type Achievement, type AchievementRarity } from './AchievementBadge';

interface AchievementNotificationProps {
  achievement: Achievement;
  onClose: () => void;
  autoClose?: number; // milliseconds, default 5000
  className?: string;
}

const rarityColors: Record<AchievementRarity, { border: string; glow: string; text: string }> = {
  common: {
    border: 'border-gray-600',
    glow: '',
    text: 'text-gray-400',
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
}: AchievementNotificationProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);

  const rarityStyle = rarityColors[achievement.rarity];
  const shouldShowConfetti = achievement.rarity === 'rare' || achievement.rarity === 'epic' || achievement.rarity === 'legendary';

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
    }, 50);

    return () => clearTimeout(showTimer);
  }, [shouldShowConfetti]);

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

  return (
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
      {/* Confetti effect for rare+ achievements */}
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
          shouldShowConfetti && rarityStyle.glow
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2 bg-gray-800/50 border-b border-gray-800">
          <span className="text-xs font-medium text-teal-400 uppercase tracking-wide">
            Achievement Unlocked!
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
          <div className="shrink-0 animate-bounce-subtle">
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
            </div>
          </div>
        </div>

        {/* Progress bar for auto-close */}
        {autoClose > 0 && (
          <div className="h-1 bg-gray-800">
            <div
              className="h-full bg-teal-500 transition-all ease-linear"
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
        @keyframes bounce-subtle {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-4px); }
        }
        .animate-bounce-subtle {
          animation: bounce-subtle 0.6s ease-in-out 2;
        }
      `}</style>
    </div>
  );
}

// Notification container for multiple achievements
interface AchievementNotificationContainerProps {
  achievements: Achievement[];
  onDismiss: (id: string) => void;
}

export function AchievementNotificationContainer({
  achievements,
  onDismiss,
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
          />
        </div>
      ))}
    </div>
  );
}

export default AchievementNotification;
