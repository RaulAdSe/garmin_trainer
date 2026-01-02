'use client';

import { useEffect, useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/Button';

/**
 * PR Type definitions
 */
export type PRType = 'pace' | 'distance' | 'duration' | 'elevation' | 'power';

/**
 * Celebration data from API when a new PR is detected
 */
export interface PRCelebrationData {
  prType: PRType;
  activityType: string;
  value: number;
  unit: string;
  improvement: number | null;
  improvementPercent: number | null;
  previousValue: number | null;
  workoutName: string | null;
  workoutDate: string | null;
  allPRs?: Array<{
    prType: PRType;
    value: number;
    unit: string;
    improvement: number | null;
  }>;
}

interface PRCelebrationModalProps {
  celebrationData: PRCelebrationData;
  onClose: () => void;
  onShare?: () => void;
  className?: string;
}

/**
 * Format a PR value for display
 */
function formatPRValue(value: number, unit: string, prType: PRType): string {
  if (prType === 'pace') {
    // Convert seconds per km to min:sec format
    const minutes = Math.floor(value / 60);
    const seconds = Math.round(value % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')} /km`;
  }
  if (prType === 'distance') {
    // Convert meters to km
    const km = value / 1000;
    return km >= 1 ? `${km.toFixed(2)} km` : `${value.toFixed(0)} m`;
  }
  if (prType === 'duration') {
    // Convert seconds to readable duration
    const hours = Math.floor(value / 3600);
    const minutes = Math.floor((value % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes} min`;
  }
  if (prType === 'elevation') {
    return `${value.toFixed(0)} m`;
  }
  if (prType === 'power') {
    return `${value.toFixed(0)} W`;
  }
  return `${value} ${unit}`;
}

/**
 * Get icon for PR type
 */
function getPRIcon(prType: PRType): string {
  const icons: Record<PRType, string> = {
    pace: 'bolt',     // Lightning bolt for speed
    distance: 'route', // Route for distance
    duration: 'clock', // Clock for time
    elevation: 'mountain', // Mountain for elevation
    power: 'zap',     // Zap for power
  };
  return icons[prType] || 'trophy';
}

/**
 * PR Celebration Modal Component
 *
 * Displays a celebratory modal when the user achieves a new personal record.
 * Features confetti animation, improvement comparison, and optional share functionality.
 */
export function PRCelebrationModal({
  celebrationData,
  onClose,
  onShare,
  className,
}: PRCelebrationModalProps) {
  const t = useTranslations('personalRecords.celebration');

  const [isVisible, setIsVisible] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  const [isExiting, setIsExiting] = useState(false);

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
      }, 3500);

      return () => clearTimeout(confettiTimer);
    }
  }, [showConfetti]);

  const handleClose = useCallback(() => {
    setIsExiting(true);
    setTimeout(() => {
      onClose();
    }, 300);
  }, [onClose]);

  const handleShare = useCallback(() => {
    if (onShare) {
      onShare();
    }
  }, [onShare]);

  const formattedValue = formatPRValue(
    celebrationData.value,
    celebrationData.unit,
    celebrationData.prType
  );

  const formattedPreviousValue = celebrationData.previousValue
    ? formatPRValue(
        celebrationData.previousValue,
        celebrationData.unit,
        celebrationData.prType
      )
    : null;

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
            'relative bg-gray-900 rounded-2xl border border-amber-500/30 shadow-2xl',
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
              {Array.from({ length: 40 }).map((_, i) => (
                <div
                  key={i}
                  className={cn(
                    'absolute w-3 h-3 animate-pr-confetti',
                    i % 6 === 0 && 'bg-amber-400 rounded-full',
                    i % 6 === 1 && 'bg-amber-500 rounded-full',
                    i % 6 === 2 && 'bg-yellow-400 rounded-full',
                    i % 6 === 3 && 'bg-orange-400 rounded-full',
                    i % 6 === 4 && 'bg-teal-400 rounded-full',
                    i % 6 === 5 && 'bg-white rounded-full'
                  )}
                  style={{
                    left: `${Math.random() * 100}%`,
                    animationDelay: `${Math.random() * 0.8}s`,
                    animationDuration: `${1.8 + Math.random() * 1.2}s`,
                  }}
                />
              ))}
            </div>
          )}

          {/* Golden glow effect at top */}
          <div className="absolute top-0 left-0 right-0 h-40 bg-gradient-to-b from-amber-500/20 to-transparent pointer-events-none" />

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
            {/* Trophy animation */}
            <div className="mb-4">
              <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-amber-400 to-amber-600 rounded-full animate-pr-trophy-bounce shadow-lg shadow-amber-500/30">
                <svg className="w-10 h-10 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 1l2.93 6.18L22 8.24l-5 4.87 1.18 6.89L12 17.27 5.82 20l1.18-6.89-5-4.87 7.07-1.06L12 1z" />
                </svg>
              </div>
            </div>

            {/* Header */}
            <h2 className="text-2xl font-bold text-amber-400 mb-2 animate-pr-pulse">
              {t('title')}
            </h2>

            <p className="text-gray-400 text-sm mb-6">
              {t('subtitle')}
            </p>

            {/* PR Value Display */}
            <div className="bg-gray-800/50 rounded-xl p-6 mb-6 border border-amber-500/20">
              <div className="text-sm text-gray-400 uppercase tracking-wide mb-2">
                {t(`prTypes.${celebrationData.prType}`)}
              </div>
              <div className="text-4xl font-bold text-white mb-2">
                {formattedValue}
              </div>

              {/* Improvement comparison */}
              {celebrationData.improvement !== null && formattedPreviousValue && (
                <div className="flex items-center justify-center gap-2 text-sm">
                  <span className="text-gray-500 line-through">
                    {formattedPreviousValue}
                  </span>
                  <span className="text-green-400 font-medium">
                    {celebrationData.prType === 'pace' ? (
                      // For pace, improvement is how much faster (negative is better)
                      <>-{Math.abs(celebrationData.improvement).toFixed(0)}s</>
                    ) : (
                      // For other types, show percentage improvement
                      celebrationData.improvementPercent !== null && (
                        <>+{celebrationData.improvementPercent.toFixed(1)}%</>
                      )
                    )}
                  </span>
                </div>
              )}
            </div>

            {/* Multiple PRs indicator */}
            {celebrationData.allPRs && celebrationData.allPRs.length > 1 && (
              <div className="mb-6">
                <p className="text-sm text-amber-400">
                  {t('multiplePRs', { count: celebrationData.allPRs.length })}
                </p>
              </div>
            )}

            {/* Workout info */}
            {celebrationData.workoutName && (
              <p className="text-sm text-gray-500 mb-6">
                {celebrationData.workoutName}
                {celebrationData.workoutDate && ` - ${celebrationData.workoutDate}`}
              </p>
            )}

            {/* Action buttons */}
            <div className="flex flex-col sm:flex-row gap-3">
              {onShare && (
                <Button
                  variant="primary"
                  onClick={handleShare}
                  className="flex-1 bg-amber-500 hover:bg-amber-600"
                >
                  {t('share')}
                </Button>
              )}
              <Button
                variant={onShare ? 'secondary' : 'primary'}
                onClick={handleClose}
                className="flex-1"
              >
                {t('celebrate')}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Inline keyframes for animations */}
      <style jsx>{`
        @keyframes pr-confetti {
          0% {
            transform: translateY(-20px) rotate(0deg) scale(1);
            opacity: 1;
          }
          100% {
            transform: translateY(450px) rotate(1440deg) scale(0.3);
            opacity: 0;
          }
        }
        .animate-pr-confetti {
          animation: pr-confetti 2.5s ease-out forwards;
        }
        @keyframes pr-trophy-bounce {
          0%, 100% { transform: translateY(0) scale(1); }
          20% { transform: translateY(-12px) scale(1.1); }
          40% { transform: translateY(0) scale(1); }
          60% { transform: translateY(-6px) scale(1.05); }
          80% { transform: translateY(0) scale(1); }
        }
        .animate-pr-trophy-bounce {
          animation: pr-trophy-bounce 1.5s ease-in-out 2;
        }
        @keyframes pr-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.8; }
        }
        .animate-pr-pulse {
          animation: pr-pulse 2s ease-in-out infinite;
        }
      `}</style>
    </>
  );
}

export default PRCelebrationModal;
