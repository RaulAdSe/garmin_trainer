/**
 * Wellness calculations service.
 * All the WHOOP-style scoring and insights logic.
 */

import { db, WellnessRecord } from './database';

// Types
export interface Direction {
  direction: 'up' | 'down' | 'stable';
  change_pct: number;
  baseline: number;
  current: number;
}

export interface Baselines {
  hrv_7d_avg: number | null;
  hrv_30d_avg: number | null;
  hrv_90d_avg: number | null;
  sleep_7d_avg: number | null;
  sleep_30d_avg: number | null;
  sleep_90d_avg: number | null;
  rhr_7d_avg: number | null;
  rhr_30d_avg: number | null;
  rhr_90d_avg: number | null;
  recovery_7d_avg: number | null;
  recovery_90d_avg: number | null;
}

export interface Insight {
  decision: 'GO' | 'MODERATE' | 'RECOVER';
  headline: string;
  explanation: string;
  strain_target: [number, number];
  sleep_target: number;
}

export interface Correlation {
  pattern_type: 'positive' | 'negative';
  category: string;
  title: string;
  description: string;
  impact: number;
  confidence: number;
  sample_size: number;
}

export interface Streak {
  name: string;
  current_count: number;
  best_count: number;
  is_active: boolean;
  last_date: string;
}

export interface TrendAlert {
  metric: string;
  direction: 'declining' | 'improving';
  days: number;
  change_pct: number;
  severity: 'warning' | 'concern' | 'positive';
}

export interface WeeklySummary {
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

export interface TodayData {
  date: string;
  sleep: {
    total_sleep_hours: number | null;
    deep_sleep_pct: number;
    rem_sleep_pct: number;
    sleep_score: number | null;
    sleep_efficiency: number | null;
    direction: Direction | null;
  } | null;
  hrv: {
    hrv_last_night_avg: number | null;
    hrv_weekly_avg: number | null;
    hrv_status: string | null;
    direction: Direction | null;
  } | null;
  stress: {
    avg_stress_level: number | null;
    body_battery_charged: number | null;
    body_battery_drained: number | null;
    direction: Direction | null;
  } | null;
  activity: {
    steps: number;
    steps_goal: number;
    steps_pct: number;
  } | null;
  resting_hr: number | null;
  rhr_direction: Direction | null;
  baselines: Baselines;
  recovery: number;
  insight: Insight;
  sleep_debt: number;
  weekly_summary: WeeklySummary;
}

// Utility functions

function calculateDirection(
  current: number | null,
  baseline: number | null,
  thresholdPct: number = 5.0,
  inverse: boolean = false
): Direction | null {
  if (current === null || baseline === null || baseline === 0) {
    return null;
  }

  const changePct = ((current - baseline) / baseline) * 100;

  let direction: 'up' | 'down' | 'stable';
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

function calculateRollingAverage(values: (number | null)[], days: number = 7): number | null {
  const validValues = values.slice(0, days).filter((v): v is number => v !== null);
  if (validValues.length < 3) return null;
  return Math.round((validValues.reduce((a, b) => a + b, 0) / validValues.length) * 100) / 100;
}

function calculateRecovery(
  currentHrv: number | null,
  currentSleepHours: number | null,
  currentBB: number | null,
  baselines: { hrv_7d_avg: number | null; sleep_7d_avg: number | null }
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

function getStrainTarget(recovery: number): [number, number] {
  if (recovery >= 67) return [14, 21];
  if (recovery >= 34) return [8, 14];
  return [0, 8];
}

function getInsight(
  recovery: number,
  hrvDirection: string | null,
  sleepHours: number | null,
  sleepBaseline: number | null,
  strainYesterday: number
): Insight {
  const strainTarget = getStrainTarget(recovery);

  // Calculate sleep need
  const baseSleep = sleepBaseline || 7.5;
  const sleepDebt = Math.max(0, baseSleep - (sleepHours || baseSleep));
  const strainAdjustment = Math.max(0, (strainYesterday - 10) * 0.05);
  const debtRepayment = sleepDebt / 7;
  const sleepTarget = Math.round((baseSleep + strainAdjustment + debtRepayment) * 100) / 100;

  let decision: 'GO' | 'MODERATE' | 'RECOVER';
  let headline: string;
  let explanation: string;

  if (recovery >= 67) {
    decision = 'GO';
    headline = 'Push hard today';
    explanation = `Recovery at ${recovery}% puts you in the green zone. ${
      hrvDirection === 'up' ? 'HRV trending up shows strong recovery.' : 'HRV at baseline.'
    } Target strain ${strainTarget[0]}-${strainTarget[1]}. Great day for intervals or competition.`;
  } else if (recovery >= 34) {
    decision = 'MODERATE';
    headline = 'Moderate effort today';
    explanation = `Recovery at ${recovery}% - yellow zone. ${
      hrvDirection === 'down' ? 'HRV below baseline suggests adaptation still in progress.' : 'Body in balanced state.'
    } Good for steady cardio or technique work.`;
  } else {
    decision = 'RECOVER';
    headline = 'Recovery focus';
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

class WellnessService {
  // Get today's wellness data with all calculations
  async getToday(): Promise<TodayData | null> {
    await db.initialize();

    // Get latest date
    const latestDate = await db.getLatestDate();
    if (!latestDate) return null;

    // Get today's record
    const record = await db.getWellness(latestDate);
    if (!record) return null;

    // Get history for baseline calculations (90 days for long-term baselines)
    const history = await db.getHistory(90);

    // Extract history arrays for baselines
    const hrvHistory = history.map(r => r.hrv?.hrv_last_night_avg ?? null);
    const sleepHistory = history.map(r =>
      r.sleep?.total_sleep_seconds ? r.sleep.total_sleep_seconds / 3600 : null
    );
    const rhrHistory = history.map(r => r.wellness?.resting_heart_rate ?? null);
    const bbHistory = history.map(r => r.stress?.body_battery_charged ?? null);

    // Calculate baselines (7-day, 30-day, and 90-day for long-term comparison)
    const baselines: Baselines = {
      hrv_7d_avg: calculateRollingAverage(hrvHistory, 7),
      hrv_30d_avg: calculateRollingAverage(hrvHistory, 30),
      hrv_90d_avg: calculateRollingAverage(hrvHistory, 90),
      sleep_7d_avg: calculateRollingAverage(sleepHistory, 7),
      sleep_30d_avg: calculateRollingAverage(sleepHistory, 30),
      sleep_90d_avg: calculateRollingAverage(sleepHistory, 90),
      rhr_7d_avg: calculateRollingAverage(rhrHistory, 7),
      rhr_30d_avg: calculateRollingAverage(rhrHistory, 30),
      rhr_90d_avg: calculateRollingAverage(rhrHistory, 90),
      recovery_7d_avg: calculateRollingAverage(bbHistory, 7),
      recovery_90d_avg: calculateRollingAverage(bbHistory, 90),
    };

    // Calculate derived values
    const totalSleepHours = record.sleep
      ? Math.round(record.sleep.total_sleep_seconds / 3600 * 100) / 100
      : null;
    const currentHrv = record.hrv?.hrv_last_night_avg ?? null;
    const currentRhr = record.wellness?.resting_heart_rate ?? null;
    const currentBB = record.stress?.body_battery_charged ?? null;

    // Calculate recovery score
    const recovery = calculateRecovery(currentHrv, totalSleepHours, currentBB, baselines);

    // Calculate strain from yesterday
    let strainYesterday = 10;
    if (history.length > 0) {
      const yesterday = history[0];
      const bbDrained = yesterday.stress?.body_battery_drained ?? 0;
      const steps = yesterday.activity?.steps ?? 0;
      const intensity = yesterday.activity?.intensity_minutes ?? 0;
      strainYesterday = calculateStrain(bbDrained, steps, intensity);
    }

    // Get HRV direction for insight
    const hrvDirection = calculateDirection(currentHrv, baselines.hrv_7d_avg);

    // Calculate sleep debt
    const sleepDebt = calculateSleepDebt(sleepHistory, baselines.sleep_7d_avg, 7);

    // Generate insight
    const insight = getInsight(
      recovery,
      hrvDirection?.direction ?? null,
      totalSleepHours,
      baselines.sleep_7d_avg,
      strainYesterday
    );

    // Generate weekly summary
    const weeklySummary = this.generateWeeklySummary(history.slice(0, 7), baselines);

    // Build response
    const sleepData = record.sleep ? {
      total_sleep_hours: totalSleepHours,
      deep_sleep_pct: record.sleep.total_sleep_seconds > 0
        ? Math.round(record.sleep.deep_sleep_seconds / record.sleep.total_sleep_seconds * 1000) / 10
        : 0,
      rem_sleep_pct: record.sleep.total_sleep_seconds > 0
        ? Math.round(record.sleep.rem_sleep_seconds / record.sleep.total_sleep_seconds * 1000) / 10
        : 0,
      sleep_score: record.sleep.sleep_score,
      sleep_efficiency: record.sleep.sleep_efficiency,
      direction: calculateDirection(totalSleepHours, baselines.sleep_7d_avg),
    } : null;

    const activityData = record.activity ? {
      steps: record.activity.steps,
      steps_goal: record.activity.steps_goal,
      steps_pct: record.activity.steps_goal > 0
        ? Math.round(record.activity.steps / record.activity.steps_goal * 1000) / 10
        : 0,
    } : null;

    return {
      date: latestDate,
      sleep: sleepData,
      hrv: record.hrv ? {
        hrv_last_night_avg: currentHrv,
        hrv_weekly_avg: record.hrv.hrv_weekly_avg,
        hrv_status: record.hrv.hrv_status,
        direction: hrvDirection,
      } : null,
      stress: record.stress ? {
        avg_stress_level: record.stress.avg_stress_level,
        body_battery_charged: currentBB,
        body_battery_drained: record.stress.body_battery_drained,
        direction: calculateDirection(currentBB, baselines.recovery_7d_avg),
      } : null,
      activity: activityData,
      resting_hr: currentRhr,
      rhr_direction: calculateDirection(currentRhr, baselines.rhr_7d_avg, 5.0, true),
      baselines,
      recovery,
      insight,
      sleep_debt: sleepDebt,
      weekly_summary: weeklySummary,
    };
  }

  // Generate weekly summary
  private generateWeeklySummary(
    weekHistory: WellnessRecord[],
    baselines: Baselines
  ): WeeklySummary {
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

    for (const record of weekHistory) {
      const sleepHours = record.sleep?.total_sleep_seconds
        ? record.sleep.total_sleep_seconds / 3600
        : null;

      const recovery = calculateRecovery(
        record.hrv?.hrv_last_night_avg ?? null,
        sleepHours,
        record.stress?.body_battery_charged ?? null,
        baselines
      );
      recoveries.push(recovery);

      const strain = calculateStrain(
        record.stress?.body_battery_drained ?? null,
        record.activity?.steps ?? null,
        record.activity?.intensity_minutes ?? null
      );
      strains.push(strain);

      if (sleepHours !== null) {
        sleeps.push(sleepHours);
        if (sleepHours < sleepBaseline) {
          sleepDebt += sleepBaseline - sleepHours;
        }
      }

      if (recovery >= 67) greenDays++;
      else if (recovery >= 34) yellowDays++;
      else redDays++;

      if (recovery > bestDay.recovery) bestDay = { date: record.date, recovery };
      if (recovery < worstDay.recovery) worstDay = { date: record.date, recovery };
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

    // Detect trends
    const trendAlerts: TrendAlert[] = [];
    if (recoveries.length >= 3) {
      let declining = 0;
      for (let i = 0; i < recoveries.length - 1; i++) {
        if (recoveries[i] < recoveries[i + 1] - 5) declining++;
      }
      if (declining >= 3) {
        const changePct = ((recoveries[0] - recoveries[recoveries.length - 1]) / recoveries[recoveries.length - 1]) * 100;
        trendAlerts.push({
          metric: 'Recovery',
          direction: 'declining',
          days: declining,
          change_pct: Math.round(changePct * 10) / 10,
          severity: changePct < -20 ? 'concern' : 'warning',
        });
      }
    }

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
      correlations: [], // Would need more data for correlations
      streaks: [], // Would need more complex streak tracking
      trend_alerts: trendAlerts,
    };
  }

  // Get history with calculated metrics
  async getHistory(days: number = 14): Promise<Array<{
    date: string;
    sleep_hours: number | null;
    hrv: number | null;
    recovery: number;
    strain: number;
    steps: number;
    body_battery: number | null;
    resting_hr: number | null;
  }>> {
    await db.initialize();
    const history = await db.getHistory(days);

    // Calculate baselines from full history
    const hrvHistory = history.map(r => r.hrv?.hrv_last_night_avg ?? null);
    const sleepHistory = history.map(r =>
      r.sleep?.total_sleep_seconds ? r.sleep.total_sleep_seconds / 3600 : null
    );
    const baselines = {
      hrv_7d_avg: calculateRollingAverage(hrvHistory, 7),
      sleep_7d_avg: calculateRollingAverage(sleepHistory, 7),
    };

    return history.map(record => {
      const sleepHours = record.sleep?.total_sleep_seconds
        ? Math.round(record.sleep.total_sleep_seconds / 3600 * 100) / 100
        : null;

      const recovery = calculateRecovery(
        record.hrv?.hrv_last_night_avg ?? null,
        sleepHours,
        record.stress?.body_battery_charged ?? null,
        baselines
      );

      const strain = calculateStrain(
        record.stress?.body_battery_drained ?? null,
        record.activity?.steps ?? null,
        record.activity?.intensity_minutes ?? null
      );

      return {
        date: record.date,
        sleep_hours: sleepHours,
        hrv: record.hrv?.hrv_last_night_avg ?? null,
        recovery,
        strain,
        steps: record.activity?.steps ?? 0,
        body_battery: record.stress?.body_battery_charged ?? null,
        resting_hr: record.wellness?.resting_heart_rate ?? null,
      };
    });
  }
}

// Singleton instance
export const wellness = new WellnessService();
