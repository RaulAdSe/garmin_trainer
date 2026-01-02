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

// VO2 Max Types
export interface VO2MaxDataPoint {
  date: string;
  vo2max_running: number | null;
  vo2max_cycling: number | null;
  training_status: string | null;
}

export interface VO2MaxTrend {
  data_points: VO2MaxDataPoint[];
  trend: 'improving' | 'stable' | 'declining' | 'unknown';
  change_percent: number;
  current_vo2max_running: number | null;
  current_vo2max_cycling: number | null;
  peak_vo2max_running: number | null;
  peak_vo2max_cycling: number | null;
  current_vs_peak_running: number | null;
  current_vs_peak_cycling: number | null;
  start_date: string;
  end_date: string;
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

// ============================================
// Explainability Types (Transparency Layer)
// ============================================

export type ImpactType = 'positive' | 'negative' | 'neutral';

export interface DataSource {
  source_type: string;
  source_name: string;
  last_updated?: string;
  confidence: number;
}

export interface ExplanationFactor {
  name: string;
  value: unknown;
  display_value: string;
  impact: ImpactType;
  weight: number;
  contribution_points: number;
  explanation: string;
  threshold?: string;
  baseline?: unknown;
  data_sources: DataSource[];
}

export interface ExplainedRecommendation {
  recommendation: string;
  confidence: number;
  confidence_explanation: string;
  factors: ExplanationFactor[];
  data_points: Record<string, unknown>;
  calculation_summary: string;
  alternatives_considered: string[];
  key_driver?: string;
}

export interface ExplainedReadiness {
  date: string;
  overall_score: number;
  zone: string;
  recommendation: ExplainedRecommendation;
  factor_breakdown: ExplanationFactor[];
  score_calculation: string;
  comparison_to_baseline?: string;
  trend?: string;
}

export interface ExplainedWorkout {
  workout_type: string;
  duration_min: number;
  intensity_description: string;
  hr_zone_target?: string;
  recommendation: ExplainedRecommendation;
  decision_tree: string[];
  readiness_influence: number;
  load_influence: number;
  pattern_influence: number;
}

export interface SessionExplanation {
  session_id: string;
  session_name: string;
  session_type: string;
  scheduled_date: string;
  rationale: ExplainedRecommendation;
  periodization_context: string;
  weekly_context: string;
  progression_note?: string;
}

// ============================================
// Gamification Types
// ============================================

export type AchievementCategory = 'consistency' | 'performance' | 'execution' | 'milestone';
export type AchievementRarity = 'common' | 'rare' | 'epic' | 'legendary';

export interface Achievement {
  id: string;
  name: string;
  description: string;
  category: AchievementCategory;
  icon: string;
  xpValue: number;
  rarity: AchievementRarity;
  conditionType?: string;
  conditionValue?: string;
  displayOrder: number;
}

export interface UserAchievement {
  achievement: Achievement;
  unlockedAt: string;
  workoutId?: string;
  isNew?: boolean;
}

export interface LevelInfo {
  level: number;
  xpRequired: number;
  xpForNext: number;
  xpInLevel: number;
  progressPercent: number;
}

export interface StreakInfo {
  current: number;
  longest: number;
  freezeTokens: number;
  isProtected: boolean;
  lastActivityDate?: string;
}

export interface LevelReward {
  level: number;
  name: string;
  title: string;
  unlocks: string[];
  description: string;
}

export interface UserProgress {
  userId?: string;
  totalXp: number;
  level: LevelInfo;
  streak: StreakInfo;
  achievementsUnlocked: number;
  updatedAt?: string;
  title?: string;
  unlockedFeatures?: string[];
  nextReward?: LevelReward;
}

export interface AchievementWithStatus {
  achievement: Achievement;
  unlocked: boolean;
  unlockedAt?: string;
  progress?: number; // 0-100 for partial progress
}

// Rarity colors
export const RARITY_COLORS: Record<AchievementRarity, string> = {
  common: 'text-gray-400',
  rare: 'text-blue-400',
  epic: 'text-purple-400',
  legendary: 'text-amber-400',
};

export const RARITY_BG_COLORS: Record<AchievementRarity, string> = {
  common: 'bg-gray-400/10',
  rare: 'bg-blue-400/10',
  epic: 'bg-purple-400/10',
  legendary: 'bg-amber-400/10',
};

// ============================================
// Strava Integration Types
// ============================================

export interface StravaStatus {
  connected: boolean;
  athlete_id?: string;
  athlete_name?: string;
  scope?: string;
}

export interface StravaPreferences {
  auto_update_description: boolean;
  include_score: boolean;
  include_summary: boolean;
  include_link: boolean;
  use_extended_format: boolean;
  custom_footer?: string;
}

export interface StravaAuthResponse {
  authorization_url: string;
  state: string;
}

export interface StravaCallbackRequest {
  code: string;
  scope?: string;
}

// ============================================
// Garmin Auto-Sync Configuration Types
// ============================================

export interface GarminSyncConfig {
  auto_sync_enabled: boolean;
  sync_frequency: 'daily' | 'weekly';
  initial_sync_days: number;
  incremental_sync_days: number;
}

export interface GarminSyncHistoryEntry {
  id: string;
  sync_type: 'manual' | 'scheduled';
  started_at: string;
  completed_at?: string;
  status: 'running' | 'completed' | 'failed';
  activities_synced: number;
  error_message?: string;
}

// ============================================
// Run/Walk Interval Types (Couch-to-5K style)
// ============================================

export interface RunWalkInterval {
  runSeconds: number;
  walkSeconds: number;
  repetitions: number;
}

export interface RunWalkTemplate {
  id: string;
  name: string;
  runSec: number;
  walkSec: number;
  reps: number;
  description: string;
  weekNumber?: number;
}

export interface RunWalkSession {
  id: string;
  template?: string;
  intervals: RunWalkInterval;
  startedAt: string;
  completedAt?: string;
  actualDurationSec: number;
  completedIntervals: number;
  paused: boolean;
}

export type RunWalkPhase = 'run' | 'walk' | 'idle';

export interface RunWalkTimerState {
  phase: RunWalkPhase;
  currentInterval: number;
  timeRemaining: number;
  totalElapsed: number;
  isRunning: boolean;
  isPaused: boolean;
  isComplete: boolean;
}

// ============================================
// Mileage Cap Types (10% Rule)
// ============================================

export type MileageCapStatus = 'safe' | 'warning' | 'near_limit' | 'exceeded';

export interface MileageCapData {
  currentWeekKm: number;
  previousWeekKm: number;
  weeklyLimitKm: number;
  remainingKm: number;
  isExceeded: boolean;
  percentageUsed: number;
  status: MileageCapStatus;
  recommendation: string;
  baseKm: number;
  allowedIncreaseKm: number;
  currentWeekStart: string;
  previousWeekStart: string;
}

export interface PlannedRunCheckData {
  plannedKm: number;
  currentWeekKm: number;
  projectedTotalKm: number;
  weeklyLimitKm: number;
  wouldExceed: boolean;
  excessKm: number;
  safeDistanceKm: number;
  suggestion: string;
}

export interface WeeklyMileageData {
  weekStart: string;
  weekEnd: string;
  totalKm: number;
  runCount: number;
  avgRunKm: number;
  longestRunKm: number;
}

export interface WeeklyComparisonData {
  currentWeek: WeeklyMileageData;
  previousWeek: WeeklyMileageData;
  changePct: number;
  changeKm: number;
}

export interface TenPercentRuleInfo {
  title: string;
  description: string;
  benefits: string[];
  tips: string[];
}

// Mileage cap status colors
export const MILEAGE_CAP_COLORS: Record<MileageCapStatus, {
  bg: string;
  text: string;
  fill: string;
  border: string;
}> = {
  safe: {
    bg: 'bg-green-500/10',
    text: 'text-green-400',
    fill: '#22c55e',
    border: 'border-green-500/30',
  },
  warning: {
    bg: 'bg-yellow-500/10',
    text: 'text-yellow-400',
    fill: '#eab308',
    border: 'border-yellow-500/30',
  },
  near_limit: {
    bg: 'bg-orange-500/10',
    text: 'text-orange-400',
    fill: '#f97316',
    border: 'border-orange-500/30',
  },
  exceeded: {
    bg: 'bg-red-500/10',
    text: 'text-red-400',
    fill: '#ef4444',
    border: 'border-red-500/30',
  },
};

// ============================================
// User Preferences Types (Beginner Mode)
// ============================================

export type IntensityScale = 'hr' | 'rpe' | 'pace';

export interface UserPreferences {
  user_id: string;
  beginner_mode_enabled: boolean;
  beginner_mode_start_date: string | null;
  show_hr_metrics: boolean;
  show_advanced_metrics: boolean;
  preferred_intensity_scale: IntensityScale;
  weekly_mileage_cap_enabled: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface UpdatePreferencesRequest {
  beginner_mode_enabled?: boolean;
  show_hr_metrics?: boolean;
  show_advanced_metrics?: boolean;
  preferred_intensity_scale?: IntensityScale;
  weekly_mileage_cap_enabled?: boolean;
}

export interface ToggleBeginnerModeResponse {
  beginner_mode_enabled: boolean;
  message: string;
}

export interface BeginnerModeStatus {
  enabled: boolean;
  days_in_beginner_mode: number | null;
  start_date: string | null;
}
