'use client';

import { useState, useCallback } from 'react';
import { db } from '@/services/database';

type ExportState = 'idle' | 'exporting' | 'success' | 'error';

interface ExportDataButtonProps {
  className?: string;
}

export function ExportDataButton({ className }: ExportDataButtonProps) {
  const [state, setState] = useState<ExportState>('idle');
  const [error, setError] = useState<string | null>(null);

  const handleExport = useCallback(async () => {
    setState('exporting');
    setError(null);

    try {
      // Get exported data
      const jsonData = await db.exportData();

      // Generate filename with current date
      const date = new Date().toISOString().split('T')[0];
      const filename = `wellness-data-${date}.json`;

      // Create blob and download
      const blob = new Blob([jsonData], { type: 'application/json' });
      const url = URL.createObjectURL(blob);

      // Create temporary link and trigger download
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Clean up the URL
      URL.revokeObjectURL(url);

      setState('success');

      // Reset to idle after showing success
      setTimeout(() => setState('idle'), 2000);
    } catch (err) {
      console.error('Export failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to export data');
      setState('error');
    }
  }, []);

  return (
    <div className={className}>
      <button
        onClick={handleExport}
        disabled={state === 'exporting'}
        className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-zinc-800 border border-zinc-700 text-white font-medium hover:bg-zinc-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {state === 'exporting' ? (
          <>
            <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span>Exporting...</span>
          </>
        ) : state === 'success' ? (
          <>
            <svg className="w-5 h-5 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span className="text-teal-400">Exported!</span>
          </>
        ) : (
          <>
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span>Export Data</span>
          </>
        )}
      </button>

      {error && (
        <div className="mt-2 flex items-start gap-2 p-3 bg-red-900/20 border border-red-800/50 rounded-xl">
          <svg className="w-4 h-4 text-red-400 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}
    </div>
  );
}

export default ExportDataButton;
