# API Reference

This document describes the API endpoints available in the WHOOP Dashboard.

---

## Base URL

```
http://localhost:3000/api
```

---

## Endpoints

### GET /api/wellness/today

Fetches today's (or most recent available) wellness data with calculated recovery score and insights.

**Response:**

```typescript
{
  // Date of the data
  date: string;  // "2024-12-27"

  // Sleep data
  sleep: {
    total_sleep_hours: number;    // 7.25
    deep_sleep_pct: number;       // 18.5
    rem_sleep_pct: number;        // 22.3
    sleep_score: number | null;   // Garmin's sleep score
    sleep_efficiency: number;     // 91.2
    direction: DirectionIndicator | null;
  } | null;

  // HRV data
  hrv: {
    hrv_last_night_avg: number | null;  // 48
    hrv_weekly_avg: number | null;      // 45
    hrv_status: string | null;          // "BALANCED"
    direction: DirectionIndicator | null;
  } | null;

  // Stress/Body Battery data
  stress: {
    avg_stress_level: number | null;
    body_battery_charged: number | null;  // 72
    body_battery_drained: number | null;  // 58
    direction: DirectionIndicator | null;
  } | null;

  // Activity data
  activity: {
    steps: number;         // 8432
    steps_goal: number;    // 10000
    steps_pct: number;     // 84.3
    intensity_minutes: number | null;
    active_calories: number | null;
  } | null;

  // Resting heart rate
  resting_heart_rate: number | null;  // 52
  rhr_direction: DirectionIndicator | null;

  // Personal baselines
  baselines: Baselines;

  // Calculated recovery score (0-100)
  recovery: number;  // 78

  // Calculated strain score (0-21)
  strain: number;  // 12.5

  // Actionable insight
  insight: {
    decision: "GO" | "MODERATE" | "RECOVER";
    headline: string;     // "Push hard today"
    explanation: string;  // Detailed reasoning
    strain_target: [number, number];  // [14, 21]
    sleep_target: number; // 7.75 (hours needed tonight)
  };

  // Sleep debt (hours)
  sleep_debt: number;  // 1.25

  // Weekly summary with causality data
  weekly_summary: WeeklySummary;
}
```

---

### GET /api/wellness/history

Fetches historical wellness data for trend analysis.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | number | 14 | Number of days to fetch |

**Request:**

```
GET /api/wellness/history?days=14
```

**Response:**

```typescript
Array<{
  date: string;

  sleep: {
    total_hours: number | null;
    deep_pct: number;
    rem_pct: number;
    score: number | null;
    efficiency: number | null;
    direction: DirectionIndicator | null;
  } | null;

  hrv: {
    value: number | null;
    baseline: number | null;
    status: string | null;
    direction: DirectionIndicator | null;
  };

  strain: {
    value: number;  // Calculated strain 0-21
    body_battery_charged: number | null;
    body_battery_drained: number | null;
    stress_avg: number | null;
    active_calories: number | null;
    intensity_minutes: number | null;
    direction: DirectionIndicator | null;
  };

  activity: {
    steps: number;
    steps_goal: number;
  };

  resting_hr: number | null;
  rhr_direction: DirectionIndicator | null;

  // Calculated recovery score
  recovery: number;

  baselines: Baselines;

  // Only on first (most recent) day
  weekly_summary?: WeeklySummary;
}>
```

---

## Data Types

### DirectionIndicator

Shows how a metric compares to personal baseline:

```typescript
{
  direction: 'up' | 'down' | 'stable';
  change_pct: number;   // e.g., 12.5 for +12.5%
  baseline: number;     // 7-day average
  current: number;      // Today's value
}
```

### Baselines

Personal baselines calculated from historical data:

```typescript
{
  hrv_7d_avg: number | null;
  hrv_30d_avg: number | null;
  sleep_7d_avg: number | null;
  sleep_30d_avg: number | null;
  rhr_7d_avg: number | null;
  rhr_30d_avg: number | null;
  recovery_7d_avg: number | null;
  strain_7d_avg: number | null;
}
```

### WeeklySummary

Weekly aggregate data with causality insights:

```typescript
{
  // Recovery zone distribution
  green_days: number;   // 67-100% recovery
  yellow_days: number;  // 34-66% recovery
  red_days: number;     // 0-33% recovery

  // Averages
  avg_recovery: number;
  avg_strain: number;
  avg_sleep: number;
  total_sleep_debt: number;

  // Best/worst days
  best_day: string;   // Date with highest recovery
  worst_day: string;  // Date with lowest recovery

  // Causality engine results
  correlations: Correlation[];
  streaks: Streak[];
  trend_alerts: TrendAlert[];
}
```

### Correlation

Detected pattern in your data:

```typescript
{
  pattern_type: 'positive' | 'negative';
  category: string;       // 'sleep', 'activity', etc.
  title: string;          // "8k+ step days"
  description: string;    // "High step days correlate with +14% recovery"
  impact: number;         // 14.2 (percentage)
  confidence: number;     // 0.0-1.0
  sample_size: number;    // Days analyzed
}
```

### Streak

Active streak tracking:

```typescript
{
  name: 'green_days' | 'sleep_consistency' | 'step_goal';
  current_count: number;  // Current streak length
  best_count: number;     // Personal best
  is_active: boolean;     // Still going?
  last_date: string;      // Last day of streak
}
```

### TrendAlert

Multi-day trend detection:

```typescript
{
  metric: 'HRV' | 'Recovery' | 'Sleep' | 'Strain';
  direction: 'declining' | 'improving';
  days: number;           // Days in trend
  change_pct: number;     // Total change
  severity: 'warning' | 'concern' | 'positive';
}
```

---

## Error Responses

### 500 Internal Server Error

```json
{
  "error": "Failed to fetch wellness data"
}
```

Common causes:
- Database file not found
- SQLite connection error
- Missing tables

---

## Example Usage

### JavaScript/TypeScript

```typescript
// Fetch today's data
const response = await fetch('/api/wellness/today');
const data = await response.json();

console.log(`Recovery: ${data.recovery}%`);
console.log(`Decision: ${data.insight.decision}`);
console.log(`Strain: ${data.strain}/21`);

// Check recovery zone
const zone = data.recovery >= 67 ? 'green'
           : data.recovery >= 34 ? 'yellow'
           : 'red';

// Fetch history for trends
const historyResponse = await fetch('/api/wellness/history?days=14');
const history = await historyResponse.json();

history.forEach(day => {
  console.log(`${day.date}: Recovery ${day.recovery}%, Strain ${day.strain.value}`);
});
```

### cURL

```bash
# Today's data
curl http://localhost:3000/api/wellness/today

# Last 7 days
curl "http://localhost:3000/api/wellness/history?days=7"
```

---

## Recovery Zone Thresholds

The API calculates recovery zones based on the following thresholds:

| Zone | Score Range | Strain Target |
|------|-------------|---------------|
| GREEN | 67-100% | 14-21 |
| YELLOW | 34-66% | 8-14 |
| RED | 0-33% | 0-8 |

---

## Calculations

### Recovery Score

```
recovery = (hrv_score * 1.5 + sleep_score * 1.0 + body_battery * 1.0) / 3.5
```

Where:
- `hrv_score = min(100, max(0, (hrv / baseline) * 80 + 20))`
- `sleep_score = min(100, max(0, (hours / baseline) * 85 + 15))`
- `body_battery = body_battery_charged` (0-100)

### Strain Score

```
strain = min(21,
  min(8, steps / 2000) +
  min(8, body_battery_drained / 12) +
  min(5, intensity_minutes / 20)
)
```

### Sleep Target

```
tonight_target = base_need + strain_adjustment + debt_repayment
```

Where:
- `base_need = 7-day sleep average`
- `strain_adjustment = max(0, (yesterday_strain - 10) * 0.05)`
- `debt_repayment = total_debt / 7`

