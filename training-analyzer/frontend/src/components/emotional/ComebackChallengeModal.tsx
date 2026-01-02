'use client';

import React, { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import type { ComebackChallenge } from '@/hooks/useComebackChallenge';

interface ComebackChallengeModalProps {
  isOpen: boolean;
  onClose: () => void;
  challenge: ComebackChallenge;
  bonusXpEarned: number;
}

/**
 * Celebration modal displayed when a comeback challenge is completed.
 * Shows bonus XP earned and streak restoration confirmation.
 */
export function ComebackChallengeModal({
  isOpen,
  onClose,
  challenge,
  bonusXpEarned,
}: ComebackChallengeModalProps) {
  const t = useTranslations('comebackChallenge');
  const [showConfetti, setShowConfetti] = useState(false);

  // Trigger confetti animation when modal opens
  useEffect(() => {
    if (isOpen) {
      setShowConfetti(true);
      const timer = setTimeout(() => setShowConfetti(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Confetti Effect */}
      {showConfetti && (
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          {[...Array(50)].map((_, i) => (
            <div
              key={i}
              className="absolute animate-confetti"
              style={{
                left: `${Math.random() * 100}%`,
                top: '-10px',
                width: `${Math.random() * 10 + 5}px`,
                height: `${Math.random() * 10 + 5}px`,
                backgroundColor: [
                  '#FFD700',
                  '#FF6B6B',
                  '#4ECDC4',
                  '#45B7D1',
                  '#F7DC6F',
                  '#BB8FCE',
                ][Math.floor(Math.random() * 6)],
                borderRadius: Math.random() > 0.5 ? '50%' : '0%',
                animationDelay: `${Math.random() * 2}s`,
                animationDuration: `${Math.random() * 2 + 2}s`,
              }}
            />
          ))}
        </div>
      )}

      {/* Modal Content */}
      <div className="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-md w-full mx-4 overflow-hidden animate-bounce-in">
        {/* Header with celebration background */}
        <div className="relative bg-gradient-to-br from-amber-400 via-orange-500 to-red-500 p-8 text-center">
          {/* Trophy Icon */}
          <div className="inline-flex items-center justify-center w-20 h-20 bg-white/20 rounded-full mb-4 animate-pulse-slow">
            <svg
              className="w-10 h-10 text-white"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M5 3h14c.6 0 1 .4 1 1v2c0 3.1-2.3 5.8-5.3 6.8.2.6.3 1.4.3 2.2v4h2c.6 0 1 .4 1 1s-.4 1-1 1H7c-.6 0-1-.4-1-1s.4-1 1-1h2v-4c0-.8.1-1.6.3-2.2C6.3 11.8 4 9.1 4 6V4c0-.6.4-1 1-1zm1 2v1c0 2.1 1.5 3.8 3.5 4.3.2-.3.5-.5.8-.7.6-.4 1.4-.6 2.2-.6s1.6.2 2.2.6c.3.2.6.4.8.7 2-.5 3.5-2.2 3.5-4.3V5H6z" />
            </svg>
          </div>

          <h2 className="text-2xl font-bold text-white mb-2">
            {t('modal.title')}
          </h2>
          <p className="text-amber-100 text-sm">
            {t('modal.subtitle')}
          </p>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* XP Earned Section */}
          <div className="text-center mb-6">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              {t('modal.bonusXpLabel')}
            </p>
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-amber-100 dark:bg-amber-900/30 rounded-full">
              <span className="text-3xl font-bold text-amber-600 dark:text-amber-400">
                +{bonusXpEarned}
              </span>
              <span className="text-lg font-semibold text-amber-500 dark:text-amber-300">
                XP
              </span>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                {t('modal.previousStreak')}
              </p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">
                {challenge.previousStreak} {t('modal.days')}
              </p>
            </div>
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                {t('modal.multiplier')}
              </p>
              <p className="text-lg font-bold text-amber-600 dark:text-amber-400">
                {challenge.xpMultiplier}x
              </p>
            </div>
          </div>

          {/* Streak Restored Message */}
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-3">
              <div className="flex-shrink-0">
                <svg
                  className="w-6 h-6 text-green-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <div>
                <p className="font-medium text-green-800 dark:text-green-200">
                  {t('modal.streakRestored')}
                </p>
                <p className="text-sm text-green-600 dark:text-green-400">
                  {t('modal.keepItUp')}
                </p>
              </div>
            </div>
          </div>

          {/* Motivational Quote */}
          <div className="text-center mb-6">
            <p className="text-sm text-gray-600 dark:text-gray-400 italic">
              &ldquo;{t('modal.motivationalQuote')}&rdquo;
            </p>
          </div>

          {/* Close Button */}
          <button
            onClick={onClose}
            className="w-full py-3 px-4 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-semibold rounded-lg transition-all duration-200 shadow-lg shadow-amber-500/30 hover:shadow-amber-500/50"
          >
            {t('modal.continueButton')}
          </button>
        </div>
      </div>

      {/* CSS for animations */}
      <style jsx>{`
        @keyframes confetti {
          0% {
            transform: translateY(0) rotate(0deg);
            opacity: 1;
          }
          100% {
            transform: translateY(100vh) rotate(720deg);
            opacity: 0;
          }
        }

        .animate-confetti {
          animation: confetti linear forwards;
        }

        @keyframes bounce-in {
          0% {
            transform: scale(0.5);
            opacity: 0;
          }
          50% {
            transform: scale(1.05);
          }
          100% {
            transform: scale(1);
            opacity: 1;
          }
        }

        .animate-bounce-in {
          animation: bounce-in 0.5s ease-out forwards;
        }

        @keyframes pulse-slow {
          0%, 100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.8;
            transform: scale(1.05);
          }
        }

        .animate-pulse-slow {
          animation: pulse-slow 2s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}

export default ComebackChallengeModal;
