'use client';

import { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import {
  getStravaStatus,
  getStravaAuthUrl,
  disconnectStrava,
  getStravaPreferences,
  updateStravaPreferences,
} from '@/lib/api-client';
import type { StravaStatus, StravaPreferences } from '@/lib/types';
import { clsx } from 'clsx';

interface StravaConnectionProps {
  initialStatus?: StravaStatus;
  initialPreferences?: StravaPreferences;
  className?: string;
}

// Strava brand color
const STRAVA_ORANGE = '#FC4C02';

export function StravaConnection({
  initialStatus,
  initialPreferences,
  className,
}: StravaConnectionProps) {
  const t = useTranslations('strava');

  const [status, setStatus] = useState<StravaStatus | null>(initialStatus ?? null);
  const [preferences, setPreferences] = useState<StravaPreferences | null>(initialPreferences ?? null);
  const [isLoading, setIsLoading] = useState(!initialStatus);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [isSavingPreferences, setIsSavingPreferences] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch status on mount if not provided
  const fetchStatus = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [statusData, prefsData] = await Promise.all([
        getStravaStatus(),
        getStravaPreferences().catch(() => null),
      ]);
      setStatus(statusData);
      if (prefsData) {
        setPreferences(prefsData);
      }
    } catch (err) {
      // Check if this is an expected error (401 = not logged in, 500 = server error)
      // These should be treated as "not connected" without showing error UI
      const isExpectedError =
        err &&
        typeof err === 'object' &&
        'status' in err &&
        (err.status === 401 || err.status === 500);

      if (isExpectedError) {
        // Silently treat as not connected
        setStatus({ connected: false });
      } else {
        // Unexpected error - show to user
        const message = err instanceof Error ? err.message : 'Failed to fetch status';
        setError(message);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initialize on mount
  useState(() => {
    if (!initialStatus) {
      fetchStatus();
    }
  });

  const handleConnect = useCallback(async () => {
    try {
      setIsConnecting(true);
      setError(null);
      const { authorization_url } = await getStravaAuthUrl();
      // Redirect to Strava OAuth page
      window.location.href = authorization_url;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to connect to Strava';
      setError(message);
      setIsConnecting(false);
    }
  }, []);

  const handleDisconnect = useCallback(async () => {
    try {
      setIsDisconnecting(true);
      setError(null);
      await disconnectStrava();
      setStatus({ connected: false });
      setPreferences(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to disconnect from Strava';
      setError(message);
    } finally {
      setIsDisconnecting(false);
    }
  }, []);

  const handlePreferenceChange = useCallback(
    async (key: keyof StravaPreferences, value: boolean | string) => {
      if (!preferences) return;

      try {
        setIsSavingPreferences(true);
        setError(null);
        const updatedPrefs = await updateStravaPreferences({
          ...preferences,
          [key]: value,
        });
        setPreferences(updatedPrefs);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update preferences';
        setError(message);
      } finally {
        setIsSavingPreferences(false);
      }
    },
    [preferences]
  );

  if (isLoading) {
    return (
      <Card className={className}>
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center gap-3">
          <StravaLogo className="w-8 h-8" />
          <div>
            <CardTitle>{t('title')}</CardTitle>
            <CardDescription>{t('subtitle')}</CardDescription>
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

        {status?.connected ? (
          <div className="space-y-6">
            {/* Connection Status */}
            <div className="flex items-center gap-3 p-4 bg-green-900/20 border border-green-800 rounded-lg">
              <div className="flex items-center justify-center w-10 h-10 bg-green-900/50 rounded-full">
                <CheckIcon className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-green-400">{t('connected')}</p>
                {status.athlete_name && (
                  <p className="text-sm text-gray-400">
                    {t('connectedAs', { name: status.athlete_name })}
                  </p>
                )}
              </div>
            </div>

            {/* Preferences */}
            {preferences && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-gray-300">{t('preferences')}</h3>

                <PreferenceToggle
                  label={t('autoUpdateDescription')}
                  description={t('autoUpdateDescriptionHint')}
                  checked={preferences.auto_update_description}
                  onChange={(checked) => handlePreferenceChange('auto_update_description', checked)}
                  disabled={isSavingPreferences}
                />

                <PreferenceToggle
                  label={t('includeScore')}
                  description={t('includeScoreHint')}
                  checked={preferences.include_score}
                  onChange={(checked) => handlePreferenceChange('include_score', checked)}
                  disabled={isSavingPreferences}
                />

                <PreferenceToggle
                  label={t('includeSummary')}
                  description={t('includeSummaryHint')}
                  checked={preferences.include_summary}
                  onChange={(checked) => handlePreferenceChange('include_summary', checked)}
                  disabled={isSavingPreferences}
                />

                <PreferenceToggle
                  label={t('includeLink')}
                  description={t('includeLinkHint')}
                  checked={preferences.include_link}
                  onChange={(checked) => handlePreferenceChange('include_link', checked)}
                  disabled={isSavingPreferences}
                />

                <PreferenceToggle
                  label={t('useExtendedFormat')}
                  description={t('useExtendedFormatHint')}
                  checked={preferences.use_extended_format}
                  onChange={(checked) => handlePreferenceChange('use_extended_format', checked)}
                  disabled={isSavingPreferences}
                />
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-gray-400">{t('notConnectedDesc')}</p>

            {/* Permission info */}
            <div className="p-4 bg-gray-800/50 rounded-lg space-y-2">
              <h4 className="text-sm font-medium text-gray-300">{t('permissionsTitle')}</h4>
              <ul className="text-sm text-gray-400 space-y-1">
                <li className="flex items-start gap-2">
                  <span className="text-teal-400 mt-1">&#8226;</span>
                  {t('permissionRead')}
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-teal-400 mt-1">&#8226;</span>
                  {t('permissionWrite')}
                </li>
              </ul>
            </div>
          </div>
        )}
      </CardContent>

      <CardFooter>
        {status?.connected ? (
          <Button
            variant="danger"
            onClick={handleDisconnect}
            isLoading={isDisconnecting}
            leftIcon={<DisconnectIcon className="w-4 h-4" />}
          >
            {t('disconnect')}
          </Button>
        ) : (
          <Button
            onClick={handleConnect}
            isLoading={isConnecting}
            leftIcon={<StravaLogo className="w-4 h-4" />}
            className="!bg-[#FC4C02] hover:!bg-[#E34402] !text-white"
          >
            {t('connect')}
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}

// Preference Toggle Component
function PreferenceToggle({
  label,
  description,
  checked,
  onChange,
  disabled,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className={clsx(
      'flex items-start justify-between gap-4 p-3 bg-gray-800/50 rounded-lg cursor-pointer',
      'hover:bg-gray-800 transition-colors',
      disabled && 'opacity-50 cursor-not-allowed'
    )}>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-200">{label}</p>
        <p className="text-xs text-gray-500 mt-0.5">{description}</p>
      </div>
      <div className="relative shrink-0">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
          className="sr-only peer"
        />
        <div className={clsx(
          'w-11 h-6 rounded-full transition-colors',
          'bg-gray-700 peer-checked:bg-[#FC4C02]',
          'peer-focus:ring-2 peer-focus:ring-[#FC4C02]/50'
        )} />
        <div className={clsx(
          'absolute left-1 top-1 w-4 h-4 rounded-full bg-white transition-transform',
          'peer-checked:translate-x-5'
        )} />
      </div>
    </label>
  );
}

// Strava Logo SVG
function StravaLogo({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill={STRAVA_ORANGE}
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.463 0l-7 13.828h4.169" />
    </svg>
  );
}

// Icon components
function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
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

function DisconnectIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
      />
    </svg>
  );
}

export default StravaConnection;
