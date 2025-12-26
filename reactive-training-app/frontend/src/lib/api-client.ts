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
} from './types';

const API_BASE = '/api/v1';

class ApiClientError extends Error {
  public code?: string;
  public details?: Record<string, unknown>;
  public status: number;

  constructor(message: string, status: number, code?: string, details?: Record<string, unknown>) {
    super(message);
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
      errorData = await response.json();
    } catch {
      errorData = { message: response.statusText || 'Unknown error' };
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

// Workout endpoints
export async function getWorkouts(
  request: WorkoutListRequest = {}
): Promise<PaginatedResponse<Workout>> {
  const params = new URLSearchParams();

  if (request.page) params.set('page', String(request.page));
  if (request.pageSize) params.set('page_size', String(request.pageSize));
  if (request.sortBy) params.set('sort_by', request.sortBy);
  if (request.sortOrder) params.set('sort_order', request.sortOrder);

  if (request.filters) {
    const { startDate, endDate, type, minDistance, maxDistance, search } = request.filters;
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    if (type) params.set('type', type);
    if (minDistance) params.set('min_distance', String(minDistance));
    if (maxDistance) params.set('max_distance', String(maxDistance));
    if (search) params.set('search', search);
  }

  const queryString = params.toString();
  const url = `${API_BASE}/workouts${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url);
  return handleResponse<PaginatedResponse<Workout>>(response);
}

export async function getWorkout(workoutId: string): Promise<Workout> {
  const response = await fetch(`${API_BASE}/workouts/${workoutId}`);
  return handleResponse<Workout>(response);
}

export async function getWorkoutAnalysis(workoutId: string): Promise<WorkoutAnalysis | null> {
  try {
    const response = await fetch(`${API_BASE}/workouts/${workoutId}/analysis`);
    if (response.status === 404) {
      return null;
    }
    return handleResponse<WorkoutAnalysis>(response);
  } catch (error) {
    if (error instanceof ApiClientError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function analyzeWorkout(
  request: AnalyzeWorkoutRequest
): Promise<WorkoutAnalysis> {
  const response = await fetch(`${API_BASE}/workouts/${request.workoutId}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      include_context: request.includeContext ?? true,
      regenerate: request.regenerate ?? false,
    }),
  });
  return handleResponse<WorkoutAnalysis>(response);
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
      const response = await fetch(
        `${API_BASE}/workouts/${request.workoutId}/analyze/stream`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          },
          body: JSON.stringify({
            include_context: request.includeContext ?? true,
            regenerate: request.regenerate ?? false,
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

        buffer += decoder.decode(value, { stream: true });

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

export { ApiClientError };
