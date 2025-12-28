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

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

interface Props {
  onGenerate: (req: GeneratePlanRequest) => void;
  onCancel?: () => void;
  isGenerating?: boolean;
  generationProgress?: { phase: string; message: string; percentage: number } | null;
  generatedPlan?: TrainingPlan | null;
  error?: Error | null;
  detectedFitnessLevel?: PlanConstraints['currentFitnessLevel'];
  detectedWeeklyMileage?: number;
}

export function PlanGenerator({
  onGenerate, onCancel, isGenerating = false, generationProgress, generatedPlan, error,
  detectedFitnessLevel, detectedWeeklyMileage,
}: Props) {
  const [step, setStep] = useState<'goal' | 'generate'>('goal');
  const [raceDistance, setRaceDistance] = useState<RaceDistance>('half_marathon');
  const [customKm, setCustomKm] = useState(50);
  const [raceDate, setRaceDate] = useState(() => format(addDays(nextMonday(new Date()), 84), 'yyyy-MM-dd'));
  const [targetTime, setTargetTime] = useState('');
  const [daysPerWeek, setDaysPerWeek] = useState(4);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [fitnessLevel, setFitnessLevel] = useState<PlanConstraints['currentFitnessLevel']>(detectedFitnessLevel || 'intermediate');
  const [periodization, setPeriodization] = useState<PeriodizationType>('undulating');
  const [longRunDay, setLongRunDay] = useState(6);
  const [restDays, setRestDays] = useState([4]);
  const [includeStrength, setIncludeStrength] = useState(true);
  const [includeCross, setIncludeCross] = useState(false);
  const [weeklyMileage, setWeeklyMileage] = useState(detectedWeeklyMileage || 30);
  const [priority, setPriority] = useState<'A' | 'B' | 'C'>('A');
  const [maxDuration, setMaxDuration] = useState(90);

  const parseTime = (s: string): number => {
    const p = s.split(':').map(Number);
    if (p.some(isNaN)) return 0;
    return p.length === 3 ? p[0] * 3600 + p[1] * 60 + p[2] : p.length === 2 ? p[0] * 60 + p[1] : 0;
  };

  const targetSec = useMemo(() => parseTime(targetTime), [targetTime]);
  const weeks = useMemo(() => Math.max(1, Math.ceil((new Date(raceDate).getTime() - Date.now()) / 604800000)), [raceDate]);
  const valid = raceDistance && raceDate && (raceDistance !== 'custom' || customKm > 0);

  const generate = () => {
    onGenerate({
      name: `${DISTANCES.find(d => d.value === raceDistance)?.label} Training Plan`,
      goal: { raceDistance, customDistance: raceDistance === 'custom' ? customKm * 1000 : undefined, targetTime: targetSec || undefined, raceDate, priority },
      constraints: { daysPerWeek, maxSessionDuration: maxDuration, longRunDay, restDays, includeStrength, includeCrossTraining: includeCross, currentFitnessLevel: fitnessLevel, weeklyMileageStart: weeklyMileage },
      periodizationType: periodization,
    });
  };

  const toggleRest = (d: number) => d !== longRunDay && setRestDays(r => r.includes(d) ? r.filter(x => x !== d) : [...r, d]);

  const input = 'w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-gray-100 focus:ring-2 focus:ring-teal-500';
  const chip = (active: boolean, color = 'teal') => clsx('flex-1 py-2 text-xs rounded-lg border transition-all', active ? `border-${color}-500 bg-${color}-500/10 text-${color}-400` : 'border-gray-700 text-gray-500');

  return (
    <div className="bg-gray-900 rounded-2xl border border-gray-800 overflow-hidden max-w-lg mx-auto">
      {/* Steps */}
      <div className="border-b border-gray-800 bg-gray-800/50 px-6 py-4 flex justify-center gap-4">
        {[{ id: 'goal', n: 1 }, { id: 'generate', n: 2 }].map(({ id, n }) => (
          <button key={id} onClick={() => (id === 'goal' || valid) && setStep(id as 'goal' | 'generate')} disabled={isGenerating || (id === 'generate' && !valid)}
            className={clsx('flex items-center gap-2 px-4 py-2 rounded-full', step === id ? 'bg-teal-600 text-white' : 'text-gray-400', id === 'generate' && !valid && 'opacity-50')}>
            <span className="w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium bg-white/20">{n}</span>
            <span className="font-medium capitalize">{id}</span>
          </button>
        ))}
      </div>

      <div className="p-6">
        {step === 'goal' ? (
          <div className="space-y-8">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-100 mb-2">What are you training for?</h2>
              <p className="text-gray-400">Choose your race distance</p>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {DISTANCES.map(d => (
                <button key={d.value} onClick={() => setRaceDistance(d.value)}
                  className={clsx('py-6 px-4 rounded-2xl border-2 flex flex-col items-center gap-2', raceDistance === d.value ? 'border-teal-500 bg-teal-500/10' : 'border-gray-700 hover:border-gray-600 bg-gray-800/50')}>
                  <span className="text-2xl font-bold text-gray-100">{d.icon}</span>
                  <span className="text-sm text-gray-400">{d.label}</span>
                </button>
              ))}
            </div>
            {raceDistance === 'custom' && (
              <div>
                <label className="block text-sm text-gray-400 mb-2">Distance (km)</label>
                <input type="number" value={customKm} onChange={e => setCustomKm(+e.target.value)} min="1" className={input} />
              </div>
            )}
            <div>
              <label className="block text-sm text-gray-400 mb-2">Race Date</label>
              <input type="date" value={raceDate} onChange={e => setRaceDate(e.target.value)} min={format(addDays(new Date(), 14), 'yyyy-MM-dd')} className={input} />
              <p className="text-sm text-gray-500 mt-2">{weeks} weeks of training</p>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Target Time (optional)</label>
              <input type="text" value={targetTime} onChange={e => setTargetTime(e.target.value)} placeholder="1:45:00" className={clsx(input, 'placeholder-gray-600')} />
              <p className="text-xs text-gray-500 mt-1">Format: H:MM:SS or MM:SS</p>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-gray-100 mb-2">Customize Your Plan</h2>
              <p className="text-gray-400">Set your training preferences</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-3">Training days per week</label>
              <div className="flex gap-2">
                {[3, 4, 5, 6].map(n => (
                  <button key={n} onClick={() => setDaysPerWeek(n)}
                    className={clsx('flex-1 py-4 rounded-xl border-2 font-bold text-xl', daysPerWeek === n ? 'border-teal-500 bg-teal-500/10 text-teal-400' : 'border-gray-700 text-gray-400 hover:border-gray-600')}>
                    {n}
                  </button>
                ))}
              </div>
            </div>
            {detectedFitnessLevel && (
              <div className="bg-blue-900/20 border border-blue-800 rounded-xl p-4 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                  <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-blue-300">Smart defaults applied</p>
                  <p className="text-xs text-blue-400/70">Based on workouts: {detectedFitnessLevel}, ~{detectedWeeklyMileage}km/week</p>
                </div>
              </div>
            )}
            <div className="border border-gray-700 rounded-xl overflow-hidden">
              <button onClick={() => setShowAdvanced(!showAdvanced)} className="w-full px-4 py-4 flex items-center justify-between bg-gray-800/50 hover:bg-gray-800">
                <span className="text-gray-300 font-medium">Advanced Options</span>
                <svg className={clsx('w-5 h-5 text-gray-400', showAdvanced && 'rotate-180')} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
              </button>
              {showAdvanced && (
                <div className="p-4 space-y-5 bg-gray-800/30">
                  <div>
                    <label className="block text-sm text-gray-400 mb-2">Race Priority</label>
                    <div className="flex gap-2">
                      {(['A', 'B', 'C'] as const).map(p => (
                        <button key={p} onClick={() => setPriority(p)}
                          className={clsx('flex-1 py-2 rounded-lg border text-sm font-medium', priority === p ? (p === 'A' ? 'border-red-500 bg-red-500/10 text-red-400' : p === 'B' ? 'border-yellow-500 bg-yellow-500/10 text-yellow-400' : 'border-gray-500 bg-gray-500/10 text-gray-400') : 'border-gray-700 text-gray-500')}>
                          {p} Race
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-2">Fitness Level</label>
                    <select value={fitnessLevel} onChange={e => setFitnessLevel(e.target.value as typeof fitnessLevel)} className={input}>
                      <option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option><option value="elite">Elite</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-2">Weekly mileage (km)</label>
                    <input type="number" value={weeklyMileage} onChange={e => setWeeklyMileage(+e.target.value)} className={input} />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-2">Max session: {maxDuration} min</label>
                    <input type="range" min="45" max="180" step="15" value={maxDuration} onChange={e => setMaxDuration(+e.target.value)} className="w-full accent-teal-500" />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-2">Periodization</label>
                    <select value={periodization} onChange={e => setPeriodization(e.target.value as PeriodizationType)} className={input}>
                      <option value="undulating">Undulating (Recommended)</option><option value="linear">Linear</option><option value="block">Block</option><option value="polarized">Polarized</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-2">Long Run Day</label>
                    <div className="flex gap-1">{DAYS.map((d, i) => <button key={i} onClick={() => setLongRunDay(i)} className={chip(longRunDay === i)}>{d}</button>)}</div>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-2">Rest Days</label>
                    <div className="flex gap-1">{DAYS.map((d, i) => <button key={i} onClick={() => toggleRest(i)} disabled={i === longRunDay} className={clsx(chip(restDays.includes(i), 'green'), i === longRunDay && 'opacity-30 cursor-not-allowed')}>{d}</button>)}</div>
                  </div>
                  <div className="space-y-3">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input type="checkbox" checked={includeStrength} onChange={e => setIncludeStrength(e.target.checked)} className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-teal-500" />
                      <span className="text-gray-300">Include strength training</span>
                    </label>
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input type="checkbox" checked={includeCross} onChange={e => setIncludeCross(e.target.checked)} className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-teal-500" />
                      <span className="text-gray-300">Include cross training</span>
                    </label>
                  </div>
                </div>
              )}
            </div>
            {isGenerating && generationProgress && (
              <div className="bg-teal-900/30 border border-teal-700 rounded-xl p-4">
                <div className="flex items-center gap-3 mb-3">
                  <div className="animate-spin w-5 h-5 border-2 border-teal-400 border-t-transparent rounded-full" />
                  <p className="font-medium text-teal-300">{generationProgress.phase}</p>
                </div>
                <p className="text-sm text-teal-400 mb-3">{generationProgress.message}</p>
                <div className="h-2 bg-teal-900 rounded-full overflow-hidden"><div className="h-full bg-teal-500 rounded-full" style={{ width: `${generationProgress.percentage}%` }} /></div>
              </div>
            )}
            {error && <div className="bg-red-900/30 border border-red-700 rounded-xl p-4"><p className="text-red-400 font-medium">Generation failed</p><p className="text-sm text-red-500">{error.message}</p></div>}
            {generatedPlan && <div className="bg-green-900/30 border border-green-700 rounded-xl p-4"><p className="text-green-400 font-medium">Plan created!</p><p className="text-sm text-green-500">{generatedPlan.totalWeeks} weeks ready</p></div>}
          </div>
        )}
      </div>

      <div className="border-t border-gray-800 bg-gray-800/50 px-6 py-4 flex justify-between">
        {step === 'goal' ? (
          <>
            {onCancel && <button onClick={onCancel} className="px-4 py-2 text-gray-400 hover:text-gray-200">Cancel</button>}
            <div className="flex-1" />
            <button onClick={() => setStep('generate')} disabled={!valid} className="px-8 py-3 bg-teal-600 text-white font-medium rounded-xl hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed">Continue</button>
          </>
        ) : (
          <>
            <button onClick={() => setStep('goal')} disabled={isGenerating} className="px-4 py-2 text-gray-400 hover:text-gray-200 disabled:opacity-50">Back</button>
            <button onClick={generate} disabled={isGenerating || !!generatedPlan} className={clsx('px-8 py-3 font-medium rounded-xl', generatedPlan ? 'bg-green-600 text-white' : 'bg-teal-600 text-white hover:bg-teal-500', (isGenerating || generatedPlan) && 'opacity-75 cursor-not-allowed')}>
              {isGenerating ? 'Generating...' : generatedPlan ? 'Done' : 'Generate Plan'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
