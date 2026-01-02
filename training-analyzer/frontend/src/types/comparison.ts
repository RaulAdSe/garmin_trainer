// Types for workout comparison feature

/**
 * Normalization mode for comparing workouts of different durations.
 */
export type NormalizationMode = 'time' | 'distance' | 'percentage';

/**
 * A workout that can be used for comparison.
 */
export interface ComparisonTarget {
  activity_id: string;
  name: string;
  activity_type: string;
  date: string;
  duration_min: number;
  distance_km?: number;
  avg_hr?: number;
  avg_pace_sec_km?: number;
  similarity_score: number;
  is_pr: boolean;
  quick_selection_type?: string;
}

/**
 * Response from the comparable workouts endpoint.
 */
export interface ComparableWorkoutsResponse {
  targets: ComparisonTarget[];
  quick_selections: ComparisonTarget[];
  total: number;
}

/**
 * Normalized time series data for a single workout.
 */
export interface NormalizedTimeSeries {
  timestamps: number[];  // Normalized 0-100 for percentage mode
  heart_rate: (number | null)[];
  pace: (number | null)[];
  power: (number | null)[];
  cadence: (number | null)[];
  elevation: (number | null)[];
}

/**
 * Statistics comparing two workouts.
 */
export interface ComparisonStats {
  hr_avg_diff?: number;        // Difference in average HR
  hr_max_diff?: number;        // Difference in max HR
  pace_avg_diff?: number;      // Difference in average pace (sec/km)
  power_avg_diff?: number;     // Difference in average power (W)
  duration_diff: number;        // Difference in duration (seconds)
  distance_diff?: number;       // Difference in distance (meters)
  improvement_metrics: {        // % improvement per metric
    [key: string]: number;      // hr_efficiency, pace, power, etc.
  };
}

/**
 * Complete comparison data between two workouts.
 */
export interface WorkoutComparisonData {
  primary_id: string;
  comparison_id: string;
  normalization_mode: NormalizationMode;
  primary_series: NormalizedTimeSeries;
  comparison_series: NormalizedTimeSeries;
  stats: ComparisonStats;
  sample_count: number;
}

/**
 * Props for comparison-aware chart components.
 */
export interface ComparisonChartProps {
  primaryData: NormalizedTimeSeries;
  comparisonData?: NormalizedTimeSeries;
  metric: 'heart_rate' | 'pace' | 'power' | 'cadence' | 'elevation';
  comparisonLabel?: string;
  showDifference?: boolean;
}

/**
 * Configuration for quick selection buttons.
 */
export interface QuickSelectionConfig {
  type: string;
  label: string;
  icon?: string;
  description?: string;
}

/**
 * Chart data point with comparison values.
 */
export interface ComparisonDataPoint {
  timestamp: number;          // Normalized timestamp (0-100)
  primary: number | null;     // Primary workout value
  comparison: number | null;  // Comparison workout value
  difference: number | null;  // Difference (primary - comparison)
}

/**
 * Legend item configuration for comparison charts.
 */
export interface ComparisonLegendItem {
  id: string;
  label: string;
  color: string;
  lineStyle: 'solid' | 'dashed' | 'dotted';
  value?: number | string;
  unit?: string;
}
