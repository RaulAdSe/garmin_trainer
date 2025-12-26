import { NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

// Calculate direction indicator
function calculateDirection(
  current: number | null,
  baseline: number | null,
  thresholdPct: number = 5.0,
  inverse: boolean = false
): { direction: string; change_pct: number; baseline: number; current: number } | null {
  if (current === null || baseline === null || baseline === 0) {
    return null;
  }

  const changePct = ((current - baseline) / baseline) * 100;

  let direction: string;
  if (Math.abs(changePct) < thresholdPct) {
    direction = 'stable';
  } else if (changePct > 0) {
    direction = inverse ? 'down' : 'up';
  } else {
    direction = inverse ? 'up' : 'down';
  }

  return {
    direction,
    change_pct: Math.round(changePct * 10) / 10,
    baseline,
    current
  };
}

// Calculate rolling average from historical data
function calculateRollingAverage(values: (number | null)[], days: number = 7): number | null {
  const validValues = values.slice(0, days).filter((v): v is number => v !== null);
  if (validValues.length < 3) return null;
  return Math.round((validValues.reduce((a, b) => a + b, 0) / validValues.length) * 100) / 100;
}

// Phase 4: Causality Engine Types
interface Correlation {
  pattern_type: 'positive' | 'negative';
  category: string;
  title: string;
  description: string;
  impact: number;
  confidence: number;
  sample_size: number;
}

interface Streak {
  name: string;
  current_count: number;
  best_count: number;
  is_active: boolean;
  last_date: string;
}

interface TrendAlert {
  metric: string;
  direction: 'declining' | 'improving';
  days: number;
  change_pct: number;
  severity: 'warning' | 'concern' | 'positive';
}

interface WeeklySummary {
  green_days: number;
  yellow_days: number;
  red_days: number;
  avg_recovery: number;
  avg_strain: number;
  avg_sleep: number;
  total_sleep_debt: number;
  best_day: string;
  worst_day: string;
  correlations: Correlation[];
  streaks: Streak[];
  trend_alerts: TrendAlert[];
}

// Calculate recovery score
function calculateRecoveryScore(
  currentHrv: number | null,
  currentSleepHours: number | null,
  currentBB: number | null,
  baselines: { hrv_7d_avg: number | null; sleep_7d_avg: number | null }
): number {
  const scores: number[] = [];
  const weights: number[] = [];

  if (currentHrv !== null && baselines.hrv_7d_avg !== null) {
    const hrvRatio = currentHrv / baselines.hrv_7d_avg;
    const hrvScore = Math.min(100, Math.max(0, hrvRatio * 80 + 20));
    scores.push(hrvScore * 1.5);
    weights.push(1.5);
  }

  if (currentSleepHours !== null && baselines.sleep_7d_avg !== null) {
    const sleepRatio = currentSleepHours / baselines.sleep_7d_avg;
    const sleepScore = Math.min(100, Math.max(0, sleepRatio * 85 + 15));
    scores.push(sleepScore);
    weights.push(1.0);
  }

  if (currentBB !== null) {
    scores.push(currentBB);
    weights.push(1.0);
  }

  if (scores.length === 0) return 0;
  const totalWeight = weights.reduce((a, b) => a + b, 0);
  const weightedSum = scores.reduce((a, b) => a + b, 0);
  return Math.round(weightedSum / totalWeight);
}

// Calculate strain
function calculateStrain(
  bbDrained: number | null,
  steps: number | null,
  intensityMins: number | null
): number {
  let strain = 0;
  if (steps !== null) strain += Math.min(8, steps / 2000);
  if (bbDrained !== null) strain += Math.min(8, bbDrained / 12);
  if (intensityMins !== null) strain += Math.min(5, intensityMins / 20);
  return Math.round(Math.min(21, strain) * 10) / 10;
}

// Calculate sleep consistency streak
function calculateSleepConsistencyStreak(
  db: InstanceType<typeof Database>,
  thresholdHours: number = 7.0
): Streak {
  const rows = db.prepare(`
    SELECT date, total_sleep_seconds / 3600.0 as sleep_hours
    FROM sleep_data
    WHERE date >= date('now', '-60 days')
    AND total_sleep_seconds IS NOT NULL
    ORDER BY date DESC
  `).all() as { date: string; sleep_hours: number }[];

  if (!rows.length) {
    return { name: 'sleep_consistency', current_count: 0, best_count: 0, is_active: false, last_date: '' };
  }

  let currentStreak = 0;
  let bestStreak = 0;
  let lastDate = '';
  let inStreak = true;

  for (let i = 0; i < rows.length; i++) {
    const meetsTarget = rows[i].sleep_hours >= thresholdHours;

    if (inStreak && meetsTarget) {
      currentStreak++;
      if (currentStreak === 1) lastDate = rows[i].date;
    } else if (inStreak && !meetsTarget) {
      inStreak = false;
    }

    if (meetsTarget) {
      let tempStreak = 1;
      for (let j = i + 1; j < rows.length; j++) {
        if (rows[j].sleep_hours >= thresholdHours) tempStreak++;
        else break;
      }
      bestStreak = Math.max(bestStreak, tempStreak);
    }
  }

  return {
    name: 'sleep_consistency',
    current_count: currentStreak,
    best_count: bestStreak,
    is_active: currentStreak > 0,
    last_date: lastDate,
  };
}

// Calculate step goal streak
function calculateStepGoalStreak(db: InstanceType<typeof Database>): Streak {
  const rows = db.prepare(`
    SELECT date, steps, steps_goal
    FROM activity_data
    WHERE date >= date('now', '-60 days')
    AND steps IS NOT NULL
    ORDER BY date DESC
  `).all() as { date: string; steps: number; steps_goal: number | null }[];

  if (!rows.length) {
    return { name: 'step_goal', current_count: 0, best_count: 0, is_active: false, last_date: '' };
  }

  let currentStreak = 0;
  let bestStreak = 0;
  let lastDate = '';
  let inStreak = true;

  for (let i = 0; i < rows.length; i++) {
    const goal = rows[i].steps_goal || 10000;
    const hitGoal = rows[i].steps >= goal;

    if (inStreak && hitGoal) {
      currentStreak++;
      if (currentStreak === 1) lastDate = rows[i].date;
    } else if (inStreak && !hitGoal) {
      inStreak = false;
    }

    if (hitGoal) {
      let tempStreak = 1;
      for (let j = i + 1; j < rows.length; j++) {
        const nextGoal = rows[j].steps_goal || 10000;
        if (rows[j].steps >= nextGoal) tempStreak++;
        else break;
      }
      bestStreak = Math.max(bestStreak, tempStreak);
    }
  }

  return {
    name: 'step_goal',
    current_count: currentStreak,
    best_count: bestStreak,
    is_active: currentStreak > 0,
    last_date: lastDate,
  };
}

// Generate weekly summary
function generateWeeklySummary(
  db: InstanceType<typeof Database>,
  baselines: { hrv_7d_avg: number | null; sleep_7d_avg: number | null }
): WeeklySummary {
  const rows = db.prepare(`
    SELECT
      h.date,
      h.hrv_last_night_avg as hrv,
      st.body_battery_charged as bb,
      st.body_battery_drained as bb_drained,
      s.total_sleep_seconds / 3600.0 as sleep_hours,
      a.steps,
      a.intensity_minutes
    FROM hrv_data h
    LEFT JOIN stress_data st ON h.date = st.date
    LEFT JOIN sleep_data s ON h.date = s.date
    LEFT JOIN activity_data a ON h.date = a.date
    WHERE h.date >= date('now', '-7 days')
    ORDER BY h.date DESC
  `).all() as {
    date: string;
    hrv: number | null;
    bb: number | null;
    bb_drained: number | null;
    sleep_hours: number | null;
    steps: number | null;
    intensity_minutes: number | null;
  }[];

  let greenDays = 0;
  let yellowDays = 0;
  let redDays = 0;
  const recoveries: number[] = [];
  const strains: number[] = [];
  const sleeps: number[] = [];
  let sleepDebt = 0;
  let bestDay = { date: '', recovery: 0 };
  let worstDay = { date: '', recovery: 100 };
  const sleepBaseline = baselines.sleep_7d_avg || 7.5;

  for (const row of rows) {
    const recovery = calculateRecoveryScore(row.hrv, row.sleep_hours, row.bb, baselines);
    recoveries.push(recovery);

    const strain = calculateStrain(row.bb_drained, row.steps, row.intensity_minutes);
    strains.push(strain);

    if (row.sleep_hours !== null) {
      sleeps.push(row.sleep_hours);
      if (row.sleep_hours < sleepBaseline) {
        sleepDebt += sleepBaseline - row.sleep_hours;
      }
    }

    if (recovery >= 67) greenDays++;
    else if (recovery >= 34) yellowDays++;
    else redDays++;

    if (recovery > bestDay.recovery) bestDay = { date: row.date, recovery };
    if (recovery < worstDay.recovery) worstDay = { date: row.date, recovery };
  }

  const avgRecovery = recoveries.length > 0
    ? Math.round(recoveries.reduce((a, b) => a + b, 0) / recoveries.length * 10) / 10
    : 0;
  const avgStrain = strains.length > 0
    ? Math.round(strains.reduce((a, b) => a + b, 0) / strains.length * 10) / 10
    : 0;
  const avgSleep = sleeps.length > 0
    ? Math.round(sleeps.reduce((a, b) => a + b, 0) / sleeps.length * 100) / 100
    : 0;

  // Get streaks
  const streaksArr: Streak[] = [];
  try {
    const sleepStreak = calculateSleepConsistencyStreak(db);
    if (sleepStreak.current_count > 0) streaksArr.push(sleepStreak);
  } catch { /* ignore */ }
  try {
    const stepStreak = calculateStepGoalStreak(db);
    if (stepStreak.current_count > 0) streaksArr.push(stepStreak);
  } catch { /* ignore */ }

  return {
    green_days: greenDays,
    yellow_days: yellowDays,
    red_days: redDays,
    avg_recovery: avgRecovery,
    avg_strain: avgStrain,
    avg_sleep: avgSleep,
    total_sleep_debt: Math.round(sleepDebt * 100) / 100,
    best_day: bestDay.date,
    worst_day: worstDay.date,
    correlations: [],  // Correlations are computed in the today route
    streaks: streaksArr,
    trend_alerts: [],  // Trend alerts are computed in the today route
  };
}

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const days = parseInt(searchParams.get('days') || '14');

    const dbPath = path.join(process.cwd(), '..', 'wellness.db');
    const db = new Database(dbPath, { readonly: true });

    // Get wellness data for the last N days plus extra for baseline calculation
    const rows = db.prepare(`
      SELECT
        dw.date,
        dw.resting_heart_rate,
        s.total_sleep_seconds,
        s.deep_sleep_seconds,
        s.rem_sleep_seconds,
        s.sleep_score,
        s.sleep_efficiency,
        h.hrv_last_night_avg,
        h.hrv_weekly_avg,
        h.hrv_status,
        st.avg_stress_level,
        st.body_battery_charged,
        st.body_battery_drained,
        a.steps,
        a.steps_goal,
        a.active_calories,
        a.intensity_minutes
      FROM daily_wellness dw
      LEFT JOIN sleep_data s ON dw.date = s.date
      LEFT JOIN hrv_data h ON dw.date = h.date
      LEFT JOIN stress_data st ON dw.date = st.date
      LEFT JOIN activity_data a ON dw.date = a.date
      ORDER BY dw.date DESC
      LIMIT ?
    `).all(days + 30) as Record<string, unknown>[]; // Extra 30 days for baseline calc

    // Calculate baselines for first day (for weekly summary)
    const firstDayHistory = rows.slice(1, 31);
    const firstDayHrvHistory = firstDayHistory.map(r => r.hrv_last_night_avg as number | null);
    const firstDaySleepHistory = firstDayHistory.map(r => {
      const secs = r.total_sleep_seconds as number | null;
      return secs !== null && secs > 0 ? secs / 3600 : null;
    });
    const firstDayBaselines = {
      hrv_7d_avg: calculateRollingAverage(firstDayHrvHistory, 7),
      sleep_7d_avg: calculateRollingAverage(firstDaySleepHistory, 7),
    };

    // Generate weekly summary before closing db
    const weeklySummary = generateWeeklySummary(db, firstDayBaselines);

    db.close();

    // Transform data with baselines calculated for each day
    const history = rows.slice(0, days).map((row, index) => {
      const totalSleep = (row.total_sleep_seconds as number) || 0;
      const deepSleep = (row.deep_sleep_seconds as number) || 0;
      const remSleep = (row.rem_sleep_seconds as number) || 0;
      const sleepHours = totalSleep > 0 ? Math.round(totalSleep / 3600 * 100) / 100 : null;
      const currentHrv = row.hrv_last_night_avg as number | null;
      const currentRhr = row.resting_heart_rate as number | null;
      const currentBB = row.body_battery_charged as number | null;

      // Get historical data for this day (days after this one in the list)
      const historyForDay = rows.slice(index + 1, index + 31);

      // Calculate baselines for this specific day
      const hrvHistory = historyForDay.map(r => r.hrv_last_night_avg as number | null);
      const sleepHistory = historyForDay.map(r => {
        const secs = r.total_sleep_seconds as number | null;
        return secs !== null && secs > 0 ? secs / 3600 : null;
      });
      const rhrHistory = historyForDay.map(r => r.resting_heart_rate as number | null);
      const bbHistory = historyForDay.map(r => r.body_battery_charged as number | null);

      const baselines = {
        hrv_7d_avg: calculateRollingAverage(hrvHistory, 7),
        hrv_30d_avg: calculateRollingAverage(hrvHistory, 30),
        sleep_7d_avg: calculateRollingAverage(sleepHistory, 7),
        sleep_30d_avg: calculateRollingAverage(sleepHistory, 30),
        rhr_7d_avg: calculateRollingAverage(rhrHistory, 7),
        rhr_30d_avg: calculateRollingAverage(rhrHistory, 30),
        recovery_7d_avg: calculateRollingAverage(bbHistory, 7),
      };

      return {
        date: row.date,
        sleep: totalSleep > 0 ? {
          total_hours: sleepHours,
          deep_pct: Math.round(deepSleep / totalSleep * 1000) / 10,
          rem_pct: Math.round(remSleep / totalSleep * 1000) / 10,
          score: row.sleep_score,
          efficiency: row.sleep_efficiency,
          direction: calculateDirection(sleepHours, baselines.sleep_7d_avg),
        } : null,
        hrv: {
          value: currentHrv,
          baseline: baselines.hrv_7d_avg || row.hrv_weekly_avg,
          status: row.hrv_status,
          direction: calculateDirection(currentHrv, baselines.hrv_7d_avg),
        },
        strain: {
          body_battery_charged: currentBB,
          body_battery_drained: row.body_battery_drained,
          stress_avg: row.avg_stress_level,
          active_calories: row.active_calories,
          intensity_minutes: row.intensity_minutes,
          direction: calculateDirection(currentBB, baselines.recovery_7d_avg),
        },
        activity: {
          steps: row.steps || 0,
          steps_goal: row.steps_goal || 10000,
        },
        resting_hr: currentRhr,
        rhr_direction: calculateDirection(currentRhr, baselines.rhr_7d_avg, 5.0, true),
        baselines,
        // Include weekly_summary for the first (most recent) day only
        weekly_summary: index === 0 ? weeklySummary : undefined,
      };
    });

    return NextResponse.json(history);

  } catch (error) {
    console.error('Database error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch history' },
      { status: 500 }
    );
  }
}
