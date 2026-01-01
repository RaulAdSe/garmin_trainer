'use client';

import { useState, useMemo } from 'react';
import { clsx } from 'clsx';
import { format, addDays, nextMonday } from 'date-fns';
import type {
  RaceDistance, PeriodizationType, PlanConstraints, PlanGoal, GeneratePlanRequest, TrainingPlan,
} from '@/lib/types';

const DISTANCES: { value: RaceDistance; label: string; icon: string }[] = [
  { value: '5k', label: '5K', icon: '5' },
  { value: '10k', label: '10K', icon: '10' },
  { value: 'half_marathon', label: 'Half', icon: '21' },
  { value: 'marathon', label: 'Marathon', icon: '42' },
  { value: 'ultra', label: 'Ultra', icon: '50+' },
  { value: 'custom', label: 'Custom', icon: '?' },
];

interface DetectedPatterns {
  avgDaysPerWeek: number;
  typicalLongRunDay: number;
  typicalRestDays: number[];
  maxSessionDurationMin: number;
  doesStrength: boolean;
  doesCrossTraining: boolean;
}

interface RacePredictions {
  '5k'?: string;
  '10k'?: string;
  'half_marathon'?: string;
  'marathon'?: string;
}

interface Props {
  onGenerate: (req: GeneratePlanRequest) => void;
  onCancel?: () => void;
  isGenerating?: boolean;
  generationProgress?: { phase: string; message: string; percentage: number } | null;
  generatedPlan?: TrainingPlan | null;
  error?: Error | null;
  detectedFitnessLevel?: PlanConstraints['currentFitnessLevel'];
  detectedWeeklyMileage?: number;
  detectedPatterns?: DetectedPatterns;
  racePredictions?: RacePredictions;
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export function PlanGenerator({
  onGenerate, onCancel, isGenerating = false, generationProgress, generatedPlan, error,
  detectedFitnessLevel = 'intermediate', detectedWeeklyMileage = 30,
  detectedPatterns, racePredictions,
}: Props) {
  // Goal inputs (user must provide)
  const [raceDistance, setRaceDistance] = useState<RaceDistance>('half_marathon');
  const [customKm, setCustomKm] = useState(50);
  const [raceDate, setRaceDate] = useState(() => format(addDays(nextMonday(new Date()), 84), 'yyyy-MM-dd'));
  const [targetTime, setTargetTime] = useState('');
  const [priority, setPriority] = useState<'A' | 'B' | 'C'>('A');

  // Derived from detected patterns (with sensible defaults)
  const patterns = detectedPatterns || {
    avgDaysPerWeek: 4,
    typicalLongRunDay: 6,
    typicalRestDays: [4],
    maxSessionDurationMin: 90,
    doesStrength: true,
    doesCrossTraining: false,
  };

  const parseTime = (s: string): number => {
    const p = s.split(':').map(Number);
    if (p.some(isNaN)) return 0;
    return p.length === 3 ? p[0] * 3600 + p[1] * 60 + p[2] : p.length === 2 ? p[0] * 60 + p[1] : 0;
  };

  const targetSec = useMemo(() => parseTime(targetTime), [targetTime]);
  const weeks = useMemo(() => Math.max(1, Math.ceil((new Date(raceDate).getTime() - Date.now()) / 604800000)), [raceDate]);
  const valid = raceDistance && raceDate && (raceDistance !== 'custom' || customKm > 0);

  // Get suggested target time from Garmin predictions
  const suggestedTime = useMemo(() => {
    if (!racePredictions) return null;
    const key = raceDistance as keyof RacePredictions;
    return racePredictions[key] || null;
  }, [raceDistance, racePredictions]);

  const generate = () => {
    const constraints: PlanConstraints = {
      daysPerWeek: patterns.avgDaysPerWeek,
      maxSessionDuration: patterns.maxSessionDurationMin,
      longRunDay: patterns.typicalLongRunDay,
      restDays: patterns.typicalRestDays,
      includeStrength: patterns.doesStrength,
      includeCrossTraining: patterns.doesCrossTraining,
      currentFitnessLevel: detectedFitnessLevel,
      weeklyMileageStart: detectedWeeklyMileage,
    };

    onGenerate({
      name: `${DISTANCES.find(d => d.value === raceDistance)?.label} Training Plan`,
      goal: {
        raceDistance,
        customDistance: raceDistance === 'custom' ? customKm * 1000 : undefined,
        targetTime: targetSec || undefined,
        raceDate,
        priority,
      },
      constraints,
      periodizationType: 'undulating' as PeriodizationType,
    });
  };

  const input = 'w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-gray-100 focus:ring-2 focus:ring-teal-500';

  return (
    <div className="bg-gray-900 rounded-2xl border border-gray-800 overflow-hidden max-w-lg mx-auto">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-800/50 px-6 py-4">
        <h2 className="text-xl font-bold text-gray-100 text-center">Create Training Plan</h2>
      </div>

      <div className="p-6 space-y-8">
        {/* Race Distance Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-3">What are you training for?</label>
          <div className="grid grid-cols-3 gap-3">
            {DISTANCES.map(d => (
              <button key={d.value} onClick={() => setRaceDistance(d.value)}
                className={clsx('py-5 px-3 rounded-2xl border-2 flex flex-col items-center gap-1.5 transition-all',
                  raceDistance === d.value ? 'border-teal-500 bg-teal-500/10' : 'border-gray-700 hover:border-gray-600 bg-gray-800/50')}>
                <span className="text-xl font-bold text-gray-100">{d.icon}</span>
                <span className="text-xs text-gray-400">{d.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Custom Distance */}
        {raceDistance === 'custom' && (
          <div>
            <label className="block text-sm text-gray-400 mb-2">Distance (km)</label>
            <input type="number" value={customKm} onChange={e => setCustomKm(+e.target.value)} min="1" className={input} />
          </div>
        )}

        {/* Race Date */}
        <div>
          <label className="block text-sm text-gray-400 mb-2">Race Date</label>
          <input type="date" value={raceDate} onChange={e => setRaceDate(e.target.value)}
            min={format(addDays(new Date(), 14), 'yyyy-MM-dd')} className={input} />
          <p className="text-sm text-gray-500 mt-2">{weeks} weeks of training</p>
        </div>

        {/* Target Time with Suggestion */}
        <div>
          <label className="block text-sm text-gray-400 mb-2">Target Time (optional)</label>
          <div className="relative">
            <input type="text" value={targetTime} onChange={e => setTargetTime(e.target.value)}
              placeholder={suggestedTime ? `Suggested: ${suggestedTime}` : '1:45:00'}
              className={clsx(input, 'placeholder-gray-600')} />
            {suggestedTime && !targetTime && (
              <button onClick={() => setTargetTime(suggestedTime)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-teal-400 hover:text-teal-300">
                Use prediction
              </button>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-1">Format: H:MM:SS or MM:SS</p>
        </div>

        {/* Race Priority */}
        <div>
          <label className="block text-sm text-gray-400 mb-2">Race Priority</label>
          <div className="flex gap-2">
            {(['A', 'B', 'C'] as const).map(p => (
              <button key={p} onClick={() => setPriority(p)}
                className={clsx('flex-1 py-2.5 rounded-xl border text-sm font-medium transition-all',
                  priority === p
                    ? (p === 'A' ? 'border-red-500 bg-red-500/10 text-red-400'
                      : p === 'B' ? 'border-yellow-500 bg-yellow-500/10 text-yellow-400'
                      : 'border-gray-500 bg-gray-500/10 text-gray-400')
                    : 'border-gray-700 text-gray-500 hover:border-gray-600')}>
                {p} Race
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-1">
            {priority === 'A' ? 'Main goal race - full taper and peak' :
             priority === 'B' ? 'Important but not primary - moderate taper' :
             'Training race - minimal adjustment'}
          </p>
        </div>

        {/* Context Summary - Show what we know */}
        <div className="bg-blue-900/20 border border-blue-800 rounded-xl p-4">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
              <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-blue-300">Plan will be optimized for you</p>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs text-blue-400/80">
            <div>Fitness: <span className="text-blue-300 capitalize">{detectedFitnessLevel}</span></div>
            <div>Volume: <span className="text-blue-300">{detectedWeeklyMileage} km/week</span></div>
            <div>Training: <span className="text-blue-300">{patterns.avgDaysPerWeek} days/week</span></div>
            <div>Long runs: <span className="text-blue-300">{DAYS[patterns.typicalLongRunDay]}s</span></div>
          </div>
        </div>

        {/* Progress indicator */}
        {isGenerating && generationProgress && (
          <div className="bg-teal-900/30 border border-teal-700 rounded-xl p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="animate-spin w-5 h-5 border-2 border-teal-400 border-t-transparent rounded-full" />
              <p className="font-medium text-teal-300">{generationProgress.phase}</p>
            </div>
            <p className="text-sm text-teal-400 mb-3">{generationProgress.message}</p>
            <div className="h-2 bg-teal-900 rounded-full overflow-hidden">
              <div className="h-full bg-teal-500 rounded-full transition-all" style={{ width: `${generationProgress.percentage}%` }} />
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-xl p-4">
            <p className="text-red-400 font-medium">Generation failed</p>
            <p className="text-sm text-red-500">{error.message}</p>
          </div>
        )}

        {/* Success state */}
        {generatedPlan && (
          <div className="bg-green-900/30 border border-green-700 rounded-xl p-4">
            <p className="text-green-400 font-medium">Plan created!</p>
            <p className="text-sm text-green-500">{generatedPlan.totalWeeks} weeks ready</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-800 bg-gray-800/50 px-6 py-4 flex justify-between">
        {onCancel && (
          <button onClick={onCancel} className="px-4 py-2 text-gray-400 hover:text-gray-200">
            Cancel
          </button>
        )}
        <div className="flex-1" />
        <button onClick={generate} disabled={!valid || isGenerating || !!generatedPlan}
          className={clsx('px-8 py-3 font-medium rounded-xl transition-all',
            generatedPlan ? 'bg-green-600 text-white' : 'bg-teal-600 text-white hover:bg-teal-500',
            (!valid || isGenerating || generatedPlan) && 'opacity-75 cursor-not-allowed')}>
          {isGenerating ? 'Generating...' : generatedPlan ? 'Done' : 'Generate Plan'}
        </button>
      </div>
    </div>
  );
}
