# Garmin Health Dashboard (Oura-Style)

Personal health dashboard that mirrors Oura's approach: daily Readiness, Sleep, and Activity scores with trend visualization, AI insights, and optional per-workout coaching — all powered by Garmin Connect data.

---

## Vision

Build a self-hosted, Oura-style health dashboard using Garmin data. Track daily wellness metrics (sleep, stress, HRV, body battery), compute personalized scores, and get AI-powered insights. Full control over data, analysis logic, and visualization.

**Note**: This is a separate project direction from the Workout Analyzer (see PROJECT_PLAN.md). Both can coexist and share the Garmin data pipeline.

---

## Core Requirements

| Requirement | Decision |
|-------------|----------|
| Data source | Garmin Connect API (via garth library) |
| Primary metrics | Sleep, Stress, Body Battery, HRV, RHR, Training Readiness |
| Scoring | Three scores (0-100): Readiness, Sleep, Activity |
| Output | React/Next.js dashboard + AI daily insights |
| LLM | OpenAI (GPT-4o-mini) |
| Backend | n8n (self-hosted) + n8n tables |
| Secondary feature | Per-workout coaching (from Workout Analyzer) |

---

## Device: Garmin Forerunner 255

Available wellness metrics:
- ✅ Sleep tracking (stages, duration, efficiency)
- ✅ Body Battery (0-100 energy score)
- ✅ Stress tracking (all-day)
- ✅ HRV (from sleep)
- ✅ Resting Heart Rate
- ✅ Training Readiness (1-100)
- ✅ Steps, calories, intensity minutes
- ✅ SpO2 (pulse ox, if worn at night)
- ❌ Body temperature (not available via API)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         React/Next.js Dashboard                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │ Readiness│  │  Sleep   │  │ Activity │  │   Trends & Insights  │ │
│  │  Score   │  │  Score   │  │  Score   │  │      (Charts)        │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                   ▲
                                   │ REST API
                                   │
┌─────────────────────────────────────────────────────────────────────┐
│                          n8n Backend                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Data Sync    │  │ Score Calc   │  │ AI Analysis              │  │
│  │ (scheduled)  │  │ (on insert)  │  │ (daily summary)          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                   ▲
                                   │ garth library
                                   │
                    ┌──────────────────────────┐
                    │   Garmin Connect API      │
                    └──────────────────────────┘
```

---

## Three Core Scores

### 1. Readiness Score (0-100) — "How ready are you today?"

**Sources:**
- Training Readiness (Garmin's built-in)
- Body Battery (morning level)
- HRV status
- RHR deviation from baseline
- Previous day's stress
- Sleep quality

**Formula:**
```python
readiness = (
    training_readiness * 0.30 +
    body_battery_morning * 0.25 +
    hrv_score * 0.20 +
    rhr_deviation_score * 0.15 +
    sleep_contribution * 0.10
)
```

### 2. Sleep Score (0-100) — "How well did you sleep?"

**Sources:**
- Sleep duration (vs 7-9h target)
- Deep sleep % (target: 15-20%)
- REM sleep % (target: 20-25%)
- Sleep efficiency
- Sleep latency
- Disruptions

**Formula:**
```python
sleep = (
    duration_score * 0.25 +
    deep_sleep_score * 0.25 +
    rem_sleep_score * 0.20 +
    efficiency_score * 0.15 +
    latency_score * 0.10 +
    disruptions_score * 0.05
)
```

### 3. Activity Score (0-100) — "How active were you today?"

**Sources:**
- Steps (% of daily goal)
- Active calories
- Intensity minutes
- Workout contribution

**Formula:**
```python
activity = (
    steps_score * 0.30 +
    active_calories_score * 0.25 +
    intensity_minutes * 0.25 +
    workout_contribution * 0.20
)
```

---

## Project Stages

### Stage 0: Foundation ✅ (Shared with Workout Analyzer)
- [x] Garmin authentication via garth library
- [x] Token persistence working
- [x] Activity fetching scripts
- [x] n8n `raw_activities` table

### Stage 1: Wellness Data Pipeline
**Goal**: Fetch sleep, stress, body battery, HRV, RHR daily.

**API Endpoints:**
```python
/wellness-service/wellness/dailySleepData/{date}     # Sleep
/usersummary-service/usersummary/daily/{date}        # Stress, Body Battery, RHR, Steps
/hrv-service/hrv/{date}                              # HRV
/metrics-service/metrics/trainingreadiness/{date}    # Training Readiness
```

**Deliverables:**
- [ ] `wellness_fetch.py` — Fetch all wellness metrics for a date
- [ ] n8n table: `daily_wellness`
- [ ] n8n table: `sleep_details`
- [ ] Workflow: `wellness-sync` (scheduled, every 30 min)
- [ ] Workflow: `wellness-backfill` (one-time, 30-90 days)

### Stage 2: Score Calculation Engine
**Goal**: Compute Readiness, Sleep, Activity scores.

**Deliverables:**
- [ ] n8n table: `daily_scores`
- [ ] Workflow: `score-calculator` (triggered on new wellness data)
- [ ] Calibrated score weights

### Stage 3: AI Daily Insights
**Goal**: Generate natural language summaries and recommendations.

**Deliverables:**
- [ ] n8n table: `daily_insights`
- [ ] Workflow: `daily-insights` (OpenAI integration)
- [ ] Prompt template for coaching

### Stage 4: Web Dashboard
**Goal**: React/Next.js dashboard with scores, trends, insights.

**Tech Stack:**
- Next.js 14 (App Router)
- Tailwind CSS
- Recharts (visualizations)
- n8n Tables API

**Pages:**
- `/` — Today (scores + insight + quick metrics)
- `/sleep` — Sleep details and trends
- `/trends` — Multi-metric charts
- `/workouts` — Per-workout coaching (from Workout Analyzer)

### Stage 5: Polish (Future)
- Mobile responsiveness
- Dark mode
- Notifications
- Personalization

---

## Dashboard Wireframe

```
┌─────────────────────────────────────────────────────────────────┐
│  Garmin Health Dashboard                       [Today] [Trends] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  READINESS  │  │    SLEEP    │  │   ACTIVITY  │             │
│  │     78      │  │     85      │  │     62      │             │
│  │   ●●●●○     │  │   ●●●●●     │  │   ●●●○○     │             │
│  │   Good      │  │  Optimal    │  │   Fair      │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Today's Insight                                             ││
│  │ Your HRV is 12% above your 7-day average, suggesting        ││
│  │ good recovery. Body Battery recovered to 85% overnight.     ││
│  │ Consider a moderate intensity workout today.                ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │Body Battery│ │    HRV     │ │    RHR     │ │   Steps    │   │
│  │    85%     │ │   52 ms    │ │   58 bpm   │ │   8,432    │   │
│  │    ▲ 12    │ │    ▲ 6     │ │    ▼ 2     │ │   84%      │   │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## File Structure (Additions to existing project)

```
garmin-workout-analyzer/
├── scripts/
│   ├── garmin_fetch.py          # Existing: Activity fetcher
│   ├── wellness_fetch.py        # NEW: Wellness data
│   ├── api.py                   # FastAPI service
│   └── ...
│
├── n8n/
│   ├── workflows/
│   │   ├── garmin-backfill.json      # Existing
│   │   ├── garmin-sync.json          # Existing
│   │   ├── wellness-backfill.json    # NEW
│   │   ├── wellness-sync.json        # NEW
│   │   ├── score-calculator.json     # NEW
│   │   └── daily-insights.json       # NEW
│   └── tables/
│       ├── daily_wellness.schema.json    # NEW
│       ├── sleep_details.schema.json     # NEW
│       ├── daily_scores.schema.json      # NEW
│       ├── daily_insights.schema.json    # NEW
│       └── raw_activities.schema.json    # Existing
│
├── dashboard/                    # NEW: Next.js app
│   ├── app/
│   │   ├── page.tsx             # Today view
│   │   ├── sleep/page.tsx
│   │   ├── trends/page.tsx
│   │   └── workouts/page.tsx
│   ├── components/
│   │   ├── ScoreCard.tsx
│   │   ├── InsightPanel.tsx
│   │   ├── SleepChart.tsx
│   │   └── TrendChart.tsx
│   └── lib/
│       └── n8n-client.ts
│
├── PROJECT_PLAN.md              # Original: Workout Analyzer
├── OURA_DASHBOARD_PLAN.md       # This file: Health Dashboard
└── README.md
```

---

## Oura → Garmin Mapping

| Oura Metric | Garmin Equivalent | API Endpoint |
|-------------|-------------------|--------------|
| Readiness Score | Training Readiness + Body Battery | `/metrics-service/metrics/trainingreadiness` |
| Sleep Score | Sleep data (calculated) | `/wellness-service/wellness/dailySleepData` |
| Activity Score | Steps + Intensity Minutes | `/usersummary-service/usersummary/daily` |
| HRV | HRV from sleep | `/hrv-service/hrv` |
| Resting HR | RHR | `/usersummary-service/usersummary/daily` |
| Body Temperature | ❌ Not available | — |
| SpO2 | Pulse Ox | Sleep data payload |
| Stress | Stress score + Body Battery | `/usersummary-service/usersummary/daily` |

---

## Success Criteria

- [ ] Daily wellness data synced automatically
- [ ] Three computed scores updated daily
- [ ] AI generates daily insight with recommendation
- [ ] Dashboard displays today's scores and trends
- [ ] 30+ days historical data visualized
- [ ] Mobile-friendly responsive design

---

## AI Coaching Prompt Template

```
You are a personal health coach analyzing daily wellness data.

Date: {{ date }}

Scores:
- Readiness: {{ readiness_score }}/100
- Sleep: {{ sleep_score }}/100
- Activity: {{ activity_score }}/100

Key Factors:
- Body Battery: {{ body_battery_morning }}%
- HRV: {{ hrv }} ms ({{ hrv_trend }} vs 7-day avg)
- Resting HR: {{ rhr }} bpm
- Sleep: {{ sleep_duration }}h ({{ deep_sleep_pct }}% deep, {{ rem_pct }}% REM)
- Stress: {{ avg_stress }}%

Provide:
1. **Daily Summary** (2 sentences)
2. **Top Insight**: Most notable pattern
3. **Recommendation**: One actionable suggestion
4. **Training Guidance**: Hard, easy, or rest?

Be concise and direct. No generic advice.
```

---

## Immediate Next Steps

1. Create `wellness_fetch.py` script
2. Test wellness API endpoints with real data
3. Create n8n tables for wellness data
4. Build and test wellness-sync workflow
