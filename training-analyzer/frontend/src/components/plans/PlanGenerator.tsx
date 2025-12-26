'use client';

import { useState } from 'react';
import { clsx } from 'clsx';
import { format, addDays, nextMonday, parseISO } from 'date-fns';
import type {
  RaceDistance,
  PeriodizationType,
  PlanConstraints,
  PlanGoal,
  GeneratePlanRequest,
  TrainingPlan,
} from '@/lib/types';

// Race distance configuration
const RACE_DISTANCES: {
  value: RaceDistance;
  label: string;
  distanceKm: number;
  typicalDuration: string;
}[] = [
  { value: '5k', label: '5K', distanceKm: 5, typicalDuration: '15-35 min' },
  { value: '10k', label: '10K', distanceKm: 10, typicalDuration: '30-70 min' },
  {
    value: 'half_marathon',
    label: 'Half Marathon',
    distanceKm: 21.1,
    typicalDuration: '1:15-3:00',
  },
  {
    value: 'marathon',
    label: 'Marathon',
    distanceKm: 42.2,
    typicalDuration: '2:30-6:00',
  },
  {
    value: 'ultra',
    label: 'Ultra Marathon',
    distanceKm: 50,
    typicalDuration: '4:00+',
  },
  {
    value: 'custom',
    label: 'Custom Distance',
    distanceKm: 0,
    typicalDuration: 'Variable',
  },
];

const PERIODIZATION_TYPES: {
  value: PeriodizationType;
  label: string;
  description: string;
}[] = [
  {
    value: 'linear',
    label: 'Linear',
    description: 'Gradual progression with steady volume increase',
  },
  {
    value: 'undulating',
    label: 'Undulating',
    description: 'Alternating easy and hard weeks for recovery',
  },
  {
    value: 'block',
    label: 'Block',
    description: 'Focused training blocks for specific adaptations',
  },
  {
    value: 'polarized',
    label: 'Polarized',
    description: '80/20 split between easy and hard training',
  },
];

const FITNESS_LEVELS = [
  { value: 'beginner', label: 'Beginner', description: '<6 months running' },
  {
    value: 'intermediate',
    label: 'Intermediate',
    description: '6-24 months running',
  },
  { value: 'advanced', label: 'Advanced', description: '2-5 years running' },
  { value: 'elite', label: 'Elite', description: '5+ years, competitive' },
] as const;

const DAYS_OF_WEEK = [
  { value: 0, label: 'Monday' },
  { value: 1, label: 'Tuesday' },
  { value: 2, label: 'Wednesday' },
  { value: 3, label: 'Thursday' },
  { value: 4, label: 'Friday' },
  { value: 5, label: 'Saturday' },
  { value: 6, label: 'Sunday' },
];

interface PlanGeneratorProps {
  onGenerate: (request: GeneratePlanRequest) => void;
  onCancel?: () => void;
  isGenerating?: boolean;
  generationProgress?: { phase: string; message: string; percentage: number } | null;
  generatedPlan?: TrainingPlan | null;
  error?: Error | null;
}

export function PlanGenerator({
  onGenerate,
  onCancel,
  isGenerating = false,
  generationProgress = null,
  generatedPlan = null,
  error = null,
}: PlanGeneratorProps) {
  // Form state
  const [step, setStep] = useState<'goal' | 'constraints' | 'review'>('goal');

  // Goal state
  const [planName, setPlanName] = useState('');
  const [raceDistance, setRaceDistance] = useState<RaceDistance>('half_marathon');
  const [customDistance, setCustomDistance] = useState<number>(0);
  const [targetTimeHours, setTargetTimeHours] = useState<number>(0);
  const [targetTimeMinutes, setTargetTimeMinutes] = useState<number>(0);
  const [targetTimeSeconds, setTargetTimeSeconds] = useState<number>(0);
  const [raceDate, setRaceDate] = useState<string>(() => {
    // Default to 12 weeks from now
    const defaultDate = addDays(nextMonday(new Date()), 84);
    return format(defaultDate, 'yyyy-MM-dd');
  });
  const [raceName, setRaceName] = useState('');
  const [priority, setPriority] = useState<'A' | 'B' | 'C'>('A');

  // Constraints state
  const [daysPerWeek, setDaysPerWeek] = useState(4);
  const [maxSessionDuration, setMaxSessionDuration] = useState(90);
  const [longRunDay, setLongRunDay] = useState(6); // Sunday
  const [restDays, setRestDays] = useState<number[]>([4]); // Friday
  const [includeStrength, setIncludeStrength] = useState(true);
  const [includeCrossTraining, setIncludeCrossTraining] = useState(false);
  const [fitnessLevel, setFitnessLevel] = useState<PlanConstraints['currentFitnessLevel']>('intermediate');
  const [weeklyMileage, setWeeklyMileage] = useState<number>(30);
  const [periodizationType, setPeriodizationType] = useState<PeriodizationType>('undulating');

  // Calculate target time in seconds
  const targetTimeInSeconds = targetTimeHours * 3600 + targetTimeMinutes * 60 + targetTimeSeconds;

  // Build the goal object
  const buildGoal = (): PlanGoal => ({
    raceDistance,
    customDistance: raceDistance === 'custom' ? customDistance * 1000 : undefined,
    targetTime: targetTimeInSeconds > 0 ? targetTimeInSeconds : undefined,
    raceDate,
    raceName: raceName || undefined,
    priority,
  });

  // Build the constraints object
  const buildConstraints = (): PlanConstraints => ({
    daysPerWeek,
    maxSessionDuration,
    longRunDay,
    restDays,
    includeStrength,
    includeCrossTraining,
    currentFitnessLevel: fitnessLevel,
    weeklyMileageStart: weeklyMileage,
  });

  // Handle form submission
  const handleSubmit = () => {
    const request: GeneratePlanRequest = {
      name: planName || `${RACE_DISTANCES.find(r => r.value === raceDistance)?.label} Training Plan`,
      goal: buildGoal(),
      constraints: buildConstraints(),
      periodizationType,
    };
    onGenerate(request);
  };

  // Toggle rest day
  const toggleRestDay = (day: number) => {
    setRestDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
    );
  };

  // Form validation
  const isGoalValid = raceDistance && raceDate;
  const isConstraintsValid = daysPerWeek >= 3 && daysPerWeek <= 7;

  const renderGoalStep = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-100 mb-4">
          What&apos;s your goal?
        </h3>

        {/* Plan Name */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Plan Name (optional)
          </label>
          <input
            type="text"
            value={planName}
            onChange={(e) => setPlanName(e.target.value)}
            placeholder="e.g., Spring Half Marathon Prep"
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
          />
        </div>

        {/* Race Distance */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Race Distance
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {RACE_DISTANCES.map((distance) => (
              <button
                key={distance.value}
                onClick={() => setRaceDistance(distance.value)}
                className={clsx(
                  'px-4 py-3 rounded-lg border-2 text-left transition-all',
                  raceDistance === distance.value
                    ? 'border-teal-500 bg-teal-900/30'
                    : 'border-gray-700 hover:border-gray-600 bg-gray-800'
                )}
              >
                <p className="font-semibold text-gray-100">{distance.label}</p>
                <p className="text-xs text-gray-500">{distance.typicalDuration}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Custom Distance */}
        {raceDistance === 'custom' && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Distance (km)
            </label>
            <input
              type="number"
              value={customDistance || ''}
              onChange={(e) => setCustomDistance(Number(e.target.value))}
              min="1"
              max="200"
              placeholder="50"
              className="w-32 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
            />
          </div>
        )}

        {/* Target Time */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Target Time (optional)
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={targetTimeHours || ''}
              onChange={(e) => setTargetTimeHours(Number(e.target.value))}
              min="0"
              max="24"
              placeholder="0"
              className="w-16 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-center text-gray-100 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
            />
            <span className="text-gray-500">h</span>
            <input
              type="number"
              value={targetTimeMinutes || ''}
              onChange={(e) => setTargetTimeMinutes(Number(e.target.value))}
              min="0"
              max="59"
              placeholder="0"
              className="w-16 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-center text-gray-100 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
            />
            <span className="text-gray-500">m</span>
            <input
              type="number"
              value={targetTimeSeconds || ''}
              onChange={(e) => setTargetTimeSeconds(Number(e.target.value))}
              min="0"
              max="59"
              placeholder="0"
              className="w-16 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-center text-gray-100 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
            />
            <span className="text-gray-500">s</span>
          </div>
        </div>

        {/* Race Date */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Race Date
          </label>
          <input
            type="date"
            value={raceDate}
            onChange={(e) => setRaceDate(e.target.value)}
            min={format(addDays(new Date(), 14), 'yyyy-MM-dd')}
            className="w-full sm:w-auto px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
          />
        </div>

        {/* Race Name */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-1">
            Race Name (optional)
          </label>
          <input
            type="text"
            value={raceName}
            onChange={(e) => setRaceName(e.target.value)}
            placeholder="e.g., City Half Marathon"
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
          />
        </div>

        {/* Priority */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Race Priority
          </label>
          <div className="flex gap-2">
            {(['A', 'B', 'C'] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPriority(p)}
                className={clsx(
                  'px-4 py-2 rounded-lg border-2 font-medium transition-all',
                  priority === p
                    ? p === 'A'
                      ? 'border-red-500 bg-red-900/30 text-red-400'
                      : p === 'B'
                        ? 'border-yellow-500 bg-yellow-900/30 text-yellow-400'
                        : 'border-gray-500 bg-gray-800 text-gray-400'
                    : 'border-gray-700 hover:border-gray-600 text-gray-500'
                )}
              >
                {p} Priority
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-1">
            {priority === 'A'
              ? 'Your main goal race - plan will peak for this'
              : priority === 'B'
                ? 'Important race - reduced taper'
                : 'Training race - minimal adjustments'}
          </p>
        </div>
      </div>
    </div>
  );

  const renderConstraintsStep = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-100 mb-4">
          Training Preferences
        </h3>

        {/* Fitness Level */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Current Fitness Level
          </label>
          <div className="grid grid-cols-2 gap-2">
            {FITNESS_LEVELS.map((level) => (
              <button
                key={level.value}
                onClick={() => setFitnessLevel(level.value)}
                className={clsx(
                  'px-4 py-3 rounded-lg border-2 text-left transition-all',
                  fitnessLevel === level.value
                    ? 'border-teal-500 bg-teal-900/30'
                    : 'border-gray-700 hover:border-gray-600 bg-gray-800'
                )}
              >
                <p className="font-semibold text-gray-100">{level.label}</p>
                <p className="text-xs text-gray-500">{level.description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Days per week */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Training Days per Week
          </label>
          <div className="flex gap-2">
            {[3, 4, 5, 6, 7].map((days) => (
              <button
                key={days}
                onClick={() => setDaysPerWeek(days)}
                className={clsx(
                  'w-12 h-12 rounded-lg border-2 font-semibold transition-all',
                  daysPerWeek === days
                    ? 'border-teal-500 bg-teal-900/30 text-teal-400'
                    : 'border-gray-700 hover:border-gray-600 text-gray-400'
                )}
              >
                {days}
              </button>
            ))}
          </div>
        </div>

        {/* Max session duration */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Max Session Duration (minutes)
          </label>
          <input
            type="range"
            min="30"
            max="180"
            step="15"
            value={maxSessionDuration}
            onChange={(e) => setMaxSessionDuration(Number(e.target.value))}
            className="w-full accent-teal-500"
          />
          <div className="flex justify-between text-sm text-gray-500">
            <span>30 min</span>
            <span className="font-semibold text-gray-100">{maxSessionDuration} min</span>
            <span>180 min</span>
          </div>
        </div>

        {/* Current weekly mileage */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Current Weekly Mileage (km)
          </label>
          <input
            type="number"
            value={weeklyMileage || ''}
            onChange={(e) => setWeeklyMileage(Number(e.target.value))}
            min="0"
            max="200"
            placeholder="30"
            className="w-32 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
          />
        </div>

        {/* Long run day */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Preferred Long Run Day
          </label>
          <div className="flex flex-wrap gap-2">
            {DAYS_OF_WEEK.map((day) => (
              <button
                key={day.value}
                onClick={() => setLongRunDay(day.value)}
                className={clsx(
                  'px-3 py-2 rounded-lg border-2 text-sm font-medium transition-all',
                  longRunDay === day.value
                    ? 'border-teal-500 bg-teal-900/30 text-teal-400'
                    : 'border-gray-700 hover:border-gray-600 text-gray-400'
                )}
              >
                {day.label.slice(0, 3)}
              </button>
            ))}
          </div>
        </div>

        {/* Rest days */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Preferred Rest Days
          </label>
          <div className="flex flex-wrap gap-2">
            {DAYS_OF_WEEK.map((day) => (
              <button
                key={day.value}
                onClick={() => toggleRestDay(day.value)}
                disabled={day.value === longRunDay}
                className={clsx(
                  'px-3 py-2 rounded-lg border-2 text-sm font-medium transition-all',
                  day.value === longRunDay
                    ? 'border-gray-800 bg-gray-900 text-gray-600 cursor-not-allowed'
                    : restDays.includes(day.value)
                      ? 'border-green-500 bg-green-900/30 text-green-400'
                      : 'border-gray-700 hover:border-gray-600 text-gray-400'
                )}
              >
                {day.label.slice(0, 3)}
              </button>
            ))}
          </div>
        </div>

        {/* Additional options */}
        <div className="space-y-3">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={includeStrength}
              onChange={(e) => setIncludeStrength(e.target.checked)}
              className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-teal-500 focus:ring-teal-500"
            />
            <div>
              <p className="font-medium text-gray-100">Include Strength Training</p>
              <p className="text-xs text-gray-500">Add strength sessions for injury prevention</p>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={includeCrossTraining}
              onChange={(e) => setIncludeCrossTraining(e.target.checked)}
              className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-teal-500 focus:ring-teal-500"
            />
            <div>
              <p className="font-medium text-gray-100">Include Cross Training</p>
              <p className="text-xs text-gray-500">Add cycling, swimming, or other activities</p>
            </div>
          </label>
        </div>

        {/* Periodization Type */}
        <div className="mt-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Periodization Style
          </label>
          <div className="grid grid-cols-2 gap-2">
            {PERIODIZATION_TYPES.map((type) => (
              <button
                key={type.value}
                onClick={() => setPeriodizationType(type.value)}
                className={clsx(
                  'px-4 py-3 rounded-lg border-2 text-left transition-all',
                  periodizationType === type.value
                    ? 'border-teal-500 bg-teal-900/30'
                    : 'border-gray-700 hover:border-gray-600 bg-gray-800'
                )}
              >
                <p className="font-semibold text-gray-100">{type.label}</p>
                <p className="text-xs text-gray-500">{type.description}</p>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  const renderReviewStep = () => {
    const distance = RACE_DISTANCES.find((r) => r.value === raceDistance);
    const fitness = FITNESS_LEVELS.find((l) => l.value === fitnessLevel);
    const periodization = PERIODIZATION_TYPES.find((p) => p.value === periodizationType);

    return (
      <div className="space-y-6">
        <h3 className="text-lg font-semibold text-gray-100 mb-4">
          Review Your Plan
        </h3>

        {/* Summary cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-gray-800 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-500 mb-2">Goal</h4>
            <p className="font-semibold text-gray-100">{distance?.label}</p>
            {targetTimeInSeconds > 0 && (
              <p className="text-sm text-gray-400">
                Target: {targetTimeHours > 0 && `${targetTimeHours}h `}
                {targetTimeMinutes > 0 && `${targetTimeMinutes}m `}
                {targetTimeSeconds > 0 && `${targetTimeSeconds}s`}
              </p>
            )}
            <p className="text-sm text-gray-400">
              Race: {format(parseISO(raceDate), 'MMMM d, yyyy')}
            </p>
            {raceName && <p className="text-sm text-gray-400">{raceName}</p>}
          </div>

          <div className="bg-gray-800 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-500 mb-2">Training</h4>
            <p className="font-semibold text-gray-100">{daysPerWeek} days/week</p>
            <p className="text-sm text-gray-400">
              Max {maxSessionDuration} min sessions
            </p>
            <p className="text-sm text-gray-400">
              {fitness?.label} level ({weeklyMileage}km/week)
            </p>
          </div>

          <div className="bg-gray-800 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-500 mb-2">Schedule</h4>
            <p className="text-sm text-gray-400">
              Long run: {DAYS_OF_WEEK[longRunDay]?.label}
            </p>
            <p className="text-sm text-gray-400">
              Rest days:{' '}
              {restDays.length > 0
                ? restDays.map((d) => DAYS_OF_WEEK[d]?.label.slice(0, 3)).join(', ')
                : 'None'}
            </p>
          </div>

          <div className="bg-gray-800 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-500 mb-2">Structure</h4>
            <p className="font-semibold text-gray-100">
              {periodization?.label} Periodization
            </p>
            <p className="text-sm text-gray-400">
              {includeStrength && 'Strength training included'}
              {includeStrength && includeCrossTraining && ', '}
              {includeCrossTraining && 'Cross training included'}
              {!includeStrength && !includeCrossTraining && 'Running only'}
            </p>
          </div>
        </div>

        {/* Generation progress */}
        {isGenerating && generationProgress && (
          <div className="bg-teal-900/30 border border-teal-700 rounded-lg p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="animate-spin w-5 h-5 border-2 border-teal-400 border-t-transparent rounded-full" />
              <p className="font-medium text-teal-300">{generationProgress.phase}</p>
            </div>
            <p className="text-sm text-teal-400 mb-2">{generationProgress.message}</p>
            <div className="h-2 bg-teal-900 rounded-full overflow-hidden">
              <div
                className="h-full bg-teal-500 rounded-full transition-all duration-300"
                style={{ width: `${generationProgress.percentage}%` }}
              />
            </div>
          </div>
        )}

        {/* Error display */}
        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-4">
            <p className="text-red-400 font-medium">Generation failed</p>
            <p className="text-sm text-red-500">{error.message}</p>
          </div>
        )}

        {/* Success message */}
        {generatedPlan && (
          <div className="bg-green-900/30 border border-green-700 rounded-lg p-4">
            <p className="text-green-400 font-medium">Plan generated successfully!</p>
            <p className="text-sm text-green-500">
              {generatedPlan.totalWeeks} weeks of training created
            </p>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
      {/* Progress steps */}
      <div className="border-b border-gray-800 bg-gray-800/50 px-6 py-4">
        <div className="flex items-center justify-between max-w-md mx-auto">
          {(['goal', 'constraints', 'review'] as const).map((s, i) => (
            <div key={s} className="flex items-center">
              <button
                onClick={() => setStep(s)}
                disabled={
                  (s === 'constraints' && !isGoalValid) ||
                  (s === 'review' && (!isGoalValid || !isConstraintsValid)) ||
                  isGenerating
                }
                className={clsx(
                  'flex items-center gap-2 px-3 py-1 rounded-full transition-all',
                  step === s
                    ? 'bg-teal-600 text-white'
                    : 'text-gray-400 hover:bg-gray-700'
                )}
              >
                <span
                  className={clsx(
                    'w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium',
                    step === s ? 'bg-white/20' : 'bg-gray-700'
                  )}
                >
                  {i + 1}
                </span>
                <span className="hidden sm:inline capitalize">{s}</span>
              </button>
              {i < 2 && (
                <div className="w-8 sm:w-16 h-px bg-gray-700 mx-2" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Form content */}
      <div className="p-6">
        {step === 'goal' && renderGoalStep()}
        {step === 'constraints' && renderConstraintsStep()}
        {step === 'review' && renderReviewStep()}
      </div>

      {/* Actions */}
      <div className="border-t border-gray-800 bg-gray-800/50 px-6 py-4 flex justify-between">
        {step === 'goal' ? (
          <>
            {onCancel && (
              <button
                onClick={onCancel}
                className="px-4 py-2 text-gray-400 hover:text-gray-200 transition-colors"
              >
                Cancel
              </button>
            )}
            <div className="flex-1" />
            <button
              onClick={() => setStep('constraints')}
              disabled={!isGoalValid}
              className="px-6 py-2 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </>
        ) : step === 'constraints' ? (
          <>
            <button
              onClick={() => setStep('goal')}
              className="px-4 py-2 text-gray-400 hover:text-gray-200 transition-colors"
            >
              Back
            </button>
            <button
              onClick={() => setStep('review')}
              disabled={!isConstraintsValid}
              className="px-6 py-2 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Review
            </button>
          </>
        ) : (
          <>
            <button
              onClick={() => setStep('constraints')}
              disabled={isGenerating}
              className="px-4 py-2 text-gray-400 hover:text-gray-200 transition-colors disabled:opacity-50"
            >
              Back
            </button>
            <button
              onClick={handleSubmit}
              disabled={isGenerating || !!generatedPlan}
              className={clsx(
                'px-6 py-2 font-medium rounded-lg transition-colors',
                generatedPlan
                  ? 'bg-green-600 text-white'
                  : 'bg-teal-600 text-white hover:bg-teal-500',
                (isGenerating || generatedPlan) && 'opacity-75 cursor-not-allowed'
              )}
            >
              {isGenerating
                ? 'Generating...'
                : generatedPlan
                  ? 'Plan Generated'
                  : 'Generate Plan'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
