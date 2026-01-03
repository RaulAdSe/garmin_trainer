// API client for the Reactive Training App

import { authFetch, hasAuthToken } from './auth-fetch';

/**
 * Check if a user is authenticated (has a valid token).
 * Use this helper before making API calls that require authentication
 * to provide better UX (e.g., show login prompt instead of error).
 *
 * Note: This only checks for token presence, not validity.
 * Token validity is verified server-side.
 */
export function isAuthenticated(): boolean {
  return hasAuthToken();
}
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
  // Gamification
  AchievementWithStatus,
  UserAchievement,
  UserProgress,
} from './types';

// Call backend directly - CORS is configured for localhost:3000
const API_BASE = 'http://localhost:8000/api/v1';

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
      try {
        errorData = JSON.parse(text);
      } catch {
        errorData = { message: text || response.statusText || 'Unknown error' };
      }
    } catch {
      errorData = { message: response.statusText || 'Unknown error' };
    }

    // Log based on error type:
    // - 401: silent (expected when not logged in)
    // - 403: warn level (authorization issue)
    // - 5xx: error level (server errors)
    // - others: error level
    if (response.status === 401) {
      // 401 is expected behavior when not authenticated - no logging needed
    } else if (response.status === 403) {
      console.warn('[API] Forbidden:', response.status, errorData);
    } else {
      console.error('[API] Error details:', response.status, errorData);
    }

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
  const url = `${API_BASE}/workouts/${queryString ? `?${queryString}` : ''}`;

  const response = await authFetch(url);
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
  const response = await authFetch(`${API_BASE}/workouts/${workoutId}`);
  const activity = await handleResponse<ActivityResponse>(response);
  return transformActivityToWorkout(activity);
}

export async function getWorkoutAnalysis(workoutId: string): Promise<WorkoutAnalysis | null> {
  try {
    const response = await authFetch(`${API_BASE}/analysis/workout/${workoutId}`);
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

  const response = await authFetch(`${API_BASE}/analysis/workout/${request.workoutId}`, {
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

      const response = await authFetch(url, {
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

  const response = await authFetch(url);
  return handleResponse<PaginatedResponse<PlanSummary>>(response);
}

// Get a single plan by ID with all details
export async function getPlan(planId: string): Promise<TrainingPlan> {
  const response = await authFetch(`${API_BASE}/plans/${planId}`);
  return handleResponse<TrainingPlan>(response);
}

// Get a specific week from a plan
export async function getPlanWeek(
  planId: string,
  weekNumber: number
): Promise<TrainingWeek> {
  const response = await authFetch(`${API_BASE}/plans/${planId}/weeks/${weekNumber}`);
  return handleResponse<TrainingWeek>(response);
}

// Create a new plan (basic creation without AI generation)
export async function createPlan(
  request: CreatePlanRequest
): Promise<TrainingPlan> {
  const response = await authFetch(`${API_BASE}/plans`, {
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
  const response = await authFetch(`${API_BASE}/plans/generate`, {
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
      const response = await authFetch(`${API_BASE}/plans/generate/stream`, {
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
  const response = await authFetch(`${API_BASE}/plans/${planId}`, {
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
  const response = await authFetch(`${API_BASE}/plans/${planId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: 'Delete failed' }));
    throw new ApiClientError(errorData.message, response.status);
  }
}

// Activate a plan
export async function activatePlan(planId: string): Promise<TrainingPlan> {
  const response = await authFetch(`${API_BASE}/plans/${planId}/activate`, {
    method: 'POST',
  });
  return handleResponse<TrainingPlan>(response);
}

// Pause a plan
export async function pausePlan(planId: string): Promise<TrainingPlan> {
  const response = await authFetch(`${API_BASE}/plans/${planId}/pause`, {
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
  const response = await authFetch(
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
    const response = await authFetch(`${API_BASE}/plans/active`);
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
  const response = await authFetch(`${API_BASE}/plans/${planId}/adapt`, {
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
  const response = await authFetch(`${API_BASE}/design/generate`, {
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
  const response = await authFetch(`${API_BASE}/design/workouts`, {
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
  const response = await authFetch(`${API_BASE}/design/workouts/${workoutId}`);
  return handleResponse<DesignedWorkout>(response);
}

// Update a designed workout
export async function updateDesignedWorkout(
  workoutId: string,
  workout: Partial<DesignedWorkout>
): Promise<DesignedWorkout> {
  const response = await authFetch(`${API_BASE}/design/workouts/${workoutId}`, {
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
  const response = await authFetch(`${API_BASE}/design/workouts/${workoutId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: 'Delete failed' }));
    throw new ApiClientError(errorData.message, response.status);
  }
}

// Get all designed workouts
export async function getDesignedWorkouts(): Promise<DesignedWorkout[]> {
  const response = await authFetch(`${API_BASE}/design/workouts`);
  return handleResponse<DesignedWorkout[]>(response);
}

// Export workout as FIT file (returns download URL)
export async function exportWorkoutAsFIT(
  workoutId: string
): Promise<FITExportResponse> {
  const response = await authFetch(`${API_BASE}/design/workouts/${workoutId}/export/fit`, {
    method: 'POST',
  });
  return handleResponse<FITExportResponse>(response);
}

// Download FIT file directly (returns blob)
export async function downloadWorkoutFIT(workoutId: string): Promise<Blob> {
  const response = await authFetch(
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
  const response = await authFetch(
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

  const response = await authFetch(url);
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

  const response = await authFetch(url);
  return handleResponse<ReadinessResponse>(response);
}

// Get fitness metrics history
export async function getFitnessMetrics(
  days: number = 30
): Promise<FitnessMetricsHistory> {
  const url = `${API_BASE}/athlete/fitness-metrics?days=${days}`;
  const response = await authFetch(url);
  return handleResponse<FitnessMetricsHistory>(response);
}

// Get VO2 Max trend
import type { VO2MaxTrend } from './types';

export async function getVO2MaxTrend(
  days: number = 90
): Promise<VO2MaxTrend> {
  const url = `${API_BASE}/athlete/vo2max-trend?days=${days}`;
  const response = await authFetch(url);
  return handleResponse<VO2MaxTrend>(response);
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

// Sync activities from Garmin Connect (legacy synchronous - may timeout on long syncs)
export async function syncGarminActivities(
  request: GarminSyncRequest
): Promise<GarminSyncResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/garmin/sync`, {
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
  } catch (error) {
    console.error('[API] Network error during Garmin sync:', error);
    throw new ApiClientError(
      'Network error: Unable to connect to server. Please check if the backend is running.',
      0,
      'NETWORK_ERROR'
    );
  }
  return handleResponse<GarminSyncResponse>(response);
}

// ============ Async Sync (prevents timeouts) ============

export interface AsyncSyncResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface SyncJobStatus {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress_percent: number;
  current_step: string;
  activities_synced: number;
  fitness_days_synced: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  result: {
    synced_count: number;
    new_activities: number;
    updated_activities: number;
    fitness_days: number;
  } | null;
}

// Start async Garmin sync (returns immediately with job ID)
export async function syncGarminActivitiesAsync(
  request: GarminSyncRequest
): Promise<AsyncSyncResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/garmin/sync-async`, {
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
  } catch (error) {
    console.error('[API] Network error starting async sync:', error);
    throw new ApiClientError(
      'Network error: Unable to connect to server. Please check if the backend is running.',
      0,
      'NETWORK_ERROR'
    );
  }
  return handleResponse<AsyncSyncResponse>(response);
}

// Poll for sync job status
export async function getSyncJobStatus(jobId: string): Promise<SyncJobStatus> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/garmin/sync-status/${jobId}`);
  } catch (error) {
    console.error('[API] Network error polling sync status:', error);
    throw new ApiClientError(
      'Network error: Lost connection to server while checking sync status.',
      0,
      'NETWORK_ERROR'
    );
  }
  return handleResponse<SyncJobStatus>(response);
}

// Get Garmin sync status
export async function getGarminSyncStatus(): Promise<GarminSyncStatus> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/garmin/status`);
  } catch (error) {
    console.error('[API] Network error getting Garmin status:', error);
    throw new ApiClientError(
      'Network error: Unable to connect to server.',
      0,
      'NETWORK_ERROR'
    );
  }
  return handleResponse<GarminSyncStatus>(response);
}

// ============ Garmin Credentials Management ============

export interface SaveCredentialsResponse {
  success: boolean;
  message: string;
}

export interface CredentialStatusResponse {
  connected: boolean;
  garmin_user?: string;
  is_valid: boolean;
  last_validated?: string;
}

// Save Garmin credentials for future syncs
export async function saveGarminCredentials(
  email: string,
  password: string
): Promise<SaveCredentialsResponse> {
  try {
    const response = await authFetch(`${API_BASE}/garmin/credentials`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    // Return failure response for 401 instead of throwing
    if (response.status === 401) {
      return {
        success: false,
        message: 'Authentication required to save credentials. Please log in again.',
      };
    }

    return handleResponse<SaveCredentialsResponse>(response);
  } catch (error) {
    // Handle network errors with more detail
    const errorMessage = error instanceof Error
      ? `Network error: ${error.message}`
      : 'Failed to connect to server';
    console.error('saveGarminCredentials error:', error);
    return {
      success: false,
      message: errorMessage,
    };
  }
}

// Delete saved Garmin credentials
// Silently succeeds on 401 (nothing to delete if not authenticated)
export async function deleteGarminCredentials(): Promise<void> {
  const response = await authFetch(`${API_BASE}/garmin/credentials`, {
    method: 'DELETE',
  });

  // 401 means not authenticated - nothing to delete, treat as success
  if (response.status === 401) {
    return;
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: 'Delete failed' }));
    throw new ApiClientError(errorData.message, response.status);
  }
}

// Get Garmin credential status
// Returns a "not connected" response for 401 errors (expected when not logged in)
export async function getGarminCredentialStatus(): Promise<CredentialStatusResponse> {
  const response = await authFetch(`${API_BASE}/garmin/credentials/status`);

  // For credential status, 401 means "not connected" - don't throw
  if (response.status === 401) {
    return {
      connected: false,
      is_valid: false,
    };
  }

  return handleResponse<CredentialStatusResponse>(response);
}

// ============ Auto-Sync Configuration ============

import type {
  GarminSyncConfig,
  GarminSyncHistoryEntry,
} from './types';

// Get auto-sync configuration
// Returns default config for 401 errors (not logged in)
export async function getGarminSyncConfig(): Promise<GarminSyncConfig> {
  const response = await authFetch(`${API_BASE}/garmin/sync-config`);

  if (response.status === 401) {
    return {
      auto_sync_enabled: false,
      sync_frequency: 'daily',
      initial_sync_days: 30,
      incremental_sync_days: 7,
    };
  }

  return handleResponse<GarminSyncConfig>(response);
}

// Update auto-sync configuration
export async function updateGarminSyncConfig(
  config: Partial<GarminSyncConfig>
): Promise<GarminSyncConfig> {
  const response = await authFetch(`${API_BASE}/garmin/sync-config`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(config),
  });
  return handleResponse<GarminSyncConfig>(response);
}

// Get sync history
// Returns empty array for 401 errors (not logged in)
export async function getGarminSyncHistory(
  limit: number = 10
): Promise<GarminSyncHistoryEntry[]> {
  const response = await authFetch(`${API_BASE}/garmin/sync-history?limit=${limit}`);

  if (response.status === 401) {
    return [];
  }

  return handleResponse<GarminSyncHistoryEntry[]>(response);
}

// Trigger manual sync (using saved credentials)
export interface TriggerSyncResponse {
  job_id: string;
  status: string;
  message: string;
}

export async function triggerManualSync(): Promise<TriggerSyncResponse> {
  const response = await authFetch(`${API_BASE}/garmin/sync/trigger`, {
    method: 'POST',
  });
  return handleResponse<TriggerSyncResponse>(response);
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

  const response = await authFetch(url);
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

  const response = await authFetch(url);
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

  const response = await authFetch(url);
  return handleResponse<ExplainedWorkout>(response);
}

// Get explained plan session
export async function getExplainedSession(
  sessionId: string
): Promise<SessionExplanation> {
  const url = `${API_BASE}/explain/plan-session/${sessionId}`;
  const response = await authFetch(url);
  return handleResponse<SessionExplanation>(response);
}

// ============================================
// Chat endpoints
// ============================================

export interface ChatMessageRequest {
  message: string;
  conversation_id?: string;
  language?: string;  // Language code (en, es)
}

export interface ChatMessageResponse {
  response: string;
  data_sources: string[];
  intent: string;
  conversation_id: string;
  // Error handling fields (optional - only present when error occurred)
  error_type?: string;  // rate_limited, quota_exceeded, ai_unavailable, etc.
  has_error?: boolean;
}

export interface ChatSuggestionsResponse {
  questions: string[];
}

// Streaming chat event types
export type ChatStreamEventType = 'status' | 'tool_start' | 'tool_end' | 'token' | 'done' | 'error';

export interface ChatStreamEvent {
  type: ChatStreamEventType;
  content?: string;
  tool?: string;
  message?: string;
  tools_used?: string[];
  token_usage?: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
  trace_id?: string;
  error?: string;
}

// Human-friendly tool names for display
export const TOOL_DISPLAY_NAMES: Record<string, string> = {
  query_workouts: 'workouts',
  get_athlete_profile: 'profile',
  get_training_patterns: 'patterns',
  query_wellness: 'wellness',
  get_fitness_metrics: 'metrics',
  get_garmin_data: 'garmin',
  compare_workouts: 'compare',
  get_workout_details: 'details',
  create_training_plan: 'planning',
  design_workout: 'design',
  log_note: 'notes',
  set_goal: 'goals',
};

// Get display name for a tool
export function getToolDisplayName(toolName: string): string {
  return TOOL_DISPLAY_NAMES[toolName] || toolName;
}

// Send a chat message (non-streaming)
export async function sendChatMessage(
  request: ChatMessageRequest
): Promise<ChatMessageResponse> {
  const response = await authFetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: request.message,
      conversation_id: request.conversation_id,
      language: request.language || 'en',
    }),
  });
  return handleResponse<ChatMessageResponse>(response);
}

// Streaming chat callbacks
export interface ChatStreamCallbacks {
  onStatus?: (message: string) => void;
  onToolStart?: (tool: string, message: string) => void;
  onToolEnd?: (tool: string) => void;
  onToken?: (content: string) => void;
  onDone?: (toolsUsed: string[], tokenUsage?: ChatStreamEvent['token_usage']) => void;
  /** @param error - Error type from backend (rate_limited, quota_exceeded, etc.) or HTTP status */
  /** @param message - User-friendly error message from backend */
  onError?: (error: string, message?: string) => void;
}

// Send a chat message with streaming response
export function sendChatMessageStream(
  request: ChatMessageRequest,
  callbacks: ChatStreamCallbacks
): () => void {
  const controller = new AbortController();

  const fetchStream = async () => {
    try {
      const response = await authFetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({
          message: request.message,
          conversation_id: request.conversation_id,
          language: request.language || 'en',
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        // Map HTTP status to error types
        const statusErrorType = response.status === 429 ? 'rate_limited'
          : response.status === 503 ? 'ai_unavailable'
          : 'network_error';
        callbacks.onError?.(statusErrorType, errorText || `HTTP ${response.status}`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        callbacks.onError?.('network_error', 'No response body');
        return;
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
              const event: ChatStreamEvent = JSON.parse(data);

              switch (event.type) {
                case 'status':
                  callbacks.onStatus?.(event.message || 'Processing...');
                  break;
                case 'tool_start':
                  callbacks.onToolStart?.(event.tool || 'unknown', event.message || '');
                  break;
                case 'tool_end':
                  callbacks.onToolEnd?.(event.tool || 'unknown');
                  break;
                case 'token':
                  callbacks.onToken?.(event.content || '');
                  break;
                case 'done':
                  callbacks.onDone?.(event.tools_used || [], event.token_usage);
                  break;
                case 'error':
                  // Pass both error type and message to the callback
                  callbacks.onError?.(event.error || 'unknown', event.message);
                  break;
              }
            } catch {
              // Not JSON, treat as raw content
              callbacks.onToken?.(data);
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name !== 'AbortError') {
        // Network/fetch errors - pass error type and message
        callbacks.onError?.('network_error', error.message);
      }
    }
  };

  fetchStream();

  // Return abort function
  return () => controller.abort();
}

// Get chat suggestions
export async function getChatSuggestions(): Promise<ChatSuggestionsResponse> {
  const response = await authFetch(`${API_BASE}/chat/suggestions`);
  return handleResponse<ChatSuggestionsResponse>(response);
}

// Start a new conversation
export async function startNewConversation(): Promise<{ conversation_id: string }> {
  const response = await authFetch(`${API_BASE}/chat/new`, {
    method: 'POST',
  });
  return handleResponse<{ conversation_id: string }>(response);
}

// Clear conversation history
export async function clearConversation(
  conversationId: string
): Promise<{ cleared: boolean }> {
  const response = await authFetch(`${API_BASE}/chat/history/${conversationId}`, {
    method: 'DELETE',
  });
  return handleResponse<{ cleared: boolean }>(response);
}

// ============================================
// Gamification API
// ============================================

interface AchievementsListResponse {
  achievements: AchievementWithStatus[];
  total: number;
  unlocked: number;
}

export async function getAchievements(): Promise<AchievementWithStatus[]> {
  const response = await authFetch(`${API_BASE}/gamification/achievements`);
  const data = await handleResponse<AchievementsListResponse>(response);
  return data.achievements;
}

interface RecentAchievementsResponse {
  achievements: UserAchievement[];
  count: number;
}

export async function getRecentAchievements(): Promise<UserAchievement[]> {
  const response = await authFetch(`${API_BASE}/gamification/achievements/recent`);
  const data = await handleResponse<RecentAchievementsResponse>(response);
  return data.achievements;
}

export async function getUserProgress(): Promise<UserProgress> {
  const response = await authFetch(`${API_BASE}/gamification/progress`);
  return handleResponse<UserProgress>(response);
}

export async function checkAchievements(): Promise<UserAchievement[]> {
  const response = await authFetch(`${API_BASE}/gamification/check`, {
    method: 'POST',
  });
  return handleResponse<UserAchievement[]>(response);
}

// ============================================
// Strava Integration API
// ============================================

import type {
  StravaStatus,
  StravaPreferences,
  StravaAuthResponse,
} from './types';

// Get Strava connection status
export async function getStravaStatus(): Promise<StravaStatus> {
  const response = await authFetch(`${API_BASE}/strava/status`);
  return handleResponse<StravaStatus>(response);
}

// Get Strava OAuth authorization URL
export async function getStravaAuthUrl(): Promise<StravaAuthResponse> {
  const response = await authFetch(`${API_BASE}/strava/auth`);
  return handleResponse<StravaAuthResponse>(response);
}

// Handle Strava OAuth callback
export async function handleStravaCallback(
  code: string,
  scope?: string
): Promise<StravaStatus> {
  const response = await authFetch(`${API_BASE}/strava/callback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ code, scope }),
  });
  return handleResponse<StravaStatus>(response);
}

// Disconnect Strava account
export async function disconnectStrava(): Promise<void> {
  const response = await authFetch(`${API_BASE}/strava/disconnect`, {
    method: 'POST',
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: 'Disconnect failed' }));
    throw new ApiClientError(errorData.message, response.status);
  }
}

// Get Strava preferences
export async function getStravaPreferences(): Promise<StravaPreferences> {
  const response = await authFetch(`${API_BASE}/strava/preferences`);
  return handleResponse<StravaPreferences>(response);
}

// Update Strava preferences
export async function updateStravaPreferences(
  prefs: Partial<StravaPreferences>
): Promise<StravaPreferences> {
  const response = await authFetch(`${API_BASE}/strava/preferences`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(prefs),
  });
  return handleResponse<StravaPreferences>(response);
}

// Sync workout analysis to Strava
export interface StravaSyncResponse {
  success: boolean;
  message: string;
  strava_activity_id?: number;
  strava_url?: string;
}

export interface StravaSyncStatus {
  workout_id: string;
  synced: boolean;
  strava_activity_id?: number;
  strava_url?: string;
  synced_at?: string;
}

export async function syncWorkoutToStrava(
  workoutId: string
): Promise<StravaSyncResponse> {
  const response = await authFetch(`${API_BASE}/strava/sync/${workoutId}`, {
    method: 'POST',
  });
  return handleResponse<StravaSyncResponse>(response);
}

// Get Strava sync status for a workout
export async function getStravaSyncStatus(
  workoutId: string
): Promise<StravaSyncStatus> {
  const response = await authFetch(`${API_BASE}/strava/sync/${workoutId}/status`);
  return handleResponse<StravaSyncStatus>(response);
}

// ============================================
// Mileage Cap API (10% Rule)
// ============================================

import type {
  MileageCapData,
  PlannedRunCheckData,
  WeeklyComparisonData,
  TenPercentRuleInfo,
} from './types';

// Get current mileage cap status
export async function getMileageCap(
  targetDate?: string
): Promise<MileageCapData> {
  const params = new URLSearchParams();
  if (targetDate) params.set('target_date', targetDate);

  const queryString = params.toString();
  const url = `${API_BASE}/athlete/mileage-cap${queryString ? `?${queryString}` : ''}`;

  const response = await authFetch(url);
  return handleResponse<MileageCapData>(response);
}

// Check if a planned run would exceed the cap
export async function checkPlannedRun(
  plannedKm: number,
  targetDate?: string
): Promise<PlannedRunCheckData> {
  const params = new URLSearchParams();
  if (targetDate) params.set('target_date', targetDate);

  const queryString = params.toString();
  const url = `${API_BASE}/athlete/mileage-cap/check${queryString ? `?${queryString}` : ''}`;

  const response = await authFetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ plannedKm }),
  });
  return handleResponse<PlannedRunCheckData>(response);
}

// Get weekly mileage comparison
export async function getWeeklyComparison(
  targetDate?: string
): Promise<WeeklyComparisonData> {
  const params = new URLSearchParams();
  if (targetDate) params.set('target_date', targetDate);

  const queryString = params.toString();
  const url = `${API_BASE}/athlete/mileage-cap/comparison${queryString ? `?${queryString}` : ''}`;

  const response = await authFetch(url);
  return handleResponse<WeeklyComparisonData>(response);
}

// Get information about the 10% rule (no auth required)
export async function getTenPercentRuleInfo(): Promise<TenPercentRuleInfo> {
  const response = await fetch(`${API_BASE}/athlete/mileage-cap/info`);
  return handleResponse<TenPercentRuleInfo>(response);
}

// ============================================
// User Preferences API (Beginner Mode)
// ============================================

import type {
  UserPreferences,
  UpdatePreferencesRequest,
  ToggleBeginnerModeResponse,
  BeginnerModeStatus,
} from './types';

// Get user preferences
export async function getUserPreferences(): Promise<UserPreferences> {
  const response = await authFetch(`${API_BASE}/preferences`);

  // Return default preferences for 401 errors (not logged in)
  if (response.status === 401) {
    return {
      user_id: '',
      beginner_mode_enabled: false,
      beginner_mode_start_date: null,
      show_hr_metrics: true,
      show_advanced_metrics: true,
      preferred_intensity_scale: 'hr',
      weekly_mileage_cap_enabled: false,
    };
  }

  return handleResponse<UserPreferences>(response);
}

// Update user preferences
export async function updateUserPreferences(
  prefs: UpdatePreferencesRequest
): Promise<UserPreferences> {
  const response = await authFetch(`${API_BASE}/preferences`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(prefs),
  });
  return handleResponse<UserPreferences>(response);
}

// Toggle beginner mode
export async function toggleBeginnerMode(): Promise<ToggleBeginnerModeResponse> {
  const response = await authFetch(`${API_BASE}/preferences/toggle-beginner-mode`, {
    method: 'POST',
  });
  return handleResponse<ToggleBeginnerModeResponse>(response);
}

// Get beginner mode status
export async function getBeginnerModeStatus(): Promise<BeginnerModeStatus> {
  const response = await authFetch(`${API_BASE}/preferences/beginner-mode-status`);

  // Return default status for 401 errors (not logged in)
  if (response.status === 401) {
    return {
      enabled: false,
      days_in_beginner_mode: null,
      start_date: null,
    };
  }

  return handleResponse<BeginnerModeStatus>(response);
}

// ============================================
// Social Proof API (Emotional Engagement)
// ============================================

export interface PercentileRanking {
  category: string;
  percentile: number;
  label: string;
  value?: number;
  unit?: string;
}

export interface CommunityActivity {
  activityType: string;
  count: number;
  timeAgo: string;
}

export interface SocialProofStats {
  athletesTrainedToday: number;
  workoutsCompletedToday: number;
  athletesTrainingNow: number;
  pacePercentile?: PercentileRanking | null;
  streakPercentile?: PercentileRanking | null;
  levelPercentile?: PercentileRanking | null;
  recentActivity: CommunityActivity[];
  generatedAt: string;
  cacheTtlSeconds: number;
}

// Get social proof stats
export async function getSocialProofStats(): Promise<SocialProofStats> {
  const response = await authFetch(`${API_BASE}/emotional/social-proof`);

  // Return default stats for 401 errors (not logged in)
  if (response.status === 401) {
    return {
      athletesTrainedToday: 0,
      workoutsCompletedToday: 0,
      athletesTrainingNow: 0,
      pacePercentile: null,
      streakPercentile: null,
      levelPercentile: null,
      recentActivity: [],
      generatedAt: new Date().toISOString(),
      cacheTtlSeconds: 60,
    };
  }

  return handleResponse<SocialProofStats>(response);
}

// ============================================
// Personal Records (PR) API
// ============================================

import type {
  PRType,
  PersonalRecord,
  PRListResponse,
  RecentPRsResponse,
  PRSummary,
  PRComparisonResult,
  DetectPRsResponse,
} from './types';

export interface GetPersonalRecordsRequest {
  prType?: PRType;
  activityType?: string;
  limit?: number;
  offset?: number;
}

export interface DetectPRsRequest {
  workoutId: string;
}

// Get all personal records
export async function getPersonalRecords(
  request: GetPersonalRecordsRequest = {}
): Promise<PRListResponse> {
  const params = new URLSearchParams();

  if (request.prType) params.set('pr_type', request.prType);
  if (request.activityType) params.set('activity_type', request.activityType);
  if (request.limit) params.set('limit', String(request.limit));
  if (request.offset) params.set('offset', String(request.offset));

  const queryString = params.toString();
  const url = `${API_BASE}/emotional/prs${queryString ? `?${queryString}` : ''}`;

  const response = await authFetch(url);
  return handleResponse<PRListResponse>(response);
}

// Get recent personal records
export async function getRecentPRs(days: number = 30): Promise<RecentPRsResponse> {
  const response = await authFetch(`${API_BASE}/emotional/prs/recent?days=${days}`);
  return handleResponse<RecentPRsResponse>(response);
}

// Get PR summary
export async function getPRSummary(): Promise<PRSummary> {
  const response = await authFetch(`${API_BASE}/emotional/prs/summary`);
  return handleResponse<PRSummary>(response);
}

// Detect PRs in a workout
export async function detectPRs(request: DetectPRsRequest): Promise<DetectPRsResponse> {
  const response = await authFetch(`${API_BASE}/emotional/prs/detect`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ workoutId: request.workoutId }),
  });
  return handleResponse<DetectPRsResponse>(response);
}

// Compare workout to PRs
export async function compareToPRs(workoutId: string): Promise<PRComparisonResult> {
  const response = await authFetch(`${API_BASE}/emotional/prs/compare/${workoutId}`);
  return handleResponse<PRComparisonResult>(response);
}

// ============================================
// Comeback Challenge API (Streak Recovery)
// ============================================

export interface ComebackChallenge {
  id: string;
  userId: string;
  triggeredAt: string;
  previousStreak: number;
  status: 'active' | 'completed' | 'expired' | 'cancelled';
  day1CompletedAt: string | null;
  day2CompletedAt: string | null;
  day3CompletedAt: string | null;
  xpMultiplier: number;
  bonusXpEarned: number;
  expiresAt: string | null;
  createdAt: string | null;
  daysCompleted: number;
  isComplete: boolean;
  isActive: boolean;
  nextDayToComplete: number | null;
}

export interface RecordComebackWorkoutResponse {
  success: boolean;
  challenge: ComebackChallenge | null;
  bonusXpEarned: number;
  totalXpEarned: number;
  challengeCompleted: boolean;
  message: string;
}

export interface ComebackChallengeHistoryResponse {
  challenges: ComebackChallenge[];
  total: number;
}

// Get active comeback challenge for current user
export async function getComebackChallenge(): Promise<ComebackChallenge | null> {
  const response = await authFetch(`${API_BASE}/emotional/comeback-challenge`);

  // Return null for 401 errors (not logged in)
  if (response.status === 401) {
    return null;
  }

  return handleResponse<ComebackChallenge | null>(response);
}

// Record a workout during comeback challenge (applies 1.5x XP multiplier)
export async function recordComebackWorkout(
  workoutId: string,
  baseXp: number = 25
): Promise<RecordComebackWorkoutResponse> {
  const response = await authFetch(`${API_BASE}/emotional/comeback-challenge/record`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ workoutId, baseXp }),
  });
  return handleResponse<RecordComebackWorkoutResponse>(response);
}

// Trigger a new comeback challenge (called when streak breaks)
export async function triggerComebackChallenge(
  previousStreak: number
): Promise<ComebackChallenge | null> {
  const response = await authFetch(`${API_BASE}/emotional/comeback-challenge/trigger`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ previousStreak }),
  });
  return handleResponse<ComebackChallenge | null>(response);
}

// Get comeback challenge history
export async function getComebackChallengeHistory(
  limit: number = 10
): Promise<ComebackChallengeHistoryResponse> {
  const response = await authFetch(`${API_BASE}/emotional/comeback-challenge/history?limit=${limit}`);

  // Return empty history for 401 errors (not logged in)
  if (response.status === 401) {
    return {
      challenges: [],
      total: 0,
    };
  }

  return handleResponse<ComebackChallengeHistoryResponse>(response);
}

// Cancel an active comeback challenge
export async function cancelComebackChallenge(
  challengeId: string
): Promise<ComebackChallenge | null> {
  const response = await authFetch(`${API_BASE}/emotional/comeback-challenge/${challengeId}/cancel`, {
    method: 'POST',
  });
  return handleResponse<ComebackChallenge | null>(response);
}

// ============================================
// Workout Comparison API
// ============================================

import type {
  ComparableWorkoutsResponse,
  NormalizedTimeSeries,
  WorkoutComparisonData,
  NormalizationMode,
} from '@/types/comparison';

/**
 * Get workouts comparable to the specified activity.
 */
export async function getComparableWorkouts(
  activityId: string,
  options: {
    limit?: number;
    workoutType?: string;
    dateStart?: string;
    dateEnd?: string;
    minDistance?: number;
    maxDistance?: number;
  } = {}
): Promise<ComparableWorkoutsResponse> {
  const params = new URLSearchParams();

  if (options.limit) params.set('limit', String(options.limit));
  if (options.workoutType) params.set('workout_type', options.workoutType);
  if (options.dateStart) params.set('date_start', options.dateStart);
  if (options.dateEnd) params.set('date_end', options.dateEnd);
  if (options.minDistance !== undefined) params.set('min_distance', String(options.minDistance));
  if (options.maxDistance !== undefined) params.set('max_distance', String(options.maxDistance));

  const queryString = params.toString();
  const url = `${API_BASE}/comparison/${activityId}/comparable${queryString ? `?${queryString}` : ''}`;

  const response = await authFetch(url);
  return handleResponse<ComparableWorkoutsResponse>(response);
}

/**
 * Get normalized time series data for an activity.
 */
export async function getNormalizedData(
  activityId: string,
  mode: NormalizationMode = 'percentage',
  sampleCount: number = 100
): Promise<NormalizedTimeSeries> {
  const params = new URLSearchParams();
  params.set('mode', mode);
  params.set('sample_count', String(sampleCount));

  const url = `${API_BASE}/comparison/${activityId}/normalized?${params.toString()}`;

  const response = await authFetch(url);
  return handleResponse<NormalizedTimeSeries>(response);
}

/**
 * Compare two workouts and get normalized overlay data.
 */
export async function compareWorkouts(
  primaryId: string,
  comparisonId: string,
  normalizationMode: NormalizationMode = 'percentage',
  sampleCount: number = 100
): Promise<WorkoutComparisonData> {
  const response = await authFetch(`${API_BASE}/comparison/${primaryId}/compare`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      comparison_id: comparisonId,
      normalization_mode: normalizationMode,
      sample_count: sampleCount,
    }),
  });
  return handleResponse<WorkoutComparisonData>(response);
}

// ============================================
// Race Pacing API
// ============================================

import type {
  PacingPlan,
  GeneratePacingPlanRequest,
  WeatherAdjustment,
  WeatherAdjustmentRequest,
  AvailableStrategiesResponse,
  RaceDistance,
} from './types';

/**
 * Generate a pacing plan for a race.
 */
export async function generatePacingPlan(
  request: GeneratePacingPlanRequest
): Promise<PacingPlan> {
  const response = await authFetch(`${API_BASE}/race/pacing-plan`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  return handleResponse<PacingPlan>(response);
}

/**
 * Calculate weather impact on pace.
 */
export async function calculateWeatherAdjustment(
  request: WeatherAdjustmentRequest
): Promise<WeatherAdjustment> {
  const response = await authFetch(`${API_BASE}/race/weather-adjustment`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  return handleResponse<WeatherAdjustment>(response);
}

/**
 * Get available pacing strategies and race distances.
 */
export async function getAvailableStrategies(): Promise<AvailableStrategiesResponse> {
  const response = await authFetch(`${API_BASE}/race/strategies`);
  return handleResponse<AvailableStrategiesResponse>(response);
}

/**
 * Quick pacing plan generator with minimal input.
 */
export async function getQuickPacingPlan(
  raceDistance: RaceDistance,
  targetTimeHours: number,
  targetTimeMinutes: number,
  targetTimeSeconds: number = 0,
  customDistanceKm?: number
): Promise<PacingPlan> {
  const params = new URLSearchParams();
  params.set('race_distance', raceDistance);
  params.set('target_time_hours', String(targetTimeHours));
  params.set('target_time_minutes', String(targetTimeMinutes));
  params.set('target_time_seconds', String(targetTimeSeconds));
  if (customDistanceKm !== undefined) {
    params.set('custom_distance_km', String(customDistanceKm));
  }

  const response = await authFetch(`${API_BASE}/race/quick-plan?${params.toString()}`);
  return handleResponse<PacingPlan>(response);
}

// ============================================
// Pattern Recognition API
// ============================================

import type {
  TimingAnalysis,
  TSBOptimalRange,
  FitnessPrediction,
  PerformanceCorrelations,
  PatternSummary,
} from '@/types/patterns';

/**
 * Get timing pattern analysis (best times/days to train).
 */
export async function getTimingAnalysis(
  days: number = 90
): Promise<TimingAnalysis> {
  const response = await authFetch(`${API_BASE}/patterns/timing?days=${days}`);
  return handleResponse<TimingAnalysis>(response);
}

/**
 * Get optimal TSB range for peak performance.
 */
export async function getTSBOptimalRange(
  days: number = 180
): Promise<TSBOptimalRange> {
  const response = await authFetch(`${API_BASE}/patterns/tsb-optimal?days=${days}`);
  return handleResponse<TSBOptimalRange>(response);
}

/**
 * Get peak fitness prediction.
 */
export async function getPeakFitnessPrediction(
  targetDate?: string,
  horizonDays: number = 90
): Promise<FitnessPrediction> {
  const params = new URLSearchParams();
  if (targetDate) params.set('target_date', targetDate);
  params.set('horizon_days', String(horizonDays));

  const response = await authFetch(`${API_BASE}/patterns/peak-prediction?${params.toString()}`);
  return handleResponse<FitnessPrediction>(response);
}

/**
 * Get performance correlations analysis.
 */
export async function getPerformanceCorrelations(
  days: number = 180
): Promise<PerformanceCorrelations> {
  const response = await authFetch(`${API_BASE}/patterns/correlations?days=${days}`);
  return handleResponse<PerformanceCorrelations>(response);
}

/**
 * Get combined pattern analysis summary.
 */
export async function getPatternSummary(
  days: number = 90
): Promise<PatternSummary> {
  const response = await authFetch(`${API_BASE}/patterns/summary?days=${days}`);
  return handleResponse<PatternSummary>(response);
}

// ============================================
// Recovery Module API
// ============================================

import type {
  RecoveryModuleResponse,
  SleepDebtResponse,
  HRVTrendResponse,
  RecoveryTimeResponse,
  RecoveryScoreResponse,
} from './types';

/**
 * Get complete recovery module data including sleep debt, HRV trend, and recovery time.
 */
export async function getRecoveryData(
  options: {
    targetDate?: string;
    includeSleepDebt?: boolean;
    includeHrvTrend?: boolean;
    includeRecoveryTime?: boolean;
    sleepTargetHours?: number;
  } = {}
): Promise<RecoveryModuleResponse> {
  const params = new URLSearchParams();

  if (options.targetDate) params.set('target_date', options.targetDate);
  if (options.includeSleepDebt !== undefined) params.set('include_sleep_debt', String(options.includeSleepDebt));
  if (options.includeHrvTrend !== undefined) params.set('include_hrv_trend', String(options.includeHrvTrend));
  if (options.includeRecoveryTime !== undefined) params.set('include_recovery_time', String(options.includeRecoveryTime));
  if (options.sleepTargetHours !== undefined) params.set('sleep_target_hours', String(options.sleepTargetHours));

  const queryString = params.toString();
  const url = `${API_BASE}/recovery/${queryString ? `?${queryString}` : ''}`;

  const response = await authFetch(url);

  // Return empty response for 401 (not logged in)
  if (response.status === 401) {
    return {
      success: false,
      error: 'Authentication required',
    };
  }

  return handleResponse<RecoveryModuleResponse>(response);
}

/**
 * Get 7-day rolling sleep debt analysis.
 */
export async function getSleepDebt(
  targetHours: number = 8.0,
  windowDays: number = 7
): Promise<SleepDebtResponse> {
  const params = new URLSearchParams();
  params.set('target_hours', String(targetHours));
  params.set('window_days', String(windowDays));

  const url = `${API_BASE}/recovery/sleep-debt?${params.toString()}`;
  const response = await authFetch(url);

  if (response.status === 401) {
    return {
      success: false,
      error: 'Authentication required',
    };
  }

  return handleResponse<SleepDebtResponse>(response);
}

/**
 * Get HRV trend analysis with rolling averages and coefficient of variation.
 */
export async function getHRVTrend(): Promise<HRVTrendResponse> {
  const response = await authFetch(`${API_BASE}/recovery/hrv-trend`);

  if (response.status === 401) {
    return {
      success: false,
      error: 'Authentication required',
    };
  }

  return handleResponse<HRVTrendResponse>(response);
}

/**
 * Get post-workout recovery time estimation.
 */
export async function getRecoveryTimeEstimate(
  workoutId?: string
): Promise<RecoveryTimeResponse> {
  const params = new URLSearchParams();
  if (workoutId) params.set('workout_id', workoutId);

  const queryString = params.toString();
  const url = `${API_BASE}/recovery/recovery-time${queryString ? `?${queryString}` : ''}`;

  const response = await authFetch(url);

  if (response.status === 401) {
    return {
      success: false,
      error: 'Authentication required',
    };
  }

  return handleResponse<RecoveryTimeResponse>(response);
}

/**
 * Get just the recovery score and status for dashboard widgets.
 */
export async function getRecoveryScore(): Promise<RecoveryScoreResponse> {
  const response = await authFetch(`${API_BASE}/recovery/score`);

  if (response.status === 401) {
    return {
      success: false,
      error: 'Authentication required',
    };
  }

  return handleResponse<RecoveryScoreResponse>(response);
}

// ============================================
// Running Economy API
// ============================================

/**
 * Get the most recent running economy metrics.
 */
export async function getCurrentEconomy(): Promise<any> {
  const response = await authFetch(`${API_BASE}/economy/current`);

  if (response.status === 401) {
    return {
      has_data: false,
      message: 'Authentication required',
    };
  }

  return handleResponse(response);
}

/**
 * Get running economy trend over time.
 */
export async function getEconomyTrend(days: number = 90): Promise<any> {
  const response = await authFetch(`${API_BASE}/economy/trend?days=${days}`);

  if (response.status === 401) {
    return {
      success: false,
      message: 'Authentication required',
    };
  }

  return handleResponse(response);
}

/**
 * Get cardiac drift analysis for a specific workout.
 */
export async function getCardiacDrift(workoutId: string): Promise<any> {
  const response = await authFetch(`${API_BASE}/economy/drift/${workoutId}`);

  if (response.status === 401) {
    return {
      success: false,
      message: 'Authentication required',
    };
  }

  return handleResponse(response);
}

/**
 * Get economy metrics by pace zone.
 */
export async function getPaceZonesEconomy(days: number = 90): Promise<any> {
  const response = await authFetch(`${API_BASE}/economy/zones?days=${days}`);

  if (response.status === 401) {
    return {
      success: false,
      message: 'Authentication required',
    };
  }

  return handleResponse(response);
}

// ============================================
// Safety Alerts API (ACWR Spike Detection)
// ============================================

import type {
  SafetyAlertsResponse,
  AcknowledgeAlertResponse,
  LoadAnalysisData,
  SpikeAnalysis,
  MonotonyStrainAnalysis,
} from './types';

export interface GetSafetyAlertsOptions {
  status?: 'active' | 'acknowledged' | 'resolved' | 'dismissed';
  severity?: 'info' | 'moderate' | 'critical';
  days?: number;
}

/**
 * Get safety alerts for the current user.
 */
export async function getSafetyAlerts(
  options: GetSafetyAlertsOptions = {}
): Promise<SafetyAlertsResponse> {
  const params = new URLSearchParams();

  if (options.status) params.set('status', options.status);
  if (options.severity) params.set('severity', options.severity);
  if (options.days) params.set('days', String(options.days));

  const queryString = params.toString();
  const url = `${API_BASE}/safety/alerts${queryString ? `?${queryString}` : ''}`;

  const response = await authFetch(url);

  // Return empty response for 401 errors (not logged in)
  if (response.status === 401) {
    return {
      alerts: [],
      total: 0,
      activeCount: 0,
      criticalCount: 0,
    };
  }

  return handleResponse<SafetyAlertsResponse>(response);
}

/**
 * Acknowledge a safety alert.
 */
export async function acknowledgeAlert(
  alertId: string
): Promise<AcknowledgeAlertResponse> {
  const response = await authFetch(`${API_BASE}/safety/alerts/${alertId}/acknowledge`, {
    method: 'POST',
  });
  return handleResponse<AcknowledgeAlertResponse>(response);
}

/**
 * Dismiss a safety alert.
 */
export async function dismissAlert(
  alertId: string
): Promise<AcknowledgeAlertResponse> {
  const response = await authFetch(`${API_BASE}/safety/alerts/${alertId}/dismiss`, {
    method: 'POST',
  });
  return handleResponse<AcknowledgeAlertResponse>(response);
}

/**
 * Get comprehensive training load analysis with spike detection.
 */
export async function getLoadAnalysis(): Promise<LoadAnalysisData> {
  const response = await authFetch(`${API_BASE}/safety/load-analysis`);
  return handleResponse<LoadAnalysisData>(response);
}

/**
 * Quick check for ACWR spike between two load values.
 */
export async function checkSpike(
  currentLoad: number,
  previousLoad: number
): Promise<SpikeAnalysis> {
  const params = new URLSearchParams();
  params.set('current_load', String(currentLoad));
  params.set('previous_load', String(previousLoad));

  const response = await authFetch(`${API_BASE}/safety/spike-check?${params.toString()}`);
  return handleResponse<SpikeAnalysis>(response);
}

/**
 * Get monotony and strain analysis for the current week.
 */
export async function getMonotonyStrain(): Promise<MonotonyStrainAnalysis> {
  const response = await authFetch(`${API_BASE}/safety/monotony`);
  return handleResponse<MonotonyStrainAnalysis>(response);
}

export { ApiClientError };
