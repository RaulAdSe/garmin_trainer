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

// Calculate recovery score using personal baselines
function calculateRecovery(
  currentHrv: number | null,
  currentSleepHours: number | null,
  currentBB: number | null,
  baselines: { hrv_7d_avg: number | null; sleep_7d_avg: number | null; recovery_7d_avg: number | null }
): number {
  const scores: number[] = [];
  const weights: number[] = [];

  // HRV Factor (primary signal - weighted 1.5x)
  if (currentHrv !== null && baselines.hrv_7d_avg !== null) {
    const hrvRatio = currentHrv / baselines.hrv_7d_avg;
    const hrvScore = Math.min(100, Math.max(0, hrvRatio * 80 + 20));
    scores.push(hrvScore * 1.5);
    weights.push(1.5);
  }

  // Sleep Factor
  if (currentSleepHours !== null && baselines.sleep_7d_avg !== null) {
    const sleepRatio = currentSleepHours / baselines.sleep_7d_avg;
    const sleepScore = Math.min(100, Math.max(0, sleepRatio * 85 + 15));
    scores.push(sleepScore);
    weights.push(1.0);
  }

  // Body Battery Factor
  if (currentBB !== null) {
    scores.push(currentBB);
    weights.push(1.0);
  }

  if (scores.length === 0) return 0;

  const totalWeight = weights.reduce((a, b) => a + b, 0);
  const weightedSum = scores.reduce((a, b) => a + b, 0);
  return Math.round(weightedSum / totalWeight);
}

// Get strain target based on recovery
function getStrainTarget(recovery: number): [number, number] {
  if (recovery >= 67) return [14, 21];
  if (recovery >= 34) return [8, 14];
  return [0, 8];
}

// Get insight/decision based on recovery
function getInsight(
  recovery: number,
  hrvDirection: string | null,
  sleepHours: number | null,
  sleepBaseline: number | null,
  strainYesterday: number
): {
  decision: string;
  headline: string;
  explanation: string;
  strain_target: [number, number];
  sleep_target: number;
} {
  const strainTarget = getStrainTarget(recovery);

  // Calculate sleep need
  const baseSleep = sleepBaseline || 7.5;
  const sleepDebt = Math.max(0, baseSleep - (sleepHours || baseSleep));
  const strainAdjustment = Math.max(0, (strainYesterday - 10) * 0.05);
  const debtRepayment = sleepDebt / 7;
  const sleepTarget = Math.round((baseSleep + strainAdjustment + debtRepayment) * 100) / 100;

  let decision: string;
  let headline: string;
  let explanation: string;

  if (recovery >= 67) {
    decision = "GO";
    headline = "Push hard today";
    explanation = `Recovery at ${recovery}% puts you in the green zone. ${
      hrvDirection === 'up' ? 'HRV trending up shows strong recovery.' : 'HRV at baseline.'
    } Target strain ${strainTarget[0]}-${strainTarget[1]}. Great day for intervals or competition.`;
  } else if (recovery >= 34) {
    decision = "MODERATE";
    headline = "Moderate effort today";
    explanation = `Recovery at ${recovery}% - yellow zone. ${
      hrvDirection === 'down' ? 'HRV below baseline suggests adaptation still in progress.' : 'Body in balanced state.'
    } Good for steady cardio or technique work.`;
  } else {
    decision = "RECOVER";
    headline = "Recovery focus";
    const sleepNote = sleepHours && sleepHours < 6 ? ` Only ${sleepHours.toFixed(1)}h sleep is limiting recovery.` : '';
    explanation = `Recovery at ${recovery}% - red zone.${sleepNote} Focus on rest, hydration, and quality sleep.`;
  }

  return {
    decision,
    headline,
    explanation,
    strain_target: strainTarget,
    sleep_target: sleepTarget,
  };
}

// Calculate sleep debt over last N days
function calculateSleepDebt(
  sleepHistory: (number | null)[],
  sleepBaseline: number | null,
  days: number = 7
): number {
  const baseline = sleepBaseline || 7.5;
  let debt = 0;
  for (let i = 0; i < Math.min(days, sleepHistory.length); i++) {
    const actual = sleepHistory[i];
    if (actual !== null) {
      debt += Math.max(0, baseline - actual);
    }
  }
  return Math.round(debt * 100) / 100;
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

// Calculate strain from activity data
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

// Detect sleep consistency impact on HRV
function detectSleepConsistencyImpact(
  db: InstanceType<typeof Database>,
  days: number = 30
): Correlation | null {
  const rows = db.prepare(`
    SELECT
      s.date,
      s.total_sleep_seconds / 3600.0 as sleep_hours,
      h.hrv_last_night_avg as hrv
    FROM sleep_data s
    LEFT JOIN hrv_data h ON s.date = h.date
    WHERE s.date >= date('now', ?)
    AND h.hrv_last_night_avg IS NOT NULL
    ORDER BY s.date DESC
  `).all(`-${days} days`) as { date: string; sleep_hours: number | null; hrv: number | null }[];

  if (rows.length < 10) return null;

  const consistentHrvs: number[] = [];
  const inconsistentHrvs: number[] = [];

  for (let i = 0; i < rows.length - 4; i++) {
    const window = rows.slice(i, i + 5);
    const windowSleep = window.map(r => r.sleep_hours).filter((s): s is number => s !== null);
    if (windowSleep.length < 5) continue;

    const hrv = rows[i].hrv;
    if (hrv === null) continue;

    if (windowSleep.every(s => s >= 7.0)) {
      consistentHrvs.push(hrv);
    } else if (windowSleep.some(s => s < 6.0)) {
      inconsistentHrvs.push(hrv);
    }
  }

  if (consistentHrvs.length < 3 || inconsistentHrvs.length < 3) return null;

  const avgConsistent = consistentHrvs.reduce((a, b) => a + b, 0) / consistentHrvs.length;
  const avgInconsistent = inconsistentHrvs.reduce((a, b) => a + b, 0) / inconsistentHrvs.length;

  if (avgInconsistent === 0) return null;

  const impact = ((avgConsistent - avgInconsistent) / avgInconsistent) * 100;
  if (Math.abs(impact) < 5) return null;

  const sampleSize = consistentHrvs.length + inconsistentHrvs.length;
  const confidence = Math.min(1.0, sampleSize / 10);

  return {
    pattern_type: impact > 0 ? 'positive' : 'negative',
    category: 'sleep',
    title: 'Sleep consistency impact',
    description: `5+ days of 7h+ sleep: HRV baseline ${impact > 0 ? 'up' : 'down'} ${Math.abs(impact).toFixed(0)}%`,
    impact: Math.round(impact * 10) / 10,
    confidence: Math.round(confidence * 100) / 100,
    sample_size: sampleSize,
  };
}

// Detect step count correlation with recovery
function detectStepCountCorrelation(
  db: InstanceType<typeof Database>,
  days: number = 30
): Correlation | null {
  const rows = db.prepare(`
    SELECT
      a.date,
      a.steps,
      h2.hrv_last_night_avg as next_hrv,
      st2.body_battery_charged as next_bb
    FROM activity_data a
    JOIN hrv_data h2 ON date(a.date, '+1 day') = h2.date
    LEFT JOIN stress_data st2 ON date(a.date, '+1 day') = st2.date
    WHERE a.date >= date('now', ?)
    AND a.steps IS NOT NULL
    ORDER BY a.date DESC
  `).all(`-${days} days`) as { date: string; steps: number; next_hrv: number | null; next_bb: number | null }[];

  if (rows.length < 5) return null;

  const highStepRecoveries: number[] = [];
  const lowStepRecoveries: number[] = [];
  const stepThreshold = 8000;

  for (const row of rows) {
    // Simple recovery proxy using body battery
    const recovery = row.next_bb || 0;
    if (recovery === 0) continue;

    if (row.steps >= stepThreshold) {
      highStepRecoveries.push(recovery);
    } else if (row.steps < 5000) {
      lowStepRecoveries.push(recovery);
    }
  }

  if (highStepRecoveries.length < 3 || lowStepRecoveries.length < 3) return null;

  const avgHigh = highStepRecoveries.reduce((a, b) => a + b, 0) / highStepRecoveries.length;
  const avgLow = lowStepRecoveries.reduce((a, b) => a + b, 0) / lowStepRecoveries.length;

  if (avgLow === 0) return null;

  const impact = ((avgHigh - avgLow) / avgLow) * 100;
  if (Math.abs(impact) < 5) return null;

  const sampleSize = highStepRecoveries.length + lowStepRecoveries.length;
  const confidence = Math.min(1.0, sampleSize / 10);

  return {
    pattern_type: impact > 0 ? 'positive' : 'negative',
    category: 'activity',
    title: `${stepThreshold / 1000}k+ step days`,
    description: `High step days (${stepThreshold / 1000}k+) correlate with ${impact > 0 ? '+' : ''}${impact.toFixed(0)}% recovery`,
    impact: Math.round(impact * 10) / 10,
    confidence: Math.round(confidence * 100) / 100,
    sample_size: sampleSize,
  };
}

// Calculate green day streak
function calculateGreenDayStreak(
  db: InstanceType<typeof Database>,
  baselines: { hrv_7d_avg: number | null; sleep_7d_avg: number | null }
): Streak {
  const rows = db.prepare(`
    SELECT
      h.date,
      h.hrv_last_night_avg as hrv,
      st.body_battery_charged as bb,
      s.total_sleep_seconds / 3600.0 as sleep_hours
    FROM hrv_data h
    LEFT JOIN stress_data st ON h.date = st.date
    LEFT JOIN sleep_data s ON h.date = s.date
    WHERE h.date >= date('now', '-60 days')
    ORDER BY h.date DESC
  `).all() as { date: string; hrv: number | null; bb: number | null; sleep_hours: number | null }[];

  if (!rows.length) {
    return { name: 'green_days', current_count: 0, best_count: 0, is_active: false, last_date: '' };
  }

  let currentStreak = 0;
  let bestStreak = 0;
  let lastDate = '';
  let inStreak = true;

  for (const row of rows) {
    const recovery = calculateRecovery(
      row.hrv,
      row.sleep_hours,
      row.bb,
      { hrv_7d_avg: baselines.hrv_7d_avg, sleep_7d_avg: baselines.sleep_7d_avg, recovery_7d_avg: null }
    );

    const isGreen = recovery >= 67;

    if (inStreak && isGreen) {
      currentStreak++;
      if (currentStreak === 1) lastDate = row.date;
    } else if (inStreak && !isGreen) {
      inStreak = false;
    }

    if (isGreen) {
      let tempStreak = 1;
      const idx = rows.indexOf(row);
      for (let i = idx + 1; i < rows.length; i++) {
        const nextRecovery = calculateRecovery(
          rows[i].hrv,
          rows[i].sleep_hours,
          rows[i].bb,
          { hrv_7d_avg: baselines.hrv_7d_avg, sleep_7d_avg: baselines.sleep_7d_avg, recovery_7d_avg: null }
        );
        if (nextRecovery >= 67) tempStreak++;
        else break;
      }
      bestStreak = Math.max(bestStreak, tempStreak);
    }
  }

  return {
    name: 'green_days',
    current_count: currentStreak,
    best_count: bestStreak,
    is_active: currentStreak > 0,
    last_date: lastDate,
  };
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

// Detect HRV trend
function detectHrvTrend(db: InstanceType<typeof Database>, days: number = 7): TrendAlert | null {
  const rows = db.prepare(`
    SELECT date, hrv_last_night_avg as hrv
    FROM hrv_data
    WHERE date >= date('now', ?)
    AND hrv_last_night_avg IS NOT NULL
    ORDER BY date DESC
  `).all(`-${days} days`) as { date: string; hrv: number }[];

  if (rows.length < 3) return null;

  let decliningDays = 0;
  let improvingDays = 0;

  for (let i = 0; i < rows.length - 1; i++) {
    if (rows[i].hrv < rows[i + 1].hrv) decliningDays++;
    else if (rows[i].hrv > rows[i + 1].hrv) improvingDays++;
  }

  const firstHrv = rows[0].hrv;
  const lastHrv = rows[rows.length - 1].hrv;

  if (lastHrv === 0) return null;

  const changePct = ((firstHrv - lastHrv) / lastHrv) * 100;

  if (decliningDays >= 3 && changePct < -10) {
    return {
      metric: 'HRV',
      direction: 'declining',
      days: decliningDays,
      change_pct: Math.round(changePct * 10) / 10,
      severity: changePct < -15 ? 'concern' : 'warning',
    };
  } else if (improvingDays >= 3 && changePct > 10) {
    return {
      metric: 'HRV',
      direction: 'improving',
      days: improvingDays,
      change_pct: Math.round(changePct * 10) / 10,
      severity: 'positive',
    };
  }

  return null;
}

// Detect recovery trend
function detectRecoveryTrend(
  db: InstanceType<typeof Database>,
  baselines: { hrv_7d_avg: number | null; sleep_7d_avg: number | null },
  days: number = 7
): TrendAlert | null {
  const rows = db.prepare(`
    SELECT
      h.date,
      h.hrv_last_night_avg as hrv,
      st.body_battery_charged as bb,
      s.total_sleep_seconds / 3600.0 as sleep_hours
    FROM hrv_data h
    LEFT JOIN stress_data st ON h.date = st.date
    LEFT JOIN sleep_data s ON h.date = s.date
    WHERE h.date >= date('now', ?)
    ORDER BY h.date DESC
  `).all(`-${days} days`) as { date: string; hrv: number | null; bb: number | null; sleep_hours: number | null }[];

  if (rows.length < 3) return null;

  const recoveries: number[] = [];
  for (const row of rows) {
    const recovery = calculateRecovery(
      row.hrv,
      row.sleep_hours,
      row.bb,
      { hrv_7d_avg: baselines.hrv_7d_avg, sleep_7d_avg: baselines.sleep_7d_avg, recovery_7d_avg: null }
    );
    if (recovery > 0) recoveries.push(recovery);
  }

  if (recoveries.length < 3) return null;

  let decliningDays = 0;
  let improvingDays = 0;

  for (let i = 0; i < recoveries.length - 1; i++) {
    if (recoveries[i] < recoveries[i + 1] - 5) decliningDays++;
    else if (recoveries[i] > recoveries[i + 1] + 5) improvingDays++;
  }

  const firstRecovery = recoveries[0];
  const lastRecovery = recoveries[recoveries.length - 1];

  if (lastRecovery === 0) return null;

  const changePct = ((firstRecovery - lastRecovery) / lastRecovery) * 100;

  if (decliningDays >= 3 && changePct < -10) {
    return {
      metric: 'Recovery',
      direction: 'declining',
      days: decliningDays,
      change_pct: Math.round(changePct * 10) / 10,
      severity: changePct < -20 ? 'concern' : 'warning',
    };
  } else if (improvingDays >= 3 && changePct > 10) {
    return {
      metric: 'Recovery',
      direction: 'improving',
      days: improvingDays,
      change_pct: Math.round(changePct * 10) / 10,
      severity: 'positive',
    };
  }

  return null;
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
    const recovery = calculateRecovery(
      row.hrv,
      row.sleep_hours,
      row.bb,
      { hrv_7d_avg: baselines.hrv_7d_avg, sleep_7d_avg: baselines.sleep_7d_avg, recovery_7d_avg: null }
    );
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

  // Get correlations
  const correlations: Correlation[] = [];
  try {
    const sleepCorr = detectSleepConsistencyImpact(db);
    if (sleepCorr) correlations.push(sleepCorr);
  } catch { /* ignore */ }
  try {
    const stepCorr = detectStepCountCorrelation(db);
    if (stepCorr) correlations.push(stepCorr);
  } catch { /* ignore */ }
  correlations.sort((a, b) => b.confidence - a.confidence);

  // Get streaks
  const streaks: Streak[] = [];
  try {
    const greenStreak = calculateGreenDayStreak(db, baselines);
    if (greenStreak.current_count > 0) streaks.push(greenStreak);
  } catch { /* ignore */ }
  try {
    const sleepStreak = calculateSleepConsistencyStreak(db);
    if (sleepStreak.current_count > 0) streaks.push(sleepStreak);
  } catch { /* ignore */ }
  try {
    const stepStreak = calculateStepGoalStreak(db);
    if (stepStreak.current_count > 0) streaks.push(stepStreak);
  } catch { /* ignore */ }

  // Get trend alerts
  const trendAlerts: TrendAlert[] = [];
  try {
    const hrvTrend = detectHrvTrend(db);
    if (hrvTrend) trendAlerts.push(hrvTrend);
  } catch { /* ignore */ }
  try {
    const recoveryTrend = detectRecoveryTrend(db, baselines);
    if (recoveryTrend) trendAlerts.push(recoveryTrend);
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
    correlations,
    streaks,
    trend_alerts: trendAlerts,
  };
}

export async function GET() {
  try {
    // Connect to SQLite database in project root
    const dbPath = path.join(process.cwd(), '..', 'wellness.db');
    const db = new Database(dbPath, { readonly: true });

    // Get today's date or most recent
    const today = new Date().toISOString().split('T')[0];

    // Try today first, then get most recent
    let dateToFetch = today;
    const latestRow = db.prepare(
      'SELECT MAX(date) as max_date FROM daily_wellness'
    ).get() as { max_date: string } | undefined;

    if (latestRow?.max_date) {
      dateToFetch = latestRow.max_date;
    }

    // Get wellness data
    const wellness = db.prepare(
      'SELECT * FROM daily_wellness WHERE date = ?'
    ).get(dateToFetch) as Record<string, unknown> | undefined;

    if (!wellness) {
      db.close();
      return NextResponse.json(null);
    }

    // Get related data
    const sleep = db.prepare(
      'SELECT * FROM sleep_data WHERE date = ?'
    ).get(dateToFetch) as Record<string, unknown> | undefined;

    const hrv = db.prepare(
      'SELECT * FROM hrv_data WHERE date = ?'
    ).get(dateToFetch) as Record<string, unknown> | undefined;

    const stress = db.prepare(
      'SELECT * FROM stress_data WHERE date = ?'
    ).get(dateToFetch) as Record<string, unknown> | undefined;

    const activity = db.prepare(
      'SELECT * FROM activity_data WHERE date = ?'
    ).get(dateToFetch) as Record<string, unknown> | undefined;

    // Get historical data for baseline calculations (last 30 days before today)
    const historyRows = db.prepare(`
      SELECT
        h.date,
        h.hrv_last_night_avg,
        s.total_sleep_seconds,
        st.body_battery_charged,
        st.body_battery_drained,
        dw.resting_heart_rate,
        a.steps,
        a.intensity_minutes
      FROM daily_wellness dw
      LEFT JOIN hrv_data h ON dw.date = h.date
      LEFT JOIN sleep_data s ON dw.date = s.date
      LEFT JOIN stress_data st ON dw.date = st.date
      LEFT JOIN activity_data a ON dw.date = a.date
      WHERE dw.date < ?
      ORDER BY dw.date DESC
      LIMIT 30
    `).all(dateToFetch) as Record<string, unknown>[];

    // Calculate personal baselines
    const hrvHistory = historyRows.map(r => r.hrv_last_night_avg as number | null);
    const sleepHistory = historyRows.map(r => {
      const secs = r.total_sleep_seconds as number | null;
      return secs !== null ? secs / 3600 : null;
    });
    const rhrHistory = historyRows.map(r => r.resting_heart_rate as number | null);
    const bbHistory = historyRows.map(r => r.body_battery_charged as number | null);

    const baselines = {
      hrv_7d_avg: calculateRollingAverage(hrvHistory, 7),
      hrv_30d_avg: calculateRollingAverage(hrvHistory, 30),
      sleep_7d_avg: calculateRollingAverage(sleepHistory, 7),
      sleep_30d_avg: calculateRollingAverage(sleepHistory, 30),
      rhr_7d_avg: calculateRollingAverage(rhrHistory, 7),
      rhr_30d_avg: calculateRollingAverage(rhrHistory, 30),
      recovery_7d_avg: calculateRollingAverage(bbHistory, 7),
    };

    // Calculate derived values
    const totalSleepHours = sleep ? Math.round(((sleep.total_sleep_seconds as number) || 0) / 3600 * 100) / 100 : null;
    const currentHrv = hrv?.hrv_last_night_avg as number | null;
    const currentRhr = wellness.resting_heart_rate as number | null;
    const currentBB = stress?.body_battery_charged as number | null;

    // Calculate recovery score
    const recovery = calculateRecovery(currentHrv, totalSleepHours, currentBB, baselines);

    // Calculate strain from yesterday for sleep target
    // We need to look at yesterday's data
    let strainYesterday = 10; // default
    if (historyRows.length > 0) {
      const yesterday = historyRows[0];
      const bbDrained = yesterday.body_battery_drained as number || 0;
      const steps = yesterday.steps as number || 0;
      const intensity = yesterday.intensity_minutes as number || 0;
      strainYesterday = Math.min(21,
        Math.min(8, bbDrained / 12) +
        Math.min(8, steps / 2000) +
        Math.min(5, intensity / 20)
      );
    }

    // Get HRV direction for insight generation
    const hrvDirection = calculateDirection(currentHrv, baselines.hrv_7d_avg);

    // Calculate sleep debt
    const sleepDebt = calculateSleepDebt(sleepHistory, baselines.sleep_7d_avg, 7);

    // Generate insights
    const insight = getInsight(
      recovery,
      hrvDirection?.direction || null,
      totalSleepHours,
      baselines.sleep_7d_avg,
      strainYesterday
    );

    // Phase 4: Generate weekly summary with causality data
    const weeklySummary = generateWeeklySummary(db, baselines);

    db.close();

    const sleepData = sleep ? {
      total_sleep_hours: totalSleepHours,
      deep_sleep_pct: (sleep.total_sleep_seconds as number) > 0
        ? Math.round(((sleep.deep_sleep_seconds as number) || 0) / (sleep.total_sleep_seconds as number) * 1000) / 10
        : 0,
      rem_sleep_pct: (sleep.total_sleep_seconds as number) > 0
        ? Math.round(((sleep.rem_sleep_seconds as number) || 0) / (sleep.total_sleep_seconds as number) * 1000) / 10
        : 0,
      sleep_score: sleep.sleep_score,
      sleep_efficiency: sleep.sleep_efficiency,
      direction: calculateDirection(totalSleepHours, baselines.sleep_7d_avg),
    } : null;

    const activityData = activity ? {
      steps: activity.steps || 0,
      steps_goal: activity.steps_goal || 10000,
      steps_pct: (activity.steps_goal as number) > 0
        ? Math.round(((activity.steps as number) || 0) / (activity.steps_goal as number) * 1000) / 10
        : 0,
    } : null;

    return NextResponse.json({
      date: dateToFetch,
      sleep: sleepData,
      hrv: hrv ? {
        hrv_last_night_avg: currentHrv,
        hrv_weekly_avg: hrv.hrv_weekly_avg,
        hrv_status: hrv.hrv_status,
        direction: hrvDirection,
      } : null,
      stress: stress ? {
        avg_stress_level: stress.avg_stress_level,
        body_battery_charged: currentBB,
        body_battery_drained: stress.body_battery_drained,
        direction: calculateDirection(currentBB, baselines.recovery_7d_avg),
      } : null,
      activity: activityData,
      resting_heart_rate: currentRhr,
      rhr_direction: calculateDirection(currentRhr, baselines.rhr_7d_avg, 5.0, true), // inverse: lower is better
      baselines,
      // Phase 3: Actionable Insights
      recovery,
      insight: {
        decision: insight.decision,
        headline: insight.headline,
        explanation: insight.explanation,
        strain_target: insight.strain_target,
        sleep_target: insight.sleep_target,
      },
      sleep_debt: sleepDebt,
      // Phase 4: Causality Engine
      weekly_summary: weeklySummary,
    });

  } catch (error) {
    console.error('Database error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch wellness data' },
      { status: 500 }
    );
  }
}
