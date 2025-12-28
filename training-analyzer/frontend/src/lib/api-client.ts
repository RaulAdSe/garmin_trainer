// API client for the Reactive Training App

import type {
  Workout,
  WorkoutAnalysis,
  PaginatedResponse,
  WorkoutListRequest,
  AnalyzeWorkoutRequest,
  ApiError,
  TrainingPlan,
  PlanSummary,
  TrainingWeek,
  TrainingSession,
  CreatePlanRequest,
  GeneratePlanRequest,
  UpdatePlanRequest,
  UpdateSessionRequest,
  PlanListRequest,
  // Phase 3: Workout Design + Garmin Export
  DesignedWorkout,
  GenerateWorkoutRequest,
  GenerateWorkoutResponse,
  SaveWorkoutRequest,
  SaveWorkoutResponse,
  FITExportResponse,
  GarminExportResponse,
  // Phase 0: Athlete Context
  AthleteContext,
  ReadinessResponse,
  FitnessMetricsHistory,
} from './types';

const API_BASE = '/api/v1';

class ApiClientError extends Error {
  public code?: string;
  public details?: Record<string, unknown>;
  public status: number;

  constructor(message: string | undefined, status: number, code?: string, details?: Record<string, unknown>) {
    super(message || `API Error (${status})`);
    this.name = 'ApiClientError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: ApiError;
    try {
      const text = await response.text();
      console.error('[API] Error response body:', text);
      try {
        errorData = JSON.parse(text);
      } catch {
        errorData = { message: text || response.statusText || 'Unknown error' };
      }
    } catch {
      errorData = { message: response.statusText || 'Unknown error' };
    }
    console.error('[API] Error details:', response.status, errorData);
    throw new ApiClientError(
      errorData.message,
      response.status,
      errorData.code,
      errorData.details
    );
  }
  return response.json();
}

// API response for activities from the backend
interface ActivityResponse {
  id: string;
  userId: string;
  type: string;
  name: string;
  date: string;
  startTime: string;
  endTime: string;
  duration: number;
  distance: number | null;
  metrics: {
    avgHeartRate?: number;
    maxHeartRate?: number;
    avgPace?: number;
  };
  source: string;
}

// Transform ActivityResponse to Workout type
function transformActivityToWorkout(activity: ActivityResponse): Workout {
  // Handle potential null/undefined metrics
  const metrics = activity.metrics || {};

  return {
    id: activity.id,
    userId: activity.userId,
    type: activity.type as Workout['type'],
    name: activity.name,
    date: activity.date,
    startTime: activity.startTime,
    endTime: activity.endTime,
    duration: activity.duration,
    distance: activity.distance ?? undefined,
    metrics: {
      avgHeartRate: metrics.avgHeartRate ?? undefined,
      maxHeartRate: metrics.maxHeartRate ?? undefined,
      avgPace: metrics.avgPace ?? undefined,
    },
    source: activity.source as Workout['source'],
    createdAt: activity.date,
    updatedAt: activity.date,
  };
}

// Backend paginated response type
interface BackendPaginatedResponse {
  items: ActivityResponse[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// Workout endpoints
export async function getWorkouts(
  request: WorkoutListRequest = {}
): Promise<PaginatedResponse<Workout>> {
  const params = new URLSearchParams();

  // Server-side pagination
  const page = request.page || 1;
  const pageSize = request.pageSize || 10;
  params.set('page', String(page));
  params.set('pageSize', String(pageSize));

  const queryString = params.toString();
  const url = `${API_BASE}/workouts${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url);
  const data = await handleResponse<BackendPaginatedResponse>(response);

  // Transform activities to Workout type
  const workouts = data.items.map(transformActivityToWorkout);

  return {
    items: workouts,
    total: data.total,
    page: data.page,
    pageSize: data.pageSize,
    totalPages: data.totalPages,
  };
}

export async function getWorkout(workoutId: string): Promise<Workout> {
  const response = await fetch(`${API_BASE}/workouts/${workoutId}`);
  const activity = await handleResponse<ActivityResponse>(response);
  return transformActivityToWorkout(activity);
}

export async function getWorkoutAnalysis(workoutId: string): Promise<WorkoutAnalysis | null> {
  try {
    const response = await fetch(`${API_BASE}/analysis/workout/${workoutId}`);
    if (response.status === 404) {
      return null;
    }

    const wrapper = await handleResponse<AnalysisResponseWrapper>(response);

    // If no cached analysis exists, the backend returns success=false with an error message
    if (!wrapper.success || !wrapper.analysis) {
      return null;
    }

    return wrapper.analysis;
  } catch (error) {
    if (error instanceof ApiClientError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

// Backend response wrapper for analysis
interface AnalysisResponseWrapper {
  success: boolean;
  analysis: WorkoutAnalysis | null;
  error?: string;
  cached: boolean;
}

export async function analyzeWorkout(
  request: AnalyzeWorkoutRequest
): Promise<WorkoutAnalysis> {
  console.log('[API] analyzeWorkout called for:', request.workoutId);

  const response = await fetch(`${API_BASE}/analysis/workout/${request.workoutId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      include_context: request.includeContext ?? true,
      force_refresh: request.regenerate ?? false,
    }),
  });

  console.log('[API] analyzeWorkout response status:', response.status);

  const wrapper = await handleResponse<AnalysisResponseWrapper>(response);

  if (!wrapper.success || !wrapper.analysis) {
    console.error('[API] Analysis failed:', wrapper.error);
    throw new ApiClientError(
      wrapper.error || 'Analysis failed',
      response.status,
      'ANALYSIS_FAILED'
    );
  }

  return wrapper.analysis;
}

// Streaming analysis endpoint
export function analyzeWorkoutStream(
  request: AnalyzeWorkoutRequest,
  onChunk: (chunk: string) => void,
  onDone: (analysis: WorkoutAnalysis) => void,
  onError: (error: Error) => void
): () => void {
  const controller = new AbortController();

  const fetchStream = async () => {
    try {
      const url = `${API_BASE}/analysis/workout/${request.workoutId}?stream=true`;

      const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          },
          body: JSON.stringify({
            include_context: request.includeContext ?? true,
            force_refresh: request.regenerate ?? false,
          }),
          signal: controller.signal,
        }
      );

      if (!response.ok) {
        throw new ApiClientError(
          'Failed to start analysis stream',
          response.status
        );
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // Process SSE events
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);

            if (data === '[DONE]') {
              continue;
            }

            try {
              const parsed = JSON.parse(data);

              if (parsed.type === 'content') {
                onChunk(parsed.content);
              } else if (parsed.type === 'done') {
                onDone(parsed.analysis);
              } else if (parsed.type === 'error') {
                onError(new Error(parsed.error));
              }
            } catch {
              // Not JSON, treat as raw content
              onChunk(data);
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name !== 'AbortError') {
        onError(error);
      }
    }
  };

  fetchStream();

  // Return abort function
  return () => controller.abort();
}

// Health check
export async function healthCheck(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/health`);
  return handleResponse<{ status: string }>(response);
}

// ============================================
// Training Plan endpoints (Phase 2)
// ============================================

// Get all plans with optional filtering
export async function getPlans(
  request: PlanListRequest = {}
): Promise<PaginatedResponse<PlanSummary>> {
  const params = new URLSearchParams();

  if (request.page) params.set('page', String(request.page));
  if (request.pageSize) params.set('page_size', String(request.pageSize));
  if (request.status) params.set('status', request.status);
  if (request.sortBy) params.set('sort_by', request.sortBy);
  if (request.sortOrder) params.set('sort_order', request.sortOrder);

  const queryString = params.toString();
  const url = `${API_BASE}/plans${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url);
  return handleResponse<PaginatedResponse<PlanSummary>>(response);
}

// Get a single plan by ID with all details
export async function getPlan(planId: string): Promise<TrainingPlan> {
  const response = await fetch(`${API_BASE}/plans/${planId}`);
  return handleResponse<TrainingPlan>(response);
}

// Get a specific week from a plan
export async function getPlanWeek(
  planId: string,
  weekNumber: number
): Promise<TrainingWeek> {
  const response = await fetch(`${API_BASE}/plans/${planId}/weeks/${weekNumber}`);
  return handleResponse<TrainingWeek>(response);
}

// Create a new plan (basic creation without AI generation)
export async function createPlan(
  request: CreatePlanRequest
): Promise<TrainingPlan> {
  const response = await fetch(`${API_BASE}/plans`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  return handleResponse<TrainingPlan>(response);
}

// Generate a plan using AI
export async function generatePlan(
  request: GeneratePlanRequest
): Promise<TrainingPlan> {
  const response = await fetch(`${API_BASE}/plans/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  return handleResponse<TrainingPlan>(response);
}

// Streaming plan generation
export function generatePlanStream(
  request: GeneratePlanRequest,
  onProgress: (progress: { phase: string; message: string; percentage: number }) => void,
  onDone: (plan: TrainingPlan) => void,
  onError: (error: Error) => void
): () => void {
  const controller = new AbortController();

  const fetchStream = async () => {
    try {
      const response = await fetch(`${API_BASE}/plans/generate/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new ApiClientError(
          'Failed to start plan generation',
          response.status
        );
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);

            if (data === '[DONE]') {
              continue;
            }

            try {
              const parsed = JSON.parse(data);

              if (parsed.type === 'progress') {
                onProgress({
                  phase: parsed.phase,
                  message: parsed.message,
                  percentage: parsed.percentage,
                });
              } else if (parsed.type === 'done') {
                onDone(parsed.plan);
              } else if (parsed.type === 'error') {
                onError(new Error(parsed.error));
              }
            } catch {
              // Ignore parse errors
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name !== 'AbortError') {
        onError(error);
      }
    }
  };

  fetchStream();

  return () => controller.abort();
}

// Update a plan
export async function updatePlan(
  planId: string,
  request: UpdatePlanRequest
): Promise<TrainingPlan> {
  const response = await fetch(`${API_BASE}/plans/${planId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  return handleResponse<TrainingPlan>(response);
}

// Delete a plan
export async function deletePlan(planId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/plans/${planId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: 'Delete failed' }));
    throw new ApiClientError(errorData.message, response.status);
  }
}

// Activate a plan
export async function activatePlan(planId: string): Promise<TrainingPlan> {
  const response = await fetch(`${API_BASE}/plans/${planId}/activate`, {
    method: 'POST',
  });
  return handleResponse<TrainingPlan>(response);
}

// Pause a plan
export async function pausePlan(planId: string): Promise<TrainingPlan> {
  const response = await fetch(`${API_BASE}/plans/${planId}/pause`, {
    method: 'POST',
  });
  return handleResponse<TrainingPlan>(response);
}

// Update a session
export async function updateSession(
  planId: string,
  sessionId: string,
  request: UpdateSessionRequest
): Promise<TrainingSession> {
  const response = await fetch(
    `${API_BASE}/plans/${planId}/sessions/${sessionId}`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    }
  );
  return handleResponse<TrainingSession>(response);
}

// Mark a session as complete
export async function completeSession(
  planId: string,
  sessionId: string,
  workoutId?: string
): Promise<TrainingSession> {
  return updateSession(planId, sessionId, {
    completionStatus: 'completed',
    workoutId,
  });
}

// Skip a session
export async function skipSession(
  planId: string,
  sessionId: string,
  notes?: string
): Promise<TrainingSession> {
  return updateSession(planId, sessionId, {
    completionStatus: 'skipped',
    notes,
  });
}

// Get active plan (current plan being followed)
export async function getActivePlan(): Promise<TrainingPlan | null> {
  try {
    const response = await fetch(`${API_BASE}/plans/active`);
    if (response.status === 404) {
      return null;
    }
    return handleResponse<TrainingPlan>(response);
  } catch (error) {
    if (error instanceof ApiClientError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

// Adapt/regenerate remaining weeks of a plan
export async function adaptPlan(
  planId: string,
  reason?: string
): Promise<TrainingPlan> {
  const response = await fetch(`${API_BASE}/plans/${planId}/adapt`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ reason }),
  });
  return handleResponse<TrainingPlan>(response);
}

// ============================================
// Phase 3: Workout Design + Garmin Export endpoints
// ============================================

// Generate AI workout suggestions
export async function generateWorkoutSuggestions(
  request: GenerateWorkoutRequest
): Promise<GenerateWorkoutResponse> {
  const response = await fetch(`${API_BASE}/design/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      workout_type: request.workoutType,
      target_duration: request.targetDuration,
      target_distance: request.targetDistance,
      difficulty: request.difficulty,
      focus_area: request.focusArea,
      include_athlete_context: request.includeAthleteContext ?? true,
      number_of_suggestions: request.numberOfSuggestions ?? 3,
    }),
  });
  return handleResponse<GenerateWorkoutResponse>(response);
}

// Save a designed workout
export async function saveDesignedWorkout(
  request: SaveWorkoutRequest
): Promise<SaveWorkoutResponse> {
  const response = await fetch(`${API_BASE}/design/workouts`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  return handleResponse<SaveWorkoutResponse>(response);
}

// Get a designed workout by ID
export async function getDesignedWorkout(
  workoutId: string
): Promise<DesignedWorkout> {
  const response = await fetch(`${API_BASE}/design/workouts/${workoutId}`);
  return handleResponse<DesignedWorkout>(response);
}

// Update a designed workout
export async function updateDesignedWorkout(
  workoutId: string,
  workout: Partial<DesignedWorkout>
): Promise<DesignedWorkout> {
  const response = await fetch(`${API_BASE}/design/workouts/${workoutId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(workout),
  });
  return handleResponse<DesignedWorkout>(response);
}

// Delete a designed workout
export async function deleteDesignedWorkout(workoutId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/design/workouts/${workoutId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: 'Delete failed' }));
    throw new ApiClientError(errorData.message, response.status);
  }
}

// Get all designed workouts
export async function getDesignedWorkouts(): Promise<DesignedWorkout[]> {
  const response = await fetch(`${API_BASE}/design/workouts`);
  return handleResponse<DesignedWorkout[]>(response);
}

// Export workout as FIT file (returns download URL)
export async function exportWorkoutAsFIT(
  workoutId: string
): Promise<FITExportResponse> {
  const response = await fetch(`${API_BASE}/design/workouts/${workoutId}/export/fit`, {
    method: 'POST',
  });
  return handleResponse<FITExportResponse>(response);
}

// Download FIT file directly (returns blob)
export async function downloadWorkoutFIT(workoutId: string): Promise<Blob> {
  const response = await fetch(
    `${API_BASE}/design/workouts/${workoutId}/download/fit`
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: 'Download failed' }));
    throw new ApiClientError(errorData.message, response.status);
  }

  return response.blob();
}

// Export workout to Garmin Connect
export async function exportWorkoutToGarmin(
  workoutId: string
): Promise<GarminExportResponse> {
  const response = await fetch(
    `${API_BASE}/design/workouts/${workoutId}/export/garmin`,
    {
      method: 'POST',
    }
  );
  return handleResponse<GarminExportResponse>(response);
}

// Check Garmin Connect connection status
export async function checkGarminConnection(): Promise<{ connected: boolean; userId?: string }> {
  const response = await fetch(`${API_BASE}/garmin/status`);
  return handleResponse<{ connected: boolean; userId?: string }>(response);
}

// ============================================
// Phase 0: Athlete Context endpoints
// ============================================

// Get full athlete context
export async function getAthleteContext(
  targetDate?: string
): Promise<AthleteContext> {
  const params = new URLSearchParams();
  if (targetDate) params.set('target_date', targetDate);

  const queryString = params.toString();
  const url = `${API_BASE}/athlete/context${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url);
  return handleResponse<AthleteContext>(response);
}

// Get today's readiness
export async function getReadiness(
  targetDate?: string
): Promise<ReadinessResponse> {
  const params = new URLSearchParams();
  if (targetDate) params.set('target_date', targetDate);

  const queryString = params.toString();
  const url = `${API_BASE}/athlete/readiness${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url);
  return handleResponse<ReadinessResponse>(response);
}

// Get fitness metrics history
export async function getFitnessMetrics(
  days: number = 30
): Promise<FitnessMetricsHistory> {
  const url = `${API_BASE}/athlete/fitness-metrics?days=${days}`;
  const response = await fetch(url);
  return handleResponse<FitnessMetricsHistory>(response);
}

// ============================================
// Garmin Sync endpoints
// ============================================

export interface GarminSyncRequest {
  email: string;
  password: string;
  days?: number;
}

export interface SyncedActivity {
  id: string;
  name: string;
  type: string;
  date: string;
  distance_km: number | null;
  duration_min: number | null;
}

export interface GarminSyncResponse {
  success: boolean;
  synced_count: number;
  message: string;
  new_activities: number;
  updated_activities: number;
  activities: SyncedActivity[];
}

export interface GarminSyncStatus {
  garmin_connect_available: boolean;
  supported_activity_types: string[];
  max_sync_days: number;
  notes: string[];
}

// Sync activities from Garmin Connect
export async function syncGarminActivities(
  request: GarminSyncRequest
): Promise<GarminSyncResponse> {
  const response = await fetch(`${API_BASE}/garmin/sync`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: request.email,
      password: request.password,
      days: request.days ?? 30,
    }),
  });
  return handleResponse<GarminSyncResponse>(response);
}

// Get Garmin sync status
export async function getGarminSyncStatus(): Promise<GarminSyncStatus> {
  const response = await fetch(`${API_BASE}/garmin/status`);
  return handleResponse<GarminSyncStatus>(response);
}

// ============================================
// Activity Details endpoints (time series, GPS, splits)
// ============================================

import type { ActivityDetailsResponse } from '@/types/workout-detail';

// Get detailed activity data with time series, GPS, and splits
export async function getActivityDetails(
  activityId: string,
  forceRefresh: boolean = false
): Promise<ActivityDetailsResponse> {
  const params = new URLSearchParams();
  if (forceRefresh) params.set('force_refresh', 'true');

  const queryString = params.toString();
  const url = `${API_BASE}/workouts/${activityId}/details${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url);
  return handleResponse<ActivityDetailsResponse>(response);
}

// ============================================
// Explainability endpoints
// ============================================

import type {
  ExplainedReadiness,
  ExplainedWorkout,
  SessionExplanation,
} from './types';

// Get explained readiness breakdown
export async function getExplainedReadiness(
  targetDate?: string
): Promise<ExplainedReadiness> {
  const params = new URLSearchParams();
  if (targetDate) params.set('target_date', targetDate);

  const queryString = params.toString();
  const url = `${API_BASE}/explain/readiness${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url);
  return handleResponse<ExplainedReadiness>(response);
}

// Get explained workout recommendation
export async function getExplainedWorkoutRecommendation(
  targetDate?: string
): Promise<ExplainedWorkout> {
  const params = new URLSearchParams();
  if (targetDate) params.set('target_date', targetDate);

  const queryString = params.toString();
  const url = `${API_BASE}/explain/workout-recommendation${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url);
  return handleResponse<ExplainedWorkout>(response);
}

// Get explained plan session
export async function getExplainedSession(
  sessionId: string
): Promise<SessionExplanation> {
  const url = `${API_BASE}/explain/plan-session/${sessionId}`;
  const response = await fetch(url);
  return handleResponse<SessionExplanation>(response);
}

export { ApiClientError };
