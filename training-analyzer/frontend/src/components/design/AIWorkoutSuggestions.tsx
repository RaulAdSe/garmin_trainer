'use client';

import { useState, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import type {
  AIWorkoutSuggestion,
  GenerateWorkoutRequest,
  WorkoutType,
  DesignedWorkout,
} from '@/lib/types';
import { generateWorkoutSuggestions } from '@/lib/api-client';
import { IntervalVisualizerCompact } from './IntervalVisualizer';

interface AIWorkoutSuggestionsProps {
  workoutType: WorkoutType;
  onSelectSuggestion: (workout: DesignedWorkout) => void;
  className?: string;
}

// Format duration in minutes
function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  if (mins >= 60) {
    const hours = Math.floor(mins / 60);
    const remainingMins = mins % 60;
    return remainingMins > 0 ? `${hours}h ${remainingMins}m` : `${hours}h`;
  }
  return `${mins}m`;
}

// Difficulty badge colors
const DIFFICULTY_COLORS = {
  easy: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  moderate: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  hard: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  very_hard: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
};

const DIFFICULTY_LABELS = {
  easy: 'Easy',
  moderate: 'Moderate',
  hard: 'Hard',
  very_hard: 'Very Hard',
};

interface SuggestionCardProps {
  suggestion: AIWorkoutSuggestion;
  isSelected: boolean;
  onSelect: () => void;
  onUse: () => void;
}

function SuggestionCard({
  suggestion,
  isSelected,
  onSelect,
  onUse,
}: SuggestionCardProps) {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div
      className={`border rounded-lg p-4 transition-all cursor-pointer ${
        isSelected
          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 ring-2 ring-blue-500'
          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
      }`}
      onClick={onSelect}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-gray-900 dark:text-white truncate">
            {suggestion.title}
          </h4>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
            {suggestion.description}
          </p>
        </div>
        <span
          className={`ml-3 px-2 py-1 text-xs font-medium rounded-full ${
            DIFFICULTY_COLORS[suggestion.difficulty]
          }`}
        >
          {DIFFICULTY_LABELS[suggestion.difficulty]}
        </span>
      </div>

      {/* Interval preview */}
      <div className="mb-3">
        <IntervalVisualizerCompact
          intervals={suggestion.workout.intervals}
          height={20}
          className="rounded"
        />
      </div>

      {/* Stats */}
      <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400 mb-3">
        <div className="flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          {formatDuration(suggestion.workout.totalDuration)}
        </div>
        <div className="flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 10V3L4 14h7v7l9-11h-7z"
            />
          </svg>
          {suggestion.focusArea}
        </div>
        <div className="flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
          Load: {suggestion.estimatedLoad}
        </div>
      </div>

      {/* Expandable rationale */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setShowDetails(!showDetails);
        }}
        className="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
      >
        {showDetails ? 'Hide' : 'Show'} rationale
        <svg
          className={`w-4 h-4 transition-transform ${showDetails ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {showDetails && (
        <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-sm text-gray-600 dark:text-gray-300">
          {suggestion.rationale}
        </div>
      )}

      {/* Action buttons */}
      {isSelected && (
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onUse();
            }}
            className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            Use This Workout
          </button>
        </div>
      )}
    </div>
  );
}

export function AIWorkoutSuggestions({
  workoutType,
  onSelectSuggestion,
  className = '',
}: AIWorkoutSuggestionsProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [targetDuration, setTargetDuration] = useState<number>(45);
  const [difficulty, setDifficulty] = useState<GenerateWorkoutRequest['difficulty']>('moderate');
  const [focusArea, setFocusArea] = useState<string>('');

  const generateMutation = useMutation({
    mutationFn: (request: GenerateWorkoutRequest) => generateWorkoutSuggestions(request),
    onSuccess: () => {
      setSelectedIndex(null);
    },
  });

  const handleGenerate = useCallback(() => {
    generateMutation.mutate({
      workoutType,
      targetDuration,
      difficulty,
      focusArea: focusArea || undefined,
      includeAthleteContext: true,
      numberOfSuggestions: 3,
    });
  }, [generateMutation, workoutType, targetDuration, difficulty, focusArea]);

  const handleSelectSuggestion = useCallback(
    (index: number) => {
      setSelectedIndex(index);
    },
    []
  );

  const handleUseSuggestion = useCallback(
    (suggestion: AIWorkoutSuggestion) => {
      onSelectSuggestion(suggestion.workout);
    },
    [onSelectSuggestion]
  );

  const suggestions = generateMutation.data?.suggestions || [];
  const athleteContext = generateMutation.data?.athleteContext;

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Generation controls */}
      <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-4">
        <div className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
          <svg className="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          AI Workout Generator
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Duration */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Target Duration
            </label>
            <select
              value={targetDuration}
              onChange={(e) => setTargetDuration(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              <option value={20}>20 minutes</option>
              <option value={30}>30 minutes</option>
              <option value={45}>45 minutes</option>
              <option value={60}>1 hour</option>
              <option value={75}>1h 15m</option>
              <option value={90}>1h 30m</option>
              <option value={120}>2 hours</option>
            </select>
          </div>

          {/* Difficulty */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Difficulty
            </label>
            <select
              value={difficulty}
              onChange={(e) =>
                setDifficulty(e.target.value as GenerateWorkoutRequest['difficulty'])
              }
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              <option value="easy">Easy</option>
              <option value="moderate">Moderate</option>
              <option value="hard">Hard</option>
              <option value="very_hard">Very Hard</option>
            </select>
          </div>

          {/* Focus Area */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Focus Area (optional)
            </label>
            <input
              type="text"
              value={focusArea}
              onChange={(e) => setFocusArea(e.target.value)}
              placeholder="e.g., speed, endurance, hills"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>
        </div>

        <button
          type="button"
          onClick={handleGenerate}
          disabled={generateMutation.isPending}
          className="w-full py-3 bg-purple-600 text-white font-medium rounded-lg hover:bg-purple-700 disabled:bg-purple-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          {generateMutation.isPending ? (
            <>
              <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
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
              Generating...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
              Generate AI Suggestions
            </>
          )}
        </button>
      </div>

      {/* Error message */}
      {generateMutation.isError && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            Failed to generate suggestions. Please try again.
          </div>
        </div>
      )}

      {/* Athlete context (if available) */}
      {athleteContext && (
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-2">
            Based on your recent training:
          </div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <div className="text-blue-600 dark:text-blue-400">Recent Volume</div>
              <div className="font-medium text-gray-900 dark:text-white">
                {athleteContext.recentVolume} km/week
              </div>
            </div>
            <div>
              <div className="text-blue-600 dark:text-blue-400">Fatigue Level</div>
              <div className="font-medium text-gray-900 dark:text-white capitalize">
                {athleteContext.fatigueLevel}
              </div>
            </div>
            <div>
              <div className="text-blue-600 dark:text-blue-400">Fitness Level</div>
              <div className="font-medium text-gray-900 dark:text-white capitalize">
                {athleteContext.fitnessLevel}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Suggestions grid */}
      {suggestions.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            AI Suggestions
          </h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
            {suggestions.map((suggestion, index) => (
              <SuggestionCard
                key={suggestion.id}
                suggestion={suggestion}
                isSelected={selectedIndex === index}
                onSelect={() => handleSelectSuggestion(index)}
                onUse={() => handleUseSuggestion(suggestion)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!generateMutation.isPending && suggestions.length === 0 && !generateMutation.isError && (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          <svg
            className="w-12 h-12 mx-auto mb-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          <p className="text-lg font-medium">No suggestions yet</p>
          <p className="mt-1">
            Click &quot;Generate AI Suggestions&quot; to get personalized workout ideas
          </p>
        </div>
      )}
    </div>
  );
}

export default AIWorkoutSuggestions;
