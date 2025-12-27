// API client for Whoop Dashboard

const API_BASE = '/api';

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
    let errorData: { message?: string; code?: string; details?: Record<string, unknown> };
    try {
      errorData = await response.json();
    } catch {
      errorData = { message: response.statusText || 'Unknown error' };
    }
    throw new ApiClientError(
      errorData.message || 'Request failed',
      response.status,
      errorData.code,
      errorData.details
    );
  }
  return response.json();
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

export { ApiClientError };
