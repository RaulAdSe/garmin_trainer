'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/Button';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import {
  getGarminSyncConfig,
  updateGarminSyncConfig,
  getGarminSyncHistory,
  triggerManualSync,
  getSyncJobStatus,
  TriggerSyncResponse,
  SyncJobStatus,
} from '@/lib/api-client';
import type { GarminSyncConfig, GarminSyncHistoryEntry } from '@/lib/types';
import { clsx } from 'clsx';

interface GarminSyncSettingsProps {
  className?: string;
  onSyncComplete?: () => void;
}

const POLL_INTERVAL = 1500;

export function GarminSyncSettings({ className, onSyncComplete }: GarminSyncSettingsProps) {
  // Configuration state
  const [config, setConfig] = useState<GarminSyncConfig | null>(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [configError, setConfigError] = useState<string | null>(null);
  const [savingConfig, setSavingConfig] = useState(false);

  // Sync history state
  const [history, setHistory] = useState<GarminSyncHistoryEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  // Manual sync state
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncJobId, setSyncJobId] = useState<string | null>(null);
  const [syncProgress, setSyncProgress] = useState(0);
  const [syncStep, setSyncStep] = useState('');
  const [syncError, setSyncError] = useState<string | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Load config and history on mount
  useEffect(() => {
    loadConfig();
    loadHistory();
  }, []);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const loadConfig = async () => {
    try {
      setConfigLoading(true);
      setConfigError(null);
      const data = await getGarminSyncConfig();
      setConfig(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load sync configuration';
      setConfigError(message);
    } finally {
      setConfigLoading(false);
    }
  };

  const loadHistory = async () => {
    try {
      setHistoryLoading(true);
      const data = await getGarminSyncHistory(10);
      setHistory(data);
    } catch (err) {
      console.error('Failed to load sync history:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleToggleAutoSync = async () => {
    if (!config) return;

    try {
      setSavingConfig(true);
      const updated = await updateGarminSyncConfig({
        auto_sync_enabled: !config.auto_sync_enabled,
      });
      setConfig(updated);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update configuration';
      setConfigError(message);
    } finally {
      setSavingConfig(false);
    }
  };

  // Poll for sync job status
  const pollJobStatus = useCallback(async (jobId: string) => {
    try {
      const status = await getSyncJobStatus(jobId);

      setSyncProgress(status.progress_percent);
      setSyncStep(status.current_step);

      if (status.status === 'completed') {
        // Stop polling
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }

        setIsSyncing(false);
        setSyncJobId(null);
        loadHistory(); // Refresh history

        if (onSyncComplete) {
          onSyncComplete();
        }
      } else if (status.status === 'failed') {
        // Stop polling
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }

        setIsSyncing(false);
        setSyncJobId(null);
        setSyncError(status.error || 'Sync failed');
        loadHistory(); // Refresh history to show failed entry
      }
    } catch (err) {
      console.error('Error polling job status:', err);
    }
  }, [onSyncComplete]);

  const handleManualSync = async () => {
    try {
      setIsSyncing(true);
      setSyncError(null);
      setSyncProgress(0);
      setSyncStep('Starting sync...');

      const response = await triggerManualSync();
      setSyncJobId(response.job_id);

      // Start polling
      pollIntervalRef.current = setInterval(() => {
        pollJobStatus(response.job_id);
      }, POLL_INTERVAL);

      // Poll immediately
      pollJobStatus(response.job_id);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start sync';
      setSyncError(message);
      setIsSyncing(false);
    }
  };

  // Convert UTC time to user's local time
  const formatLocalTime = (utcHour: number): string => {
    const utcDate = new Date();
    utcDate.setUTCHours(utcHour, 0, 0, 0);
    return utcDate.toLocaleTimeString(undefined, {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  // Format timestamp in user's locale
  const formatTimestamp = (isoString: string): string => {
    const date = new Date(isoString);
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  // Get relative time (e.g., "2 hours ago")
  const getRelativeTime = (isoString: string): string => {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatTimestamp(isoString);
  };

  // Get status icon and color
  const getStatusDisplay = (status: GarminSyncHistoryEntry['status']) => {
    switch (status) {
      case 'completed':
        return {
          icon: <CheckIcon className="w-4 h-4" />,
          color: 'text-green-400',
          bgColor: 'bg-green-900/30',
          label: 'Completed',
        };
      case 'failed':
        return {
          icon: <ErrorIcon className="w-4 h-4" />,
          color: 'text-red-400',
          bgColor: 'bg-red-900/30',
          label: 'Failed',
        };
      case 'running':
        return {
          icon: <LoadingSpinner size="xs" />,
          color: 'text-teal-400',
          bgColor: 'bg-teal-900/30',
          label: 'Running',
        };
    }
  };

  if (configLoading) {
    return (
      <div className={clsx('bg-gray-900 rounded-lg border border-gray-800 p-6', className)}>
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner size="md" label="Loading sync settings..." />
        </div>
      </div>
    );
  }

  if (configError && !config) {
    return (
      <div className={clsx('bg-gray-900 rounded-lg border border-gray-800 p-6', className)}>
        <div className="flex items-start gap-2 p-3 bg-red-900/20 border border-red-800 rounded-md">
          <ErrorIcon className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm text-red-400">{configError}</p>
            <button
              onClick={loadConfig}
              className="text-sm text-red-300 underline hover:text-red-200 mt-1"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const lastSync = history.find(h => h.status !== 'running');
  const runningSync = history.find(h => h.status === 'running');
  const isCurrentlySyncing = isSyncing || !!runningSync;

  return (
    <div className={clsx('bg-gray-900 rounded-lg border border-gray-800', className)}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <SettingsIcon className="w-5 h-5 text-gray-400" />
          <div>
            <h3 className="text-base font-medium text-gray-100">Auto-Sync Settings</h3>
            <p className="text-sm text-gray-400">Configure automatic activity syncing</p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Auto-sync toggle */}
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <label className="text-sm font-medium text-gray-200">
              Enable automatic sync
            </label>
            <p className="text-xs text-gray-400 mt-0.5">
              Syncs daily at 6 AM UTC ({formatLocalTime(6)} your time)
            </p>
          </div>
          <button
            onClick={handleToggleAutoSync}
            disabled={savingConfig}
            className={clsx(
              'relative w-12 h-6 rounded-full transition-colors',
              config?.auto_sync_enabled ? 'bg-teal-600' : 'bg-gray-600',
              savingConfig && 'opacity-50 cursor-not-allowed'
            )}
            aria-checked={config?.auto_sync_enabled}
            role="switch"
          >
            <span
              className={clsx(
                'absolute top-0.5 w-5 h-5 bg-white rounded-full transition-transform',
                config?.auto_sync_enabled ? 'translate-x-6' : 'translate-x-0.5'
              )}
            />
          </button>
        </div>

        {/* Last sync status */}
        {lastSync && (
          <div className="p-4 bg-gray-800/50 rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Last sync</span>
              <span className="text-xs text-gray-500">
                {lastSync.completed_at
                  ? getRelativeTime(lastSync.completed_at)
                  : getRelativeTime(lastSync.started_at)}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {(() => {
                const display = getStatusDisplay(lastSync.status);
                return (
                  <>
                    <span className={clsx('p-1 rounded', display.bgColor, display.color)}>
                      {display.icon}
                    </span>
                    <span className={clsx('text-sm font-medium', display.color)}>
                      {display.label}
                    </span>
                    {lastSync.status === 'completed' && (
                      <span className="text-sm text-gray-400">
                        - {lastSync.activities_synced} activities
                      </span>
                    )}
                    {lastSync.status === 'failed' && lastSync.error_message && (
                      <span className="text-sm text-gray-400 truncate max-w-[200px]">
                        - {lastSync.error_message}
                      </span>
                    )}
                  </>
                );
              })()}
            </div>
          </div>
        )}

        {/* Sync error message */}
        {syncError && (
          <div className="flex items-start gap-2 p-3 bg-red-900/20 border border-red-800 rounded-md">
            <ErrorIcon className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
            <p className="text-sm text-red-400">{syncError}</p>
          </div>
        )}

        {/* Sync progress */}
        {isCurrentlySyncing && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">{syncStep || 'Syncing...'}</span>
              <span className="text-teal-400 font-mono">{syncProgress}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
              <div
                className="bg-teal-500 h-full rounded-full transition-all duration-300"
                style={{ width: `${syncProgress}%` }}
              />
            </div>
          </div>
        )}

        {/* Sync Now button */}
        <Button
          onClick={handleManualSync}
          variant="primary"
          isLoading={isCurrentlySyncing}
          disabled={isCurrentlySyncing}
          leftIcon={<SyncIcon className="w-4 h-4" />}
          fullWidth
        >
          {isCurrentlySyncing ? 'Syncing...' : 'Sync Now'}
        </Button>

        {/* Sync History */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-300">Sync History</h4>
          {historyLoading ? (
            <div className="flex justify-center py-4">
              <LoadingSpinner size="sm" />
            </div>
          ) : history.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-4">
              No sync history yet
            </p>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {history.slice(0, 5).map((entry) => {
                const display = getStatusDisplay(entry.status);
                return (
                  <div
                    key={entry.id}
                    className="flex items-center justify-between p-2 bg-gray-800/50 rounded-md"
                  >
                    <div className="flex items-center gap-2">
                      <span className={clsx('p-1 rounded', display.bgColor, display.color)}>
                        {display.icon}
                      </span>
                      <div className="flex flex-col">
                        <span className="text-sm text-gray-200">
                          {entry.sync_type === 'scheduled' ? 'Scheduled' : 'Manual'}
                        </span>
                        <span className="text-xs text-gray-500">
                          {formatTimestamp(entry.started_at)}
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={clsx('text-sm', display.color)}>
                        {entry.status === 'completed'
                          ? `${entry.activities_synced} activities`
                          : entry.status === 'failed'
                          ? 'Failed'
                          : 'Running'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Icon components
function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
      />
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

export default GarminSyncSettings;
