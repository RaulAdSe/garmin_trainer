'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import {
  syncGarminActivitiesAsync,
  getSyncJobStatus,
  getGarminCredentialStatus,
  saveGarminCredentials,
  deleteGarminCredentials,
  GarminSyncResponse,
  SyncedActivity,
  SyncJobStatus,
  CredentialStatusResponse,
} from '@/lib/api-client';
import { GarminSyncSettings } from './GarminSyncSettings';
import { clsx } from 'clsx';

interface GarminSyncProps {
  onSyncComplete?: (result: GarminSyncResponse) => void;
  onClose?: () => void;
  className?: string;
}

type SyncState = 'idle' | 'syncing' | 'success' | 'error';
type ViewMode = 'loading' | 'setup' | 'connected';

const REMEMBER_EMAIL_KEY = 'garmin-sync-email';
const POLL_INTERVAL = 1000; // Poll every 1 second

export function GarminSync({ onSyncComplete, onClose, className }: GarminSyncProps) {
  // Credential status
  const [viewMode, setViewMode] = useState<ViewMode>('loading');
  const [credentialStatus, setCredentialStatus] = useState<CredentialStatusResponse | null>(null);
  const [savingCredentials, setSavingCredentials] = useState(false);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [days, setDays] = useState(30);
  const [rememberEmail, setRememberEmail] = useState(false);
  const [saveCredentialsChecked, setSaveCredentialsChecked] = useState(true);
  const [credentialsSavedSuccessfully, setCredentialsSavedSuccessfully] = useState(false);
  const [credentialSaveError, setCredentialSaveError] = useState<string | null>(null);
  const [syncState, setSyncState] = useState<SyncState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GarminSyncResponse | null>(null);
  // Async sync progress state
  const [jobId, setJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [activitiesSynced, setActivitiesSynced] = useState(0);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Check credential status on mount
  useEffect(() => {
    checkCredentialStatus();
  }, []);

  const checkCredentialStatus = async () => {
    try {
      setViewMode('loading');
      const status = await getGarminCredentialStatus();
      setCredentialStatus(status);
      setViewMode(status.connected ? 'connected' : 'setup');
    } catch (err) {
      // 401 errors are expected when user is not authenticated
      // Treat as "not connected" and show the setup form without logging errors
      const isAuthError = err instanceof Error &&
        'status' in err &&
        (err as { status: number }).status === 401;

      if (!isAuthError) {
        // Only log unexpected errors
        console.error('Failed to check credential status:', err);
      }

      // For both auth errors and other errors, show the setup form
      setCredentialStatus(null);
      setViewMode('setup');
    }
  };

  // Load remembered email on mount
  useEffect(() => {
    const savedEmail = localStorage.getItem(REMEMBER_EMAIL_KEY);
    if (savedEmail) {
      setEmail(savedEmail);
      setRememberEmail(true);
    }
  }, []);

  // Save/remove email when checkbox or email changes
  useEffect(() => {
    if (rememberEmail && email) {
      localStorage.setItem(REMEMBER_EMAIL_KEY, email);
    } else if (!rememberEmail) {
      localStorage.removeItem(REMEMBER_EMAIL_KEY);
    }
  }, [rememberEmail, email]);

  // Cleanup polling interval on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // Poll for job status
  const pollJobStatus = useCallback(async (jobIdToPoll: string) => {
    try {
      const status = await getSyncJobStatus(jobIdToPoll);

      setProgress(status.progress_percent);
      setCurrentStep(status.current_step);
      setActivitiesSynced(status.activities_synced);

      if (status.status === 'completed' && status.result) {
        // Stop polling
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }

        // Build result response
        const syncResult: GarminSyncResponse = {
          success: true,
          message: `Synced ${status.result.synced_count} activities`,
          synced_count: status.result.synced_count,
          new_activities: status.result.new_activities,
          updated_activities: status.result.updated_activities,
          activities: [], // Async endpoint doesn't return activity list
        };

        setResult(syncResult);
        setSyncState('success');
        setPassword('');

        if (onSyncComplete) {
          onSyncComplete(syncResult);
        }
      } else if (status.status === 'failed') {
        // Stop polling
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }

        setError(status.error || 'Sync failed');
        setSyncState('error');
      }
    } catch (err) {
      // Don't stop polling on transient errors, just log them
      console.error('Error polling job status:', err);
    }
  }, [onSyncComplete]);

  const handleSync = useCallback(async () => {
    if (!email || !password) {
      setError('Please enter your Garmin Connect email and password');
      return;
    }

    setSyncState('syncing');
    setError(null);
    setCredentialSaveError(null);
    setCredentialsSavedSuccessfully(false);
    setResult(null);
    setProgress(0);
    setCurrentStep('Starting sync...');
    setActivitiesSynced(0);
    setJobId(null);

    try {
      // Save credentials if checkbox is checked
      if (saveCredentialsChecked) {
        setSavingCredentials(true);
        setCurrentStep('Saving credentials...');
        try {
          const saveResult = await saveGarminCredentials(email, password);
          // Check if save actually succeeded (API returns success: false on 401)
          if (saveResult && 'success' in saveResult && saveResult.success === false) {
            const errorMsg = saveResult.message || 'Failed to save credentials - authentication required';
            console.error('Credential save failed:', errorMsg);
            setCredentialSaveError(errorMsg);
          } else {
            setCredentialsSavedSuccessfully(true);
          }
        } catch (err) {
          const errorMsg = err instanceof Error ? err.message : 'Failed to save credentials';
          console.error('Failed to save credentials:', errorMsg);
          setCredentialSaveError(errorMsg);
          // Continue with sync even if saving credentials fails
        }
        setSavingCredentials(false);
      }

      setCurrentStep('Starting sync...');

      // Start async sync
      const response = await syncGarminActivitiesAsync({
        email,
        password,
        days,
      });

      setJobId(response.job_id);

      // Start polling for status
      pollIntervalRef.current = setInterval(() => {
        pollJobStatus(response.job_id);
      }, POLL_INTERVAL);

      // Also poll immediately
      pollJobStatus(response.job_id);

    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to start sync';
      setError(errorMessage);
      setSyncState('error');
    }
  }, [email, password, days, saveCredentialsChecked, pollJobStatus]);

  const handleDisconnect = useCallback(async () => {
    try {
      await deleteGarminCredentials();
      setCredentialStatus(null);
      setViewMode('setup');
      setEmail('');
      setPassword('');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to disconnect';
      setError(errorMessage);
    }
  }, []);

  const handleReset = useCallback(() => {
    // Stop any ongoing polling
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setSyncState('idle');
    setError(null);
    setResult(null);
    setJobId(null);
    setProgress(0);
    setCurrentStep('');
    setActivitiesSynced(0);
  }, []);

  const handleSyncSuccess = useCallback(() => {
    // After a successful sync, check if credentials were saved and switch to connected view
    if (saveCredentialsChecked) {
      checkCredentialStatus();
    }
  }, [saveCredentialsChecked]);

  const isSubmitDisabled = !email || !password || syncState === 'syncing';

  // Loading state
  if (viewMode === 'loading') {
    return (
      <div className={clsx('bg-gray-900 rounded-lg border border-gray-800', className)}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <GarminIcon className="w-8 h-8 text-teal-400" />
            <div>
              <h2 className="text-lg font-semibold text-gray-100">Garmin Connect</h2>
              <p className="text-sm text-gray-400">Loading...</p>
            </div>
          </div>
        </div>
        <div className="p-6 flex items-center justify-center py-12">
          <LoadingSpinner size="lg" label="Checking connection..." />
        </div>
      </div>
    );
  }

  // Connected view with sync settings
  if (viewMode === 'connected' && credentialStatus?.connected) {
    return (
      <div className={clsx('bg-gray-900 rounded-lg border border-gray-800', className)}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <GarminIcon className="w-8 h-8 text-teal-400" />
            <div>
              <h2 className="text-lg font-semibold text-gray-100">Garmin Connect</h2>
              <div className="flex items-center gap-2 text-sm">
                <span className="inline-flex items-center gap-1 text-green-400">
                  <CheckIcon className="w-3.5 h-3.5" />
                  Connected
                </span>
                {credentialStatus.garmin_user && (
                  <span className="text-gray-500">({credentialStatus.garmin_user})</span>
                )}
              </div>
            </div>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-200 transition-colors"
              aria-label="Close"
            >
              <CloseIcon className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Sync Settings */}
        <div className="p-6">
          <GarminSyncSettings onSyncComplete={onSyncComplete ? () => onSyncComplete({
            success: true,
            synced_count: 0,
            new_activities: 0,
            updated_activities: 0,
            message: 'Sync completed',
            activities: [],
          }) : undefined} />

          {/* Disconnect button */}
          <div className="mt-6 pt-6 border-t border-gray-800">
            <Button
              variant="ghost"
              onClick={handleDisconnect}
              className="text-red-400 hover:text-red-300 hover:bg-red-900/20"
            >
              <DisconnectIcon className="w-4 h-4 mr-2" />
              Disconnect Garmin Account
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={clsx('bg-gray-900 rounded-lg border border-gray-800', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <GarminIcon className="w-8 h-8 text-teal-400" />
          <div>
            <h2 className="text-lg font-semibold text-gray-100">Garmin Connect</h2>
            <p className="text-sm text-gray-400">Sync your activities from Garmin</p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 transition-colors"
            aria-label="Close"
          >
            <CloseIcon className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Content */}
      <div className="p-6">
        {syncState === 'success' && result ? (
          <SyncResult
            result={result}
            onReset={handleReset}
            onClose={onClose}
            onViewSettings={() => checkCredentialStatus()}
            credentialsSaved={credentialsSavedSuccessfully}
            credentialSaveError={credentialSaveError}
          />
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSync();
            }}
            className="space-y-4"
          >
            {/* Email input */}
            <Input
              label="Garmin Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              autoComplete="email"
              disabled={syncState === 'syncing'}
            />

            {/* Password input */}
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your Garmin Connect password"
              autoComplete="current-password"
              disabled={syncState === 'syncing'}
            />

            {/* Days to sync */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-gray-300">
                Days to sync
              </label>
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                disabled={syncState === 'syncing'}
                className="block w-full px-4 py-2.5 text-sm rounded-lg border bg-gray-800 text-gray-100 border-gray-700 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 focus:outline-none transition-colors"
              >
                <option value={7}>Last 7 days</option>
                <option value={14}>Last 14 days</option>
                <option value={30}>Last 30 days</option>
                <option value={60}>Last 60 days</option>
                <option value={90}>Last 90 days</option>
                <option value={180}>Last 6 months</option>
                <option value={365}>Last year</option>
              </select>
            </div>

            {/* Save credentials checkbox */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={saveCredentialsChecked}
                onChange={(e) => setSaveCredentialsChecked(e.target.checked)}
                className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-teal-500 focus:ring-teal-500 focus:ring-offset-gray-900"
              />
              <span className="text-sm text-gray-400">
                Save credentials for automatic sync
              </span>
            </label>

            {/* Remember email checkbox */}
            {!saveCredentialsChecked && (
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={rememberEmail}
                  onChange={(e) => setRememberEmail(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-teal-500 focus:ring-teal-500 focus:ring-offset-gray-900"
                />
                <span className="text-sm text-gray-400">Remember my email only</span>
              </label>
            )}

            {/* Security notice */}
            <div className="flex items-start gap-2 p-3 bg-gray-800/50 rounded-md">
              <InfoIcon className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
              <p className="text-xs text-gray-400">
                {saveCredentialsChecked
                  ? 'Your credentials will be securely stored on the server to enable automatic daily syncing.'
                  : 'Your password is only used for this sync request and is not stored.'}
              </p>
            </div>

            {/* Error message */}
            {error && (
              <div className="flex items-start gap-2 p-3 bg-red-900/20 border border-red-800 rounded-md">
                <ErrorIcon className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            {/* Progress bar during sync */}
            {syncState === 'syncing' && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">{currentStep || 'Starting...'}</span>
                  <span className="text-teal-400 font-mono">{progress}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-teal-500 h-full rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                {activitiesSynced > 0 && (
                  <p className="text-xs text-gray-500 text-center">
                    {activitiesSynced} activities synced
                  </p>
                )}
              </div>
            )}

            {/* Submit button */}
            <div className="flex gap-3 pt-2">
              <Button
                type="submit"
                variant="primary"
                isLoading={syncState === 'syncing'}
                disabled={isSubmitDisabled}
                fullWidth
                leftIcon={<SyncIcon className="w-4 h-4" />}
              >
                {syncState === 'syncing' ? 'Syncing...' : 'Sync Activities'}
              </Button>
              {onClose && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={onClose}
                  disabled={syncState === 'syncing'}
                >
                  Cancel
                </Button>
              )}
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

// Success result display
function SyncResult({
  result,
  onReset,
  onClose,
  onViewSettings,
  credentialsSaved,
  credentialSaveError,
}: {
  result: GarminSyncResponse;
  onReset: () => void;
  onClose?: () => void;
  onViewSettings?: () => void;
  credentialsSaved?: boolean;
  credentialSaveError?: string | null;
}) {
  return (
    <div className="space-y-4">
      {/* Success header */}
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-10 h-10 bg-teal-900/50 rounded-full">
          <CheckIcon className="w-5 h-5 text-teal-400" />
        </div>
        <div>
          <h3 className="text-lg font-medium text-gray-100">Sync Complete</h3>
          <p className="text-sm text-gray-400">{result.message}</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Total Synced" value={result.synced_count.toString()} />
        <StatCard
          label="New"
          value={result.new_activities.toString()}
          accent="teal"
        />
        <StatCard
          label="Updated"
          value={result.updated_activities.toString()}
          accent="blue"
        />
      </div>

      {/* Credentials saved notice */}
      {credentialsSaved && (
        <div className="flex items-start gap-2 p-3 bg-teal-900/20 border border-teal-800 rounded-md">
          <CheckIcon className="w-4 h-4 text-teal-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm text-teal-300">Credentials saved successfully</p>
            <p className="text-xs text-teal-400/80 mt-0.5">
              Automatic sync is now available. Your activities will sync daily at 6 AM UTC.
            </p>
          </div>
        </div>
      )}

      {/* Credentials save error notice */}
      {credentialSaveError && (
        <div className="flex items-start gap-2 p-3 bg-amber-900/20 border border-amber-700 rounded-md">
          <WarningIcon className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm text-amber-300">Could not save credentials for auto-sync</p>
            <p className="text-xs text-amber-400/80 mt-0.5">
              {credentialSaveError}. You can still sync manually.
            </p>
          </div>
        </div>
      )}

      {/* Recent activities preview */}
      {result.activities.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-300">
            Recent Activities ({Math.min(5, result.activities.length)} of{' '}
            {result.activities.length})
          </h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {result.activities.slice(0, 5).map((activity) => (
              <ActivityPreview key={activity.id} activity={activity} />
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        {credentialsSaved && onViewSettings ? (
          <>
            <Button variant="outline" onClick={onReset}>
              Sync Again
            </Button>
            <Button variant="primary" onClick={onViewSettings} fullWidth>
              View Sync Settings
            </Button>
          </>
        ) : (
          <>
            <Button variant="outline" onClick={onReset} fullWidth>
              Sync Again
            </Button>
            {onClose && (
              <Button variant="primary" onClick={onClose} fullWidth>
                Done
              </Button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: 'teal' | 'blue';
}) {
  const valueColor =
    accent === 'teal'
      ? 'text-teal-400'
      : accent === 'blue'
      ? 'text-blue-400'
      : 'text-gray-100';

  return (
    <div className="bg-gray-800 rounded-lg p-3 text-center">
      <dt className="text-xs text-gray-500 uppercase tracking-wide">{label}</dt>
      <dd className={clsx('text-xl font-semibold mt-1', valueColor)}>{value}</dd>
    </div>
  );
}

function ActivityPreview({ activity }: { activity: SyncedActivity }) {
  return (
    <div className="flex items-center justify-between p-2 bg-gray-800 rounded-md">
      <div className="flex items-center gap-2">
        <ActivityTypeIcon type={activity.type} className="w-4 h-4 text-gray-400" />
        <div>
          <p className="text-sm text-gray-200 truncate max-w-[200px]">
            {activity.name}
          </p>
          <p className="text-xs text-gray-500">{activity.date}</p>
        </div>
      </div>
      <div className="text-right text-xs text-gray-400">
        {activity.distance_km && (
          <span>{activity.distance_km.toFixed(1)} km</span>
        )}
        {activity.distance_km && activity.duration_min && <span> / </span>}
        {activity.duration_min && (
          <span>{Math.round(activity.duration_min)} min</span>
        )}
      </div>
    </div>
  );
}

// Icon components
function GarminIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z" />
    </svg>
  );
}

function CloseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

function SyncIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
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

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
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
        d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
      />
    </svg>
  );
}

function ActivityTypeIcon({ type, className }: { type: string; className?: string }) {
  // Simple running icon for all types (could be expanded)
  const iconPaths: Record<string, string> = {
    running: 'M13.5 5.5c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zM9.8 8.9L7 23h2.1l1.8-8 2.1 2v6h2v-7.5l-2.1-2 .6-3C14.8 12 16.8 13 19 13v-2c-1.9 0-3.5-1-4.3-2.4l-1-1.6c-.4-.6-1-1-1.7-1-.3 0-.5.1-.8.1L6 8.3V13h2V9.6l1.8-.7',
    cycling: 'M15.5 5.5c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zM5 12c-2.8 0-5 2.2-5 5s2.2 5 5 5 5-2.2 5-5-2.2-5-5-5zm0 8.5c-1.9 0-3.5-1.6-3.5-3.5s1.6-3.5 3.5-3.5 3.5 1.6 3.5 3.5-1.6 3.5-3.5 3.5zm5.8-10l2.4-2.4.8.8c1.3 1.3 3 2.1 5.1 2.1V9c-1.5 0-2.7-.6-3.6-1.5l-1.9-1.9c-.5-.4-1-.6-1.6-.6s-1.1.2-1.4.6L7.8 8.4c-.4.4-.6.9-.6 1.4 0 .6.2 1.1.6 1.4L11 14v5h2v-6.2l-2.2-2.3zM19 12c-2.8 0-5 2.2-5 5s2.2 5 5 5 5-2.2 5-5-2.2-5-5-5zm0 8.5c-1.9 0-3.5-1.6-3.5-3.5s1.6-3.5 3.5-3.5 3.5 1.6 3.5 3.5-1.6 3.5-3.5 3.5z',
    swimming: 'M22 21c-1.11 0-1.73-.37-2.18-.64-.37-.22-.6-.36-1.15-.36-.56 0-.78.13-1.15.36-.46.27-1.07.64-2.18.64s-1.73-.37-2.18-.64c-.37-.22-.6-.36-1.15-.36-.56 0-.78.13-1.15.36-.46.27-1.08.64-2.19.64-1.11 0-1.73-.37-2.18-.64-.37-.23-.6-.36-1.15-.36s-.78.13-1.15.36c-.46.27-1.08.64-2.19.64v-2c.56 0 .78-.13 1.15-.36.46-.27 1.08-.64 2.19-.64s1.73.37 2.18.64c.37.23.59.36 1.15.36.56 0 .78-.13 1.15-.36.46-.27 1.08-.64 2.19-.64 1.11 0 1.73.37 2.18.64.37.22.6.36 1.15.36s.78-.13 1.15-.36c.45-.27 1.07-.64 2.18-.64s1.73.37 2.18.64c.37.23.59.36 1.15.36v2zm0-4.5c-1.11 0-1.73-.37-2.18-.64-.37-.22-.6-.36-1.15-.36-.56 0-.78.13-1.15.36-.45.27-1.07.64-2.18.64s-1.73-.37-2.18-.64c-.37-.22-.6-.36-1.15-.36-.56 0-.78.13-1.15.36-.45.27-1.07.64-2.18.64s-1.73-.37-2.18-.64c-.37-.22-.6-.36-1.15-.36s-.78.13-1.15.36c-.47.27-1.09.64-2.2.64v-2c.56 0 .78-.13 1.15-.36.45-.27 1.07-.64 2.18-.64s1.73.37 2.18.64c.37.22.6.36 1.15.36.56 0 .78-.13 1.15-.36.45-.27 1.07-.64 2.18-.64s1.73.37 2.18.64c.37.22.6.36 1.15.36s.78-.13 1.15-.36c.45-.27 1.07-.64 2.18-.64s1.73.37 2.18.64c.37.22.6.36 1.15.36v2zM8.67 12c.56 0 .78-.13 1.15-.36.46-.27 1.08-.64 2.19-.64 1.11 0 1.73.37 2.18.64.37.22.6.36 1.15.36s.78-.13 1.15-.36c.12-.07.26-.15.41-.23L10.48 5C10.17 4.39 9.55 4 8.85 4H7.15c-.7 0-1.32.39-1.63 1L2.2 11.52c.14.08.29.16.41.23.37.22.6.36 1.15.36s.78-.13 1.15-.36c.46-.27 1.08-.64 2.19-.64.52 0 .93.12 1.26.28L12 7.79v4.2c-.68.01-1.08.27-1.49.51-.37.22-.6.36-1.15.36-.56 0-.78-.13-1.15-.36-.46-.27-1.08-.64-2.19-.64s-1.73.37-2.18.64c-.37.22-.6.36-1.15.36s-.78-.13-1.15-.36c-.45-.27-1.07-.64-2.18-.64v-2c1.11 0 1.73.37 2.18.64.37.22.6.36 1.15.36s.78-.13 1.15-.36c.46-.27 1.08-.64 2.19-.64z',
  };

  const pathData =
    iconPaths[type.toLowerCase()] ||
    iconPaths['running'];

  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d={pathData} />
    </svg>
  );
}

export default GarminSync;
