'use client';

import { useState, useEffect } from 'react';

interface DirectionIndicator {
  direction: 'up' | 'down' | 'stable';
  change_pct: number;
  baseline: number;
  current: number;
}

interface Baselines {
  hrv_7d_avg: number | null;
  hrv_30d_avg: number | null;
  sleep_7d_avg: number | null;
  sleep_30d_avg: number | null;
  rhr_7d_avg: number | null;
  rhr_30d_avg: number | null;
  recovery_7d_avg: number | null;
}

interface DayData {
  date: string;
  sleep: {
    total_hours: number;
    deep_pct: number;
    rem_pct: number;
    score: number | null;
    efficiency: number | null;
    direction?: DirectionIndicator | null;
  } | null;
  hrv: {
    value: number | null;
    baseline: number | null;
    status: string | null;
    direction?: DirectionIndicator | null;
  };
  strain: {
    body_battery_charged: number | null;
    body_battery_drained: number | null;
    stress_avg: number | null;
    active_calories: number | null;
    intensity_minutes: number | null;
    direction?: DirectionIndicator | null;
  };
  activity: {
    steps: number;
    steps_goal: number;
  };
  resting_hr: number | null;
  rhr_direction?: DirectionIndicator | null;
  baselines?: Baselines;
}

function calculateRecovery(day: DayData): number {
  // Use personal baselines instead of fixed thresholds
  // This implements the WHOOP philosophy: "Your HRV vs *your* 7-day avg, not 'normal'"
  const weights: number[] = [];
  const scores: number[] = [];

  // HRV Factor (primary signal - weighted 1.5x)
  // Compare against personal 7-day baseline, not fixed values
  if (day.hrv?.value && day.baselines?.hrv_7d_avg) {
    const hrvRatio = day.hrv.value / day.baselines.hrv_7d_avg;
    // Score: 80 at baseline (ratio=1), scales with ratio
    // Below baseline decreases score, above increases
    const hrvScore = Math.min(100, Math.max(0, hrvRatio * 80 + 20));
    scores.push(hrvScore * 1.5);
    weights.push(1.5);
  } else if (day.hrv?.value && day.hrv?.baseline) {
    // Fallback to weekly avg from Garmin if personal baseline not available
    const hrvRatio = day.hrv.value / day.hrv.baseline;
    const hrvScore = Math.min(100, Math.max(0, hrvRatio * 75 + 25));
    scores.push(hrvScore * 1.5);
    weights.push(1.5);
  }

  // Sleep Factor - compare against personal sleep baseline
  if (day.sleep?.total_hours && day.baselines?.sleep_7d_avg) {
    const sleepRatio = day.sleep.total_hours / day.baselines.sleep_7d_avg;
    // Score based on how well you met YOUR personal sleep need
    const sleepScore = Math.min(100, Math.max(0, sleepRatio * 85 + 15));
    scores.push(sleepScore);
    weights.push(1.0);
  } else if (day.sleep) {
    // Fallback to fixed 8h target
    const sleepScore = Math.min(100, (day.sleep.total_hours / 8) * 85 +
      (day.sleep.deep_pct / 20) * 15);
    scores.push(sleepScore);
    weights.push(1.0);
  }

  // Body Battery Factor - direct recovery indicator
  if (day.strain?.body_battery_charged) {
    scores.push(day.strain.body_battery_charged);
    weights.push(1.0);
  }

  if (scores.length === 0) return 0;

  // Calculate weighted average
  const totalWeight = weights.reduce((a, b) => a + b, 0);
  const weightedSum = scores.reduce((a, b) => a + b, 0);
  return Math.round(weightedSum / totalWeight);
}

function calculateStrain(day: DayData): number {
  let strain = 0;

  if (day.activity?.steps) {
    strain += Math.min(8, day.activity.steps / 2000);
  }

  if (day.strain?.body_battery_drained) {
    strain += Math.min(8, day.strain.body_battery_drained / 12);
  }

  if (day.strain?.intensity_minutes) {
    strain += Math.min(5, day.strain.intensity_minutes / 20);
  }

  return Math.round(Math.min(21, strain) * 10) / 10;
}

function getRecoveryColor(recovery: number): string {
  if (recovery >= 67) return '#00F19B';
  if (recovery >= 34) return '#FFCC00';
  return '#FF4D4D';
}

function getRecoveryZone(recovery: number): string {
  if (recovery >= 67) return 'GREEN';
  if (recovery >= 34) return 'YELLOW';
  return 'RED';
}

export default function Dashboard() {
  const [history, setHistory] = useState<DayData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDay, setSelectedDay] = useState<DayData | null>(null);
  const [view, setView] = useState<'overview' | 'sleep' | 'strain' | 'recovery'>('overview');

  useEffect(() => {
    fetch('/api/wellness/history?days=14')
      .then(res => res.json())
      .then(data => {
        setHistory(data);
        if (data.length > 0) setSelectedDay(data[0]);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-gray-700 border-t-white rounded-full animate-spin" />
      </div>
    );
  }

  if (!selectedDay) {
    return (
      <div className="min-h-screen bg-black flex flex-col items-center justify-center gap-4 text-gray-400">
        <div>No data available</div>
        <code className="text-sm bg-gray-900 px-3 py-1 rounded">whoop fetch --days 14</code>
      </div>
    );
  }

  const recovery = calculateRecovery(selectedDay);
  const strain = calculateStrain(selectedDay);
  const recoveryColor = getRecoveryColor(recovery);

  // Calculate weekly averages
  const weekData = history.slice(0, 7);
  const avgRecovery = Math.round(weekData.reduce((sum, d) => sum + calculateRecovery(d), 0) / weekData.length);
  const avgStrain = Math.round(weekData.reduce((sum, d) => sum + calculateStrain(d), 0) / weekData.length * 10) / 10;
  const avgSleep = Math.round(weekData.reduce((sum, d) => sum + (d.sleep?.total_hours || 0), 0) / weekData.length * 10) / 10;

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Top Navigation */}
      <nav className="flex items-center justify-between px-4 py-3 border-b border-gray-900">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-teal-400 to-blue-500 flex items-center justify-center text-xs font-bold">
            W
          </div>
          <span className="font-semibold tracking-tight">DASHBOARD</span>
        </div>
        <div className="text-gray-500 text-sm">
          {new Date(selectedDay.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
        </div>
      </nav>

      {/* View Tabs */}
      <div className="flex border-b border-gray-900">
        {(['overview', 'recovery', 'strain', 'sleep'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setView(tab)}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              view === tab
                ? 'text-white border-b-2 border-white'
                : 'text-gray-600 hover:text-gray-400'
            }`}
          >
            {tab.toUpperCase()}
          </button>
        ))}
      </div>

      <main className="max-w-lg mx-auto">
        {view === 'overview' && (
          <OverviewView
            selectedDay={selectedDay}
            history={history}
            recovery={recovery}
            strain={strain}
            recoveryColor={recoveryColor}
            avgRecovery={avgRecovery}
            avgStrain={avgStrain}
            avgSleep={avgSleep}
            onSelectDay={setSelectedDay}
          />
        )}
        {view === 'recovery' && (
          <RecoveryView
            selectedDay={selectedDay}
            history={history}
            recovery={recovery}
            recoveryColor={recoveryColor}
            onSelectDay={setSelectedDay}
          />
        )}
        {view === 'strain' && (
          <StrainView
            selectedDay={selectedDay}
            history={history}
            strain={strain}
            onSelectDay={setSelectedDay}
          />
        )}
        {view === 'sleep' && (
          <SleepView
            selectedDay={selectedDay}
            history={history}
            onSelectDay={setSelectedDay}
          />
        )}
      </main>
    </div>
  );
}

function OverviewView({
  selectedDay,
  history,
  recovery,
  strain,
  recoveryColor,
  avgRecovery,
  avgStrain,
  avgSleep,
  onSelectDay,
}: {
  selectedDay: DayData;
  history: DayData[];
  recovery: number;
  strain: number;
  recoveryColor: string;
  avgRecovery: number;
  avgStrain: number;
  avgSleep: number;
  onSelectDay: (day: DayData) => void;
}) {
  return (
    <div className="p-4 space-y-6">
      {/* Weekly Summary Bar */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-gray-900 rounded-xl p-3 text-center">
          <div className="text-gray-500 text-xs mb-1">AVG RECOVERY</div>
          <div className="text-xl font-bold" style={{ color: getRecoveryColor(avgRecovery) }}>
            {avgRecovery}%
          </div>
        </div>
        <div className="bg-gray-900 rounded-xl p-3 text-center">
          <div className="text-gray-500 text-xs mb-1">AVG STRAIN</div>
          <div className="text-xl font-bold text-blue-400">{avgStrain}</div>
        </div>
        <div className="bg-gray-900 rounded-xl p-3 text-center">
          <div className="text-gray-500 text-xs mb-1">AVG SLEEP</div>
          <div className="text-xl font-bold text-purple-400">{avgSleep}h</div>
        </div>
      </div>

      {/* Day Selector */}
      <div className="flex gap-1 overflow-x-auto pb-2 -mx-4 px-4">
        {history.slice(0, 14).map((day) => {
          const dayRecovery = calculateRecovery(day);
          const isSelected = day.date === selectedDay.date;
          return (
            <button
              key={day.date}
              onClick={() => onSelectDay(day)}
              className={`flex-shrink-0 w-12 py-2 rounded-lg transition-all ${
                isSelected ? 'bg-gray-800 ring-1 ring-gray-600' : 'hover:bg-gray-900'
              }`}
            >
              <div className="text-gray-500 text-[10px]">
                {new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase()}
              </div>
              <div className="text-xs font-medium mt-0.5">
                {new Date(day.date).getDate()}
              </div>
              <div
                className="w-2 h-2 rounded-full mx-auto mt-1"
                style={{ backgroundColor: getRecoveryColor(dayRecovery) }}
              />
            </button>
          );
        })}
      </div>

      {/* Main Recovery Display */}
      <div className="flex flex-col items-center py-4">
        <div className="relative w-52 h-52">
          <svg className="w-full h-full transform -rotate-90">
            <circle cx="104" cy="104" r="92" fill="none" stroke="#1a1a1a" strokeWidth="16" />
            <circle
              cx="104"
              cy="104"
              r="92"
              fill="none"
              stroke={recoveryColor}
              strokeWidth="16"
              strokeLinecap="round"
              strokeDasharray={`${recovery * 5.78} 578`}
              className="transition-all duration-700"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-6xl font-bold" style={{ color: recoveryColor }}>
              {recovery}%
            </span>
            <span className="text-gray-500 text-sm mt-1">RECOVERY</span>
          </div>
        </div>

        <div
          className="mt-4 px-5 py-2 rounded-full text-sm font-semibold"
          style={{ backgroundColor: recoveryColor + '20', color: recoveryColor }}
        >
          {getRecoveryZone(recovery)} ZONE
        </div>
      </div>

      {/* Today's Stats Grid */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard
          label="STRAIN"
          value={strain.toString()}
          unit="of 21"
          color="#3B82F6"
          progress={strain / 21}
        />
        <StatCard
          label="SLEEP"
          value={selectedDay.sleep?.total_hours.toFixed(1) || '--'}
          unit="hours"
          color="#A855F7"
          progress={(selectedDay.sleep?.total_hours || 0) / (selectedDay.baselines?.sleep_7d_avg || 8)}
          direction={selectedDay.sleep?.direction}
          baselineLabel="vs your avg"
        />
        <StatCard
          label="HRV"
          value={selectedDay.hrv?.value?.toString() || '--'}
          unit="ms"
          color="#10B981"
          direction={selectedDay.hrv?.direction}
          baselineLabel="vs your avg"
        />
        <StatCard
          label="RHR"
          value={selectedDay.resting_hr?.toString() || '--'}
          unit="bpm"
          color="#EF4444"
          direction={selectedDay.rhr_direction}
          baselineLabel="vs your avg"
        />
      </div>

      {/* Daily Insight */}
      <div className="bg-gradient-to-br from-gray-900 to-gray-950 rounded-2xl p-4 border border-gray-800">
        <div className="text-gray-500 text-xs mb-2">INSIGHT</div>
        <p className="text-gray-300 text-sm leading-relaxed">
          {recovery >= 67 ? (
            <>Your body is primed for peak performance. HRV is {selectedDay.hrv?.value && selectedDay.hrv?.baseline && selectedDay.hrv.value >= selectedDay.hrv.baseline ? 'above' : 'near'} baseline. Consider a high-intensity workout or competition.</>
          ) : recovery >= 34 ? (
            <>Moderate recovery detected. Your body can handle activity but avoid overexertion. Focus on technique work or moderate cardio.</>
          ) : (
            <>Recovery is low. Prioritize rest, hydration, and sleep quality tonight. Light stretching or yoga recommended.</>
          )}
        </p>
      </div>
    </div>
  );
}

function RecoveryView({
  selectedDay,
  history,
  recovery,
  recoveryColor,
  onSelectDay,
}: {
  selectedDay: DayData;
  history: DayData[];
  recovery: number;
  recoveryColor: string;
  onSelectDay: (day: DayData) => void;
}) {
  const recoveryHistory = history.map(d => calculateRecovery(d)).reverse();
  const maxRecovery = Math.max(...recoveryHistory, 100);

  return (
    <div className="p-4 space-y-6">
      {/* Recovery Gauge */}
      <div className="flex flex-col items-center py-4">
        <div className="relative w-44 h-44">
          <svg className="w-full h-full transform -rotate-90">
            <circle cx="88" cy="88" r="76" fill="none" stroke="#1a1a1a" strokeWidth="14" />
            <circle
              cx="88"
              cy="88"
              r="76"
              fill="none"
              stroke={recoveryColor}
              strokeWidth="14"
              strokeLinecap="round"
              strokeDasharray={`${recovery * 4.77} 477`}
              className="transition-all duration-700"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-5xl font-bold" style={{ color: recoveryColor }}>
              {recovery}%
            </span>
          </div>
        </div>
        <div className="text-gray-500 text-sm mt-2">
          {new Date(selectedDay.date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
        </div>
      </div>

      {/* Recovery Trend Chart */}
      <div className="bg-gray-900 rounded-2xl p-4">
        <div className="text-gray-500 text-xs mb-4">14-DAY TREND</div>
        <div className="h-32 flex items-end gap-1">
          {recoveryHistory.map((val, i) => {
            const day = history[history.length - 1 - i];
            const isSelected = day?.date === selectedDay.date;
            return (
              <button
                key={i}
                onClick={() => day && onSelectDay(day)}
                className={`flex-1 rounded-t transition-all ${isSelected ? 'ring-1 ring-white' : ''}`}
                style={{
                  height: `${(val / maxRecovery) * 100}%`,
                  backgroundColor: getRecoveryColor(val),
                  minHeight: '4px',
                }}
              />
            );
          })}
        </div>
        <div className="flex justify-between mt-2 text-[10px] text-gray-600">
          <span>{history[history.length - 1]?.date.slice(5)}</span>
          <span>Today</span>
        </div>
      </div>

      {/* Recovery Factors */}
      <div className="space-y-3">
        <div className="text-gray-500 text-xs">CONTRIBUTING FACTORS (vs your baselines)</div>
        <FactorRow
          label="HRV"
          value={selectedDay.hrv?.value}
          baseline={selectedDay.baselines?.hrv_7d_avg || selectedDay.hrv?.baseline}
          unit="ms"
          direction={selectedDay.hrv?.direction}
        />
        <FactorRow
          label="Sleep"
          value={selectedDay.sleep?.total_hours}
          baseline={selectedDay.baselines?.sleep_7d_avg}
          unit="h"
          direction={selectedDay.sleep?.direction}
        />
        <FactorRow
          label="Body Battery Charged"
          value={selectedDay.strain?.body_battery_charged}
          baseline={selectedDay.baselines?.recovery_7d_avg}
          unit=""
          direction={selectedDay.strain?.direction}
        />
        <FactorRow
          label="Resting Heart Rate"
          value={selectedDay.resting_hr}
          baseline={selectedDay.baselines?.rhr_7d_avg}
          unit="bpm"
          direction={selectedDay.rhr_direction}
          inverse={true}
        />
      </div>
    </div>
  );
}

function StrainView({
  selectedDay,
  history,
  strain,
  onSelectDay,
}: {
  selectedDay: DayData;
  history: DayData[];
  strain: number;
  onSelectDay: (day: DayData) => void;
}) {
  const strainHistory = history.map(d => calculateStrain(d)).reverse();
  const maxStrain = Math.max(...strainHistory, 21);

  return (
    <div className="p-4 space-y-6">
      {/* Strain Display */}
      <div className="flex flex-col items-center py-4">
        <div className="text-7xl font-bold text-blue-400">{strain}</div>
        <div className="text-gray-500 text-sm">of 21.0 max strain</div>

        {/* Strain Bar */}
        <div className="w-full max-w-xs mt-6 h-3 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full transition-all duration-500"
            style={{ width: `${(strain / 21) * 100}%` }}
          />
        </div>

        <div className="flex justify-between w-full max-w-xs mt-1 text-[10px] text-gray-600">
          <span>Light</span>
          <span>Moderate</span>
          <span>High</span>
          <span>All Out</span>
        </div>
      </div>

      {/* Strain Trend */}
      <div className="bg-gray-900 rounded-2xl p-4">
        <div className="text-gray-500 text-xs mb-4">14-DAY STRAIN</div>
        <div className="h-28 flex items-end gap-1">
          {strainHistory.map((val, i) => {
            const day = history[history.length - 1 - i];
            const isSelected = day?.date === selectedDay.date;
            return (
              <button
                key={i}
                onClick={() => day && onSelectDay(day)}
                className={`flex-1 rounded-t transition-all ${isSelected ? 'ring-1 ring-white' : ''}`}
                style={{
                  height: `${(val / maxStrain) * 100}%`,
                  backgroundColor: '#3B82F6',
                  minHeight: '4px',
                }}
              />
            );
          })}
        </div>
      </div>

      {/* Strain Breakdown */}
      <div className="space-y-3">
        <div className="text-gray-500 text-xs">STRAIN BREAKDOWN</div>
        <div className="bg-gray-900 rounded-xl p-4 space-y-4">
          <div className="flex justify-between">
            <span className="text-gray-400">Steps</span>
            <span className="font-medium">{selectedDay.activity?.steps.toLocaleString() || 0}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Active Calories</span>
            <span className="font-medium">{selectedDay.strain?.active_calories || '--'} kcal</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Intensity Minutes</span>
            <span className="font-medium">{selectedDay.strain?.intensity_minutes || 0} min</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Energy Drained</span>
            <span className="font-medium">{selectedDay.strain?.body_battery_drained || '--'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function SleepView({
  selectedDay,
  history,
  onSelectDay,
}: {
  selectedDay: DayData;
  history: DayData[];
  onSelectDay: (day: DayData) => void;
}) {
  const sleep = selectedDay.sleep;
  const sleepHistory = history.map(d => d.sleep?.total_hours || 0).reverse();
  const maxSleep = Math.max(...sleepHistory, 10);

  return (
    <div className="p-4 space-y-6">
      {/* Sleep Display */}
      <div className="flex flex-col items-center py-4">
        <div className="flex items-baseline">
          <div className="text-6xl font-bold text-purple-400">
            {sleep?.total_hours.toFixed(1) || '--'}
          </div>
          <span className="text-2xl font-normal text-gray-500 ml-1">hrs</span>
          {sleep?.direction && sleep.direction.direction !== 'stable' && (
            <span className={`text-lg ml-2 ${sleep.direction.direction === 'up' ? 'text-green-400' : 'text-red-400'}`}>
              {sleep.direction.direction === 'up' ? '+' : ''}{sleep.direction.change_pct.toFixed(0)}%
            </span>
          )}
        </div>
        <div className="text-gray-500 text-sm mt-1">
          {sleep?.efficiency ? `${sleep.efficiency.toFixed(0)}% efficiency` : 'No sleep data'}
        </div>
        {selectedDay.baselines?.sleep_7d_avg && (
          <div className="text-gray-600 text-xs mt-1">
            Your avg: {selectedDay.baselines.sleep_7d_avg.toFixed(1)}h
          </div>
        )}
      </div>

      {/* Sleep Stages */}
      {sleep && (
        <div className="bg-gray-900 rounded-2xl p-4">
          <div className="text-gray-500 text-xs mb-3">SLEEP STAGES</div>

          {/* Stage Bar */}
          <div className="h-8 rounded-lg overflow-hidden flex">
            <div
              className="bg-indigo-700 transition-all"
              style={{ width: `${sleep.deep_pct}%` }}
            />
            <div
              className="bg-cyan-500 transition-all"
              style={{ width: `${sleep.rem_pct}%` }}
            />
            <div
              className="bg-purple-400 transition-all"
              style={{ width: `${100 - sleep.deep_pct - sleep.rem_pct}%` }}
            />
          </div>

          {/* Legend */}
          <div className="flex justify-between mt-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-indigo-700" />
              <span className="text-gray-400">Deep</span>
              <span className="font-medium">{sleep.deep_pct.toFixed(0)}%</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-cyan-500" />
              <span className="text-gray-400">REM</span>
              <span className="font-medium">{sleep.rem_pct.toFixed(0)}%</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-purple-400" />
              <span className="text-gray-400">Light</span>
              <span className="font-medium">{(100 - sleep.deep_pct - sleep.rem_pct).toFixed(0)}%</span>
            </div>
          </div>
        </div>
      )}

      {/* Sleep Trend */}
      <div className="bg-gray-900 rounded-2xl p-4">
        <div className="text-gray-500 text-xs mb-4">14-DAY SLEEP</div>
        <div className="h-28 flex items-end gap-1">
          {sleepHistory.map((val, i) => {
            const day = history[history.length - 1 - i];
            const isSelected = day?.date === selectedDay.date;
            return (
              <button
                key={i}
                onClick={() => day && onSelectDay(day)}
                className={`flex-1 rounded-t transition-all ${isSelected ? 'ring-1 ring-white' : ''}`}
                style={{
                  height: `${(val / maxSleep) * 100}%`,
                  backgroundColor: '#A855F7',
                  minHeight: val > 0 ? '4px' : '0',
                }}
              />
            );
          })}
        </div>
        <div className="flex justify-between mt-2">
          <div className="text-[10px] text-gray-600">Target: 7-9 hours</div>
          <div className="text-[10px] text-gray-600">
            Avg: {(sleepHistory.reduce((a, b) => a + b, 0) / sleepHistory.filter(s => s > 0).length).toFixed(1)}h
          </div>
        </div>
      </div>

      {/* Sleep Score */}
      {sleep?.score && (
        <div className="bg-gray-900 rounded-2xl p-4">
          <div className="flex justify-between items-center">
            <span className="text-gray-400">Sleep Score</span>
            <span className="text-2xl font-bold text-purple-400">{sleep.score}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// Direction arrow component
function DirectionArrow({ direction }: { direction?: DirectionIndicator | null }) {
  if (!direction) return null;

  if (direction.direction === 'up') {
    return <span className="text-green-400 ml-1">+{Math.abs(direction.change_pct)}%</span>;
  } else if (direction.direction === 'down') {
    return <span className="text-red-400 ml-1">-{Math.abs(direction.change_pct)}%</span>;
  }
  return <span className="text-gray-500 ml-1">--</span>;
}

function StatCard({
  label,
  value,
  unit,
  color,
  progress,
  subtext,
  direction,
  baselineLabel,
}: {
  label: string;
  value: string;
  unit: string;
  color: string;
  progress?: number;
  subtext?: string;
  direction?: DirectionIndicator | null;
  baselineLabel?: string;
}) {
  return (
    <div className="bg-gray-900 rounded-2xl p-4">
      <div className="text-gray-500 text-xs mb-2">{label}</div>
      <div className="flex items-baseline gap-1">
        <span className="text-2xl font-bold" style={{ color }}>{value}</span>
        <span className="text-gray-600 text-sm">{unit}</span>
        <DirectionArrow direction={direction} />
      </div>
      {direction?.baseline && (
        <div className="text-gray-600 text-xs mt-1">
          {baselineLabel || 'vs 7d avg'}: {direction.baseline.toFixed(1)}
        </div>
      )}
      {subtext && !direction?.baseline && <div className="text-gray-600 text-xs mt-1">{subtext}</div>}
      {progress !== undefined && (
        <div className="mt-3 h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${Math.min(100, progress * 100)}%`, backgroundColor: color }}
          />
        </div>
      )}
    </div>
  );
}

function FactorRow({
  label,
  value,
  baseline,
  unit,
  direction,
  inverse = false,
}: {
  label: string;
  value: number | null | undefined;
  baseline?: number | null;
  unit: string;
  direction?: DirectionIndicator | null;
  inverse?: boolean;
}) {
  // Determine if the value is "good" based on direction
  // For inverse metrics (like RHR), down is good
  const isGood = direction ? (
    inverse
      ? direction.direction === 'down' || (direction.direction === 'up' && direction.change_pct < 0)
      : direction.direction === 'up'
  ) : undefined;

  const isBad = direction ? (
    inverse
      ? direction.direction === 'up' && direction.change_pct > 0
      : direction.direction === 'down'
  ) : undefined;

  return (
    <div className="bg-gray-900 rounded-xl p-4 flex justify-between items-center">
      <div className="flex flex-col">
        <span className="text-gray-400">{label}</span>
        {baseline && (
          <span className="text-gray-600 text-xs">baseline: {typeof baseline === 'number' ? baseline.toFixed(1) : baseline}{unit}</span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <span className={`font-medium ${isGood ? 'text-green-400' : isBad ? 'text-red-400' : ''}`}>
          {value !== null && value !== undefined ? (typeof value === 'number' ? value.toFixed(1) : value) : '--'}{unit}
        </span>
        {direction && direction.direction !== 'stable' && (
          <span className={isGood ? 'text-green-400' : isBad ? 'text-red-400' : 'text-gray-500'}>
            {direction.direction === 'up' ? '+' : ''}{direction.change_pct.toFixed(0)}%
          </span>
        )}
        {direction?.direction === 'stable' && (
          <span className="text-gray-500 text-xs">stable</span>
        )}
      </div>
    </div>
  );
}
