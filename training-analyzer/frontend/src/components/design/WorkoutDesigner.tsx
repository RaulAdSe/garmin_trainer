'use client';

import { useState, useCallback, useMemo, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import type { WorkoutType, WorkoutInterval, DesignedWorkout } from '@/lib/types';
import { saveDesignedWorkout } from '@/lib/api-client';
import { IntervalBuilder } from './IntervalBuilder';
import { IntervalVisualizer } from './IntervalVisualizer';
import { AIWorkoutSuggestions } from './AIWorkoutSuggestions';
import { FITExportButton } from './FITExportButton';

interface WorkoutDesignerProps {
  initialWorkout?: DesignedWorkout;
  onSave?: (workout: DesignedWorkout) => void;
  onCancel?: () => void;
  className?: string;
}

const WORKOUT_TYPES: { value: WorkoutType; label: string }[] = [
  { value: 'running', label: 'Run' },
  { value: 'cycling', label: 'Bike' },
  { value: 'swimming', label: 'Swim' },
  { value: 'strength', label: 'Strength' },
  { value: 'hiit', label: 'HIIT' },
  { value: 'walking', label: 'Walk' },
];

function createBlankWorkout(type: WorkoutType): DesignedWorkout {
  return { name: '', type, intervals: [], totalDuration: 0 };
}

export function WorkoutDesigner({
  initialWorkout,
  onSave,
  onCancel,
  className = '',
}: WorkoutDesignerProps) {
  const [showManualBuilder, setShowManualBuilder] = useState(!!initialWorkout);
  const [showDetails, setShowDetails] = useState(false);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [workout, setWorkout] = useState<DesignedWorkout>(
    initialWorkout || createBlankWorkout('running')
  );
  const [savedWorkoutId, setSavedWorkoutId] = useState<string | null>(
    initialWorkout?.id || null
  );

  // Auto-dismiss toast
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const saveMutation = useMutation({
    mutationFn: saveDesignedWorkout,
    onSuccess: (data) => {
      setSavedWorkoutId(data.id);
      setWorkout(data.workout);
      onSave?.(data.workout);
      setToast({ type: 'success', message: 'Workout saved!' });
    },
    onError: () => {
      setToast({ type: 'error', message: 'Failed to save. Please try again.' });
    },
  });

  const handleTypeChange = useCallback((type: WorkoutType) => {
    setWorkout((prev) => ({ ...prev, type }));
  }, []);

  const handleNameChange = useCallback((name: string) => {
    setWorkout((prev) => ({ ...prev, name }));
  }, []);

  const handleDescriptionChange = useCallback((description: string) => {
    setWorkout((prev) => ({ ...prev, description }));
  }, []);

  const handleIntervalsChange = useCallback((intervals: WorkoutInterval[]) => {
    const totalDuration = intervals.reduce((sum, i) => sum + i.duration, 0);
    const totalDistance = intervals.reduce((sum, i) => sum + (i.distance || 0), 0);
    setWorkout((prev) => ({
      ...prev,
      intervals,
      totalDuration,
      totalDistance: totalDistance > 0 ? totalDistance : undefined,
    }));
  }, []);

  const handleSelectAISuggestion = useCallback((aiWorkout: DesignedWorkout) => {
    setWorkout({ ...aiWorkout, id: undefined, aiGenerated: true });
    setShowManualBuilder(true);
    setSavedWorkoutId(null);
  }, []);

  const handleSave = useCallback(() => {
    if (!workout.name.trim()) {
      setToast({ type: 'error', message: 'Please enter a workout name' });
      return;
    }
    if (workout.intervals.length === 0) {
      setToast({ type: 'error', message: 'Please add at least one interval' });
      return;
    }
    saveMutation.mutate({ workout: { ...workout, id: savedWorkoutId || undefined } });
  }, [workout, savedWorkoutId, saveMutation]);

  const isValid = useMemo(() => {
    return workout.name.trim() !== '' && workout.intervals.length > 0;
  }, [workout]);

  const hasChanges = useMemo(() => {
    if (!initialWorkout) return workout.intervals.length > 0;
    return JSON.stringify(workout) !== JSON.stringify(initialWorkout);
  }, [workout, initialWorkout]);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Toast notification */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg flex items-center gap-2 ${toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'} text-white`}>
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={toast.type === 'success' ? 'M5 13l4 4L19 7' : 'M6 18L18 6M6 6l12 12'} />
          </svg>
          {toast.message}
        </div>
      )}

      {/* Header with inline name input and actions */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <input
          type="text"
          value={workout.name}
          onChange={(e) => handleNameChange(e.target.value)}
          placeholder="Workout name..."
          className="flex-1 px-4 py-2 text-lg font-medium border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <div className="flex items-center gap-2">
          {onCancel && (
            <button type="button" onClick={onCancel} className="px-3 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
              Cancel
            </button>
          )}
          <button
            type="button"
            onClick={handleSave}
            disabled={!isValid || saveMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {saveMutation.isPending ? 'Saving...' : 'Save'}
          </button>
          {savedWorkoutId && (
            <FITExportButton workoutId={savedWorkoutId} workoutName={workout.name} disabled={hasChanges} />
          )}
        </div>
      </div>

      {/* Workout type pills */}
      <div className="flex flex-wrap gap-2">
        {WORKOUT_TYPES.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            onClick={() => handleTypeChange(value)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              workout.type === value
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
          >
            {label}
          </button>
        ))}
        {/* Collapsible details toggle */}
        <button
          type="button"
          onClick={() => setShowDetails(!showDetails)}
          className="px-3 py-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 flex items-center gap-1"
        >
          <svg className={`w-4 h-4 transition-transform ${showDetails ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
          Details
        </button>
      </div>

      {/* Collapsible description */}
      {showDetails && (
        <textarea
          value={workout.description || ''}
          onChange={(e) => handleDescriptionChange(e.target.value)}
          placeholder="Describe the workout goals and focus..."
          rows={2}
          className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 resize-none"
        />
      )}

      {/* AI Suggestions - Hero section */}
      {!showManualBuilder && (
        <div className="bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-xl border border-purple-200 dark:border-purple-800 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <span className="text-purple-600">*</span> AI Workout Generator
          </h2>
          <AIWorkoutSuggestions workoutType={workout.type} onSelectSuggestion={handleSelectAISuggestion} />
          <button type="button" onClick={() => setShowManualBuilder(true)} className="mt-4 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
            + Build from scratch
          </button>
        </div>
      )}

      {/* Manual builder */}
      {showManualBuilder && (
        <div className="space-y-4">
          {workout.aiGenerated && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-purple-600 dark:text-purple-400">* AI-generated - customize below</span>
              <button type="button" onClick={() => { setShowManualBuilder(false); setWorkout(createBlankWorkout(workout.type)); }} className="text-gray-500 hover:text-gray-700">
                Start over with AI
              </button>
            </div>
          )}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
              <IntervalBuilder intervals={workout.intervals} onChange={handleIntervalsChange} />
            </div>
            <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Preview</h3>
              <IntervalVisualizer intervals={workout.intervals} height={120} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default WorkoutDesigner;
