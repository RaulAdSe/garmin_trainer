'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  syncGarminActivities,
  GarminSyncResponse,
  SyncedActivity,
} from '@/lib/api-client';
import { clsx } from 'clsx';

interface GarminSyncProps {
  onSyncComplete?: (result: GarminSyncResponse) => void;
  onClose?: () => void;
  className?: string;
}

type SyncState = 'idle' | 'syncing' | 'success' | 'error';

const REMEMBER_EMAIL_KEY = 'garmin-sync-email';

export function GarminSync({ onSyncComplete, onClose, className }: GarminSyncProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [days, setDays] = useState(30);
  const [rememberEmail, setRememberEmail] = useState(false);
  const [syncState, setSyncState] = useState<SyncState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GarminSyncResponse | null>(null);

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

  const handleSync = useCallback(async () => {
    if (!email || !password) {
      setError('Please enter your Garmin Connect email and password');
      return;
    }

    setSyncState('syncing');
    setError(null);
    setResult(null);

    try {
      const response = await syncGarminActivities({
        email,
        password,
        days,
      });

      setResult(response);
      setSyncState('success');

      // Clear password after successful sync for security
      setPassword('');

      // Notify parent component
      if (onSyncComplete) {
        onSyncComplete(response);
      }
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to sync activities';
      setError(errorMessage);
      setSyncState('error');
    }
  }, [email, password, days, onSyncComplete]);

  const handleReset = useCallback(() => {
    setSyncState('idle');
    setError(null);
    setResult(null);
  }, []);

  const isSubmitDisabled = !email || !password || syncState === 'syncing';

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
          <SyncResult result={result} onReset={handleReset} onClose={onClose} />
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

            {/* Remember email checkbox */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={rememberEmail}
                onChange={(e) => setRememberEmail(e.target.checked)}
                className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-teal-500 focus:ring-teal-500 focus:ring-offset-gray-900"
              />
              <span className="text-sm text-gray-400">Remember my email</span>
            </label>

            {/* Security notice */}
            <div className="flex items-start gap-2 p-3 bg-gray-800/50 rounded-md">
              <InfoIcon className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
              <p className="text-xs text-gray-400">
                Your password is only used for this sync request and is not stored.
                We recommend using HTTPS in production.
              </p>
            </div>

            {/* Error message */}
            {error && (
              <div className="flex items-start gap-2 p-3 bg-red-900/20 border border-red-800 rounded-md">
                <ErrorIcon className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                <p className="text-sm text-red-400">{error}</p>
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
}: {
  result: GarminSyncResponse;
  onReset: () => void;
  onClose?: () => void;
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
        <Button variant="outline" onClick={onReset} fullWidth>
          Sync Again
        </Button>
        {onClose && (
          <Button variant="primary" onClick={onClose} fullWidth>
            Done
          </Button>
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

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
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
