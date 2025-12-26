'use client';

import { useState, useCallback, useId } from 'react';
import type { WorkoutInterval, IntervalType, PaceTarget, HRTarget } from '@/lib/types';
import { INTERVAL_TYPE_COLORS, INTERVAL_TYPE_LABELS } from '@/lib/types';
import { PaceSelector } from './PaceSelector';

interface IntervalBuilderProps {
  intervals: WorkoutInterval[];
  onChange: (intervals: WorkoutInterval[]) => void;
  className?: string;
}

// Generate a unique ID for new intervals
function generateId(): string {
  return `interval-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// Format duration for display
function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) {
    return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Parse duration string to seconds
function parseDuration(value: string): number | null {
  // Try HH:MM:SS format
  let match = value.match(/^(\d{1,2}):(\d{2}):(\d{2})$/);
  if (match) {
    const hours = parseInt(match[1], 10);
    const mins = parseInt(match[2], 10);
    const secs = parseInt(match[3], 10);
    if (mins < 60 && secs < 60) {
      return hours * 3600 + mins * 60 + secs;
    }
  }

  // Try MM:SS format
  match = value.match(/^(\d{1,3}):(\d{2})$/);
  if (match) {
    const mins = parseInt(match[1], 10);
    const secs = parseInt(match[2], 10);
    if (secs < 60) {
      return mins * 60 + secs;
    }
  }

  // Try just minutes
  const mins = parseInt(value, 10);
  if (!isNaN(mins)) {
    return mins * 60;
  }

  return null;
}

interface IntervalItemProps {
  interval: WorkoutInterval;
  index: number;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onUpdate: (interval: WorkoutInterval) => void;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  canMoveUp: boolean;
  canMoveDown: boolean;
  onDragStart: (e: React.DragEvent, index: number) => void;
  onDragOver: (e: React.DragEvent, index: number) => void;
  onDragEnd: () => void;
  isDragging: boolean;
  isDragOver: boolean;
}

function IntervalItem({
  interval,
  index,
  isExpanded,
  onToggleExpand,
  onUpdate,
  onRemove,
  onMoveUp,
  onMoveDown,
  canMoveUp,
  canMoveDown,
  onDragStart,
  onDragOver,
  onDragEnd,
  isDragging,
  isDragOver,
}: IntervalItemProps) {
  const [durationInput, setDurationInput] = useState(
    formatDuration(interval.duration)
  );
  const inputId = useId();

  const handleDurationChange = useCallback(
    (value: string) => {
      setDurationInput(value);
      const seconds = parseDuration(value);
      if (seconds !== null) {
        onUpdate({ ...interval, duration: seconds });
      }
    },
    [interval, onUpdate]
  );

  const handleTypeChange = useCallback(
    (type: IntervalType) => {
      onUpdate({ ...interval, type });
    },
    [interval, onUpdate]
  );

  const handleNameChange = useCallback(
    (name: string) => {
      onUpdate({ ...interval, name: name || undefined });
    },
    [interval, onUpdate]
  );

  const handlePaceChange = useCallback(
    (paceTarget: PaceTarget | undefined) => {
      onUpdate({ ...interval, paceTarget });
    },
    [interval, onUpdate]
  );

  const handleHRChange = useCallback(
    (hrTarget: HRTarget | undefined) => {
      onUpdate({ ...interval, hrTarget });
    },
    [interval, onUpdate]
  );

  const handleNotesChange = useCallback(
    (notes: string) => {
      onUpdate({ ...interval, notes: notes || undefined });
    },
    [interval, onUpdate]
  );

  const intervalColor = INTERVAL_TYPE_COLORS[interval.type];

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, index)}
      onDragOver={(e) => onDragOver(e, index)}
      onDragEnd={onDragEnd}
      className={`border rounded-lg transition-all ${
        isDragging ? 'opacity-50' : ''
      } ${
        isDragOver
          ? 'border-blue-500 border-2'
          : 'border-gray-200 dark:border-gray-700'
      }`}
    >
      {/* Collapsed view */}
      <div
        className="flex items-center gap-3 p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50"
        onClick={onToggleExpand}
      >
        {/* Drag handle */}
        <div className="cursor-grab text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 8h16M4 16h16"
            />
          </svg>
        </div>

        {/* Color indicator */}
        <div
          className="w-3 h-8 rounded-full"
          style={{ backgroundColor: intervalColor }}
        />

        {/* Interval info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-900 dark:text-white">
              {interval.name || INTERVAL_TYPE_LABELS[interval.type]}
            </span>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {formatDuration(interval.duration)}
            </span>
          </div>
          {interval.paceTarget && (
            <div className="text-xs text-gray-500 dark:text-gray-400">
              Pace: {formatDuration(interval.paceTarget.min)} -{' '}
              {formatDuration(interval.paceTarget.max)} {interval.paceTarget.unit}
            </div>
          )}
        </div>

        {/* Actions */}
        <div
          className="flex items-center gap-1"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            onClick={onMoveUp}
            disabled={!canMoveUp}
            className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Move up"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            </svg>
          </button>
          <button
            type="button"
            onClick={onMoveDown}
            disabled={!canMoveDown}
            className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed"
            title="Move down"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <button
            type="button"
            onClick={onRemove}
            className="p-1.5 text-red-400 hover:text-red-600 dark:hover:text-red-400"
            title="Remove interval"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <button
            type="button"
            onClick={onToggleExpand}
            className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <svg
              className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Expanded view */}
      {isExpanded && (
        <div
          className="border-t border-gray-200 dark:border-gray-700 p-4 space-y-4 bg-gray-50 dark:bg-gray-800/30"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Type selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Interval Type
            </label>
            <div className="flex flex-wrap gap-2">
              {(Object.keys(INTERVAL_TYPE_LABELS) as IntervalType[]).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => handleTypeChange(type)}
                  className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                    interval.type === type
                      ? 'border-transparent text-white'
                      : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
                  }`}
                  style={{
                    backgroundColor:
                      interval.type === type
                        ? INTERVAL_TYPE_COLORS[type]
                        : 'transparent',
                  }}
                >
                  {INTERVAL_TYPE_LABELS[type]}
                </button>
              ))}
            </div>
          </div>

          {/* Name */}
          <div>
            <label
              htmlFor={`${inputId}-name`}
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Name (optional)
            </label>
            <input
              id={`${inputId}-name`}
              type="text"
              value={interval.name || ''}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder={INTERVAL_TYPE_LABELS[interval.type]}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Duration */}
          <div>
            <label
              htmlFor={`${inputId}-duration`}
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Duration
            </label>
            <input
              id={`${inputId}-duration`}
              type="text"
              value={durationInput}
              onChange={(e) => handleDurationChange(e.target.value)}
              placeholder="5:00"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Format: MM:SS or HH:MM:SS
            </p>
          </div>

          {/* Pace/HR targets */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Pace / Heart Rate Target
            </label>
            <PaceSelector
              value={interval.paceTarget}
              hrValue={interval.hrTarget}
              onChange={handlePaceChange}
              onHRChange={handleHRChange}
              mode="both"
            />
          </div>

          {/* Notes */}
          <div>
            <label
              htmlFor={`${inputId}-notes`}
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Notes (optional)
            </label>
            <textarea
              id={`${inputId}-notes`}
              value={interval.notes || ''}
              onChange={(e) => handleNotesChange(e.target.value)}
              placeholder="e.g., Focus on form, stay relaxed"
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            />
          </div>
        </div>
      )}
    </div>
  );
}

const INTERVAL_TEMPLATES: { label: string; interval: Omit<WorkoutInterval, 'id'> }[] = [
  {
    label: 'Warm-up (10 min)',
    interval: { type: 'warmup', duration: 600, name: 'Warm-up' },
  },
  {
    label: 'Work (5 min)',
    interval: { type: 'work', duration: 300, name: 'Work Interval' },
  },
  {
    label: 'Recovery (2 min)',
    interval: { type: 'recovery', duration: 120, name: 'Recovery' },
  },
  {
    label: 'Cool-down (10 min)',
    interval: { type: 'cooldown', duration: 600, name: 'Cool-down' },
  },
  {
    label: '400m Repeat',
    interval: { type: 'work', duration: 90, distance: 400, name: '400m Repeat' },
  },
  {
    label: '800m Repeat',
    interval: { type: 'work', duration: 180, distance: 800, name: '800m Repeat' },
  },
];

export function IntervalBuilder({
  intervals,
  onChange,
  className = '',
}: IntervalBuilderProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  const handleAddInterval = useCallback(
    (template?: Omit<WorkoutInterval, 'id'>) => {
      const newInterval: WorkoutInterval = template
        ? { ...template, id: generateId() }
        : {
            id: generateId(),
            type: 'work',
            duration: 300,
          };
      onChange([...intervals, newInterval]);
      setExpandedIndex(intervals.length);
    },
    [intervals, onChange]
  );

  const handleUpdateInterval = useCallback(
    (index: number, interval: WorkoutInterval) => {
      const newIntervals = [...intervals];
      newIntervals[index] = interval;
      onChange(newIntervals);
    },
    [intervals, onChange]
  );

  const handleRemoveInterval = useCallback(
    (index: number) => {
      const newIntervals = intervals.filter((_, i) => i !== index);
      onChange(newIntervals);
      if (expandedIndex === index) {
        setExpandedIndex(null);
      } else if (expandedIndex !== null && expandedIndex > index) {
        setExpandedIndex(expandedIndex - 1);
      }
    },
    [intervals, onChange, expandedIndex]
  );

  const handleMoveInterval = useCallback(
    (fromIndex: number, toIndex: number) => {
      if (toIndex < 0 || toIndex >= intervals.length) return;

      const newIntervals = [...intervals];
      const [removed] = newIntervals.splice(fromIndex, 1);
      newIntervals.splice(toIndex, 0, removed);
      onChange(newIntervals);

      if (expandedIndex === fromIndex) {
        setExpandedIndex(toIndex);
      } else if (expandedIndex !== null) {
        if (fromIndex < expandedIndex && toIndex >= expandedIndex) {
          setExpandedIndex(expandedIndex - 1);
        } else if (fromIndex > expandedIndex && toIndex <= expandedIndex) {
          setExpandedIndex(expandedIndex + 1);
        }
      }
    },
    [intervals, onChange, expandedIndex]
  );

  const handleDragStart = useCallback(
    (e: React.DragEvent, index: number) => {
      setDragIndex(index);
      e.dataTransfer.effectAllowed = 'move';
    },
    []
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent, index: number) => {
      e.preventDefault();
      if (dragIndex !== null && dragIndex !== index) {
        setDragOverIndex(index);
      }
    },
    [dragIndex]
  );

  const handleDragEnd = useCallback(() => {
    if (dragIndex !== null && dragOverIndex !== null && dragIndex !== dragOverIndex) {
      handleMoveInterval(dragIndex, dragOverIndex);
    }
    setDragIndex(null);
    setDragOverIndex(null);
  }, [dragIndex, dragOverIndex, handleMoveInterval]);

  const totalDuration = intervals.reduce((sum, i) => sum + i.duration, 0);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header with total duration */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Intervals
        </h3>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Total: {formatDuration(totalDuration)}
        </div>
      </div>

      {/* Interval list */}
      {intervals.length > 0 ? (
        <div className="space-y-2">
          {intervals.map((interval, index) => (
            <IntervalItem
              key={interval.id}
              interval={interval}
              index={index}
              isExpanded={expandedIndex === index}
              onToggleExpand={() =>
                setExpandedIndex(expandedIndex === index ? null : index)
              }
              onUpdate={(updated) => handleUpdateInterval(index, updated)}
              onRemove={() => handleRemoveInterval(index)}
              onMoveUp={() => handleMoveInterval(index, index - 1)}
              onMoveDown={() => handleMoveInterval(index, index + 1)}
              canMoveUp={index > 0}
              canMoveDown={index < intervals.length - 1}
              onDragStart={handleDragStart}
              onDragOver={handleDragOver}
              onDragEnd={handleDragEnd}
              isDragging={dragIndex === index}
              isDragOver={dragOverIndex === index}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400 border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-lg">
          <p>No intervals yet. Add your first interval below.</p>
        </div>
      )}

      {/* Add interval buttons */}
      <div className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {INTERVAL_TEMPLATES.map((template, index) => (
            <button
              key={index}
              type="button"
              onClick={() => handleAddInterval(template.interval)}
              className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300 transition-colors"
            >
              + {template.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={() => handleAddInterval()}
          className="w-full py-3 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg text-gray-600 dark:text-gray-400 hover:border-blue-500 hover:text-blue-500 dark:hover:border-blue-400 dark:hover:text-blue-400 transition-colors"
        >
          + Add Custom Interval
        </button>
      </div>

      {/* Quick actions */}
      {intervals.length > 0 && (
        <div className="flex gap-2 pt-2">
          <button
            type="button"
            onClick={() => {
              // Duplicate last interval
              const last = intervals[intervals.length - 1];
              const duplicate = { ...last, id: generateId() };
              onChange([...intervals, duplicate]);
            }}
            className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
          >
            Duplicate last
          </button>
          <span className="text-gray-300 dark:text-gray-600">|</span>
          <button
            type="button"
            onClick={() => onChange([])}
            className="text-sm text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300"
          >
            Clear all
          </button>
        </div>
      )}
    </div>
  );
}

export default IntervalBuilder;
