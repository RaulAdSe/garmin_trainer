'use client';

import React, { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Card } from '@/components/ui/Card';
import type { ComebackChallenge } from '@/hooks/useComebackChallenge';

interface ComebackChallengeCardProps {
  challenge: ComebackChallenge;
  onComplete?: () => void;
}

/**
 * Displays the Comeback Challenge card when a user has broken their streak.
 * Shows a 3-day challenge progress with XP multiplier badge and countdown timer.
 */
export function ComebackChallengeCard({
  challenge,
  onComplete,
}: ComebackChallengeCardProps) {
  const t = useTranslations('comebackChallenge');
  const [timeRemaining, setTimeRemaining] = useState<string>('');

  // Calculate time remaining until expiration
  useEffect(() => {
    if (!challenge.expiresAt) return;

    const updateTimeRemaining = () => {
      const now = new Date();
      const expires = new Date(challenge.expiresAt!);
      const diff = expires.getTime() - now.getTime();

      if (diff <= 0) {
        setTimeRemaining(t('expired'));
        return;
      }

      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

      if (days > 0) {
        setTimeRemaining(t('timeRemainingDays', { days, hours }));
      } else if (hours > 0) {
        setTimeRemaining(t('timeRemainingHours', { hours, minutes }));
      } else {
        setTimeRemaining(t('timeRemainingMinutes', { minutes }));
      }
    };

    updateTimeRemaining();
    const interval = setInterval(updateTimeRemaining, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [challenge.expiresAt, t]);

  // Day completion status
  const days = [
    { day: 1, completed: !!challenge.day1CompletedAt },
    { day: 2, completed: !!challenge.day2CompletedAt },
    { day: 3, completed: !!challenge.day3CompletedAt },
  ];

  // Determine the next day to complete
  const nextDay = challenge.nextDayToComplete;

  return (
    <Card className="relative overflow-hidden bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 border-amber-200 dark:border-amber-700">
      {/* XP Multiplier Badge */}
      <div className="absolute top-3 right-3">
        <div className="flex items-center gap-1 px-2 py-1 bg-amber-500 text-white text-xs font-bold rounded-full shadow-md">
          <span className="text-base">1.5x</span>
          <span className="uppercase tracking-wide">XP</span>
        </div>
      </div>

      <div className="p-4 sm:p-6">
        {/* Header */}
        <div className="mb-4">
          <h3 className="text-lg font-bold text-amber-900 dark:text-amber-100">
            {t('title')}
          </h3>
          <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
            {t('subtitle', { streak: challenge.previousStreak })}
          </p>
        </div>

        {/* Motivational Message */}
        <div className="mb-6 p-3 bg-white/50 dark:bg-black/20 rounded-lg">
          <p className="text-sm text-amber-800 dark:text-amber-200 italic">
            &ldquo;{t('motivationalMessage')}&rdquo;
          </p>
        </div>

        {/* 3-Day Progress */}
        <div className="mb-6">
          <div className="flex items-center justify-center gap-4 sm:gap-8">
            {days.map(({ day, completed }) => {
              const isNext = nextDay === day;
              const isCompleted = completed;

              return (
                <div
                  key={day}
                  className="flex flex-col items-center"
                >
                  {/* Day Circle */}
                  <div
                    className={`
                      relative w-14 h-14 sm:w-16 sm:h-16 rounded-full flex items-center justify-center
                      transition-all duration-300
                      ${isCompleted
                        ? 'bg-green-500 text-white shadow-lg shadow-green-500/30'
                        : isNext
                          ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/30 animate-pulse'
                          : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                      }
                    `}
                  >
                    {isCompleted ? (
                      <svg
                        className="w-6 h-6 sm:w-8 sm:h-8"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={3}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    ) : (
                      <span className="text-lg sm:text-xl font-bold">{day}</span>
                    )}
                  </div>

                  {/* Day Label */}
                  <span
                    className={`
                      mt-2 text-xs font-medium
                      ${isCompleted
                        ? 'text-green-600 dark:text-green-400'
                        : isNext
                          ? 'text-amber-600 dark:text-amber-400'
                          : 'text-gray-500 dark:text-gray-400'
                      }
                    `}
                  >
                    {t('day', { day })}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Connecting Lines */}
          <div className="relative -mt-10 sm:-mt-12 mb-4">
            <div className="absolute left-1/2 transform -translate-x-1/2 w-3/5 sm:w-1/2 h-0.5 flex">
              <div
                className={`flex-1 ${
                  challenge.day1CompletedAt
                    ? 'bg-green-500'
                    : 'bg-gray-300 dark:bg-gray-600'
                }`}
              />
              <div
                className={`flex-1 ${
                  challenge.day2CompletedAt
                    ? 'bg-green-500'
                    : 'bg-gray-300 dark:bg-gray-600'
                }`}
              />
            </div>
          </div>
        </div>

        {/* Progress Text */}
        <div className="text-center mb-4">
          <p className="text-sm font-medium text-amber-900 dark:text-amber-100">
            {t('progressText', {
              completed: challenge.daysCompleted,
              total: 3,
            })}
          </p>
        </div>

        {/* Bonus XP Earned */}
        {challenge.bonusXpEarned > 0 && (
          <div className="text-center mb-4">
            <p className="text-xs text-amber-700 dark:text-amber-300">
              {t('bonusXpEarned', { xp: challenge.bonusXpEarned })}
            </p>
          </div>
        )}

        {/* Countdown Timer */}
        {timeRemaining && !challenge.isComplete && (
          <div className="flex items-center justify-center gap-2 text-xs text-amber-600 dark:text-amber-400">
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span>{timeRemaining}</span>
          </div>
        )}

        {/* Call to Action */}
        {!challenge.isComplete && nextDay && (
          <div className="mt-4 text-center">
            <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
              {t('callToAction', { day: nextDay })}
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}

export default ComebackChallengeCard;
