// Workout types for the Reactive Training App

export type WorkoutType =
  | 'running'
  | 'trail_running'
  | 'cycling'
  | 'swimming'
  | 'walking'
  | 'hiking'
  | 'strength'
  | 'hiit'
  | 'yoga'
  | 'skiing'
  | 'football'
  | 'tennis'
  | 'basketball'
  | 'golf'
  | 'rowing'
  | 'surfing'
  | 'elliptical'
  | 'climbing'
  | 'martial_arts'
  | 'skating'
  | 'dance'
  | 'triathlon'
  | 'other';

export type HRZone = 'zone1' | 'zone2' | 'zone3' | 'zone4' | 'zone5';

export interface HRZoneData {
  zone: HRZone;
  label: string;
  percentage: number;
  duration: number; // in seconds
  avgHR: number;
}

export interface PaceSplit {
  splitNumber: number;
  distance: number; // in meters
  duration: number; // in seconds
  pace: number; // seconds per km
  avgHR?: number;
  elevation?: number;
}

export interface WorkoutMetrics {
  avgHeartRate?: number;
  maxHeartRate?: number;
  avgPace?: number; // seconds per km
  maxPace?: number;
  avgCadence?: number;
  avgPower?: number;
  calories?: number;
  elevationGain?: number;
  elevationLoss?: number;
  trainingEffect?: number;
  vo2maxEstimate?: number;
}

export interface Workout {
  id: string;
  userId: string;
  type: WorkoutType;
  name: string;
  date: string; // ISO date string
  startTime: string; // ISO datetime string
  endTime: string; // ISO datetime string
  duration: number; // in seconds
  distance?: number; // in meters
  metrics: WorkoutMetrics;
  hrZones?: HRZoneData[];
  paceSplits?: PaceSplit[];
  notes?: string;
  source: 'garmin' | 'strava' | 'manual';
  rawData?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface WorkoutAnalysisSection {
  title: string;
  content: string;
}

export interface WorkoutAnalysis {
  // Core IDs
  workoutId: string;
  analysisId?: string;

  // Analysis content
  summary: string;
  whatWentWell: string[];  // Backend: what_worked_well -> whatWentWell
  improvements: string[];   // Backend: observations -> improvements
  recommendations?: string[];

  // Training context (backend uses trainingFit)
  trainingContext?: string; // Frontend compatibility
  trainingFit?: string;     // Backend field name

  // Additional sections (optional)
  sections?: WorkoutAnalysisSection[];

  // Ratings and levels
  effortLevel?: 'easy' | 'moderate' | 'hard' | 'very_hard';
  executionRating?: 'excellent' | 'good' | 'fair' | 'needs_improvement';
  effortAlignment?: string;

  // Scores (0-100 overall, 0-5 training effect, HRSS load)
  overallScore?: number;
  trainingEffectScore?: number;
  loadScore?: number;
  recoveryHours?: number;

  // Recovery
  recoveryRecommendation?: string;

  // Metadata
  generatedAt?: string;     // Frontend compatibility
  createdAt?: string;       // Backend field name
  modelUsed?: string;

  // Legacy support
  id?: string;
}

export interface AnalysisStreamChunk {
  type: 'content' | 'done' | 'error';
  content?: string;
  section?: string;
  error?: string;
}

export interface WorkoutListFilters {
  startDate?: string;
  endDate?: string;
  type?: WorkoutType;
  minDistance?: number;
  maxDistance?: number;
  search?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, unknown>;
}

// Request types
export interface AnalyzeWorkoutRequest {
  workoutId: string;
  includeContext?: boolean;
  regenerate?: boolean;
}

export interface WorkoutListRequest {
  page?: number;
  pageSize?: number;
  filters?: WorkoutListFilters;
  sortBy?: 'date' | 'distance' | 'duration';
  sortOrder?: 'asc' | 'desc';
}

// ============================================
// Training Plan Types (Phase 2)
// ============================================

export type TrainingPhase = 'base' | 'build' | 'peak' | 'taper' | 'recovery';

export type SessionType =
  | 'easy'
  | 'long_run'
  | 'tempo'
  | 'interval'
  | 'hill'
  | 'recovery'
  | 'race'
  | 'cross_training'
  | 'strength'
  | 'rest';

export type RaceDistance =
  | '5k'
  | '10k'
  | 'half_marathon'
  | 'marathon'
  | 'ultra'
  | 'custom';

export type PeriodizationType = 'linear' | 'undulating' | 'block' | 'polarized';

export type CompletionStatus = 'pending' | 'completed' | 'skipped' | 'partial';

export interface TrainingSession {
  id: string;
  weekId: string;
  dayOfWeek: number; // 0 = Monday, 6 = Sunday
  date: string; // ISO date string
  sessionType: SessionType;
  name: string;
  description: string;
  targetDuration: number; // in minutes
  actualDuration?: number;
  targetLoad: number; // training stress score
  actualLoad?: number;
  targetDistance?: number; // in meters
  actualDistance?: number;
  targetPace?: number; // seconds per km
  actualPace?: number;
  targetHeartRateZone?: HRZone;
  completionStatus: CompletionStatus;
  workoutId?: string; // linked actual workout
  notes?: string;
  warmup?: string;
  mainSet?: string;
  cooldown?: string;
}

export interface TrainingWeek {
  id: string;
  planId: string;
  weekNumber: number;
  startDate: string;
  endDate: string;
  phase: TrainingPhase;
  targetLoad: number;
  actualLoad: number;
  sessions: TrainingSession[];
  focusAreas: string[];
  notes?: string;
}

export interface PlanGoal {
  raceDistance: RaceDistance;
  customDistance?: number; // in meters, for custom distances
  targetTime?: number; // in seconds
  raceDate: string; // ISO date string
  raceName?: string;
  priority: 'A' | 'B' | 'C';
}

export interface PlanConstraints {
  daysPerWeek: number; // 3-7
  maxSessionDuration: number; // in minutes
  longRunDay: number; // 0-6
  restDays: number[]; // days of week
  includeStrength: boolean;
  includeCrossTraining: boolean;
  currentFitnessLevel: 'beginner' | 'intermediate' | 'advanced' | 'elite';
  weeklyMileageStart?: number; // starting weekly mileage in km
  injuryHistory?: string[];
}

export interface TrainingPlan {
  id: string;
  userId: string;
  name: string;
  description?: string;
  goal: PlanGoal;
  constraints: PlanConstraints;
  periodizationType: PeriodizationType;
  startDate: string;
  endDate: string;
  totalWeeks: number;
  currentWeek: number;
  weeks: TrainingWeek[];
  status: 'draft' | 'active' | 'completed' | 'paused' | 'cancelled';
  compliance: PlanCompliance;
  createdAt: string;
  updatedAt: string;
}

export interface PlanCompliance {
  totalSessions: number;
  completedSessions: number;
  skippedSessions: number;
  partialSessions: number;
  compliancePercentage: number;
  loadAdherence: number; // percentage of target load achieved
  weeklyCompliance: WeeklyCompliance[];
}

export interface WeeklyCompliance {
  weekNumber: number;
  targetLoad: number;
  actualLoad: number;
  adherence: number;
  sessionsPlanned: number;
  sessionsCompleted: number;
}

export interface PlanSummary {
  id: string;
  name: string;
  goal: PlanGoal;
  status: TrainingPlan['status'];
  startDate: string;
  endDate: string;
  totalWeeks: number;
  currentWeek: number;
  compliancePercentage: number;
}

// Request types for plans
export interface CreatePlanRequest {
  name: string;
  description?: string;
  goal: PlanGoal;
  constraints: PlanConstraints;
  periodizationType: PeriodizationType;
  startDate?: string; // defaults to next Monday if not provided
}

export interface GeneratePlanRequest extends CreatePlanRequest {
  regenerate?: boolean;
}

export interface UpdatePlanRequest {
  name?: string;
  description?: string;
  status?: TrainingPlan['status'];
}

export interface UpdateSessionRequest {
  completionStatus?: CompletionStatus;
  actualDuration?: number;
  actualDistance?: number;
  actualLoad?: number;
  workoutId?: string;
  notes?: string;
}

export interface PlanListRequest {
  page?: number;
  pageSize?: number;
  status?: TrainingPlan['status'];
  sortBy?: 'startDate' | 'endDate' | 'createdAt' | 'name';
  sortOrder?: 'asc' | 'desc';
}

// ============================================
// Phase 3: Workout Design + Garmin Export Types
// ============================================

export type IntervalType = 'warmup' | 'work' | 'recovery' | 'cooldown' | 'rest';

export type PaceUnit = 'min/km' | 'min/mile';

export type TrainingZone = 'easy' | 'tempo' | 'threshold' | 'interval' | 'repetition';

export interface PaceTarget {
  min: number; // seconds per km/mile
  max: number; // seconds per km/mile
  unit: PaceUnit;
}

export interface HRTarget {
  min: number; // bpm
  max: number; // bpm
  zone?: HRZone;
}

export interface WorkoutInterval {
  id: string;
  type: IntervalType;
  name?: string;
  duration: number; // in seconds
  distance?: number; // in meters (optional, alternative to duration)
  paceTarget?: PaceTarget;
  hrTarget?: HRTarget;
  notes?: string;
  repetitions?: number; // for repeat intervals
}

export interface DesignedWorkout {
  id?: string;
  name: string;
  description?: string;
  type: WorkoutType;
  intervals: WorkoutInterval[];
  totalDuration: number; // calculated from intervals
  totalDistance?: number; // calculated from intervals
  targetDate?: string; // ISO date string
  aiGenerated?: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface AIWorkoutSuggestion {
  id: string;
  title: string;
  description: string;
  workout: DesignedWorkout;
  rationale: string;
  difficulty: 'easy' | 'moderate' | 'hard' | 'very_hard';
  focusArea: string;
  estimatedLoad: number;
}

export interface GenerateWorkoutRequest {
  workoutType: WorkoutType;
  targetDuration?: number; // in minutes
  targetDistance?: number; // in meters
  difficulty?: 'easy' | 'moderate' | 'hard' | 'very_hard';
  focusArea?: string;
  includeAthleteContext?: boolean;
  numberOfSuggestions?: number;
}

export interface GenerateWorkoutResponse {
  suggestions: AIWorkoutSuggestion[];
  athleteContext?: {
    recentVolume: number;
    fatigueLevel: string;
    fitnessLevel: string;
  };
}

export interface SaveWorkoutRequest {
  workout: DesignedWorkout;
}

export interface SaveWorkoutResponse {
  id: string;
  workout: DesignedWorkout;
}

export interface FITExportRequest {
  workoutId: string;
}

export interface FITExportResponse {
  fileUrl: string;
  fileName: string;
  expiresAt: string;
}

export interface GarminExportRequest {
  workoutId: string;
}

export interface GarminExportResponse {
  success: boolean;
  garminWorkoutId?: string;
  message?: string;
}

export interface TrainingZoneConfig {
  zone: TrainingZone;
  label: string;
  description: string;
  pacePercentage: { min: number; max: number }; // percentage of threshold pace
  hrPercentage: { min: number; max: number }; // percentage of max HR
  color: string;
}

export const TRAINING_ZONES: TrainingZoneConfig[] = [
  {
    zone: 'easy',
    label: 'Easy',
    description: 'Conversational pace, recovery runs',
    pacePercentage: { min: 65, max: 75 },
    hrPercentage: { min: 60, max: 70 },
    color: '#22c55e', // green
  },
  {
    zone: 'tempo',
    label: 'Tempo',
    description: 'Comfortably hard, marathon pace',
    pacePercentage: { min: 80, max: 88 },
    hrPercentage: { min: 75, max: 85 },
    color: '#eab308', // yellow
  },
  {
    zone: 'threshold',
    label: 'Threshold',
    description: 'Lactate threshold, 1-hour race pace',
    pacePercentage: { min: 88, max: 95 },
    hrPercentage: { min: 85, max: 90 },
    color: '#f97316', // orange
  },
  {
    zone: 'interval',
    label: 'Interval',
    description: 'VO2max work, 5K-10K race pace',
    pacePercentage: { min: 95, max: 105 },
    hrPercentage: { min: 90, max: 95 },
    color: '#ef4444', // red
  },
  {
    zone: 'repetition',
    label: 'Repetition',
    description: 'Speed work, mile race pace or faster',
    pacePercentage: { min: 105, max: 120 },
    hrPercentage: { min: 95, max: 100 },
    color: '#dc2626', // dark red
  },
];

export const INTERVAL_TYPE_COLORS: Record<IntervalType, string> = {
  warmup: '#3b82f6', // blue
  work: '#ef4444', // red
  recovery: '#22c55e', // green
  cooldown: '#8b5cf6', // purple
  rest: '#6b7280', // gray
};

export const INTERVAL_TYPE_LABELS: Record<IntervalType, string> = {
  warmup: 'Warm-up',
  work: 'Work',
  recovery: 'Recovery',
  cooldown: 'Cool-down',
  rest: 'Rest',
};

// ============================================
// Athlete Context Types (Phase 0)
// ============================================

export interface FitnessMetrics {
  ctl: number;
  atl: number;
  tsb: number;
  acwr: number;
  risk_zone: string;
  daily_load: number;
}

export interface Physiology {
  max_hr: number;
  rest_hr: number;
  lthr: number;
  age?: number;
  gender?: string;
  weight_kg?: number;
  vdot?: number;
}

export interface HRZoneInfo {
  zone: number;
  name: string;
  min_hr: number;
  max_hr: number;
  description: string;
}

export interface TrainingPace {
  name: string;
  pace_sec_per_km: number;
  pace_formatted: string;
  hr_zone: string;
  description: string;
}

export interface RaceGoalInfo {
  distance: string;
  distance_km: number;
  target_time_formatted: string;
  target_pace_formatted: string;
  race_date: string;
  weeks_remaining: number;
}

export interface ReadinessInfo {
  score: number;
  zone: string;
  recommendation: string;
}

export interface AthleteContext {
  fitness: FitnessMetrics;
  physiology: Physiology;
  hr_zones: HRZoneInfo[];
  training_paces: TrainingPace[];
  race_goals: RaceGoalInfo[];
  readiness: ReadinessInfo;
}

export interface ReadinessResponse {
  date: string;
  readiness: {
    score: number;
    zone: string;
    factors?: Record<string, unknown>;
  };
  recommendation: string;
  narrative?: string;
}

export interface FitnessMetricsHistory {
  start_date: string;
  end_date: string;
  metrics: Array<{
    date: string;
    ctl: number;
    atl: number;
    tsb: number;
    acwr: number;
    daily_load: number;
    risk_zone: string;
  }>;
}

// ============================================
// Workout Score Types (Analysis v2)
// ============================================

export type ScoreLevel = 'excellent' | 'good' | 'moderate' | 'fair' | 'poor';
export type ScoreColor = 'green' | 'yellow' | 'orange' | 'red';

export interface WorkoutScore {
  name: string;
  value: number;
  maxValue: number;
  label: ScoreLevel;
  color: ScoreColor;
  description: string;
}

export interface WorkoutScores {
  overallQuality: WorkoutScore;
  trainingEffect: WorkoutScore;
  loadManagement: WorkoutScore;
  recoveryImpact: WorkoutScore;
}

// Helper function to determine score color based on value and thresholds
export function getScoreColor(value: number, maxValue: number): ScoreColor {
  const percentage = (value / maxValue) * 100;
  if (percentage >= 80) return 'green';
  if (percentage >= 60) return 'yellow';
  if (percentage >= 40) return 'orange';
  return 'red';
}

// Helper function to determine score label based on value and thresholds
export function getScoreLabel(value: number, maxValue: number): ScoreLevel {
  const percentage = (value / maxValue) * 100;
  if (percentage >= 90) return 'excellent';
  if (percentage >= 75) return 'good';
  if (percentage >= 55) return 'moderate';
  if (percentage >= 35) return 'fair';
  return 'poor';
}

// Score color mappings for Tailwind CSS classes
export const SCORE_COLOR_MAP: Record<ScoreColor, {
  bg: string;
  text: string;
  fill: string;
  gradient: string;
}> = {
  green: {
    bg: 'bg-green-500',
    text: 'text-green-400',
    fill: '#22c55e',
    gradient: 'from-green-500 to-green-600',
  },
  yellow: {
    bg: 'bg-yellow-500',
    text: 'text-yellow-400',
    fill: '#eab308',
    gradient: 'from-yellow-500 to-yellow-600',
  },
  orange: {
    bg: 'bg-orange-500',
    text: 'text-orange-400',
    fill: '#f97316',
    gradient: 'from-orange-500 to-orange-600',
  },
  red: {
    bg: 'bg-red-500',
    text: 'text-red-400',
    fill: '#ef4444',
    gradient: 'from-red-500 to-red-600',
  },
};

// Score label display mappings
export const SCORE_LABEL_MAP: Record<ScoreLevel, string> = {
  excellent: 'Excellent',
  good: 'Good',
  moderate: 'Moderate',
  fair: 'Fair',
  poor: 'Needs Work',
};
