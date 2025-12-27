/**
 * Utility functions for calculating period-based trends.
 */

export interface TrendResult {
  direction: 'up' | 'down' | 'stable';
  percentChange: number;
  currentAvg: number;
  previousAvg: number;
  hasEnoughData: boolean;
  periodLabel: string; // "vs last week", "vs last month", "vs last quarter"
}

/**
 * Calculate period-based trend from an array of values.
 * Compares based on the selected period:
 * - 14D: this week (7d) vs last week (7d)
 * - 30D: this month (15d) vs last month (15d)
 * - 90D: this quarter (45d) vs last quarter (45d)
 *
 * @param values - Array of numeric values, most recent first (index 0 = today)
 * @param period - The trend period (14, 30, or 90 days)
 * @param minDataPoints - Minimum data points required in each period (default: 3)
 * @returns TrendResult with direction, percentage change, averages, and period label
 */
export function calculatePeriodTrend(
  values: (number | null | undefined)[],
  period: 14 | 30 | 90,
  minDataPoints: number = 3
): TrendResult {
  // Determine comparison window based on period
  let currentWindow: number;
  let periodLabel: string;

  switch (period) {
    case 14:
      currentWindow = 7; // Compare week vs week
      periodLabel = 'vs last week';
      break;
    case 30:
      currentWindow = 15; // Compare ~half month vs half month
      periodLabel = 'vs last month';
      break;
    case 90:
      currentWindow = 45; // Compare ~half quarter vs half quarter
      periodLabel = 'vs last quarter';
      break;
    default:
      currentWindow = 7;
      periodLabel = 'vs last week';
  }

  // Current period values
  const currentValues = values.slice(0, currentWindow).filter((v): v is number => v != null && v > 0);

  // Previous period values
  const previousValues = values.slice(currentWindow, currentWindow * 2).filter((v): v is number => v != null && v > 0);

  // Check if we have enough data
  const hasEnoughData = currentValues.length >= minDataPoints && previousValues.length >= minDataPoints;

  if (!hasEnoughData || currentValues.length === 0 || previousValues.length === 0) {
    return {
      direction: 'stable',
      percentChange: 0,
      currentAvg: currentValues.length > 0
        ? currentValues.reduce((a, b) => a + b, 0) / currentValues.length
        : 0,
      previousAvg: previousValues.length > 0
        ? previousValues.reduce((a, b) => a + b, 0) / previousValues.length
        : 0,
      hasEnoughData: false,
      periodLabel,
    };
  }

  const currentAvg = currentValues.reduce((a, b) => a + b, 0) / currentValues.length;
  const previousAvg = previousValues.reduce((a, b) => a + b, 0) / previousValues.length;

  // Avoid division by zero
  if (previousAvg === 0) {
    return {
      direction: currentAvg > 0 ? 'up' : 'stable',
      percentChange: currentAvg > 0 ? 100 : 0,
      currentAvg,
      previousAvg,
      hasEnoughData: true,
      periodLabel,
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
    periodLabel,
  };
}

/**
 * Calculate week-over-week trend from an array of values.
 * Compares current 7-day average vs previous 7-day average.
 * @deprecated Use calculatePeriodTrend instead for adaptive comparisons
 */
export function calculateWeekOverWeekTrend(
  values: (number | null | undefined)[],
  minDataPoints: number = 3
): TrendResult {
  return calculatePeriodTrend(values, 14, minDataPoints);
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
  const text = `${arrow} ${absChange.toFixed(0)}% ${trend.periodLabel}`;

  // Determine if this is "good" or "bad"
  const isImprovement = inverse
    ? trend.direction === 'down'
    : trend.direction === 'up';

  const colorClass = isImprovement ? 'text-green-400' : 'text-red-400';

  return { text, colorClass, arrow };
}
