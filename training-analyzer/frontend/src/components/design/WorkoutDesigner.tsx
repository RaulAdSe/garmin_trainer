'use client';

import { useState, useCallback, useMemo } from 'react';
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

const WORKOUT_TYPES: { value: WorkoutType; label: string; icon: string }[] = [
  { value: 'running', label: 'Running', icon: 'M13 16.12c.68-.19 1.29-.36 1.92-.36.64 0 1.25.17 1.94.36l.58.16c.44.12.9-.03 1.21-.35l2.35-2.35c-.7-1.1-1.74-1.99-2.98-2.57l-1.96 1.96-.7-.7 1.5-1.5c-.35-.1-.7-.19-1.07-.26-.41-.07-.81-.11-1.22-.11-.41 0-.81.04-1.22.11-.37.07-.72.16-1.07.26l1.5 1.5-.7.7-1.96-1.96c-1.24.58-2.28 1.47-2.98 2.57l2.35 2.35c.31.32.77.47 1.21.35l.58-.16zM5.5 14.5c0 1.93.57 3.73 1.55 5.24A10.05 10.05 0 0012 21.5c1.93 0 3.73-.57 5.24-1.55A10.05 10.05 0 0018.5 14.5a6.5 6.5 0 00-13 0zm16 0a8.5 8.5 0 01-17 0 8.5 8.5 0 0117 0z' },
  { value: 'cycling', label: 'Cycling', icon: 'M15.5 5.5c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zM5 12c-2.8 0-5 2.2-5 5s2.2 5 5 5 5-2.2 5-5-2.2-5-5-5zm0 8.5c-1.9 0-3.5-1.6-3.5-3.5s1.6-3.5 3.5-3.5 3.5 1.6 3.5 3.5-1.6 3.5-3.5 3.5zm5.8-10l2.4-2.4.8.8c1.3 1.3 3 2.1 5.1 2.1V9c-1.5 0-2.7-.6-3.6-1.5l-1.9-1.9c-.5-.4-1-.6-1.6-.6s-1.1.2-1.4.6L7.8 8.4c-.4.4-.6.9-.6 1.4 0 .6.2 1.1.6 1.4L11 14v5h2v-6.2l-2.2-2.3zM19 12c-2.8 0-5 2.2-5 5s2.2 5 5 5 5-2.2 5-5-2.2-5-5-5zm0 8.5c-1.9 0-3.5-1.6-3.5-3.5s1.6-3.5 3.5-3.5 3.5 1.6 3.5 3.5-1.6 3.5-3.5 3.5z' },
  { value: 'swimming', label: 'Swimming', icon: 'M22 21c-1.11 0-1.73-.37-2.18-.64-.37-.22-.6-.36-1.15-.36-.56 0-.78.13-1.15.36-.46.27-1.07.64-2.18.64s-1.73-.37-2.18-.64c-.37-.22-.6-.36-1.15-.36-.56 0-.78.13-1.15.36-.46.27-1.08.64-2.19.64-1.11 0-1.73-.37-2.18-.64-.37-.23-.6-.36-1.15-.36s-.78.13-1.15.36c-.46.27-1.08.64-2.19.64v-2c.56 0 .78-.13 1.15-.36.46-.27 1.08-.64 2.19-.64s1.73.37 2.18.64c.37.23.59.36 1.15.36.56 0 .78-.13 1.15-.36.46-.27 1.08-.64 2.19-.64 1.11 0 1.73.37 2.18.64.37.22.6.36 1.15.36s.78-.13 1.15-.36c.45-.27 1.07-.64 2.18-.64s1.73.37 2.18.64c.37.22.6.36 1.15.36v2zm0-4.5c-1.11 0-1.73-.37-2.18-.64-.37-.22-.6-.36-1.15-.36-.56 0-.78.13-1.15.36-.45.27-1.07.64-2.18.64s-1.73-.37-2.18-.64c-.37-.22-.6-.36-1.15-.36-.56 0-.78.13-1.15.36-.45.27-1.07.64-2.18.64s-1.73-.37-2.18-.64c-.37-.22-.6-.36-1.15-.36s-.78.13-1.15.36c-.47.27-1.09.64-2.2.64v-2c.56 0 .78-.13 1.15-.36.45-.27 1.07-.64 2.18-.64s1.73.37 2.18.64c.37.22.6.36 1.15.36.56 0 .78-.13 1.15-.36.45-.27 1.07-.64 2.18-.64s1.73.37 2.18.64c.37.22.6.36 1.15.36s.78-.13 1.15-.36c.45-.27 1.07-.64 2.18-.64s1.73.37 2.18.64c.37.22.6.36 1.15.36v2zM8.67 12c.56 0 .78-.13 1.15-.36.46-.27 1.08-.64 2.19-.64 1.11 0 1.73.37 2.18.64.37.22.6.36 1.15.36s.78-.13 1.15-.36c.12-.07.26-.15.41-.23L10.48 5C10.03 4.37 9.3 4 8.5 4c-.87 0-1.67.48-2.08 1.25L4.48 9h5.23l1.41 1.41-4.63 4.63c.85.32 1.46.74 1.84.99.37.19.59.33 1.34.33v-.36z' },
  { value: 'strength', label: 'Strength', icon: 'M20.57 14.86L22 13.43 20.57 12 17 15.57 8.43 7 12 3.43 10.57 2 9.14 3.43 7.71 2 5.57 4.14 4.14 2.71 2.71 4.14l1.43 1.43L2 7.71l1.43 1.43L2 10.57 3.43 12 7 8.43 15.57 17 12 20.57 13.43 22l1.43-1.43L16.29 22l2.14-2.14 1.43 1.43 1.43-1.43-1.43-1.43L22 16.29l-1.43-1.43z' },
  { value: 'hiit', label: 'HIIT', icon: 'M13 2.05v2.02c3.95.49 7 3.85 7 7.93 0 3.21-1.92 6-4.72 7.28L13 17v5.05c5.05-.5 9-4.76 9-9.95 0-5.19-3.95-9.45-9-9.95zM11 2.05C5.95 2.55 2 6.81 2 12c0 5.19 3.95 9.45 9 9.95V17l-2.28 2.28C5.92 18 4 15.21 4 12c0-4.08 3.05-7.44 7-7.93V2.05z' },
  { value: 'walking', label: 'Walking', icon: 'M13.5 5.5c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zM9.8 8.9L7 23h2.1l1.8-8 2.1 2v6h2v-7.5l-2.1-2 .6-3C14.8 12 16.8 13 19 13v-2c-1.9 0-3.5-1-4.3-2.4l-1-1.6c-.4-.6-1-1-1.7-1-.3 0-.5.1-.8.1L6 8.3V13h2V9.6l1.8-.7' },
];

// Generate unique ID
function generateId(): string {
  return `workout-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// Create a blank workout
function createBlankWorkout(type: WorkoutType): DesignedWorkout {
  return {
    name: '',
    type,
    intervals: [],
    totalDuration: 0,
  };
}

export function WorkoutDesigner({
  initialWorkout,
  onSave,
  onCancel,
  className = '',
}: WorkoutDesignerProps) {
  const [mode, setMode] = useState<'manual' | 'ai'>(
    initialWorkout ? 'manual' : 'ai'
  );
  const [workout, setWorkout] = useState<DesignedWorkout>(
    initialWorkout || createBlankWorkout('running')
  );
  const [savedWorkoutId, setSavedWorkoutId] = useState<string | null>(
    initialWorkout?.id || null
  );

  // Save workout mutation
  const saveMutation = useMutation({
    mutationFn: saveDesignedWorkout,
    onSuccess: (data) => {
      setSavedWorkoutId(data.id);
      setWorkout(data.workout);
      onSave?.(data.workout);
    },
  });

  // Update workout type
  const handleTypeChange = useCallback((type: WorkoutType) => {
    setWorkout((prev) => ({ ...prev, type }));
  }, []);

  // Update workout name
  const handleNameChange = useCallback((name: string) => {
    setWorkout((prev) => ({ ...prev, name }));
  }, []);

  // Update workout description
  const handleDescriptionChange = useCallback((description: string) => {
    setWorkout((prev) => ({ ...prev, description }));
  }, []);

  // Update intervals
  const handleIntervalsChange = useCallback((intervals: WorkoutInterval[]) => {
    const totalDuration = intervals.reduce((sum, i) => sum + i.duration, 0);
    const totalDistance = intervals.reduce(
      (sum, i) => sum + (i.distance || 0),
      0
    );
    setWorkout((prev) => ({
      ...prev,
      intervals,
      totalDuration,
      totalDistance: totalDistance > 0 ? totalDistance : undefined,
    }));
  }, []);

  // Handle AI suggestion selection
  const handleSelectAISuggestion = useCallback((aiWorkout: DesignedWorkout) => {
    setWorkout({
      ...aiWorkout,
      id: undefined, // Clear ID so it creates a new workout
      aiGenerated: true,
    });
    setMode('manual'); // Switch to manual mode for customization
    setSavedWorkoutId(null);
  }, []);

  // Handle interval click in visualizer
  const handleIntervalClick = useCallback(
    (_interval: WorkoutInterval, _index: number) => {
      // Could expand/scroll to interval in builder
    },
    []
  );

  // Save workout
  const handleSave = useCallback(() => {
    if (!workout.name.trim()) {
      alert('Please enter a workout name');
      return;
    }
    if (workout.intervals.length === 0) {
      alert('Please add at least one interval');
      return;
    }

    saveMutation.mutate({
      workout: {
        ...workout,
        id: savedWorkoutId || undefined,
      },
    });
  }, [workout, savedWorkoutId, saveMutation]);

  // Check if workout is valid for saving
  const isValid = useMemo(() => {
    return workout.name.trim() !== '' && workout.intervals.length > 0;
  }, [workout]);

  // Check if there are unsaved changes
  const hasChanges = useMemo(() => {
    if (!initialWorkout) return workout.intervals.length > 0;
    return JSON.stringify(workout) !== JSON.stringify(initialWorkout);
  }, [workout, initialWorkout]);

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {initialWorkout ? 'Edit Workout' : 'Design Workout'}
          </h1>
          <p className="mt-1 text-gray-500 dark:text-gray-400">
            Create a structured workout with intervals
          </p>
        </div>

        <div className="flex items-center gap-3">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            >
              Cancel
            </button>
          )}

          <button
            type="button"
            onClick={handleSave}
            disabled={!isValid || saveMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {saveMutation.isPending ? (
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
                Saving...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"
                  />
                </svg>
                Save Workout
              </>
            )}
          </button>

          {savedWorkoutId && (
            <FITExportButton
              workoutId={savedWorkoutId}
              workoutName={workout.name}
              disabled={hasChanges}
            />
          )}
        </div>
      </div>

      {/* Save error */}
      {saveMutation.isError && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          Failed to save workout. Please try again.
        </div>
      )}

      {/* Save success */}
      {saveMutation.isSuccess && !hasChanges && (
        <div className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-green-600 dark:text-green-400 flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
          Workout saved successfully!
        </div>
      )}

      {/* Workout type selection */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Workout Type
        </label>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
          {WORKOUT_TYPES.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => handleTypeChange(value)}
              className={`flex flex-col items-center gap-2 p-3 rounded-lg border transition-colors ${
                workout.type === value
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400'
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 text-gray-700 dark:text-gray-300'
              }`}
            >
              <span className="text-sm font-medium">{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Workout name and description */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4 space-y-4">
        <div>
          <label
            htmlFor="workout-name"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Workout Name
          </label>
          <input
            id="workout-name"
            type="text"
            value={workout.name}
            onChange={(e) => handleNameChange(e.target.value)}
            placeholder="e.g., Tempo Run with Intervals"
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label
            htmlFor="workout-description"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Description (optional)
          </label>
          <textarea
            id="workout-description"
            value={workout.description || ''}
            onChange={(e) => handleDescriptionChange(e.target.value)}
            placeholder="Describe the purpose and goals of this workout..."
            rows={2}
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          />
        </div>
      </div>

      {/* Mode toggle */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setMode('ai')}
          className={`flex-1 py-3 px-4 font-medium rounded-lg transition-colors flex items-center justify-center gap-2 ${
            mode === 'ai'
              ? 'bg-purple-600 text-white'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          AI Assistant
        </button>
        <button
          type="button"
          onClick={() => setMode('manual')}
          className={`flex-1 py-3 px-4 font-medium rounded-lg transition-colors flex items-center justify-center gap-2 ${
            mode === 'manual'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
            />
          </svg>
          Manual Builder
        </button>
      </div>

      {/* AI mode */}
      {mode === 'ai' && (
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
          <AIWorkoutSuggestions
            workoutType={workout.type}
            onSelectSuggestion={handleSelectAISuggestion}
          />
        </div>
      )}

      {/* Manual mode */}
      {mode === 'manual' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Interval builder */}
          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
            <IntervalBuilder
              intervals={workout.intervals}
              onChange={handleIntervalsChange}
            />
          </div>

          {/* Interval visualizer */}
          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Workout Structure
            </h3>
            <IntervalVisualizer
              intervals={workout.intervals}
              onIntervalClick={handleIntervalClick}
              height={150}
            />
          </div>
        </div>
      )}

      {/* AI generated badge */}
      {workout.aiGenerated && (
        <div className="flex items-center gap-2 text-sm text-purple-600 dark:text-purple-400">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          This workout was generated by AI. You can customize it above.
        </div>
      )}
    </div>
  );
}

export default WorkoutDesigner;
