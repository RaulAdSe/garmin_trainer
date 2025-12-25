# Garmin Workout Analyzer - Stage 0 Complete

**Date**: 2025-12-25
**Status**: Stage 0 Complete - Data ingestion working

---

## What Works Now

### garmin-backfill.json
- **Status**: Working
- **Trigger**: Manual (run on demand)
- **Fetches**: 100 activities
- **Flow**: Manual Trigger → Config → Fetch Activities → Normalize & Filter → Save to Table

### garmin-sync.json
- **Status**: Working
- **Trigger**: Schedule (every 30 min)
- **Fetches**: 10 activities
- **Flow**: Schedule Trigger → Config → Fetch Activities → Normalize & Filter → Save to Table

### Common Architecture
- **Auth**: Bearer token (hardcoded in Config node)
- **API**: `https://connectapi.garmin.com/activitylist-service/activities/search/activities`
- **Headers**: `Authorization: Bearer <token>`, `User-Agent: GCM-iOS-5.7.2.1`
- **Output**: Upserts to n8n table `i7a1sPDBgxZk6ehE`
- **Deduplication**: Uses `activity_id` as matching column - no duplicates

---

## The Authentication Problem

Garmin Connect doesn't offer simple API keys. Their auth flow:

```
User credentials
     ↓
SSO login (sso.garmin.com) ← cookies, CSRF tokens
     ↓
Ticket exchange
     ↓
Bearer token (24h lifespan)
     ↓
API calls to connectapi.garmin.com
```

**Why n8n can't do this natively:**
- HTTP Request nodes don't share cookies between requests
- Multi-step redirects with stateful session required
- CSRF token extraction needed

**Current solution:** Manually obtain Bearer token and paste into Config node.

---

## Authentication Options for Future

| Option | Effort | Maintenance | Best For |
|--------|--------|-------------|----------|
| **Bearer token** (current) | None | Refresh every 24h | One-time backfills |
| **Python API** (api.py ready) | Start service | Keep running | Scheduled automation |
| **Garmin Developer OAuth2** | Apply for access | Minimal once set up | Production use |

---

## Data Schema (n8n Table: i7a1sPDBgxZk6ehE)

| Field | Type | Description |
|-------|------|-------------|
| activity_id | number | Primary key (Garmin ID) |
| activity_type | string | running, trail_running, treadmill_running |
| activity_name | string | User-given name |
| start_time | datetime | Local start time |
| distance_m | number | Distance in meters |
| duration_s | number | Duration in seconds |
| avg_hr | number | Average heart rate |
| max_hr | number | Maximum heart rate |
| avg_cadence | number | Steps per minute |
| avg_pace_sec_per_km | number | Calculated pace |
| elevation_gain_m | number | Total ascent |
| elevation_loss_m | number | Total descent |
| training_effect_aerobic | number | Garmin metric (1-5) |
| training_effect_anaerobic | number | Garmin metric (1-5) |
| vo2max | number | Estimated VO2max |
| calories | number | Calories burned |
| raw_json | string | Full API response |
| synced_at | datetime | When we fetched it |

---

## File Structure

```
n8n-claude/
├── scripts/
│   ├── api.py              # FastAPI service (ready, not running)
│   ├── requirements.txt    # garth, fastapi, uvicorn
│   └── test_connection.py  # Auth test script
├── n8n/
│   └── workflows/
│       ├── garmin-backfill.json  # Working - manual, 100 activities
│       └── garmin-sync.json      # Working - scheduled, 10 activities
├── progress/
│   └── 2025-12-25_stage0-complete.md  # This file
└── .env                    # GARMIN_EMAIL, GARMIN_PASSWORD
```

---

## Quick Commands

```bash
# Get fresh Bearer token
cd /Users/rauladell/n8n-claude/scripts
python -c "import garth; garth.login('email', 'pass'); print(garth.client.oauth2_token.access_token)"

# Alternative: Start Python API for auto-refresh
uvicorn api:app --host 0.0.0.0 --port 8765
```

---

## What Comes Next

### Stage 1: Data Analysis Workflow
Build n8n workflow to analyze stored activities:
- Weekly/monthly summaries
- Trends (distance, pace, HR over time)
- Training load analysis
- Output to dashboard or notification

### Stage 2: Insights & Alerts
- Detect anomalies (unusually high HR, pace drops)
- Recovery recommendations based on training effect
- Weekly training summary via email/Slack

### Stage 3: AI Integration
- Connect to Claude API for natural language insights
- "How was my training this week?"
- Personalized coaching suggestions

### Stage 4: Dashboard
- Visual dashboard with charts
- Compare periods (this month vs last month)
- Goal tracking

---

## Lessons Learned

1. **Garmin SSO is complex** - Can't replicate in pure n8n HTTP nodes
2. **Bearer tokens work** - Simple solution, just need manual refresh
3. **Upsert prevents duplicates** - Safe to run both workflows anytime
4. **activityType varies** - Some activities return string, some return object with typeKey
5. **API endpoint matters** - Must use `connectapi.garmin.com`, not `connect.garmin.com`
