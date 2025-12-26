'use client';

import { useState, useCallback } from 'react';
import { useFITExport } from '@/hooks/useFITExport';

interface FITExportButtonProps {
  workoutId: string;
  workoutName: string;
  disabled?: boolean;
  className?: string;
}

type ExportState = 'idle' | 'downloading' | 'exporting' | 'success' | 'error';

export function FITExportButton({
  workoutId,
  workoutName,
  disabled = false,
  className = '',
}: FITExportButtonProps) {
  const [showDropdown, setShowDropdown] = useState(false);
  const [exportState, setExportState] = useState<ExportState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const {
    downloadFIT,
    exportToGarmin,
    isDownloading,
    isExporting,
    garminConnected,
    checkingConnection,
  } = useFITExport();

  const handleDownloadFIT = useCallback(async () => {
    setExportState('downloading');
    setErrorMessage(null);
    setSuccessMessage(null);
    setShowDropdown(false);

    try {
      await downloadFIT(workoutId, workoutName);
      setExportState('success');
      setSuccessMessage('FIT file downloaded successfully!');
      setTimeout(() => {
        setExportState('idle');
        setSuccessMessage(null);
      }, 3000);
    } catch (error) {
      setExportState('error');
      setErrorMessage(
        error instanceof Error ? error.message : 'Failed to download FIT file'
      );
      setTimeout(() => {
        setExportState('idle');
        setErrorMessage(null);
      }, 5000);
    }
  }, [downloadFIT, workoutId, workoutName]);

  const handleExportToGarmin = useCallback(async () => {
    setExportState('exporting');
    setErrorMessage(null);
    setSuccessMessage(null);
    setShowDropdown(false);

    try {
      const result = await exportToGarmin(workoutId);
      if (result.success) {
        setExportState('success');
        setSuccessMessage(
          result.message || 'Workout exported to Garmin Connect!'
        );
        setTimeout(() => {
          setExportState('idle');
          setSuccessMessage(null);
        }, 3000);
      } else {
        throw new Error(result.message || 'Export failed');
      }
    } catch (error) {
      setExportState('error');
      setErrorMessage(
        error instanceof Error ? error.message : 'Failed to export to Garmin'
      );
      setTimeout(() => {
        setExportState('idle');
        setErrorMessage(null);
      }, 5000);
    }
  }, [exportToGarmin, workoutId]);

  const isLoading = isDownloading || isExporting || checkingConnection;
  const isDisabled = disabled || isLoading;

  // Button content based on state
  const getButtonContent = () => {
    if (exportState === 'downloading') {
      return (
        <>
          <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          Downloading...
        </>
      );
    }

    if (exportState === 'exporting') {
      return (
        <>
          <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          Exporting...
        </>
      );
    }

    if (exportState === 'success') {
      return (
        <>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
          Success!
        </>
      );
    }

    if (exportState === 'error') {
      return (
        <>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
          Error
        </>
      );
    }

    return (
      <>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
          />
        </svg>
        Export
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </>
    );
  };

  // Button color based on state
  const getButtonColor = () => {
    if (exportState === 'success') {
      return 'bg-green-600 hover:bg-green-700';
    }
    if (exportState === 'error') {
      return 'bg-red-600 hover:bg-red-700';
    }
    return 'bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400';
  };

  return (
    <div className={`relative ${className}`}>
      {/* Main button */}
      <button
        type="button"
        onClick={() => setShowDropdown(!showDropdown)}
        disabled={isDisabled}
        className={`flex items-center gap-2 px-4 py-2 text-white font-medium rounded-lg transition-colors disabled:cursor-not-allowed ${getButtonColor()}`}
      >
        {getButtonContent()}
      </button>

      {/* Dropdown menu */}
      {showDropdown && exportState === 'idle' && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowDropdown(false)}
          />

          {/* Menu */}
          <div className="absolute right-0 mt-2 w-64 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-20">
            <div className="p-2">
              {/* Download FIT */}
              <button
                type="button"
                onClick={handleDownloadFIT}
                className="w-full flex items-center gap-3 px-3 py-2 text-left rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <div className="w-10 h-10 flex items-center justify-center bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-lg">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10"
                    />
                  </svg>
                </div>
                <div>
                  <div className="font-medium text-gray-900 dark:text-white">
                    Download FIT File
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Save to your computer
                  </div>
                </div>
              </button>

              {/* Divider */}
              <div className="my-2 border-t border-gray-200 dark:border-gray-700" />

              {/* Export to Garmin */}
              <button
                type="button"
                onClick={handleExportToGarmin}
                disabled={!garminConnected}
                className={`w-full flex items-center gap-3 px-3 py-2 text-left rounded-lg transition-colors ${
                  garminConnected
                    ? 'hover:bg-gray-100 dark:hover:bg-gray-700'
                    : 'opacity-50 cursor-not-allowed'
                }`}
              >
                <div className="w-10 h-10 flex items-center justify-center bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 rounded-lg">
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
                  </svg>
                </div>
                <div>
                  <div className="font-medium text-gray-900 dark:text-white">
                    Export to Garmin Connect
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {garminConnected
                      ? 'Sync directly to your watch'
                      : 'Connect Garmin account first'}
                  </div>
                </div>
              </button>

              {/* Connection status */}
              {!garminConnected && !checkingConnection && (
                <div className="mt-2 px-3 py-2 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  Go to Settings to connect Garmin
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* Success/Error message toast */}
      {(successMessage || errorMessage) && (
        <div
          className={`absolute top-full mt-2 right-0 px-4 py-2 rounded-lg text-sm font-medium shadow-lg z-30 whitespace-nowrap ${
            successMessage
              ? 'bg-green-600 text-white'
              : 'bg-red-600 text-white'
          }`}
        >
          {successMessage || errorMessage}
        </div>
      )}
    </div>
  );
}

// Simplified version just for download
export function FITDownloadButton({
  workoutId,
  workoutName,
  disabled = false,
  className = '',
}: FITExportButtonProps) {
  const { downloadFIT, isDownloading } = useFITExport();
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');

  const handleDownload = useCallback(async () => {
    try {
      await downloadFIT(workoutId, workoutName);
      setStatus('success');
      setTimeout(() => setStatus('idle'), 2000);
    } catch {
      setStatus('error');
      setTimeout(() => setStatus('idle'), 3000);
    }
  }, [downloadFIT, workoutId, workoutName]);

  return (
    <button
      type="button"
      onClick={handleDownload}
      disabled={disabled || isDownloading}
      className={`flex items-center gap-2 px-4 py-2 font-medium rounded-lg transition-colors disabled:cursor-not-allowed ${
        status === 'success'
          ? 'bg-green-600 text-white'
          : status === 'error'
          ? 'bg-red-600 text-white'
          : 'bg-blue-600 hover:bg-blue-700 text-white disabled:bg-blue-400'
      } ${className}`}
    >
      {isDownloading ? (
        <>
          <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          Downloading...
        </>
      ) : status === 'success' ? (
        <>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          Downloaded!
        </>
      ) : status === 'error' ? (
        <>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
          Failed
        </>
      ) : (
        <>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
          Download FIT
        </>
      )}
    </button>
  );
}

export default FITExportButton;
