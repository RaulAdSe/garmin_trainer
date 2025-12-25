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
