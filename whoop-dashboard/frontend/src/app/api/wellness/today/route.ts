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
    });

  } catch (error) {
    console.error('Database error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch wellness data' },
      { status: 500 }
    );
  }
}
