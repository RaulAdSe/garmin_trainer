/**
 * Utility functions for calculating week-over-week trends.
 */

export interface TrendResult {
  direction: 'up' | 'down' | 'stable';
  percentChange: number;
  currentAvg: number;
  previousAvg: number;
  hasEnoughData: boolean;
}

/**
 * Calculate week-over-week trend from an array of values.
 * Compares current 7-day average vs previous 7-day average.
 *
 * @param values - Array of numeric values, most recent first (index 0 = today)
 * @param minDataPoints - Minimum data points required in each week (default: 3)
 * @returns TrendResult with direction, percentage change, and averages
 */
export function calculateWeekOverWeekTrend(
  values: (number | null | undefined)[],
  minDataPoints: number = 3
): TrendResult {
  // Current week: indices 0-6 (most recent 7 days)
  const currentWeekValues = values.slice(0, 7).filter((v): v is number => v != null && v > 0);

  // Previous week: indices 7-13
  const previousWeekValues = values.slice(7, 14).filter((v): v is number => v != null && v > 0);

  // Check if we have enough data
  const hasEnoughData = currentWeekValues.length >= minDataPoints && previousWeekValues.length >= minDataPoints;

  if (!hasEnoughData || currentWeekValues.length === 0 || previousWeekValues.length === 0) {
    return {
      direction: 'stable',
      percentChange: 0,
      currentAvg: currentWeekValues.length > 0
        ? currentWeekValues.reduce((a, b) => a + b, 0) / currentWeekValues.length
        : 0,
      previousAvg: previousWeekValues.length > 0
        ? previousWeekValues.reduce((a, b) => a + b, 0) / previousWeekValues.length
        : 0,
      hasEnoughData: false,
    };
  }

  const currentAvg = currentWeekValues.reduce((a, b) => a + b, 0) / currentWeekValues.length;
  const previousAvg = previousWeekValues.reduce((a, b) => a + b, 0) / previousWeekValues.length;

  // Avoid division by zero
  if (previousAvg === 0) {
    return {
      direction: currentAvg > 0 ? 'up' : 'stable',
      percentChange: currentAvg > 0 ? 100 : 0,
      currentAvg,
      previousAvg,
      hasEnoughData: true,
    };
  }

  const percentChange = ((currentAvg - previousAvg) / previousAvg) * 100;

  // Threshold for considering a change significant (2%)
  const threshold = 2;

  let direction: 'up' | 'down' | 'stable';
  if (percentChange > threshold) {
    direction = 'up';
  } else if (percentChange < -threshold) {
    direction = 'down';
  } else {
    direction = 'stable';
  }

  return {
    direction,
    percentChange,
    currentAvg,
    previousAvg,
    hasEnoughData: true,
  };
}

/**
 * Format a trend result into a display string.
 *
 * @param trend - The TrendResult to format
 * @param inverse - If true, down is good (e.g., for RHR)
 * @returns Object with display text, color class, and arrow
 */
export function formatTrendDisplay(
  trend: TrendResult,
  inverse: boolean = false
): { text: string; colorClass: string; arrow: string } | null {
  if (!trend.hasEnoughData || trend.direction === 'stable') {
    return null;
  }

  const absChange = Math.abs(trend.percentChange);
  const arrow = trend.direction === 'up' ? '↑' : '↓';
  const text = `${arrow} ${absChange.toFixed(0)}% vs last week`;

  // Determine if this is "good" or "bad"
  const isImprovement = inverse
    ? trend.direction === 'down'
    : trend.direction === 'up';

  const colorClass = isImprovement ? 'text-green-400' : 'text-red-400';

  return { text, colorClass, arrow };
}
