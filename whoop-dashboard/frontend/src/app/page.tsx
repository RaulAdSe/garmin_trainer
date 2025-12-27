'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { useWellnessHistory, useGarminSync, DayData } from '../services/hooks';
import { calculatePeriodTrend, formatTrendDisplay, TrendResult } from '../lib/trends';

// Info Modal component for displaying metric details
function InfoModal({
  info,
  onClose,
}: {
  info: { title: string; description: string; impact: string; tips: string[] };
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />
      <div
        className="relative bg-gray-900 rounded-2xl p-6 max-w-md w-full border border-gray-700 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-500 hover:text-white transition-colors text-xl"
        >
          ×
        </button>
        <h2 className="text-xl font-bold text-white mb-3">{info.title}</h2>
        <p className="text-gray-400 text-sm mb-4">{info.description}</p>
        <div className="mb-4">
          <h3 className="text-gray-500 text-xs mb-1">HEALTH IMPACT</h3>
          <p className="text-gray-300 text-sm">{info.impact}</p>
        </div>
        <div>
          <h3 className="text-gray-500 text-xs mb-2">TIPS</h3>
          <ul className="space-y-2">
            {info.tips.map((tip, i) => {
              const bulletColor = tip.startsWith('Green') ? 'text-green-400' :
                                  tip.startsWith('Yellow') ? 'text-yellow-400' :
                                  tip.startsWith('Red') ? 'text-red-400' : 'text-teal-400';
              return (
                <li key={i} className="text-gray-400 text-sm flex gap-2">
                  <span className={bulletColor}>•</span>
                  <span>{tip}</span>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </div>
  );
}

// Info button component
function InfoButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className="w-5 h-5 rounded-full bg-gray-700 hover:bg-gray-600 text-gray-400 hover:text-white text-xs flex items-center justify-center transition-colors"
      aria-label="More info"
    >
      ?
    </button>
  );
}

// Metric info content
const METRIC_INFO: Record<string, { title: string; description: string; impact: string; tips: string[] }> = {
  recovery: {
    title: 'Recovery Score',
    description: 'Your recovery score (0-100%) measures how ready your body is to perform today. It combines HRV, sleep quality, and body battery to estimate your physiological readiness.',
    impact: 'Higher recovery means your nervous system is balanced and your body has restored energy. Low recovery suggests accumulated stress or insufficient rest.',
    tips: [
      'Green (67-100%): Push hard - ideal for intense workouts',
      'Yellow (34-66%): Moderate effort - technique work or steady cardio',
      'Red (0-33%): Recovery focus - rest, mobility, light yoga',
    ],
  },
  strain: {
    title: 'Strain Score',
    description: 'Strain (0-21) measures the cardiovascular load on your body throughout the day. It combines steps, intensity minutes, and energy expenditure.',
    impact: 'The scale is logarithmic - going from 18 to 19 is much harder than 5 to 6. This prevents overtraining by making high strain harder to achieve.',
    tips: [
      'Match strain to recovery for optimal adaptation',
      'Higher recovery days = higher strain targets',
      'Consistent moderate strain beats occasional extreme strain',
    ],
  },
  sleep: {
    title: 'Sleep',
    description: 'Sleep duration and quality are crucial for recovery. We track total hours, sleep stages (deep, REM, light), and efficiency (time asleep vs time in bed).',
    impact: 'Deep sleep restores physical energy and repairs muscles. REM sleep consolidates memory and regulates mood. Both are essential for full recovery.',
    tips: [
      'Aim for your personal baseline, not a fixed 8 hours',
      'Higher strain days require more sleep',
      'Consistency matters more than occasional long sleeps',
    ],
  },
  hrv: {
    title: 'Heart Rate Variability (HRV)',
    description: 'HRV measures the variation in time between heartbeats (in milliseconds). Higher HRV generally indicates better cardiovascular fitness and recovery.',
    impact: 'HRV reflects your autonomic nervous system balance. High HRV = parasympathetic (rest) dominant. Low HRV = sympathetic (stress) dominant.',
    tips: [
      'Compare to YOUR baseline, not population averages',
      'Sudden drops may indicate stress, illness, or overtraining',
      'HRV naturally varies - look at 7-day trends',
    ],
  },
  rhr: {
    title: 'Resting Heart Rate (RHR)',
    description: 'Your resting heart rate is measured during sleep. Lower RHR generally indicates better cardiovascular fitness and recovery.',
    impact: 'Elevated RHR (above your baseline) can signal stress, dehydration, illness, or overtraining. It\'s an early warning system for your body.',
    tips: [
      'Lower is generally better for RHR',
      'A spike of 5+ bpm above baseline warrants attention',
      'Alcohol, late meals, and stress all elevate RHR',
    ],
  },
  body_battery: {
    title: 'Body Battery',
    description: 'Body Battery (0-100) tracks your energy levels throughout the day. It charges during rest and sleep, and drains during activity and stress.',
    impact: 'High morning body battery indicates good overnight recovery. Tracking drain rate helps understand how activities affect your energy.',
    tips: [
      'Aim to start the day with 60+ body battery',
      'High stress drains battery even without physical activity',
      'Matches well with subjective energy feelings',
    ],
  },
  sleep_stages: {
    title: 'Sleep Stages',
    description: 'Sleep cycles through stages: Light (N1/N2), Deep (N3), and REM. Each serves different recovery functions.',
    impact: 'Deep sleep (15-20%): Physical restoration, muscle repair, immune function. REM (20-25%): Mental recovery, memory consolidation, emotional regulation.',
    tips: [
      'Alcohol suppresses REM sleep',
      'Late exercise can reduce deep sleep',
      'Cool room temperature promotes better deep sleep',
    ],
  },
  sleep_debt: {
    title: 'Sleep Debt',
    description: 'Sleep debt accumulates when you sleep less than your body needs. It represents the total hours of missed sleep over recent days.',
    impact: 'Accumulated sleep debt impairs cognitive function, mood, and physical recovery. It takes multiple nights of good sleep to fully repay.',
    tips: [
      'Spread debt repayment over several nights',
      'Add 10-15 mins per night to gradually repay',
      'Sleeping in on weekends doesn\'t fully repay weekday debt',
    ],
  },
};

interface DirectionIndicator {
  direction: 'up' | 'down' | 'stable';
  change_pct: number;
  baseline: number;
  current: number;
}

interface CorrelationData {
  pattern_type: 'positive' | 'negative';
  category: string;
  title: string;
  description: string;
  impact: number;
  confidence: number;
  sample_size: number;
}

interface StreakData {
  name: string;
  current_count: number;
  best_count: number;
  is_active: boolean;
  last_date: string;
}

interface TrendAlertData {
  metric: string;
  direction: 'declining' | 'improving';
  days: number;
  change_pct: number;
  severity: 'warning' | 'concern' | 'positive';
}

interface WeeklySummaryData {
  green_days: number;
  yellow_days: number;
  red_days: number;
  avg_recovery: number;
  avg_strain: number;
  avg_sleep: number;
  total_sleep_debt: number;
  best_day: string;
  worst_day: string;
  correlations: CorrelationData[];
  streaks: StreakData[];
  trend_alerts: TrendAlertData[];
}

// Note: Baselines type is defined in hooks.ts and used via DayData.baselines

// DayData is imported from hooks.ts

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

// Strain target based on recovery zone
function getStrainTarget(recovery: number): [number, number] {
  if (recovery >= 67) return [14, 21];
  if (recovery >= 34) return [8, 14];
  return [0, 8];
}

// Strain recommendation text
function getStrainRecommendation(recovery: number): string {
  if (recovery >= 67) return "Great day for intervals or racing";
  if (recovery >= 34) return "Steady cardio or technique work";
  return "Rest, mobility, light yoga";
}

// Decision text based on recovery
function getDecisionText(recovery: number): string {
  if (recovery >= 67) return "GO FOR IT";
  if (recovery >= 34) return "MODERATE";
  return "RECOVER";
}

// Get insight text based on recovery and HRV
function getInsightText(recovery: number, day: DayData): string {
  if (recovery >= 67) {
    const hrvStatus = day.hrv?.direction?.direction === 'up' ? 'HRV trending up' : 'HRV at baseline';
    return `Your body is primed for intensity. ${hrvStatus}. Push hard today.`;
  }
  if (recovery >= 34) {
    return "Your body can handle moderate effort. Avoid all-out intensity.";
  }
  const sleepNote = day.sleep && day.sleep.total_hours < 6 ? ` Only ${day.sleep.total_hours.toFixed(1)}h sleep is limiting you.` : '';
  return `Focus on recovery today.${sleepNote} Light movement is fine.`;
}

// Calculate sleep target for tonight
function calculateSleepTarget(
  sleepBaseline: number,
  strainYesterday: number,
  sleepDebt: number
): number {
  const strainAdjustment = Math.max(0, (strainYesterday - 10) * 0.05);
  const debtRepayment = Math.max(0, sleepDebt) / 7;
  return Math.round((sleepBaseline + strainAdjustment + debtRepayment) * 100) / 100;
}

// Format hours as "Xh Ym"
function formatHoursMinutes(hours: number): string {
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  return `${h}h ${m.toString().padStart(2, '0')}m`;
}

// Get streak display info
function getStreakInfo(streak: StreakData): { icon: string; label: string } {
  switch (streak.name) {
    case 'green_days':
      return { icon: '!', label: `${streak.current_count}-day green streak` };
    case 'sleep_consistency':
      return { icon: '~', label: `${streak.current_count} days of 7h+ sleep` };
    case 'step_goal':
      return { icon: '#', label: `${streak.current_count} days hitting step goal` };
    default:
      return { icon: '*', label: `${streak.current_count}-day streak` };
  }
}

// Zone badge component
function ZoneBadge({ color, count, label }: { color: 'green' | 'yellow' | 'red'; count: number; label: string }) {
  const bgColors = {
    green: 'bg-green-900/40 border-green-700',
    yellow: 'bg-yellow-900/40 border-yellow-700',
    red: 'bg-red-900/40 border-red-700',
  };
  const textColors = {
    green: 'text-green-400',
    yellow: 'text-yellow-400',
    red: 'text-red-400',
  };

  return (
    <div className={`flex-1 px-3 py-2 rounded-lg border ${bgColors[color]}`}>
      <div className={`text-xl font-bold ${textColors[color]}`}>{count}</div>
      <div className="text-gray-500 text-xs">{label}</div>
    </div>
  );
}

// Week-over-week trend indicator component
function WeekTrendIndicator({
  trend,
  inverse = false,
  className = '',
}: {
  trend: TrendResult;
  inverse?: boolean;
  className?: string;
}) {
  const display = formatTrendDisplay(trend, inverse);

  if (!display) {
    if (!trend.hasEnoughData && trend.currentAvg > 0) {
      return (
        <div className={`text-xs text-gray-500 ${className}`}>
          -- vs last week
        </div>
      );
    }
    return null;
  }

  return (
    <div className={`text-xs ${display.colorClass} ${className}`}>
      {display.text}
    </div>
  );
}

// Weekly Insights component - Phase 4 Causality Engine
function WeeklyInsights({ history, weeklySummary }: { history: DayData[]; weeklySummary?: WeeklySummaryData }) {
  const weekData = history.slice(0, 7);
  const greenDays = weeklySummary?.green_days ?? weekData.filter(d => calculateRecovery(d) >= 67).length;
  const yellowDays = weeklySummary?.yellow_days ?? weekData.filter(d => {
    const r = calculateRecovery(d);
    return r >= 34 && r < 67;
  }).length;
  const redDays = weeklySummary?.red_days ?? weekData.filter(d => calculateRecovery(d) < 34).length;

  // Calculate this week's avg vs last week
  const thisWeekRecoveries = weekData.map(d => calculateRecovery(d));
  const avgRecovery = weeklySummary?.avg_recovery ??
    (thisWeekRecoveries.length > 0
      ? Math.round(thisWeekRecoveries.reduce((a, b) => a + b, 0) / thisWeekRecoveries.length)
      : 0);

  // Get last week data for comparison
  const lastWeekData = history.slice(7, 14);
  const lastWeekRecoveries = lastWeekData.map(d => calculateRecovery(d));
  const lastWeekAvg = lastWeekRecoveries.length > 0
    ? Math.round(lastWeekRecoveries.reduce((a, b) => a + b, 0) / lastWeekRecoveries.length)
    : avgRecovery;

  const recoveryDiff = avgRecovery - lastWeekAvg;

  // Get correlations and alerts from weekly summary
  const correlations = weeklySummary?.correlations || [];
  const streaks = weeklySummary?.streaks || [];
  const alerts = weeklySummary?.trend_alerts || [];

  // Get the most confident correlation to display
  const topCorrelation = correlations.length > 0 ? correlations[0] : null;

  return (
    <div className="bg-gray-900 rounded-2xl p-4 space-y-4">
      <div className="text-gray-500 text-xs">THIS WEEK</div>

      {/* Zone breakdown */}
      <div className="flex gap-2">
        <ZoneBadge color="green" count={greenDays} label="Green" />
        <ZoneBadge color="yellow" count={yellowDays} label="Yellow" />
        <ZoneBadge color="red" count={redDays} label="Red" />
      </div>

      {/* Trend indicator */}
      {recoveryDiff !== 0 && (
        <div className={`text-sm ${recoveryDiff > 0 ? 'text-green-400' : 'text-red-400'}`}>
          {recoveryDiff > 0 ? '+' : ''}{recoveryDiff.toFixed(1)}% recovery vs last week
        </div>
      )}

      {/* Active Streaks */}
      {streaks.length > 0 && (
        <div className="space-y-2">
          {streaks.slice(0, 3).map((streak, i) => {
            const { icon, label } = getStreakInfo(streak);
            return (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className="text-orange-400 font-bold">{icon}</span>
                <span className="text-gray-300">{label}</span>
                {streak.current_count >= streak.best_count && streak.best_count > 0 && (
                  <span className="text-yellow-400 text-xs">(Personal best!)</span>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Trend Alerts */}
      {alerts.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-gray-800">
          {alerts.map((alert, i) => (
            <div
              key={i}
              className={`flex items-start gap-2 text-sm ${
                alert.severity === 'positive' ? 'text-green-400' :
                alert.severity === 'concern' ? 'text-red-400' : 'text-yellow-400'
              }`}
            >
              <span>{alert.severity === 'positive' ? '^' : '!'}</span>
              <span>
                {alert.metric} {alert.direction} for {alert.days} days ({alert.change_pct > 0 ? '+' : ''}{alert.change_pct.toFixed(0)}%)
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Pattern detected */}
      {topCorrelation && (
        <div className={`border-l-2 pl-3 ${
          topCorrelation.pattern_type === 'negative' ? 'border-yellow-400' : 'border-green-400'
        }`}>
          <div className={`text-sm font-medium ${
            topCorrelation.pattern_type === 'negative' ? 'text-yellow-400' : 'text-green-400'
          }`}>
            Pattern Detected
          </div>
          <div className="text-gray-400 text-sm">
            {topCorrelation.description}
          </div>
          {topCorrelation.confidence >= 0.7 && (
            <div className="text-gray-600 text-xs mt-1">
              Based on {topCorrelation.sample_size} data points
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Trend period toggle component
type TrendPeriod = 14 | 30 | 90;

function TrendPeriodToggle({
  value,
  onChange,
}: {
  value: TrendPeriod;
  onChange: (period: TrendPeriod) => void;
}) {
  const periods: TrendPeriod[] = [14, 30, 90];

  return (
    <div className="inline-flex rounded-full bg-gray-800 p-0.5 text-xs">
      {periods.map((period) => (
        <button
          key={period}
          onClick={() => onChange(period)}
          className={`px-2.5 py-1 rounded-full transition-all ${
            value === period
              ? 'bg-gray-700 text-white'
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          {period}D
        </button>
      ))}
    </div>
  );
}

// Overview period toggle component - minimal design for non-invasive UX
type OverviewPeriod = 7 | 14 | 30;

function OverviewPeriodToggle({
  value,
  onChange,
}: {
  value: OverviewPeriod;
  onChange: (period: OverviewPeriod) => void;
}) {
  const periods: OverviewPeriod[] = [7, 14, 30];

  return (
    <div className="inline-flex rounded-md bg-gray-800/50 p-0.5 text-[10px]">
      {periods.map((period) => (
        <button
          key={period}
          onClick={() => onChange(period)}
          className={`px-1.5 py-0.5 rounded transition-all ${
            value === period
              ? 'bg-gray-700 text-white'
              : 'text-gray-500 hover:text-gray-400'
          }`}
        >
          {period}D
        </button>
      ))}
    </div>
  );
}

export default function Dashboard() {
  // Trend period state - shared across all trend charts
  const [trendPeriod, setTrendPeriod] = useState<TrendPeriod>(14);
  // Overview period state - for weekly summary averages (7, 14, or 30 days)
  const [overviewPeriod, setOverviewPeriod] = useState<OverviewPeriod>(7);

  // Use client-side hook - fetch max available data (90 days) for full history access
  const { history, loading, error: historyError } = useWellnessHistory(90);
  const garminSync = useGarminSync();
  const [view, setView] = useState<'overview' | 'sleep' | 'strain' | 'recovery'>('overview');
  const [activeInfoModal, setActiveInfoModal] = useState<string | null>(null);
  const [syncDays, setSyncDays] = useState(14);

  // Derive selected day from history - defaults to first day (today)
  // Use state only for user-driven day selection
  const [userSelectedDay, setUserSelectedDay] = useState<string | null>(null);
  const selectedDay = useMemo(() => {
    if (userSelectedDay) {
      return history.find(d => d.date === userSelectedDay) || (history.length > 0 ? history[0] : null);
    }
    return history.length > 0 ? history[0] : null;
  }, [history, userSelectedDay]);

  // Handler for selecting a day
  const handleSelectDay = (day: DayData) => {
    setUserSelectedDay(day.date);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-gray-700 border-t-white rounded-full animate-spin" />
      </div>
    );
  }

  if (!selectedDay) {
    return (
      <div className="min-h-screen bg-black flex flex-col items-center justify-center gap-6 text-gray-400 p-6">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-teal-400 to-blue-500 flex items-center justify-center text-3xl font-bold text-white">
          W
        </div>
        <div className="text-center">
          <h1 className="text-white text-xl font-semibold mb-2">Welcome to WHOOP Dashboard</h1>
          <p className="text-gray-500 text-sm max-w-xs">
            Connect your Garmin account to sync your wellness data and start tracking your recovery.
          </p>
        </div>
        <Link
          href="/sync"
          className="flex items-center gap-2 bg-teal-500 hover:bg-teal-400 text-black font-semibold px-6 py-3 rounded-full transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Sync with Garmin
        </Link>
      </div>
    );
  }

  const recovery = calculateRecovery(selectedDay);
  const strain = calculateStrain(selectedDay);
  const recoveryColor = getRecoveryColor(recovery);

  // Calculate averages based on selected overview period (7, 14, or 30 days)
  const periodData = history.slice(0, overviewPeriod);
  const avgRecovery = periodData.length > 0
    ? Math.round(periodData.reduce((sum, d) => sum + calculateRecovery(d), 0) / periodData.length)
    : 0;
  const avgStrain = periodData.length > 0
    ? Math.round(periodData.reduce((sum, d) => sum + calculateStrain(d), 0) / periodData.length * 10) / 10
    : 0;
  const avgSleep = periodData.length > 0
    ? Math.round(periodData.reduce((sum, d) => sum + (d.sleep?.total_hours || 0), 0) / periodData.length * 10) / 10
    : 0;

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
        <div className="flex items-center gap-4">
          <Link
            href="/sync"
            className="flex items-center gap-1.5 text-gray-400 hover:text-teal-400 transition-colors text-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span className="hidden sm:inline">Sync</span>
          </Link>
          <div className="text-gray-500 text-sm">
            {new Date(selectedDay.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          </div>
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
            overviewPeriod={overviewPeriod}
            onOverviewPeriodChange={setOverviewPeriod}
            onSelectDay={handleSelectDay}
            onShowInfo={setActiveInfoModal}
            garminSync={garminSync}
            syncDays={syncDays}
            onSyncDaysChange={setSyncDays}
          />
        )}
        {view === 'recovery' && (
          <RecoveryView
            selectedDay={selectedDay}
            history={history}
            recovery={recovery}
            recoveryColor={recoveryColor}
            onSelectDay={handleSelectDay}
            onShowInfo={setActiveInfoModal}
            trendPeriod={trendPeriod}
            onTrendPeriodChange={setTrendPeriod}
          />
        )}
        {view === 'strain' && (
          <StrainView
            selectedDay={selectedDay}
            history={history}
            strain={strain}
            onSelectDay={handleSelectDay}
            onShowInfo={setActiveInfoModal}
            trendPeriod={trendPeriod}
            onTrendPeriodChange={setTrendPeriod}
          />
        )}
        {view === 'sleep' && (
          <SleepView
            selectedDay={selectedDay}
            history={history}
            onSelectDay={handleSelectDay}
            onShowInfo={setActiveInfoModal}
            trendPeriod={trendPeriod}
            onTrendPeriodChange={setTrendPeriod}
          />
        )}
      </main>

      {/* Info Modal */}
      {activeInfoModal && METRIC_INFO[activeInfoModal] && (
        <InfoModal
          info={METRIC_INFO[activeInfoModal]}
          onClose={() => setActiveInfoModal(null)}
        />
      )}
    </div>
  );
}

// Sync panel props type
interface GarminSyncState {
  isAuthenticated: boolean | null;
  syncing: boolean;
  progress: { current: number; total: number } | null;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  sync: (days: number) => Promise<boolean>;
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
  overviewPeriod,
  onOverviewPeriodChange,
  onSelectDay,
  onShowInfo,
  garminSync,
  syncDays,
  onSyncDaysChange,
}: {
  selectedDay: DayData;
  history: DayData[];
  recovery: number;
  strain: number;
  recoveryColor: string;
  avgRecovery: number;
  avgStrain: number;
  avgSleep: number;
  overviewPeriod: OverviewPeriod;
  onOverviewPeriodChange: (period: OverviewPeriod) => void;
  onSelectDay: (day: DayData) => void;
  onShowInfo: (key: string) => void;
  garminSync: GarminSyncState;
  syncDays: number;
  onSyncDaysChange: (days: number) => void;
}) {
  const strainTarget = getStrainTarget(recovery);
  const [showLogin, setShowLogin] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState<string | null>(null);

  const handleLogin = async () => {
    setLoginError(null);
    const success = await garminSync.login(email, password);
    if (success) {
      setShowLogin(false);
      // Auto-sync after login
      garminSync.sync(syncDays);
    } else {
      setLoginError(garminSync.error || 'Login failed');
    }
  };

  const handleSync = async () => {
    if (!garminSync.isAuthenticated) {
      setShowLogin(true);
      return;
    }
    await garminSync.sync(syncDays);
    // Reload page to show new data
    window.location.reload();
  };

  return (
    <div className="p-4 space-y-6">
      {/* Hero Decision Component - THE FIRST THING YOU SEE */}
      <div className="text-center py-6 bg-gradient-to-b from-gray-900 to-black rounded-2xl">
        <div className={`text-5xl sm:text-6xl font-bold mb-3 ${
          recovery >= 67 ? 'text-green-400' :
          recovery >= 34 ? 'text-yellow-400' : 'text-red-400'
        }`}>
          {getDecisionText(recovery)}
        </div>
        <p className="text-gray-400 text-base max-w-xs mx-auto px-4">
          {getInsightText(recovery, selectedDay)}
        </p>
        <div className="mt-4 flex items-center justify-center gap-4 text-sm">
          <div className="text-gray-500">
            Target strain: <span className="text-white font-medium">{strainTarget[0]}-{strainTarget[1]}</span>
          </div>
          <div className="w-px h-4 bg-gray-700" />
          <div className="text-gray-500">
            {getStrainRecommendation(recovery)}
          </div>
        </div>
      </div>

      {/* Weekly Summary Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between px-1">
          <div className="text-gray-500 text-xs">{overviewPeriod}-DAY AVERAGES</div>
          <OverviewPeriodToggle value={overviewPeriod} onChange={onOverviewPeriodChange} />
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-900 rounded-xl p-3 text-center">
            <div className="text-gray-500 text-xs mb-1">RECOVERY</div>
            <div className="text-xl font-bold" style={{ color: getRecoveryColor(avgRecovery) }}>
              {avgRecovery}%
            </div>
          </div>
          <div className="bg-gray-900 rounded-xl p-3 text-center">
            <div className="text-gray-500 text-xs mb-1">STRAIN</div>
            <div className="text-xl font-bold text-blue-400">{avgStrain}</div>
          </div>
          <div className="bg-gray-900 rounded-xl p-3 text-center">
            <div className="text-gray-500 text-xs mb-1">SLEEP</div>
            <div className="text-xl font-bold text-purple-400">{avgSleep}h</div>
          </div>
        </div>
      </div>

      {/* Day Selector - shows all loaded days, swipe right for older */}
      <div className="flex gap-1 overflow-x-auto pb-2 -mx-4 px-4 scrollbar-hide">
        {history.map((day) => {
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
          {/* Info button */}
          <div className="absolute top-0 right-0 z-10">
            <InfoButton onClick={() => onShowInfo('recovery')} />
          </div>
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
          infoKey="strain"
          onShowInfo={onShowInfo}
        />
        <StatCard
          label="SLEEP"
          value={selectedDay.sleep?.total_hours.toFixed(1) || '--'}
          unit="hours"
          color="#A855F7"
          progress={(selectedDay.sleep?.total_hours || 0) / (selectedDay.baselines?.sleep_7d_avg || 8)}
          direction={selectedDay.sleep?.direction}
          baselineLabel="vs your avg"
          infoKey="sleep"
          onShowInfo={onShowInfo}
        />
        <StatCard
          label="HRV"
          value={selectedDay.hrv?.value?.toString() || '--'}
          unit="ms"
          color="#10B981"
          direction={selectedDay.hrv?.direction}
          baselineLabel="vs your avg"
          infoKey="hrv"
          onShowInfo={onShowInfo}
        />
        <StatCard
          label="RHR"
          value={selectedDay.resting_hr?.toString() || '--'}
          unit="bpm"
          color="#EF4444"
          direction={selectedDay.rhr_direction}
          baselineLabel="vs your avg"
          infoKey="rhr"
          onShowInfo={onShowInfo}
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

      {/* Weekly Insights - Phase 4 Causality Engine */}
      <WeeklyInsights history={history} weeklySummary={selectedDay.weekly_summary} />

      {/* Garmin Sync Panel */}
      <div className="bg-gradient-to-br from-teal-900/30 to-gray-900 rounded-2xl p-4 border border-teal-800/30">
        <div className="flex justify-between items-center mb-3">
          <div className="text-gray-400 text-xs font-medium">GARMIN SYNC</div>
          {garminSync.isAuthenticated && (
            <button
              onClick={() => garminSync.logout()}
              className="text-xs text-gray-500 hover:text-gray-300"
            >
              Logout
            </button>
          )}
        </div>

        {showLogin ? (
          <div className="space-y-3">
            <input
              type="email"
              placeholder="Garmin Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-teal-500"
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-teal-500"
            />
            {loginError && (
              <div className="text-red-400 text-xs">{loginError}</div>
            )}
            <div className="flex gap-2">
              <button
                onClick={handleLogin}
                className="flex-1 bg-teal-500 hover:bg-teal-400 text-black font-semibold py-2 rounded-lg text-sm transition-colors"
              >
                Login & Sync
              </button>
              <button
                onClick={() => setShowLogin(false)}
                className="px-4 bg-gray-700 hover:bg-gray-600 text-white py-2 rounded-lg text-sm transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <select
                value={syncDays}
                onChange={(e) => onSyncDaysChange(Number(e.target.value))}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-teal-500"
              >
                <option value={7}>7 days</option>
                <option value={14}>14 days</option>
                <option value={30}>30 days</option>
                <option value={60}>60 days</option>
                <option value={90}>90 days</option>
              </select>
              <button
                onClick={handleSync}
                disabled={garminSync.syncing}
                className="flex-1 bg-teal-500 hover:bg-teal-400 disabled:bg-teal-700 disabled:cursor-not-allowed text-black font-semibold py-2 rounded-lg text-sm transition-colors flex items-center justify-center gap-2"
              >
                {garminSync.syncing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                    {garminSync.progress ? `${garminSync.progress.current}/${garminSync.progress.total}` : 'Syncing...'}
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    {garminSync.isAuthenticated ? 'Sync Now' : 'Connect Garmin'}
                  </>
                )}
              </button>
            </div>
            {garminSync.error && (
              <div className="text-red-400 text-xs">{garminSync.error}</div>
            )}
            {garminSync.isAuthenticated && (
              <div className="text-gray-500 text-xs text-center">
                Connected to Garmin Connect
              </div>
            )}
          </div>
        )}
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
  onShowInfo,
  trendPeriod,
  onTrendPeriodChange,
}: {
  selectedDay: DayData;
  history: DayData[];
  recovery: number;
  recoveryColor: string;
  onSelectDay: (day: DayData) => void;
  onShowInfo: (key: string) => void;
  trendPeriod: TrendPeriod;
  onTrendPeriodChange: (period: TrendPeriod) => void;
}) {
  // Slice history based on selected trend period for chart display
  const periodHistory = history.slice(0, trendPeriod);
  const recoveryHistory = periodHistory.map(d => calculateRecovery(d)).reverse();
  const maxRecovery = Math.max(...recoveryHistory, 100);

  // Calculate period-based trend for recovery (needs full history for comparison)
  const allRecoveryValues = useMemo(() => history.map(d => calculateRecovery(d)), [history]);
  const recoveryTrend = useMemo(() => calculatePeriodTrend(allRecoveryValues, trendPeriod), [allRecoveryValues, trendPeriod]);

  return (
    <div className="p-4 space-y-6">
      {/* Recovery Gauge */}
      <div className="flex flex-col items-center py-4">
        <div className="relative w-44 h-44">
          {/* Info button */}
          <div className="absolute top-0 right-0 z-10">
            <InfoButton onClick={() => onShowInfo('recovery')} />
          </div>
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
        {/* Week-over-week trend indicator */}
        <WeekTrendIndicator trend={recoveryTrend} className="mt-1" />
      </div>

      {/* Recovery Trend Chart */}
      <div className="bg-gray-900 rounded-2xl p-4">
        <div className="flex justify-between items-center mb-4">
          <div className="text-gray-500 text-xs">{trendPeriod}-DAY TREND</div>
          <TrendPeriodToggle value={trendPeriod} onChange={onTrendPeriodChange} />
        </div>
        <div className="h-32 flex items-end gap-0.5 overflow-x-auto">
          {recoveryHistory.map((val, i) => {
            const day = periodHistory[periodHistory.length - 1 - i];
            const isSelected = day?.date === selectedDay.date;
            // Adjust bar width based on period
            const barWidth = trendPeriod <= 14 ? 'flex-1' : trendPeriod <= 30 ? 'min-w-[8px] flex-shrink-0' : 'min-w-[4px] flex-shrink-0';
            return (
              <button
                key={i}
                onClick={() => day && onSelectDay(day)}
                className={`${barWidth} rounded-t transition-all ${isSelected ? 'ring-1 ring-white' : ''}`}
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
          <span>{periodHistory[periodHistory.length - 1]?.date.slice(5)}</span>
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
  onShowInfo,
  trendPeriod,
  onTrendPeriodChange,
}: {
  selectedDay: DayData;
  history: DayData[];
  strain: number;
  onSelectDay: (day: DayData) => void;
  onShowInfo: (key: string) => void;
  trendPeriod: TrendPeriod;
  onTrendPeriodChange: (period: TrendPeriod) => void;
}) {
  // Slice history based on selected trend period for chart display
  const periodHistory = history.slice(0, trendPeriod);
  const strainHistory = periodHistory.map(d => calculateStrain(d)).reverse();
  const maxStrain = Math.max(...strainHistory, 21);
  const recovery = calculateRecovery(selectedDay);
  const strainTarget = getStrainTarget(recovery);
  const isInTarget = strain >= strainTarget[0] && strain <= strainTarget[1];
  const isBelowTarget = strain < strainTarget[0];
  const isAboveTarget = strain > strainTarget[1];

  // Calculate period-based trend for strain (needs full history for comparison)
  const allStrainValues = useMemo(() => history.map(d => calculateStrain(d)), [history]);
  const strainTrend = useMemo(() => calculatePeriodTrend(allStrainValues, trendPeriod), [allStrainValues, trendPeriod]);

  return (
    <div className="p-4 space-y-6">
      {/* Strain Display */}
      <div className="flex flex-col items-center py-4 relative">
        <div className="absolute top-4 right-4">
          <InfoButton onClick={() => onShowInfo('strain')} />
        </div>
        <div className="text-7xl font-bold text-blue-400">{strain}</div>
        <div className="text-gray-500 text-sm">of 21.0 max strain</div>
        {/* Week-over-week trend indicator */}
        <WeekTrendIndicator trend={strainTrend} className="mt-1" />

        {/* Strain Bar with Target Zone */}
        <div className="w-full max-w-xs mt-6 relative">
          {/* Target zone indicator */}
          <div
            className="absolute h-5 bg-gray-700/50 rounded-sm -top-1"
            style={{
              left: `${(strainTarget[0] / 21) * 100}%`,
              width: `${((strainTarget[1] - strainTarget[0]) / 21) * 100}%`,
            }}
          />
          {/* Strain bar */}
          <div className="h-3 bg-gray-800 rounded-full overflow-hidden relative z-10">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                isInTarget ? 'bg-gradient-to-r from-green-600 to-green-400' :
                isAboveTarget ? 'bg-gradient-to-r from-red-600 to-red-400' :
                'bg-gradient-to-r from-blue-600 to-blue-400'
              }`}
              style={{ width: `${(strain / 21) * 100}%` }}
            />
          </div>
        </div>

        <div className="flex justify-between w-full max-w-xs mt-1 text-[10px] text-gray-600">
          <span>Light</span>
          <span>Moderate</span>
          <span>High</span>
          <span>All Out</span>
        </div>

        {/* Target Status */}
        <div className={`mt-4 px-4 py-2 rounded-lg text-sm ${
          isInTarget ? 'bg-green-900/30 text-green-400' :
          isBelowTarget ? 'bg-gray-800 text-gray-400' :
          'bg-red-900/30 text-red-400'
        }`}>
          {isInTarget ? (
            <>In target zone ({strainTarget[0]}-{strainTarget[1]})</>
          ) : isBelowTarget ? (
            <>Target: {strainTarget[0]}-{strainTarget[1]} | {(strainTarget[0] - strain).toFixed(1)} more to go</>
          ) : (
            <>Above target ({strainTarget[0]}-{strainTarget[1]}) - Consider recovery</>
          )}
        </div>
      </div>

      {/* Strain Trend */}
      <div className="bg-gray-900 rounded-2xl p-4">
        <div className="flex justify-between items-center mb-4">
          <div className="text-gray-500 text-xs">{trendPeriod}-DAY STRAIN</div>
          <TrendPeriodToggle value={trendPeriod} onChange={onTrendPeriodChange} />
        </div>
        <div className="h-28 flex items-end gap-0.5 overflow-x-auto">
          {strainHistory.map((val, i) => {
            const day = periodHistory[periodHistory.length - 1 - i];
            const isSelected = day?.date === selectedDay.date;
            // Adjust bar width based on period
            const barWidth = trendPeriod <= 14 ? 'flex-1' : trendPeriod <= 30 ? 'min-w-[8px] flex-shrink-0' : 'min-w-[4px] flex-shrink-0';
            return (
              <button
                key={i}
                onClick={() => day && onSelectDay(day)}
                className={`${barWidth} rounded-t transition-all ${isSelected ? 'ring-1 ring-white' : ''}`}
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
  onShowInfo,
  trendPeriod,
  onTrendPeriodChange,
}: {
  selectedDay: DayData;
  history: DayData[];
  onSelectDay: (day: DayData) => void;
  onShowInfo: (key: string) => void;
  trendPeriod: TrendPeriod;
  onTrendPeriodChange: (period: TrendPeriod) => void;
}) {
  const sleep = selectedDay.sleep;
  // Slice history based on selected trend period for chart display
  const periodHistory = history.slice(0, trendPeriod);
  const sleepHistory = periodHistory.map(d => d.sleep?.total_hours || 0).reverse();
  const maxSleep = Math.max(...sleepHistory, 10);

  // Calculate period-based trend for sleep (needs full history for comparison)
  const allSleepValues = useMemo(() => history.map(d => d.sleep?.total_hours || 0), [history]);
  const sleepTrend = useMemo(() => calculatePeriodTrend(allSleepValues, trendPeriod), [allSleepValues, trendPeriod]);

  // Calculate sleep debt and tonight's target
  const sleepBaseline = selectedDay.baselines?.sleep_7d_avg || 7.5;
  const strainYesterday = history[1] ? calculateStrain(history[1]) : 10;

  // Calculate accumulated debt over last 7 days
  const accumulatedDebt = history.slice(0, 7).reduce((debt, day) => {
    const dayBaseline = day.baselines?.sleep_7d_avg || sleepBaseline;
    const daySleep = day.sleep?.total_hours || 0;
    return debt + Math.max(0, dayBaseline - daySleep);
  }, 0);

  const sleepTarget = calculateSleepTarget(sleepBaseline, strainYesterday, accumulatedDebt);
  const strainAdjustmentMins = Math.round(Math.max(0, (strainYesterday - 10) * 0.05) * 60);
  const debtRepaymentMins = Math.round((Math.max(0, accumulatedDebt) / 7) * 60);

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
        {/* Week-over-week trend indicator */}
        <WeekTrendIndicator trend={sleepTrend} className="mt-1" />
      </div>

      {/* Tonight's Sleep Target - PERSONALIZED */}
      <div className="bg-gradient-to-br from-purple-900/40 to-gray-900 rounded-2xl p-4 border border-purple-800/30 relative">
        <div className="flex justify-between items-start mb-3">
          <div className="text-gray-400 text-xs">TONIGHT&apos;S TARGET</div>
          <InfoButton onClick={() => onShowInfo('sleep_debt')} />
        </div>
        <div className="flex items-baseline justify-center mb-4">
          <span className="text-4xl font-bold text-purple-400">{formatHoursMinutes(sleepTarget)}</span>
        </div>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between text-gray-500">
            <span>Your baseline</span>
            <span className="text-gray-300">{formatHoursMinutes(sleepBaseline)}</span>
          </div>
          {strainAdjustmentMins > 0 && (
            <div className="flex justify-between text-gray-500">
              <span>Strain adjustment (strain was {strainYesterday.toFixed(1)})</span>
              <span className="text-purple-400">+{strainAdjustmentMins}m</span>
            </div>
          )}
          {accumulatedDebt > 0 && (
            <div className="flex justify-between text-gray-500">
              <span>Debt repayment ({formatHoursMinutes(accumulatedDebt)} total)</span>
              <span className="text-purple-400">+{debtRepaymentMins}m</span>
            </div>
          )}
        </div>
        {accumulatedDebt > 0.5 && (
          <div className="mt-4 pt-3 border-t border-gray-800 text-xs text-gray-500 text-center">
            Sleep debt: {formatHoursMinutes(accumulatedDebt)} accumulated over 7 days
          </div>
        )}
      </div>

      {/* Sleep Stages */}
      {sleep && (
        <div className="bg-gray-900 rounded-2xl p-4 relative">
          <div className="flex justify-between items-start mb-3">
            <div className="text-gray-500 text-xs">SLEEP STAGES</div>
            <InfoButton onClick={() => onShowInfo('sleep_stages')} />
          </div>

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
        <div className="flex justify-between items-center mb-4">
          <div className="text-gray-500 text-xs">{trendPeriod}-DAY SLEEP</div>
          <TrendPeriodToggle value={trendPeriod} onChange={onTrendPeriodChange} />
        </div>
        <div className="h-28 flex items-end gap-0.5 overflow-x-auto">
          {sleepHistory.map((val, i) => {
            const day = periodHistory[periodHistory.length - 1 - i];
            const isSelected = day?.date === selectedDay.date;
            // Adjust bar width based on period
            const barWidth = trendPeriod <= 14 ? 'flex-1' : trendPeriod <= 30 ? 'min-w-[8px] flex-shrink-0' : 'min-w-[4px] flex-shrink-0';
            return (
              <button
                key={i}
                onClick={() => day && onSelectDay(day)}
                className={`${barWidth} rounded-t transition-all ${isSelected ? 'ring-1 ring-white' : ''}`}
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
    return <span className="text-green-400 ml-1">+{Math.abs(direction.change_pct).toFixed(1)}%</span>;
  } else if (direction.direction === 'down') {
    return <span className="text-red-400 ml-1">-{Math.abs(direction.change_pct).toFixed(1)}%</span>;
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
  infoKey,
  onShowInfo,
}: {
  label: string;
  value: string;
  unit: string;
  color: string;
  progress?: number;
  subtext?: string;
  direction?: DirectionIndicator | null;
  baselineLabel?: string;
  infoKey?: string;
  onShowInfo?: (key: string) => void;
}) {
  return (
    <div className="bg-gray-900 rounded-2xl p-4 relative">
      <div className="flex justify-between items-start mb-2">
        <div className="text-gray-500 text-xs">{label}</div>
        {infoKey && onShowInfo && (
          <InfoButton onClick={() => onShowInfo(infoKey)} />
        )}
      </div>
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
