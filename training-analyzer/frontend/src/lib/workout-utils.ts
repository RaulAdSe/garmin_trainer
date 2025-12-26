// Workout-specific utility functions

/**
 * Convert pace (seconds per km) to speed (km/h)
 */
export function paceToSpeed(paceSecPerKm: number): number {
  if (paceSecPerKm <= 0) return 0;
  return 3600 / paceSecPerKm;
}

/**
 * Convert speed (km/h) to pace (seconds per km)
 */
export function speedToPace(speedKmh: number): number {
  if (speedKmh <= 0) return 0;
  return 3600 / speedKmh;
}

/**
 * Format speed for display
 */
export function formatSpeed(speedKmh: number, decimals: number = 1): string {
  return `${speedKmh.toFixed(decimals)} km/h`;
}

/**
 * Format elapsed time in seconds to readable format
 */
export function formatElapsedTime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format elapsed time for chart axis (abbreviated)
 */
export function formatChartTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  const remainingMins = mins % 60;
  return `${hours}h${remainingMins > 0 ? remainingMins + 'm' : ''}`;
}

/**
 * Get the activity category for metrics display
 */
export function getActivityCategory(
  workoutType: string
): 'running' | 'cycling' | 'swimming' | 'other' {
  const runningTypes = ['running', 'trail_running', 'walking', 'hiking', 'triathlon', 'treadmill_running'];
  const cyclingTypes = ['cycling', 'indoor_cycling', 'mountain_biking', 'gravel_cycling'];
  const swimmingTypes = ['swimming', 'pool_swimming', 'open_water_swimming'];

  const type = workoutType.toLowerCase();
  if (runningTypes.includes(type)) return 'running';
  if (cyclingTypes.includes(type)) return 'cycling';
  if (swimmingTypes.includes(type)) return 'swimming';
  return 'other';
}

/**
 * Downsample data array for chart rendering performance
 */
export function downsampleData<T>(data: T[], maxPoints: number = 500): T[] {
  if (data.length <= maxPoints) return data;

  const step = Math.ceil(data.length / maxPoints);
  const downsampled: T[] = [];

  for (let i = 0; i < data.length; i += step) {
    downsampled.push(data[i]);
  }

  // Always include the last point
  if (downsampled[downsampled.length - 1] !== data[data.length - 1]) {
    downsampled.push(data[data.length - 1]);
  }

  return downsampled;
}

/**
 * Calculate HR zone (1-5) from heart rate and max HR
 */
export function getHRZone(heartRate: number, maxHR: number): 1 | 2 | 3 | 4 | 5 {
  const pct = (heartRate / maxHR) * 100;
  if (pct < 60) return 1;
  if (pct < 70) return 2;
  if (pct < 80) return 3;
  if (pct < 90) return 4;
  return 5;
}

/**
 * Get HR zone color
 */
export function getHRZoneColorByValue(heartRate: number, maxHR: number): string {
  const zone = getHRZone(heartRate, maxHR);
  const colors = {
    1: '#22c55e', // green - recovery
    2: '#3b82f6', // blue - aerobic
    3: '#eab308', // yellow - tempo
    4: '#f97316', // orange - threshold
    5: '#ef4444', // red - VO2max
  };
  return colors[zone];
}
