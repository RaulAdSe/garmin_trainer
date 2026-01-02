/**
 * Pattern Recognition Types
 *
 * TypeScript interfaces for pattern recognition API responses.
 */

// ============================================
// Enums and Constants
// ============================================

export type TimeOfDay =
  | 'early_morning'  // 5-7am
  | 'morning'        // 7-10am
  | 'late_morning'   // 10am-12pm
  | 'afternoon'      // 12-3pm
  | 'late_afternoon' // 3-6pm
  | 'evening'        // 6-9pm
  | 'night';         // 9pm-5am

export type DayOfWeek =
  | 'monday'
  | 'tuesday'
  | 'wednesday'
  | 'thursday'
  | 'friday'
  | 'saturday'
  | 'sunday';

export type TSBZone =
  | 'deep_fatigue'  // TSB < -25
  | 'fatigued'      // -25 <= TSB < -10
  | 'functional'    // -10 <= TSB < 0
  | 'fresh'         // 0 <= TSB < 15
  | 'peaked'        // 15 <= TSB < 30
  | 'detrained';    // TSB >= 30

// ============================================
// Timing Analysis Types
// ============================================

export interface TimeSlotPerformance {
  time_slot: TimeOfDay;
  workout_count: number;
  avg_performance_score: number;
  avg_hr_efficiency: number;
  avg_execution_rating: number | null;
  sample_workouts: string[];
}

export interface DayPerformance {
  day: DayOfWeek;
  workout_count: number;
  avg_performance_score: number;
  avg_training_load: number;
  preferred_workout_types: string[];
  sample_workouts: string[];
}

export interface OptimalWindow {
  time_slot: TimeOfDay;
  day: DayOfWeek | null;
  performance_boost: number;
  confidence: number;
  sample_size: number;
}

export interface TimingAnalysis {
  user_id: string;
  analyzed_at: string;
  analysis_period_days: number;

  // Performance by time of day
  time_slot_performance: TimeSlotPerformance[];

  // Performance by day of week
  day_performance: DayPerformance[];

  // Identified optimal windows
  optimal_windows: OptimalWindow[];

  // Best single time slot
  best_time_slot: TimeOfDay | null;
  best_time_slot_boost: number;

  // Best day of week
  best_day: DayOfWeek | null;
  best_day_boost: number;

  // Worst performers (for recommendations)
  avoid_time_slot: TimeOfDay | null;
  avoid_day: DayOfWeek | null;

  // Summary stats
  total_workouts_analyzed: number;
  data_quality_score: number;
}

// ============================================
// TSB Optimal Range Types
// ============================================

export interface TSBPerformancePoint {
  workout_id: string;
  workout_date: string;
  tsb: number;
  ctl: number;
  atl: number;
  performance_score: number;
  workout_type: string;
  distance_km: number | null;
  duration_min: number | null;
}

export interface TSBZoneStats {
  zone: TSBZone;
  tsb_range: [number, number];
  workout_count: number;
  avg_performance: number;
  std_performance: number;
  best_performance: number;
  worst_performance: number;
}

export interface TSBOptimalRange {
  user_id: string;
  analyzed_at: string;
  analysis_period_days: number;

  // Core optimal range
  optimal_tsb_min: number;
  optimal_tsb_max: number;
  optimal_zone: TSBZone;

  // Performance by zone
  zone_stats: TSBZoneStats[];

  // Individual data points (for scatter plot)
  data_points: TSBPerformancePoint[];

  // Correlation metrics
  tsb_performance_correlation: number;
  correlation_confidence: number;

  // Race timing recommendations
  recommended_taper_days: number;
  peak_tsb_target: number;
  current_tsb: number | null;
  days_to_peak: number | null;

  // Summary stats
  total_workouts_analyzed: number;
  data_quality_score: number;
}

// ============================================
// Peak Fitness Prediction Types
// ============================================

export interface CTLProjection {
  date: string;
  projected_ctl: number;
  confidence_lower: number;
  confidence_upper: number;
  is_historical: boolean;
}

export interface PlannedEvent {
  event_id: string | null;
  name: string;
  event_date: string;
  event_type: string;
  priority: string;
}

export interface FitnessPrediction {
  user_id: string;
  predicted_at: string;
  prediction_horizon_days: number;

  // Current state
  current_ctl: number;
  current_atl: number;
  current_tsb: number;
  current_weekly_load: number;

  // Peak prediction (without target date)
  natural_peak_date: string | null;
  natural_peak_ctl: number | null;
  days_to_natural_peak: number | null;

  // Target event analysis
  target_event: PlannedEvent | null;
  target_date: string | null;
  projected_ctl_at_target: number | null;
  projected_tsb_at_target: number | null;

  // CTL trajectory (for chart)
  ctl_projection: CTLProjection[];

  // Recommendations
  weekly_load_recommendation: number;
  load_change_percentage: number;
  taper_start_date: string | null;

  // Confidence
  prediction_confidence: number;

  // Planned events
  planned_events: PlannedEvent[];
}

// ============================================
// Correlation Analysis Types
// ============================================

export interface CorrelationFactor {
  factor_name: string;
  correlation_coefficient: number;
  p_value: number;
  sample_size: number;
  is_significant: boolean;
}

export interface PerformanceCorrelations {
  user_id: string;
  analyzed_at: string;
  analysis_period_days: number;

  // Key correlations
  correlations: CorrelationFactor[];

  // Top positive and negative factors
  top_positive_factors: string[];
  top_negative_factors: string[];

  // Insights
  key_insights: string[];

  // Data quality
  total_workouts_analyzed: number;
  data_quality_score: number;
}

// ============================================
// Combined Pattern Summary
// ============================================

export interface PatternSummary {
  timing_correlations: TimingAnalysis | null;
  tsb_correlations: TSBOptimalRange | null;
  performance_correlations: PerformanceCorrelations | null;
  fitness_prediction: FitnessPrediction | null;
}

// ============================================
// Helper Types
// ============================================

export interface TimeSlotLabel {
  slot: TimeOfDay;
  label: string;
  shortLabel: string;
  timeRange: string;
}

export const TIME_SLOT_LABELS: TimeSlotLabel[] = [
  { slot: 'early_morning', label: 'Early Morning', shortLabel: 'Early AM', timeRange: '5-7am' },
  { slot: 'morning', label: 'Morning', shortLabel: 'Morning', timeRange: '7-10am' },
  { slot: 'late_morning', label: 'Late Morning', shortLabel: 'Late AM', timeRange: '10am-12pm' },
  { slot: 'afternoon', label: 'Afternoon', shortLabel: 'Afternoon', timeRange: '12-3pm' },
  { slot: 'late_afternoon', label: 'Late Afternoon', shortLabel: 'Late PM', timeRange: '3-6pm' },
  { slot: 'evening', label: 'Evening', shortLabel: 'Evening', timeRange: '6-9pm' },
  { slot: 'night', label: 'Night', shortLabel: 'Night', timeRange: '9pm-5am' },
];

export interface DayLabel {
  day: DayOfWeek;
  label: string;
  shortLabel: string;
}

export const DAY_LABELS: DayLabel[] = [
  { day: 'monday', label: 'Monday', shortLabel: 'Mon' },
  { day: 'tuesday', label: 'Tuesday', shortLabel: 'Tue' },
  { day: 'wednesday', label: 'Wednesday', shortLabel: 'Wed' },
  { day: 'thursday', label: 'Thursday', shortLabel: 'Thu' },
  { day: 'friday', label: 'Friday', shortLabel: 'Fri' },
  { day: 'saturday', label: 'Saturday', shortLabel: 'Sat' },
  { day: 'sunday', label: 'Sunday', shortLabel: 'Sun' },
];

export interface TSBZoneLabel {
  zone: TSBZone;
  label: string;
  description: string;
  color: string;
}

export const TSB_ZONE_LABELS: TSBZoneLabel[] = [
  { zone: 'deep_fatigue', label: 'Deep Fatigue', description: 'Very fatigued, need extended rest', color: '#EF4444' },
  { zone: 'fatigued', label: 'Fatigued', description: 'High training load accumulated', color: '#F97316' },
  { zone: 'functional', label: 'Functional', description: 'Good for steady training', color: '#EAB308' },
  { zone: 'fresh', label: 'Fresh', description: 'Recovered and ready to perform', color: '#22C55E' },
  { zone: 'peaked', label: 'Peaked', description: 'Ideal for race day', color: '#14B8A6' },
  { zone: 'detrained', label: 'Detrained', description: 'Too much rest, losing fitness', color: '#6B7280' },
];

// Helper functions
export function getTimeSlotLabel(slot: TimeOfDay): TimeSlotLabel {
  return TIME_SLOT_LABELS.find(s => s.slot === slot) || TIME_SLOT_LABELS[0];
}

export function getDayLabel(day: DayOfWeek): DayLabel {
  return DAY_LABELS.find(d => d.day === day) || DAY_LABELS[0];
}

export function getTSBZoneLabel(zone: TSBZone): TSBZoneLabel {
  return TSB_ZONE_LABELS.find(z => z.zone === zone) || TSB_ZONE_LABELS[3];
}

export function getCorrelationStrength(coefficient: number): string {
  const r = Math.abs(coefficient);
  if (r >= 0.7) return 'strong';
  if (r >= 0.4) return 'moderate';
  if (r >= 0.2) return 'weak';
  return 'negligible';
}

export function getCorrelationColor(coefficient: number): string {
  if (coefficient >= 0.4) return '#22C55E'; // Strong positive - green
  if (coefficient >= 0.2) return '#84CC16'; // Weak positive - lime
  if (coefficient >= -0.2) return '#6B7280'; // Negligible - gray
  if (coefficient >= -0.4) return '#F97316'; // Weak negative - orange
  return '#EF4444'; // Strong negative - red
}
