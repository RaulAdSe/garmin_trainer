# API Reference

This document describes the REST API endpoints available in trAIner.

---

## Base URL

```
http://localhost:8000/api/v1
```

---

## Authentication

Currently, no authentication is required (designed for local single-user use).

---

## Endpoints

### Garmin Integration

#### GET /garmin/oauth/start

Start the Garmin OAuth flow for authentication.

**Response:**
Redirects to Garmin Connect login page.

---

#### GET /garmin/oauth/callback

OAuth callback endpoint (called by Garmin after authorization).

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `code` | string | Authorization code from Garmin |

**Response:**
Redirects to frontend with success/error status.

---

#### POST /garmin/sync

Sync activities from Garmin Connect.

**Request Body:**

```typescript
{
  start_date?: string;   // YYYY-MM-DD (default: 1 year ago)
  end_date?: string;     // YYYY-MM-DD (default: today)
}
```

**Response:**

```typescript
{
  success: boolean;
  activities_synced: number;
  date_range: {
    start: string;
    end: string;
  };
  errors?: string[];
}
```

---

#### GET /garmin/status

Get Garmin connection status.

**Response:**

```typescript
{
  connected: boolean;
  last_sync?: string;      // ISO datetime
  activities_count?: number;
}
```

---

### Athlete Context

#### GET /athlete/context

Get the full athlete context for LLM injection. This aggregates all relevant data.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `target_date` | string | Date in YYYY-MM-DD format (default: today) |

**Response:**

```typescript
{
  fitness: {
    ctl: number;         // Chronic Training Load
    atl: number;         // Acute Training Load
    tsb: number;         // Training Stress Balance
    acwr: number;        // Acute:Chronic Workload Ratio
    risk_zone: string;   // 'optimal' | 'caution' | 'danger' | 'undertrained'
    daily_load: number;  // Today's training load
  };
  physiology: {
    max_hr: number;
    rest_hr: number;
    lthr: number;        // Lactate threshold HR
    age?: number;
    gender?: string;
    weight_kg?: number;
    vdot?: number;       // Estimated VDOT from goals
  };
  hr_zones: Array<{
    zone: number;        // 1-5
    name: string;        // 'Recovery', 'Aerobic', etc.
    min_hr: number;
    max_hr: number;
    description: string;
  }>;
  training_paces: Array<{
    name: string;           // 'Easy', 'Tempo', etc.
    pace_sec_per_km: number;
    pace_formatted: string; // '5:30/km'
    hr_zone: string;
    description: string;
  }>;
  race_goals: Array<{
    distance: string;          // '10K', 'Half Marathon'
    distance_km: number;
    target_time_formatted: string;
    target_pace_formatted: string;
    race_date: string;
    weeks_remaining: number;
  }>;
  readiness: {
    score: number;        // 0-100
    zone: string;         // 'green' | 'yellow' | 'red'
    recommendation: string;
  };
}
```

---

#### GET /athlete/readiness

Get today's readiness score and training recommendation.

**Response:**

```typescript
{
  date: string;
  readiness: {
    score: number;
    zone: string;
    factors: {
      hrv_score: number | null;
      sleep_score: number | null;
      body_battery: number | null;
      stress_score: number | null;
      training_load_score: number | null;
      recovery_days: number;
    };
  };
  recommendation: string;
  narrative: string;
}
```

---

#### GET /athlete/fitness-metrics

Get historical fitness metrics.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | number | 30 | Number of days of history |
| `period` | string | '30d' | Period: '14d', '30d', '90d' |

**Response:**

```typescript
{
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
```

---

### Workouts

#### GET /workouts

List workouts with pagination and filtering.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | number | 1 | Page number |
| `pageSize` | number | 10 | Items per page (max 100) |
| `type` | string | - | Filter by workout type |
| `startDate` | string | - | Start date (YYYY-MM-DD) |
| `endDate` | string | - | End date (YYYY-MM-DD) |
| `search` | string | - | Search workout names |

**Response:**

```typescript
{
  items: Array<Workout>;
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}
```

---

#### GET /workouts/{workout_id}

Get a specific workout with details.

**Response:**

```typescript
{
  id: string;
  date: string;
  activity_type: string;
  name: string;
  duration_sec: number;
  distance_m: number | null;
  avg_hr: number | null;
  max_hr: number | null;
  calories: number | null;
  hrss: number | null;
  pace_sec_per_km: number | null;
  elevation_gain_m: number | null;
  splits: Array<Split> | null;
  hr_zones_distribution: object | null;
  analysis: WorkoutAnalysis | null;
}
```

---

### Workout Analysis

#### POST /analysis/workout/{workout_id}

Analyze a workout with AI-powered insights.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `workout_id` | string | The workout ID to analyze |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `stream` | boolean | false | Stream the response as SSE |

**Request Body (optional):**

```typescript
{
  force_refresh?: boolean;    // Bypass cache
  include_similar?: boolean;  // Include similar workout comparison
}
```

**Response:**

```typescript
{
  success: boolean;
  analysis: {
    workout_id: string;
    summary: string;              // Brief summary (1-2 sentences)
    execution_rating: 'excellent' | 'good' | 'moderate' | 'needs_improvement';
    what_went_well: string[];     // List of positives
    areas_for_improvement: string[];
    how_it_fits: string;          // Context in training plan
    detailed_analysis: string;    // Full analysis text
    cached_at?: string;
  } | null;
  cached: boolean;
  error?: string;
}
```

---

#### GET /analysis/recent

Get recent workouts with quick AI summaries.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | number | 10 | Number of workouts (1-50) |
| `include_summaries` | boolean | true | Generate AI summaries |

**Response:**

```typescript
{
  workouts: Array<{
    workout_id: string;
    date: string;
    activity_type: string;
    duration_min: number;
    distance_km: number | null;
    avg_hr: number | null;
    hrss: number | null;
    ai_summary: string | null;
    execution_rating: string | null;
    has_full_analysis: boolean;
  }>;
  count: number;
}
```

---

#### POST /analysis/batch

Batch analyze multiple workouts.

**Request Body:**

```typescript
{
  workout_ids: string[];
  force_refresh?: boolean;
}
```

**Response:**

```typescript
{
  analyses: Array<AnalysisResponse>;
  total_count: number;
  success_count: number;
  cached_count: number;
  failed_count: number;
}
```

---

### Training Plans

#### POST /plans/generate

Generate a periodized training plan using AI.

**Request Body:**

```typescript
{
  goal: {
    race_date: string;       // YYYY-MM-DD
    distance: string;        // '5k' | '10k' | 'half' | 'marathon' | 'ultra'
    target_time: string;     // 'H:MM:SS' or 'MM:SS'
    race_name?: string;
    priority?: number;       // 1=A race, 2=B, 3=C
  };
  constraints?: {
    days_per_week?: number;           // 3-7, default 5
    long_run_day?: string;            // 'sunday'
    rest_days?: string[];             // ['monday', 'friday']
    max_weekly_hours?: number;        // 2-20, default 8
    max_session_duration_min?: number; // 30-240, default 150
    include_cross_training?: boolean;
    back_to_back_hard_ok?: boolean;
  };
  periodization_type?: string;  // 'linear' | 'reverse' | 'block'
}
```

**Response:**

```typescript
{
  id: string;
  name: string | null;
  description: string | null;
  goal: {
    race_date: string;
    distance: string;
    target_time_formatted: string;
    target_time_seconds: number;
  };
  periodization: string;
  total_weeks: number;
  peak_week: number;
  phases_summary: {
    base: number;
    build: number;
    peak: number;
    taper: number;
  };
  total_planned_load: number;
  weeks: Array<WeekPlan>;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}
```

---

#### GET /plans

List all training plans.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `active_only` | boolean | false | Only return active plans |
| `limit` | number | 50 | Max plans to return |
| `offset` | number | 0 | Pagination offset |

**Response:**

```typescript
{
  plans: Array<PlanSummary>;
  count: number;
  total: number;
  offset: number;
  limit: number;
}
```

---

#### GET /plans/active

Get the currently active training plan with current week info.

**Response:**

```typescript
{
  active_plan: PlanSummary | null;
  current_week: WeekData | null;
  weeks_completed: number;
  weeks_remaining: number;
  days_until_race: number;
}
```

---

#### POST /plans/{plan_id}/activate

Set a plan as the active training plan.

**Response:**

```typescript
{
  message: string;
  plan_id: string;
}
```

---

#### POST /plans/{plan_id}/adapt

AI-assisted plan adaptation based on recent performance.

**Request Body:**

```typescript
{
  reason?: string;           // Reason for adaptation
  force_recalculate?: boolean;
  weeks_to_adapt?: number[]; // Specific weeks to adapt
}
```

**Response:** Updated plan object.

---

### Workout Design

#### POST /workouts/design

Design a structured workout with AI.

**Request Body:**

```typescript
{
  workout_type: string;    // 'easy' | 'tempo' | 'intervals' | 'threshold' | 'long' | 'fartlek'
  duration_min?: number;   // 10-300
  target_load?: number;    // 0-500
  focus?: string;          // 'speed' | 'endurance' | 'threshold' | 'recovery'
  use_ai?: boolean;        // Use LLM for nuanced design
}
```

**Response:**

```typescript
{
  workout_id: string;
  name: string;
  description: string;
  sport: string;
  intervals: Array<{
    type: string;              // 'warmup' | 'work' | 'recovery' | 'cooldown' | 'rest'
    duration_sec: number | null;
    distance_m: number | null;
    target_pace_min: number | null;  // seconds per km
    target_pace_max: number | null;
    target_hr_min: number | null;
    target_hr_max: number | null;
    repetitions: number;
    notes: string | null;
    intensity_zone: string | null;
  }>;
  estimated_duration_min: number;
  estimated_distance_km: number | null;
  estimated_load: number | null;
  created_at: string | null;
}
```

---

#### GET /workouts/{workout_id}/fit

Download workout as Garmin FIT file.

**Response:** Binary FIT file download.

**Headers:**
```
Content-Type: application/vnd.ant.fit
Content-Disposition: attachment; filename="workout_xxx.fit"
```

---

#### Quick Workout Endpoints

| Endpoint | Default Duration | Description |
|----------|------------------|-------------|
| `POST /workouts/quick/easy` | 45 min | Easy recovery run |
| `POST /workouts/quick/tempo` | 50 min | Tempo run with warmup/cooldown |
| `POST /workouts/quick/intervals` | 55 min | VO2max interval session |
| `POST /workouts/quick/long` | 90 min | Long aerobic run |

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Race date must be at least 1 week away"
}
```

### 404 Not Found

```json
{
  "detail": "Workout abc123 not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Failed to generate plan: LLM error"
}
```

---

## Streaming Responses

The `/analysis/workout/{id}?stream=true` endpoint supports Server-Sent Events (SSE):

```javascript
const response = await fetch('/api/v1/analysis/workout/123?stream=true');
const reader = response.body.getReader();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = new TextDecoder().decode(value);
  console.log(text); // Incremental analysis text
}
```

---

## Rate Limiting

No rate limiting is currently implemented (local use only).

---

## OpenAPI Documentation

When the server is running, interactive API docs are available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
