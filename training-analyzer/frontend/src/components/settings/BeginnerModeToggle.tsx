'use client';

import { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { clsx } from 'clsx';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { usePreferences } from '@/contexts/preferences-context';

interface BeginnerModeToggleProps {
  className?: string;
}

export function BeginnerModeToggle({ className }: BeginnerModeToggleProps) {
  const t = useTranslations('settings');
  const {
    beginnerModeEnabled,
    isLoading,
    toggleBeginnerMode,
    updatePreferences,
  } = usePreferences();

  const [isToggling, setIsToggling] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleToggle = useCallback(async () => {
    // If turning off beginner mode, show confirmation dialog
    if (beginnerModeEnabled) {
      setShowConfirmDialog(true);
      return;
    }

    // Turning on beginner mode - no confirmation needed
    try {
      setIsToggling(true);
      setError(null);
      await toggleBeginnerMode();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('beginner.errorToggle'));
    } finally {
      setIsToggling(false);
    }
  }, [beginnerModeEnabled, toggleBeginnerMode, t]);

  const handleConfirmDisable = useCallback(async () => {
    try {
      setIsToggling(true);
      setError(null);
      await toggleBeginnerMode();
      setShowConfirmDialog(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('beginner.errorToggle'));
    } finally {
      setIsToggling(false);
    }
  }, [toggleBeginnerMode, t]);

  const handleCancelDisable = useCallback(() => {
    setShowConfirmDialog(false);
  }, []);

  if (isLoading) {
    return (
      <Card className={className}>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-teal-400" />
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card className={className}>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 bg-teal-500/10 rounded-lg">
              <BeginnerIcon className="w-5 h-5 text-teal-400" />
            </div>
            <div>
              <CardTitle>{t('beginner.title')}</CardTitle>
              <CardDescription>{t('beginner.subtitle')}</CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {error && (
            <div className="mb-4 flex items-start gap-2 p-3 bg-red-900/20 border border-red-800 rounded-md">
              <ErrorIcon className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          <div className="space-y-4">
            {/* Toggle Switch */}
            <div className="flex items-center justify-between gap-4 p-4 bg-gray-800/50 rounded-lg">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-200">
                  {t('beginner.toggleLabel')}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {beginnerModeEnabled
                    ? t('beginner.statusEnabled')
                    : t('beginner.statusDisabled')}
                </p>
              </div>

              <button
                onClick={handleToggle}
                disabled={isToggling}
                className={clsx(
                  'relative shrink-0 w-14 h-7 rounded-full transition-colors focus:outline-none',
                  'focus:ring-2 focus:ring-teal-400/50',
                  beginnerModeEnabled ? 'bg-teal-500' : 'bg-gray-600',
                  isToggling && 'opacity-50 cursor-not-allowed'
                )}
                aria-pressed={beginnerModeEnabled}
                aria-label={t('beginner.toggleLabel')}
              >
                <span
                  className={clsx(
                    'absolute left-1 top-1 w-5 h-5 rounded-full bg-white transition-transform',
                    beginnerModeEnabled && 'translate-x-7'
                  )}
                />
              </button>
            </div>

            {/* Benefits List */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-300">
                {t('beginner.benefitsTitle')}
              </h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <BenefitItem
                  icon={<SimplifyIcon className="w-4 h-4" />}
                  text={t('beginner.benefit1')}
                />
                <BenefitItem
                  icon={<FocusIcon className="w-4 h-4" />}
                  text={t('beginner.benefit2')}
                />
                <BenefitItem
                  icon={<GuidanceIcon className="w-4 h-4" />}
                  text={t('beginner.benefit3')}
                />
                <BenefitItem
                  icon={<ProgressIcon className="w-4 h-4" />}
                  text={t('beginner.benefit4')}
                />
              </ul>
            </div>

            {/* Info Box */}
            <div className="p-4 bg-teal-900/20 border border-teal-800/30 rounded-lg">
              <div className="flex items-start gap-3">
                <InfoIcon className="w-5 h-5 text-teal-400 shrink-0 mt-0.5" />
                <div className="text-sm text-gray-300">
                  <p className="font-medium text-teal-400 mb-1">
                    {t('beginner.infoTitle')}
                  </p>
                  <p>{t('beginner.infoDescription')}</p>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Confirmation Dialog */}
      {showConfirmDialog && (
        <ConfirmDialog
          title={t('beginner.confirmDisableTitle')}
          message={t('beginner.confirmDisableMessage')}
          confirmLabel={t('beginner.confirmDisableButton')}
          cancelLabel={t('common.cancel')}
          onConfirm={handleConfirmDisable}
          onCancel={handleCancelDisable}
          isLoading={isToggling}
        />
      )}
    </>
  );
}

// Benefit Item Component
function BenefitItem({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <li className="flex items-start gap-2">
      <span className="text-teal-400 mt-0.5">{icon}</span>
      <span>{text}</span>
    </li>
  );
}

// Confirmation Dialog Component
function ConfirmDialog({
  title,
  message,
  confirmLabel,
  cancelLabel,
  onConfirm,
  onCancel,
  isLoading,
}: {
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* Dialog */}
      <div className="relative z-10 w-full max-w-md bg-gray-900 rounded-xl border border-gray-700 shadow-xl">
        <div className="p-6">
          <div className="flex items-start gap-4">
            <div className="flex items-center justify-center w-12 h-12 bg-yellow-500/10 rounded-full shrink-0">
              <WarningIcon className="w-6 h-6 text-yellow-400" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-white">{title}</h3>
              <p className="mt-2 text-sm text-gray-400">{message}</p>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 px-6 py-4 bg-gray-800/50 rounded-b-xl border-t border-gray-700">
          <Button
            variant="secondary"
            onClick={onCancel}
            disabled={isLoading}
          >
            {cancelLabel}
          </Button>
          <Button
            variant="primary"
            onClick={onConfirm}
            isLoading={isLoading}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

// Icon Components
function BeginnerIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
      />
    </svg>
  );
}

function SimplifyIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 6h16M4 12h8m-8 6h16"
      />
    </svg>
  );
}

function FocusIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
      />
    </svg>
  );
}

function GuidanceIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
      />
    </svg>
  );
}

function ProgressIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
      />
    </svg>
  );
}

function InfoIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function ErrorIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function WarningIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      />
    </svg>
  );
}

export default BeginnerModeToggle;
