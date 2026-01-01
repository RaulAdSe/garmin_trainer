'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useRouter } from '@/i18n/navigation';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { handleStravaCallback } from '@/lib/api-client';
import type { StravaStatus } from '@/lib/types';

// Strava brand color
const STRAVA_ORANGE = '#FC4C02';

type CallbackState = 'loading' | 'success' | 'error';

function StravaCallbackContent() {
  const t = useTranslations('strava');
  const router = useRouter();
  const searchParams = useSearchParams();

  const [state, setState] = useState<CallbackState>('loading');
  const [status, setStatus] = useState<StravaStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const processCallback = async () => {
      const code = searchParams.get('code');
      const scope = searchParams.get('scope');
      const errorParam = searchParams.get('error');

      // Handle OAuth error from Strava
      if (errorParam) {
        setError(errorParam === 'access_denied' ? t('errorAccessDenied') : errorParam);
        setState('error');
        return;
      }

      // Validate code parameter
      if (!code) {
        setError(t('errorNoCode'));
        setState('error');
        return;
      }

      try {
        // Exchange the code for tokens
        const result = await handleStravaCallback(code, scope ?? undefined);
        setStatus(result);
        setState('success');

        // Redirect to settings page after a short delay
        setTimeout(() => {
          router.push('/settings/strava');
        }, 3000);
      } catch (err) {
        const message = err instanceof Error ? err.message : t('errorUnknown');
        setError(message);
        setState('error');
      }
    };

    processCallback();
  }, [searchParams, router, t]);

  const handleGoToSettings = () => {
    router.push('/settings/strava');
  };

  const handleTryAgain = () => {
    router.push('/settings/strava');
  };

  return (
    <div className="min-h-[60vh] flex items-center justify-center p-4">
      <Card className="max-w-md w-full">
        <CardContent className="py-8">
          {state === 'loading' && (
            <div className="flex flex-col items-center gap-4 text-center">
              <div className="relative">
                <LoadingSpinner size="xl" />
                <StravaLogo className="absolute inset-0 m-auto w-8 h-8" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-100">
                  {t('callbackConnecting')}
                </h2>
                <p className="text-sm text-gray-400 mt-1">
                  {t('callbackConnectingDesc')}
                </p>
              </div>
            </div>
          )}

          {state === 'success' && (
            <div className="flex flex-col items-center gap-4 text-center">
              <div className="flex items-center justify-center w-16 h-16 bg-green-900/50 rounded-full">
                <CheckIcon className="w-8 h-8 text-green-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-100">
                  {t('callbackSuccess')}
                </h2>
                <p className="text-sm text-gray-400 mt-1">
                  {status?.athlete_name
                    ? t('callbackSuccessWithName', { name: status.athlete_name })
                    : t('callbackSuccessDesc')}
                </p>
              </div>
              <div className="flex flex-col gap-2 w-full mt-2">
                <Button
                  onClick={handleGoToSettings}
                  className="!bg-[#FC4C02] hover:!bg-[#E34402] !text-white"
                  fullWidth
                >
                  {t('callbackGoToSettings')}
                </Button>
                <p className="text-xs text-gray-500">
                  {t('callbackRedirecting')}
                </p>
              </div>
            </div>
          )}

          {state === 'error' && (
            <div className="flex flex-col items-center gap-4 text-center">
              <div className="flex items-center justify-center w-16 h-16 bg-red-900/50 rounded-full">
                <ErrorIcon className="w-8 h-8 text-red-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-100">
                  {t('callbackError')}
                </h2>
                <p className="text-sm text-red-400 mt-1">{error}</p>
              </div>
              <Button
                variant="outline"
                onClick={handleTryAgain}
                fullWidth
              >
                {t('callbackTryAgain')}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
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

// Wrap in Suspense for useSearchParams
export default function StravaCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-[60vh] flex items-center justify-center">
          <LoadingSpinner size="xl" />
        </div>
      }
    >
      <StravaCallbackContent />
    </Suspense>
  );
}
