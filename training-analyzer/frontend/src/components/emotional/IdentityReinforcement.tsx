'use client';

import React, { useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Sparkles, Heart, Award, CheckCircle } from 'lucide-react';

interface IdentityStatement {
  id: number;
  userId: string;
  statement: string;
  createdAt: string;
  lastReinforcedAt: string;
  reinforcementCount: number;
}

interface IdentityReinforcementProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** The user's identity statement */
  statement: IdentityStatement;
  /** Callback when modal is dismissed */
  onDismiss: () => void;
  /** Callback when user confirms/reinforces */
  onReinforce: () => void;
  /** Loading state for reinforcement action */
  isLoading?: boolean;
}

/**
 * IdentityReinforcement - Weekly reminder modal to reinforce identity commitment
 *
 * Features:
 * - Periodic reminder (weekly) with "Remember: You are someone who..."
 * - Reinforcement counter showing progress
 * - Motivational framing to strengthen commitment
 * - Smooth animations
 */
export function IdentityReinforcement({
  isOpen,
  statement,
  onDismiss,
  onReinforce,
  isLoading = false,
}: IdentityReinforcementProps) {
  const t = useTranslations('identity');

  const handleReinforce = useCallback(() => {
    onReinforce();
  }, [onReinforce]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onDismiss}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="
              fixed inset-x-4 top-1/2 -translate-y-1/2
              sm:inset-x-auto sm:left-1/2 sm:-translate-x-1/2
              sm:max-w-md sm:w-full
              z-50
            "
          >
            <div className="relative overflow-hidden rounded-3xl bg-white dark:bg-gray-900 shadow-2xl">
              {/* Decorative gradient header */}
              <div className="absolute top-0 inset-x-0 h-32 bg-gradient-to-br from-orange-400 via-amber-500 to-yellow-500 opacity-90" />

              {/* Decorative elements */}
              <div className="absolute top-4 left-4">
                <motion.div
                  animate={{
                    scale: [1, 1.2, 1],
                    rotate: [0, 10, -10, 0],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    repeatDelay: 3,
                  }}
                >
                  <Sparkles className="w-6 h-6 text-white/80" />
                </motion.div>
              </div>
              <div className="absolute top-6 right-6">
                <motion.div
                  animate={{
                    scale: [1, 1.1, 1],
                    rotate: [0, -5, 5, 0],
                  }}
                  transition={{
                    duration: 2.5,
                    repeat: Infinity,
                    repeatDelay: 2,
                    delay: 0.5,
                  }}
                >
                  <Heart className="w-5 h-5 text-white/60" />
                </motion.div>
              </div>

              {/* Close button */}
              <button
                onClick={onDismiss}
                className="
                  absolute top-4 right-4 p-2 rounded-full z-10
                  bg-white/20 hover:bg-white/30
                  transition-colors
                "
                aria-label={t('dismiss')}
              >
                <X className="w-4 h-4 text-white" />
              </button>

              {/* Content */}
              <div className="relative pt-20 pb-6 px-6">
                {/* Icon */}
                <div className="absolute top-10 left-1/2 -translate-x-1/2">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.2, type: 'spring' }}
                    className="
                      w-16 h-16 rounded-2xl
                      bg-white dark:bg-gray-800
                      shadow-lg
                      flex items-center justify-center
                    "
                  >
                    <Award className="w-8 h-8 text-orange-500" />
                  </motion.div>
                </div>

                <div className="pt-8 text-center">
                  {/* Title */}
                  <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
                    {t('reinforcement.title')}
                  </h2>

                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                    {t('reinforcement.subtitle')}
                  </p>

                  {/* Statement Card */}
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="
                      p-5 rounded-2xl mb-6
                      bg-gradient-to-br from-orange-50 to-amber-50
                      dark:from-orange-900/30 dark:to-amber-900/30
                      border border-orange-200 dark:border-orange-800
                    "
                  >
                    <p className="text-lg font-medium text-gray-900 dark:text-white">
                      {t('prefix')}{' '}
                      <span className="text-orange-600 dark:text-orange-400 font-semibold">
                        {statement.statement}
                      </span>
                    </p>
                  </motion.div>

                  {/* Reinforcement counter */}
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.4 }}
                    className="flex items-center justify-center gap-2 mb-6"
                  >
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gray-100 dark:bg-gray-800">
                      <CheckCircle className="w-4 h-4 text-green-500" />
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        {t('reinforcement.counter', {
                          count: statement.reinforcementCount,
                        })}
                      </span>
                    </div>
                  </motion.div>

                  {/* Actions */}
                  <div className="space-y-3">
                    <motion.button
                      onClick={handleReinforce}
                      disabled={isLoading}
                      className="
                        w-full py-3.5 px-6 rounded-xl
                        bg-gradient-to-r from-orange-500 to-amber-500
                        hover:from-orange-600 hover:to-amber-600
                        text-white font-semibold
                        shadow-lg shadow-orange-500/30
                        transition-all disabled:opacity-50
                      "
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      {isLoading
                        ? t('reinforcement.confirming')
                        : t('reinforcement.confirm')}
                    </motion.button>

                    <button
                      onClick={onDismiss}
                      disabled={isLoading}
                      className="
                        w-full py-3 px-6 rounded-xl
                        text-gray-600 dark:text-gray-400
                        hover:text-gray-900 dark:hover:text-white
                        hover:bg-gray-100 dark:hover:bg-gray-800
                        transition-colors disabled:opacity-50
                      "
                    >
                      {t('reinforcement.later')}
                    </button>
                  </div>

                  {/* Motivational note */}
                  <p className="mt-4 text-xs text-gray-500 dark:text-gray-400">
                    {t('reinforcement.note')}
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
