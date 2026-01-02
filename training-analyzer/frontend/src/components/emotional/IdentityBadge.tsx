'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import { motion } from 'framer-motion';
import { Edit2, Sparkles, Award } from 'lucide-react';

interface IdentityStatement {
  id: number;
  userId: string;
  statement: string;
  createdAt: string;
  lastReinforcedAt: string;
  reinforcementCount: number;
}

interface IdentityBadgeProps {
  /** The user's identity statement */
  statement: IdentityStatement;
  /** Callback when edit button is clicked */
  onEdit?: () => void;
  /** Show in compact mode (for dashboard) */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * IdentityBadge - Displays the user's identity commitment statement
 *
 * Features:
 * - Shows "I am someone who..." with the statement
 * - Subtle animation on hover
 * - Edit button for settings
 * - Reinforcement count indicator
 */
export function IdentityBadge({
  statement,
  onEdit,
  compact = false,
  className = '',
}: IdentityBadgeProps) {
  const t = useTranslations('identity');

  if (compact) {
    return (
      <motion.div
        className={`
          relative group p-3 rounded-xl
          bg-gradient-to-br from-orange-50 to-amber-50
          dark:from-orange-900/20 dark:to-amber-900/20
          border border-orange-200 dark:border-orange-800/50
          ${className}
        `}
        whileHover={{ scale: 1.02 }}
        transition={{ duration: 0.2 }}
      >
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-orange-500 flex-shrink-0" />
          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
            {t('prefix')}{' '}
            <span className="text-orange-600 dark:text-orange-400">
              {statement.statement}
            </span>
          </p>
        </div>
        {onEdit && (
          <button
            onClick={onEdit}
            className="
              absolute right-2 top-1/2 -translate-y-1/2
              p-1.5 rounded-lg opacity-0 group-hover:opacity-100
              hover:bg-orange-100 dark:hover:bg-orange-900/40
              transition-all duration-200
            "
            aria-label={t('edit')}
          >
            <Edit2 className="w-3.5 h-3.5 text-orange-600 dark:text-orange-400" />
          </button>
        )}
      </motion.div>
    );
  }

  return (
    <motion.div
      className={`
        relative group overflow-hidden rounded-2xl
        bg-gradient-to-br from-orange-50 via-amber-50 to-yellow-50
        dark:from-orange-900/20 dark:via-amber-900/20 dark:to-yellow-900/20
        border border-orange-200 dark:border-orange-800/50
        ${className}
      `}
      whileHover={{ scale: 1.01 }}
      transition={{ duration: 0.2 }}
    >
      {/* Decorative background element */}
      <div className="absolute inset-0 opacity-20">
        <div className="absolute -right-8 -top-8 w-32 h-32 rounded-full bg-orange-300 dark:bg-orange-500 blur-3xl" />
        <div className="absolute -left-8 -bottom-8 w-24 h-24 rounded-full bg-amber-300 dark:bg-amber-500 blur-3xl" />
      </div>

      <div className="relative p-5">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-orange-100 dark:bg-orange-900/40">
              <Sparkles className="w-4 h-4 text-orange-600 dark:text-orange-400" />
            </div>
            <span className="text-xs font-semibold text-orange-600 dark:text-orange-400 uppercase tracking-wider">
              {t('myIdentity')}
            </span>
          </div>
          {onEdit && (
            <motion.button
              onClick={onEdit}
              className="
                p-2 rounded-lg opacity-0 group-hover:opacity-100
                hover:bg-orange-100 dark:hover:bg-orange-900/40
                transition-all duration-200
              "
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              aria-label={t('edit')}
            >
              <Edit2 className="w-4 h-4 text-orange-600 dark:text-orange-400" />
            </motion.button>
          )}
        </div>

        {/* Statement */}
        <p className="text-lg font-medium text-gray-900 dark:text-white leading-relaxed">
          {t('prefix')}{' '}
          <span className="text-orange-600 dark:text-orange-400 font-semibold">
            {statement.statement}
          </span>
        </p>

        {/* Reinforcement indicator */}
        {statement.reinforcementCount > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 flex items-center gap-2"
          >
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-orange-100 dark:bg-orange-900/40">
              <Award className="w-3.5 h-3.5 text-orange-600 dark:text-orange-400" />
              <span className="text-xs font-medium text-orange-700 dark:text-orange-300">
                {t('reinforcedTimes', { count: statement.reinforcementCount })}
              </span>
            </div>
          </motion.div>
        )}
      </div>

      {/* Hover glow effect */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        initial={{ opacity: 0 }}
        whileHover={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        <div className="absolute inset-0 bg-gradient-to-r from-orange-500/5 via-transparent to-amber-500/5" />
      </motion.div>
    </motion.div>
  );
}
