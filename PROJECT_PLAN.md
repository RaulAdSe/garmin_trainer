# Garmin Workout Analyzer

Personal cardio training analysis system that pulls data from Garmin Connect, processes key running metrics, and delivers AI-powered insights and coaching feedback.

---

## Vision

Build a self-hosted, customizable alternative to paid running analysis tools (Runalyze Pro, Strava AI). Full control over metrics, analysis logic, and data storage. Start lean with n8n, evolve into a full app if the concept proves valuable.

---

## Core Requirements

| Requirement | Decision |
|-------------|----------|
| Data source | Garmin Connect API (via garth library) |
| Sync mode | Automated polling |
| Analysis scope | Workout-by-workout (phase 1), longitudinal trends (phase 2) |
| Output | Dashboard + coaching feedback |
| LLM | OpenAI (GPT-4o or GPT-4o-mini) |
| Stack | n8n (self-hosted) + n8n tables |
| Future stack | FastAPI + React (if validated) |

---

## Device: Garmin Forerunner 255

Available metrics from this device:
- ✅ Heart Rate (wrist optical)
- ✅ Pace / Speed
- ✅ Distance (GPS)
- ✅ Cadence
- ✅ Training Effect (aerobic/anaerobic)
- ✅ VO2max estimate
- ✅ Elevation gain/loss
- ✅ Stride length (calculated)
- ❌ Ground contact time (requires Running Dynamics Pod)
- ❌ Vertical oscillation (requires Running Dynamics Pod)
- ❌ Ground contact balance (requires Running Dynamics Pod)

---

## Workflow Configuration Pattern

All workflows use a **Config Set node** at the start for easy tuning:

```javascript
// Config Set Node - placed at start of each workflow
{
  // Garmin settings
  "garmin_email": "{{ $credentials.garminEmail }}",
  "garmin_password": "{{ $credentials.garminPassword }}",
  "activities_to_fetch": 10,           // per sync (1-100)
  "backfill_count": 100,               // initial historical load
  "polling_interval_minutes": 30,
  
  // HR Zones (customize to your thresholds)
  "hr_zones": {
    "z1_max": 125,   // Recovery
    "z2_max": 145,   // Aerobic/Easy
    "z3_max": 162,   // Tempo
    "z4_max": 175,   // Threshold
    "z5_max": 200    // VO2max
  },
  
  // Analysis settings
  "llm_model": "gpt-4o-mini",          // or "gpt-4o"
  "analysis_language": "en",           // or "es"
  
  // Activity filters
  "activity_types": ["running", "trail_running", "treadmill_running"]
}
```

This pattern means you can adjust any parameter without touching workflow logic.

---

## Metrics to Capture & Analyze

### Primary Metrics (from Garmin 255)
- **Pace**: overall, per-km splits, elevation-adjusted
- **Heart Rate**: avg, max, zones distribution, cardiac drift
- **Cadence**: avg, variability across workout
- **Distance & Duration**
- **Training Effect**: aerobic and anaerobic scores
- **VO2max**: current estimate

### Derived Analysis
- Pace vs HR efficiency (aerobic decoupling %)
- Fatigue detection (pace drop + HR rise in final splits)
- Zone compliance (did you stay in intended zone?)
- Cadence consistency (std deviation)
- Effort score (custom weighted metric)

---

## Project Stages

### Stage 0: Research & API Access
**Goal**: Confirm Garmin Connect API access path and data availability.

- [ ] Research Garmin Connect API options:
  - Official API (requires partner program, unlikely for personal use)
  - Garmin Health API (needs enterprise account)
  - **Garth library** (Python, reverse-engineered, commonly used)
  - **garminconnect** Python package
- [ ] Test authentication flow (OAuth or session-based)
- [ ] Pull a sample activity and inspect available fields
- [ ] Document rate limits and sync strategy (polling interval)

**Output**: Working Python script that fetches latest activity JSON.

---

### Stage 1: n8n Data Ingestion Workflows
**Goal**: Automated pipeline that detects new workouts and stores raw data, plus one-time backfill.

#### Workflow 1: `garmin-backfill` (run once)
```
[Manual Trigger] → [Config Set] → [Python: Fetch last N activities] → [Loop] → [n8n Table: raw_activities]
```
- Fetches historical activities (configurable, default 100)
- Run once to populate initial data
- Can re-run with different count if needed

#### Workflow 2: `garmin-sync` (scheduled)
```
[Schedule Trigger] → [Config Set] → [Python: Fetch recent] → [Filter: New only] → [n8n Table: raw_activities]
```
- Runs every 30 min (configurable)
- Only fetches last N activities (default 10)
- Skips any already in table

**Tasks**:
- [ ] Set up n8n credential storage for Garmin (email/password, stored securely)
- [ ] Create Python execution node using garth library
- [ ] Handle authentication + token refresh
- [ ] Create `raw_activities` table schema:
  - `activity_id` (PK, string)
  - `activity_type` (string)
  - `activity_name` (string)
  - `start_time` (datetime)
  - `distance_m` (number)
  - `duration_s` (number)
  - `avg_hr` (number)
  - `max_hr` (number)
  - `avg_cadence` (number)
  - `avg_pace_sec_per_km` (number)
  - `elevation_gain_m` (number)
  - `elevation_loss_m` (number)
  - `training_effect_aerobic` (number)
  - `training_effect_anaerobic` (number)
  - `vo2max` (number)
  - `calories` (number)
  - `raw_json` (text, full payload)
  - `synced_at` (datetime)
- [ ] Dedupe logic (skip if `activity_id` exists)
- [ ] Error handling + notifications on failure

**Output**: All Garmin activities (historical + new) in n8n table.

---

### Stage 2: Metrics Extraction & Enrichment
**Goal**: Parse raw data into structured, analysis-ready metrics.

#### Workflow: `activity-enrichment`
```
[Trigger: New row in raw_activities] → [Code Node: Extract metrics] → [n8n Table: enriched_activities]
```

**Tasks**:
- [ ] Create `enriched_activities` table:
  - All primary metrics (normalized units)
  - HR zone percentages (Z1-Z5)
  - Pace per km splits (array or JSON)
  - Cardiac drift % (first half vs second half HR at same pace)
  - Cadence std deviation
  - Elevation-adjusted pace
- [ ] Write extraction logic (JavaScript code node)
- [ ] Handle missing fields gracefully (not all runs have all metrics)

**Output**: Clean, structured data ready for AI analysis.

---

### Stage 3: AI Analysis & Coaching
**Goal**: Generate natural language insights and actionable feedback per workout.

#### Workflow: `ai-analysis`
```
[Trigger: New row in enriched_activities] → [Config Set] → [Build prompt] → [OpenAI Node] → [n8n Table: activity_analysis]
```

**Tasks**:
- [ ] Design analysis prompt template:
  ```
  You are an experienced running coach analyzing a workout for an experienced runner.
  
  Workout: {{ activity_name }}
  Date: {{ start_time }}
  Type: {{ activity_type }}
  
  Metrics:
  - Distance: {{ distance_km }} km
  - Duration: {{ duration_formatted }}
  - Avg Pace: {{ avg_pace }} /km
  - Avg HR: {{ avg_hr }} bpm | Max HR: {{ max_hr }} bpm
  - HR Zones: Z1: {{ z1_pct }}%, Z2: {{ z2_pct }}%, Z3: {{ z3_pct }}%, Z4: {{ z4_pct }}%, Z5: {{ z5_pct }}%
  - Cadence: {{ avg_cadence }} spm
  - Cardiac drift: {{ cardiac_drift }}%
  - Training Effect: {{ te_aerobic }} aerobic / {{ te_anaerobic }} anaerobic
  - Elevation: +{{ elevation_gain }}m / -{{ elevation_loss }}m
  
  Splits (pace per km):
  {{ splits_formatted }}
  
  Provide a structured analysis:
  1. **Summary**: 2-3 sentence overview of the workout
  2. **Execution**: What was done well
  3. **Observations**: Patterns or areas to note (pacing, HR response, fatigue signs)
  4. **Coaching tip**: One specific, actionable suggestion for improvement
  
  Be direct and technical. Skip generic advice.
  ```
- [ ] Create `activity_analysis` table:
  - `activity_id` (FK, string)
  - `summary` (text)
  - `execution` (text)
  - `observations` (text)
  - `coaching_tip` (text)
  - `raw_llm_response` (text)
  - `model_used` (string)
  - `tokens_used` (number)
  - `analyzed_at` (datetime)
- [ ] Configure OpenAI credentials in n8n
- [ ] Use model from config (gpt-4o-mini for cost, gpt-4o for depth)
- [ ] Test with 5-10 sample workouts, refine prompt

**Output**: Every workout gets AI-generated analysis stored.

---

### Stage 4: Dashboard MVP
**Goal**: Simple UI to view workouts and their analysis.

**Options** (pick one for MVP):
1. **n8n + embedded iframe**: Use n8n's table view directly (quick, ugly)
2. **Notion integration**: Push to Notion database, use Notion as UI
3. **Simple React app**: Fetch from n8n tables API, render cards
4. **Retool/Appsmith**: Low-code dashboard connected to n8n tables

**MVP Features**:
- [ ] List of recent workouts (date, type, distance, pace)
- [ ] Click to expand: full metrics + AI analysis
- [ ] Visual: HR zone pie chart, pace splits bar chart
- [ ] Filter by date range, activity type

**Output**: Usable interface to consume the analysis.

---

### Stage 5 (Future): Longitudinal Analysis
**Goal**: Trends over time, fitness progression, training load balance.

- Weekly/monthly summaries
- Fitness vs fatigue curves
- Pace at HR trends (aerobic efficiency over months)
- Training volume patterns
- Injury risk indicators (sudden load spikes)

*Deferred until workout-by-workout is validated.*

---

## Technical Notes

### Garmin API Access via Garth
Since Garmin doesn't offer a public API, we use **garth** (Python library):
- Handles OAuth-like session authentication
- Well-maintained, used by Home Assistant Garmin integration
- Supports activity list, activity details, and splits data

**n8n Integration Options**:
1. **Execute Command node**: Call external Python script
2. **Code node with child_process**: Spawn Python inline
3. **HTTP Request to microservice**: FastAPI wrapper around garth (cleaner, more reliable)

Recommended for n8n: Start with Execute Command node calling a Python script. If it gets complex, extract to microservice.

### n8n Tables (Self-Hosted)
- No row limits on self-hosted
- Simple key-value queries, no joins
- Good for prototyping, may need Postgres for complex queries later
- Tables: `raw_activities`, `enriched_activities`, `activity_analysis`

### LLM Cost Estimate (OpenAI)
- ~800 tokens per analysis (prompt + response)
- At 5 workouts/week: ~4,000 tokens/week
- GPT-4o-mini: ~$0.02/month
- GPT-4o: ~$0.40/month
- Negligible cost either way

### Python Dependencies
```
garth>=0.4.0
requests
```

---

## Resolved Decisions

| Question | Decision |
|----------|----------|
| Device | Garmin Forerunner 255 (no running dynamics) |
| HR zones | Configurable via Config Set node |
| LLM provider | OpenAI (GPT-4o-mini default, GPT-4o optional) |
| n8n hosting | Self-hosted (no limits) |
| Backfill | 100 activities initial load (configurable) |
| Config pattern | Config Set node at workflow start |

---

## Remaining Open Questions

- [ ] What are your current HR zones? (or should we pull from Garmin?)
- [ ] Do you want analysis in English or Spanish?
- [ ] Any specific coaching focus? (e.g., marathon training, speed work, base building)

---

## Immediate Next Steps

1. **Test garth library** — Python script that authenticates and fetches 5 activities
2. **Inspect activity JSON** — Confirm available fields from Garmin 255
3. **Set up n8n tables** — Create the 3 table schemas
4. **Build backfill workflow** — Fetch 100 historical activities
5. **Build sync workflow** — Scheduled polling for new activities
6. **Test with real data** — Validate data quality before analysis stage

---

## Success Criteria (Phase 1)

✅ 100 historical activities backfilled into n8n tables  
✅ New Garmin runs automatically appear within 30 minutes of sync  
✅ Each run gets structured AI analysis with actionable coaching tip  
✅ Can view workouts + analysis in a simple dashboard  
✅ All parameters (HR zones, fetch count, LLM model) configurable via Config Set  
✅ Total setup < 1 day of focused work  

---

## File Structure

```
garmin-workout-analyzer/
├── scripts/
│   ├── garmin_fetch.py      # Garth-based activity fetcher
│   └── test_connection.py   # Auth test script
├── n8n/
│   ├── workflows/
│   │   ├── garmin-backfill.json
│   │   ├── garmin-sync.json
│   │   ├── activity-enrichment.json
│   │   └── ai-analysis.json
│   └── tables/
│       ├── raw_activities.schema.json
│       ├── enriched_activities.schema.json
│       └── activity_analysis.schema.json
├── dashboard/               # Future: React dashboard
├── PROJECT_PLAN.md
└── README.md
```  
