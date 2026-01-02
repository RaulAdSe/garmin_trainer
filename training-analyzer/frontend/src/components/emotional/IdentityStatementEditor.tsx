'use client';

import React, { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, Edit3, Sparkles, User } from 'lucide-react';

interface IdentityTemplate {
  id: string;
  statement: string;
  description: string;
}

interface IdentityStatementEditorProps {
  /** Pre-selected template ID */
  initialTemplateId?: string;
  /** Pre-filled custom statement */
  initialStatement?: string;
  /** Available templates from API */
  templates: IdentityTemplate[];
  /** Whether this is an edit (vs first-time creation) */
  isEditing?: boolean;
  /** Callback when statement is saved */
  onSave: (statement: string) => void;
  /** Callback when cancelled */
  onCancel?: () => void;
  /** Loading state */
  isLoading?: boolean;
}

/**
 * IdentityStatementEditor - Editor for creating/editing identity commitment statements
 *
 * Features:
 * - Template selection with visual cards
 * - Custom statement input
 * - Preview of how statement will appear
 * - Triggered at Level 3 or from settings
 */
export function IdentityStatementEditor({
  initialTemplateId,
  initialStatement,
  templates,
  isEditing = false,
  onSave,
  onCancel,
  isLoading = false,
}: IdentityStatementEditorProps) {
  const t = useTranslations('identity');

  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(
    initialTemplateId || null
  );
  const [customStatement, setCustomStatement] = useState(
    initialStatement || ''
  );
  const [isCustomMode, setIsCustomMode] = useState(
    initialStatement && !initialTemplateId ? true : false
  );

  // Get the current statement (either from template or custom)
  const getCurrentStatement = useCallback((): string => {
    if (isCustomMode) {
      return customStatement.trim();
    }
    if (selectedTemplateId) {
      const template = templates.find((t) => t.id === selectedTemplateId);
      return template?.statement || '';
    }
    return '';
  }, [isCustomMode, customStatement, selectedTemplateId, templates]);

  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplateId(templateId);
    setIsCustomMode(false);
    setCustomStatement('');
  };

  const handleCustomModeToggle = () => {
    setIsCustomMode(true);
    setSelectedTemplateId(null);
  };

  const handleSave = () => {
    const statement = getCurrentStatement();
    if (statement) {
      onSave(statement);
    }
  };

  const canSave = getCurrentStatement().length >= 3;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-orange-100 dark:bg-orange-900/30 mb-4">
          <User className="w-6 h-6 text-orange-600 dark:text-orange-400" />
        </div>
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          {isEditing ? t('editTitle') : t('createTitle')}
        </h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          {t('subtitle')}
        </p>
      </div>

      {/* Template Selection */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {t('chooseTemplate')}
        </label>
        <div className="grid gap-3">
          {templates.map((template) => (
            <motion.button
              key={template.id}
              type="button"
              onClick={() => handleTemplateSelect(template.id)}
              className={`
                relative w-full p-4 text-left rounded-xl border-2 transition-all
                ${
                  selectedTemplateId === template.id && !isCustomMode
                    ? 'border-orange-500 bg-orange-50 dark:bg-orange-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-orange-300 dark:hover:border-orange-700'
                }
              `}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="font-medium text-gray-900 dark:text-white">
                    {t('prefix')}{' '}
                    <span className="text-orange-600 dark:text-orange-400">
                      {template.statement}
                    </span>
                  </p>
                  <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    {template.description}
                  </p>
                </div>
                {selectedTemplateId === template.id && !isCustomMode && (
                  <CheckCircle className="w-5 h-5 text-orange-500 flex-shrink-0 ml-2" />
                )}
              </div>
            </motion.button>
          ))}

          {/* Custom Option */}
          <motion.button
            type="button"
            onClick={handleCustomModeToggle}
            className={`
              relative w-full p-4 text-left rounded-xl border-2 border-dashed transition-all
              ${
                isCustomMode
                  ? 'border-orange-500 bg-orange-50 dark:bg-orange-900/20'
                  : 'border-gray-300 dark:border-gray-600 hover:border-orange-300 dark:hover:border-orange-700'
              }
            `}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
          >
            <div className="flex items-center gap-3">
              <Edit3 className="w-5 h-5 text-gray-400" />
              <span className="font-medium text-gray-700 dark:text-gray-300">
                {t('customOption')}
              </span>
              {isCustomMode && (
                <CheckCircle className="w-5 h-5 text-orange-500 ml-auto" />
              )}
            </div>
          </motion.button>
        </div>
      </div>

      {/* Custom Input */}
      <AnimatePresence>
        {isCustomMode && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('customLabel')}
              </label>
              <div className="relative">
                <span className="absolute left-3 top-3 text-gray-500 dark:text-gray-400">
                  {t('prefix')}
                </span>
                <input
                  type="text"
                  value={customStatement}
                  onChange={(e) => setCustomStatement(e.target.value)}
                  placeholder={t('customPlaceholder')}
                  maxLength={200}
                  className="
                    w-full pl-[140px] pr-4 py-3 rounded-xl
                    border border-gray-300 dark:border-gray-600
                    bg-white dark:bg-gray-800
                    text-gray-900 dark:text-white
                    placeholder:text-gray-400 dark:placeholder:text-gray-500
                    focus:ring-2 focus:ring-orange-500 focus:border-transparent
                    transition-all
                  "
                />
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {customStatement.length}/200 {t('characters')}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Preview */}
      <AnimatePresence>
        {canSave && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="p-4 rounded-xl bg-gradient-to-br from-orange-50 to-amber-50 dark:from-orange-900/20 dark:to-amber-900/20 border border-orange-200 dark:border-orange-800"
          >
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-orange-500" />
              <span className="text-sm font-medium text-orange-700 dark:text-orange-300">
                {t('preview')}
              </span>
            </div>
            <p className="text-lg font-medium text-gray-900 dark:text-white">
              {t('prefix')}{' '}
              <span className="text-orange-600 dark:text-orange-400">
                {getCurrentStatement()}
              </span>
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Actions */}
      <div className="flex gap-3">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="
              flex-1 px-4 py-3 rounded-xl
              border border-gray-300 dark:border-gray-600
              text-gray-700 dark:text-gray-300
              hover:bg-gray-50 dark:hover:bg-gray-800
              transition-colors disabled:opacity-50
            "
          >
            {t('cancel')}
          </button>
        )}
        <button
          type="button"
          onClick={handleSave}
          disabled={!canSave || isLoading}
          className="
            flex-1 px-4 py-3 rounded-xl
            bg-orange-500 hover:bg-orange-600
            text-white font-medium
            transition-colors disabled:opacity-50 disabled:cursor-not-allowed
          "
        >
          {isLoading ? t('saving') : isEditing ? t('update') : t('save')}
        </button>
      </div>

      {/* Science Note */}
      <p className="text-xs text-center text-gray-500 dark:text-gray-400">
        {t('scienceNote')}
      </p>
    </div>
  );
}
