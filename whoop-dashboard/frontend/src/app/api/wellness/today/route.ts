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
        dw.resting_heart_rate
      FROM daily_wellness dw
      LEFT JOIN hrv_data h ON dw.date = h.date
      LEFT JOIN sleep_data s ON dw.date = s.date
      LEFT JOIN stress_data st ON dw.date = st.date
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

    db.close();

    // Calculate derived values
    const totalSleepHours = sleep ? Math.round(((sleep.total_sleep_seconds as number) || 0) / 3600 * 100) / 100 : null;
    const currentHrv = hrv?.hrv_last_night_avg as number | null;
    const currentRhr = wellness.resting_heart_rate as number | null;
    const currentBB = stress?.body_battery_charged as number | null;

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
        direction: calculateDirection(currentHrv, baselines.hrv_7d_avg),
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
    });

  } catch (error) {
    console.error('Database error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch wellness data' },
      { status: 500 }
    );
  }
}
