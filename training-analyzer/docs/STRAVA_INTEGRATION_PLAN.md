# Strava Integration Implementation Plan

> **Feature Branch**: `workout-strava-integration`
> **Status**: Planning
> **Related Work**: Gamification (user retention) → Social aspect (Strava sharing)

---

## Executive Summary

This document outlines a comprehensive plan for integrating Strava with the Training Analyzer app. The goal is to enable automatic sharing of workout analysis to Strava, similar to how apps like **Runna** enrich Strava activity posts with analysis overlays and prefilled descriptions.

### Key Finding: Image Upload Limitation

**⚠️ CRITICAL**: The Strava public API **does not support uploading photos/images to activities**. This capability is restricted to official Strava partner applications (Zwift, TrainerRoad, Peloton, Runna, etc.).

To achieve Runna-style image overlays, you would need to:
1. Apply to become a Strava partner through [partners.strava.com](https://partners.strava.com/developers)
2. Or implement alternative approaches (detailed in Phase 4)

---

## 1. Current Architecture Assessment

### Existing Codebase Structure

The training-analyzer already has a well-designed integration foundation:

**Backend (FastAPI + Python):**
| File | Purpose |
|------|---------|
| `src/integrations/strava.py` | Existing Strava client skeleton with OAuth flow and activity models |
| `src/integrations/base.py` | OAuth credential handling, token refresh patterns |
| `src/services/analysis_service.py` | Workout analysis generation (LLM-powered) |
| `src/models/analysis.py` | Rich analysis data models (WorkoutAnalysisResult, ScoreCard, etc.) |

**Frontend (Next.js 16 + React 19):**
| File | Purpose |
|------|---------|
| `frontend/src/components/workouts/WorkoutAnalysis.tsx` | Analysis display component |
| `frontend/src/components/workouts/ScoreCard.tsx` | Visual score cards (radial charts) |

### Existing Strava Integration Code

The `strava.py` file already contains:
- `StravaOAuthFlow` class with OAuth 2.0 structure
- `StravaClient` class with activity read endpoints
- `StravaActivity`, `StravaSegment` models
- Placeholder implementations (marked "In production, use httpx")

---

## 2. Strava API Capabilities

### What IS Available (Public API)

| Capability | Endpoint | Scope Required |
|-----------|----------|----------------|
| OAuth Authentication | `/oauth/authorize`, `/oauth/token` | - |
| Read Activities | `GET /athlete/activities` | `activity:read` or `activity:read_all` |
| Get Activity Details | `GET /activities/{id}` | `activity:read` or `activity:read_all` |
| **Update Activity** | `PUT /activities/{id}` | `activity:write` |
| Activity Streams | `GET /activities/{id}/streams` | `activity:read` |
| Webhooks | `POST /push_subscriptions` | - |

### What is NOT Available (Partner-Only)

| Capability | Status |
|-----------|--------|
| Upload photos/images to activities | 🔒 Partner-only |
| Custom media overlays | 🔒 Partner-only |
| Bespoke activity thumbnails | 🔒 Partner-only |

### Rate Limits

- **15-minute limit**: 200 requests
- **Daily limit**: 2,000 requests
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Usage`

---

## 3. Implementation Phases

### Phase 1: OAuth Authentication

**Objective**: Implement full OAuth 2.0 flow for Strava

#### Backend Changes

**1. Update Config (`config.py`)**
```python
# Add Strava OAuth settings
strava_client_id: str = ""
strava_client_secret: str = ""
strava_redirect_uri: str = "http://localhost:3000/auth/strava/callback"
```

**2. Implement OAuth Routes (`api/routes/strava.py`)**
- `GET /api/v1/strava/auth` - Generate authorization URL
- `GET /api/v1/strava/callback` - Handle OAuth callback
- `POST /api/v1/strava/disconnect` - Revoke access
- `GET /api/v1/strava/status` - Check connection status

**3. Token Storage - New Database Table**
```sql
CREATE TABLE IF NOT EXISTS strava_credentials (
    user_id TEXT PRIMARY KEY DEFAULT 'default',
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    athlete_id TEXT,
    athlete_name TEXT,
    scope TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**4. Complete StravaOAuthFlow Implementation**
- Use `httpx` for actual HTTP requests
- Implement token refresh with 5-minute buffer
- Add proper error handling

#### Frontend Changes

**1. Strava Connect Page** (`app/[locale]/settings/strava/page.tsx`)
- "Connect to Strava" button
- Connection status display
- Disconnect option

**2. OAuth Callback Handler** (`app/[locale]/auth/strava/callback/page.tsx`)
- Process authorization code
- Display success/error state
- Redirect to settings

---

### Phase 2: Activity Sync via Webhooks

**Objective**: Real-time notification when user completes an activity on Strava

#### Webhook Implementation

**1. Webhook Subscription Endpoints**

Create `/api/v1/strava/webhooks`:
- `GET` - Handle Strava validation challenge
- `POST` - Receive activity events

**2. Event Processing Flow**

```
[Strava Webhook Event]
    → [Validate subscription_id]
    → [Check aspect_type == "create" && object_type == "activity"]
    → [Queue background job]
    → [Return 200 OK within 2 seconds]
```

**3. Background Job Processing**

```python
async def process_strava_activity_webhook(event: dict):
    """Process incoming Strava activity webhook."""
    activity_id = event["object_id"]
    athlete_id = event["owner_id"]

    # 1. Get stored credentials for this athlete
    credentials = db.get_strava_credentials(athlete_id)

    # 2. Refresh token if needed
    if credentials.needs_refresh:
        credentials = await oauth.refresh_token(credentials)
        db.save_strava_credentials(credentials)

    # 3. Fetch full activity details from Strava
    client = StravaClient(credentials)
    activity = await client.get_activity(activity_id)

    # 4. Match with Garmin activity (by timestamp/distance)
    local_activity = match_garmin_activity(activity)

    # 5. Generate or retrieve analysis
    analysis = await get_or_generate_analysis(local_activity)

    # 6. Update Strava activity description
    await update_strava_description(client, activity_id, analysis)
```

**4. Activity Matching Logic**

Match Strava activities to local Garmin activities using:
- Start time (within 5-minute window)
- Activity type mapping
- Duration (within 2% tolerance)
- Distance (within 2% tolerance)

---

### Phase 3: Description Updates

**Objective**: Automatically update Strava activity descriptions with analysis

#### Update Activity Implementation

**1. Add updateActivity to StravaClient**

```python
async def update_activity(
    self,
    activity_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    gear_id: Optional[str] = None,
) -> StravaActivity:
    """Update an activity owned by the authenticated athlete."""
    data = {}
    if name:
        data["name"] = name
    if description:
        data["description"] = description
    if gear_id:
        data["gear_id"] = gear_id

    response = await self._request("PUT", f"/activities/{activity_id}", json_data=data)
    return StravaActivity.from_api_response(response)
```

**2. Description Formatting - Default Preset (Generic Workouts)**

The default preset prioritizes **simplicity and elegance**. Less is more on Strava - a clean message invites curiosity without overwhelming the feed.

```python
def format_strava_description_simple(analysis: WorkoutAnalysisResult, share_url: str) -> str:
    """Simple, attractive format for generic workouts."""
    score_emoji = "🟢" if analysis.overall_score >= 80 else "🟡" if analysis.overall_score >= 60 else "🔴"

    # One clean summary line (max 100 chars)
    summary = analysis.summary[:100].rstrip('.') if analysis.summary else "Great session"

    return f"""{score_emoji} {analysis.overall_score}/100 · {summary}

---
📊 Analyzed by Training Analyzer
🔗 {share_url}"""
```

**Default Output (Generic Workout):**
```
🟢 85/100 · Strong negative splits with heart rate in optimal zone throughout

---
📊 Analyzed by Training Analyzer
🔗 training-analyzer.app/s/abc123
```

This format is:
- **Scannable**: Score + one-liner visible at a glance
- **Non-intrusive**: Doesn't spam your friends' feeds
- **Actionable**: Link invites deeper exploration
- **Branded**: Subtle attribution builds awareness

#### Why This Works

| Element | Purpose |
|---------|---------|
| Color emoji (🟢🟡🔴) | Instant visual feedback |
| Score | The "headline" - shareable, comparable |
| One-liner | Context without overwhelming |
| Short link | Invites curiosity, drives engagement |

#### Extended Format (Optional)

Users can enable a more detailed format in preferences:

```
🟢 85/100 · Strong negative splits with heart rate in optimal zone

📈 Training Effect: 3.2 (Improving)
⏱️ Recovery: 24h

---
📊 Analyzed by Training Analyzer
🔗 training-analyzer.app/s/abc123
```

**3. User Preferences Table**

```sql
CREATE TABLE IF NOT EXISTS strava_preferences (
    user_id TEXT PRIMARY KEY DEFAULT 'default',
    auto_update_description BOOLEAN DEFAULT TRUE,
    include_score BOOLEAN DEFAULT TRUE,
    include_training_effect BOOLEAN DEFAULT TRUE,
    include_recovery BOOLEAN DEFAULT TRUE,
    include_summary BOOLEAN DEFAULT TRUE,
    include_insights BOOLEAN DEFAULT TRUE,
    custom_footer TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

### Phase 4: Alternative Image Sharing Solutions

Since direct image upload is not available via public API, implement alternatives:

#### Option A: Shareable Link with OG Image (Recommended)

**1. Create Share Page** (`app/[locale]/share/[workoutId]/page.tsx`)
- Public page with workout analysis visualization
- OpenGraph meta tags with dynamic image
- When link is shared, shows analysis card preview

**2. Dynamic OG Image Generation**

Using `@vercel/og` or `satori`:

```typescript
// app/api/og/workout/[id]/route.tsx
import { ImageResponse } from '@vercel/og';

export async function GET(request: Request, { params }) {
  const analysis = await fetchAnalysis(params.id);

  return new ImageResponse(
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      background: 'linear-gradient(to br, #1a1a2e, #0a0a0e)',
      width: '1200px',
      height: '630px',
      padding: '40px',
    }}>
      {/* Render score cards, summary, etc. */}
    </div>,
    { width: 1200, height: 630 }
  );
}
```

**3. Include Link in Description**

```python
def format_strava_description_with_link(analysis, workout, share_url):
    description = format_strava_description(analysis, workout)
    description += f"\n\n🔗 Full Analysis: {share_url}"
    return description
```

#### Option B: Manual Share Feature

**1. Share Button in UI**
- Copies formatted text to clipboard
- Opens Strava activity edit page in new tab
- User pastes description manually

**2. Image Download**
- Generate analysis image on frontend (canvas/html2canvas)
- Allow user to download and manually add to Strava via mobile app

#### Option C: Apply for Strava Partnership (Long-term)

1. Visit [partners.strava.com/developers](https://partners.strava.com/developers)
2. Apply for partner program
3. Once approved, gain access to image upload APIs

---

### Phase 5: Frontend Integration

#### Settings Page - Strava Connection Card

```tsx
// components/settings/StravaConnection.tsx
export function StravaConnection() {
  const { data: status } = useQuery(['strava', 'status'], fetchStravaStatus);

  return (
    <Card>
      <CardHeader>
        <StravaLogo />
        <h3>Strava Integration</h3>
      </CardHeader>
      <CardContent>
        {status?.connected ? (
          <>
            <p>Connected as {status.athlete_name}</p>
            <PreferencesForm />
            <Button variant="destructive" onClick={disconnect}>
              Disconnect
            </Button>
          </>
        ) : (
          <Button onClick={connect}>
            Connect to Strava
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
```

#### Workout Analysis Share UI

Add share button to `WorkoutAnalysis.tsx`:
```tsx
<Button onClick={shareToStrava}>
  <StravaIcon />
  Share to Strava
</Button>
```

#### Activity List - Sync Status Badge

Show Strava sync status on each activity:
- 🟢 Green check: Synced to Strava
- 🟡 Yellow clock: Pending sync
- ⚪ Gray dash: Not on Strava

---

## 4. Database Schema Changes

### Complete Schema

```sql
-- Strava OAuth credentials storage
CREATE TABLE IF NOT EXISTS strava_credentials (
    user_id TEXT PRIMARY KEY DEFAULT 'default',
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    athlete_id TEXT,
    athlete_name TEXT,
    scope TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- User preferences for Strava integration
CREATE TABLE IF NOT EXISTS strava_preferences (
    user_id TEXT PRIMARY KEY DEFAULT 'default',
    auto_update_description BOOLEAN DEFAULT TRUE,
    include_score BOOLEAN DEFAULT TRUE,
    include_training_effect BOOLEAN DEFAULT TRUE,
    include_recovery BOOLEAN DEFAULT TRUE,
    include_summary BOOLEAN DEFAULT TRUE,
    include_insights BOOLEAN DEFAULT TRUE,
    custom_footer TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Activity mapping (local activity <-> Strava activity)
CREATE TABLE IF NOT EXISTS strava_activity_sync (
    local_activity_id TEXT PRIMARY KEY,
    strava_activity_id INTEGER NOT NULL,
    sync_status TEXT DEFAULT 'pending',  -- pending, synced, failed
    last_synced_at TEXT,
    description_updated BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Webhook subscription management
CREATE TABLE IF NOT EXISTS strava_webhook_subscription (
    id INTEGER PRIMARY KEY,
    subscription_id INTEGER NOT NULL,
    callback_url TEXT NOT NULL,
    verify_token TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_strava_sync_status ON strava_activity_sync(sync_status);
CREATE INDEX IF NOT EXISTS idx_strava_activity ON strava_activity_sync(strava_activity_id);
```

---

## 5. Privacy and User Consent

### Data Handling Requirements

1. **Explicit Consent**: Users must explicitly connect Strava
2. **Scope Transparency**: Show exactly what permissions are requested
3. **Easy Disconnect**: One-click disconnection
4. **Data Deletion**: Clear all Strava-related data on disconnect

### OAuth Scopes Needed

```python
STRAVA_SCOPES = [
    "read",              # Read public segments, activities
    "activity:read_all", # Read all activities (including private)
    "activity:write",    # Update activity descriptions
]
```

### User Consent Flow

1. Show explanation of what data will be accessed
2. List all permissions being requested
3. Explain automatic description updates
4. Allow granular control of what's shared

---

## 6. Technical Architecture

### Data Flow Diagram

```
┌─────────────────────┐
│   User Completes    │
│   Workout (Garmin)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     ┌─────────────────────┐
│   Garmin Connect    │────▶│   Training Analyzer │
│   API Sync          │     │   Database          │
└─────────────────────┘     └──────────┬──────────┘
                                       │
                            ┌──────────▼──────────┐
                            │   Analysis Service  │
                            │   (LLM Analysis)    │
                            └──────────┬──────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           │                           │                           │
           ▼                           ▼                           ▼
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   Strava Webhook    │     │   Activity Matcher  │     │   Description       │
│   (Activity Create) │────▶│   (Timestamp/Dist)  │────▶│   Updater           │
└─────────────────────┘     └─────────────────────┘     └──────────┬──────────┘
                                                                    │
                                                                    ▼
                                                        ┌─────────────────────┐
                                                        │   Strava API        │
                                                        │   PUT /activities   │
                                                        └─────────────────────┘
```

### API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/strava/auth` | Get OAuth authorization URL |
| GET | `/api/v1/strava/callback` | Handle OAuth callback |
| POST | `/api/v1/strava/disconnect` | Revoke Strava access |
| GET | `/api/v1/strava/status` | Check connection status |
| GET | `/api/v1/strava/preferences` | Get user preferences |
| PUT | `/api/v1/strava/preferences` | Update preferences |
| GET | `/api/v1/strava/webhooks` | Handle webhook validation |
| POST | `/api/v1/strava/webhooks` | Receive webhook events |
| POST | `/api/v1/strava/sync/{activity_id}` | Manually sync activity |
| GET | `/api/v1/share/{workout_id}` | Get shareable link |

---

## 7. Testing Strategy

### Unit Tests

- OAuth flow (token exchange, refresh)
- Activity matching algorithm
- Description formatting
- Webhook event parsing

### Integration Tests

- Full OAuth flow with mock Strava API
- Webhook subscription and event handling
- Activity update flow

### E2E Tests

- Connect Strava account
- Complete workout and verify sync
- Update preferences and verify behavior

---

## 8. Deployment Considerations

### Environment Variables

```bash
# Strava OAuth
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REDIRECT_URI=https://yourapp.com/auth/strava/callback
STRAVA_WEBHOOK_VERIFY_TOKEN=random_secure_string

# App URLs
APP_BASE_URL=https://yourapp.com
```

### Webhook Requirements

1. **HTTPS Required**: Strava only sends webhooks to HTTPS endpoints
2. **SSL Certificate**: Must be valid (not self-signed)
3. **Response Time**: Must respond within 2 seconds
4. **Retry Handling**: Strava retries up to 3 times on failure

### Scaling Considerations

- Use background job queue for webhook processing
- Implement rate limit tracking
- Cache Strava API responses where appropriate
- Monitor API usage vs. daily limits

---

## 9. Milestones

| Phase | Deliverables |
|-------|--------------|
| **Phase 1** | Full OAuth authentication flow, token storage |
| **Phase 2** | Webhook-based real-time activity detection |
| **Phase 3** | Automatic description enrichment |
| **Phase 4** | OG images for shareable links |
| **Phase 5** | Settings UI, share buttons |
| **Phase 6** | Full test coverage, edge cases |

---

## 10. Limitations and Workarounds

### Cannot Upload Images (Public API)

| Approach | Effort | User Experience |
|----------|--------|-----------------|
| Dynamic OG images for share links | Medium | Good - preview shows when link shared |
| Manual download + upload via mobile | Low | Acceptable - extra steps required |
| Apply for Strava partnership | High | Best - native integration like Runna |

### Rate Limits

**Mitigation:**
- Cache activity data
- Batch webhook processing
- Implement exponential backoff

### Activity Matching

**Challenge:** Activities may not have exact timestamp match

**Solution:**
- Use fuzzy matching (5-min window)
- Fallback to manual linking UI

---

## 11. Key Files for Implementation

| File | Purpose |
|------|---------|
| `src/integrations/strava.py` | Complete OAuth and API client |
| `src/db/schema.py` | Add Strava-related tables |
| `src/api/routes/garmin.py` | Pattern reference for new routes |
| `src/models/analysis.py` | WorkoutAnalysisResult for description |
| `frontend/src/components/workouts/WorkoutAnalysis.tsx` | Add share UI |

---

## 12. Connection to Gamification

This Strava integration supports the broader gamification strategy:

| Gamification Element | Strava Integration |
|---------------------|-------------------|
| **Social Sharing** | Auto-post achievements to Strava |
| **Visibility** | Friends see your workout scores |
| **Accountability** | Public commitment to training |
| **Competition** | Compare scores with friends |
| **Streaks** | Share streak milestones |

The social aspect of Strava creates external motivation that complements the internal gamification system (XP, levels, achievements).

---

## 13. Workout Types: Generic vs Planned

The Strava description format will evolve based on **workout context**. We start with generic workouts (MVP), then expand to planned workouts for richer insights.

### Workout Type Detection

```
┌─────────────────────────────────────────────────────────────────┐
│                      Workout Completed                          │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │  Was this a planned       │
                    │  workout from the app?    │
                    └─────────────┬─────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 │                                 │
                 ▼                                 ▼
        ┌────────────────┐                ┌────────────────┐
        │  NO: Generic   │                │  YES: Planned  │
        │  Workout       │                │  Workout       │
        └───────┬────────┘                └───────┬────────┘
                │                                 │
                ▼                                 ▼
        ┌────────────────┐                ┌────────────────┐
        │  Simple Format │                │  Rich Format   │
        │  Score + Link  │                │  + Structure   │
        └────────────────┘                └────────────────┘
```

---

### Type 1: Generic Workouts (MVP - Start Here)

Any workout not linked to a planned session. This is the **default** for all activities.

**What we know:**
- Post-workout metrics (HR, pace, power, cadence)
- Garmin training effect & recovery
- LLM-generated analysis

**Default Format:**
```
🟢 85/100 · Strong negative splits with heart rate in optimal zone throughout

---
📊 Analyzed by Training Analyzer
🔗 training-analyzer.app/s/abc123
```

**Implementation:** Phase 1-3 (current plan)

---

### Type 2: Planned Workouts (Future)

Workouts the app **prescribed** - training plans, suggested sessions, coach recommendations.

**What we additionally know:**
- Target structure (warm-up, intervals, cool-down)
- Prescribed zones/paces/power
- Intended workout purpose
- Rest interval requirements

**Rich Format for Planned Workouts:**

```
🟢 88/100 · Nailed the tempo intervals

📋 Workout: 4x1km @ Tempo
✅ Structure: 4/4 intervals completed
🎯 Execution: 96% zone accuracy

Splits: 4:02 → 3:58 → 3:55 → 3:52 ✨

---
📊 Analyzed by Training Analyzer
🔗 training-analyzer.app/s/abc123
```

**Alternative - Structured Workout Examples:**

```
🟡 72/100 · Struggled on final intervals

📋 Workout: 6x800m @ VO2max
⚠️ Structure: 4/6 intervals in zone (dropped off)
📉 Interval 5-6: HR ceiling reached early

💡 Consider longer recovery or reduced volume next time

---
📊 Analyzed by Training Analyzer
🔗 training-analyzer.app/s/abc123
```

```
🟢 92/100 · Perfect long run execution

📋 Workout: Long Run (90min Z2)
✅ 94% time in Zone 2
📈 Negative split: 5:45 → 5:32/km
💪 Strong finish, low cardiac drift

---
📊 Analyzed by Training Analyzer
🔗 training-analyzer.app/s/abc123
```

---

### Additional Data for Planned Workouts

| Data Point | Source | Display |
|------------|--------|---------|
| Workout structure | Training plan | "4x1km @ Tempo" |
| Interval completion | Activity matching | "4/4 completed" |
| Zone accuracy | HR/pace/power vs target | "96% in zone" |
| Split progression | Lap data | "4:02 → 3:58 → 3:55" |
| Execution quality | Algorithm | "Perfect pacing" |
| Fatigue indicators | HR drift, pace fade | "Low cardiac drift" |
| Recovery compliance | Rest interval analysis | "Rest intervals respected" |

---

### Planned Workout Matching

To detect if a completed activity is a planned workout:

```python
def match_to_planned_workout(activity: Activity, planned_workouts: list[PlannedWorkout]) -> Optional[PlannedWorkout]:
    """Match a completed activity to a planned workout."""

    for planned in planned_workouts:
        # Check date (same day or within 1 day)
        if abs((activity.start_time.date() - planned.scheduled_date).days) > 1:
            continue

        # Check activity type
        if activity.type != planned.activity_type:
            continue

        # Check duration (within 20% of planned)
        if abs(activity.duration - planned.target_duration) / planned.target_duration > 0.2:
            continue

        # Structure matching (if intervals planned)
        if planned.has_intervals:
            interval_match = match_interval_structure(activity.laps, planned.intervals)
            if interval_match > 0.7:  # 70% structure match
                return planned
        else:
            return planned

    return None
```

---

### Database Extension for Planned Workouts

```sql
-- Planned workout templates
CREATE TABLE IF NOT EXISTS planned_workouts (
    id TEXT PRIMARY KEY,
    user_id TEXT DEFAULT 'default',
    scheduled_date DATE NOT NULL,
    activity_type TEXT NOT NULL,
    title TEXT NOT NULL,                    -- "4x1km @ Tempo"
    description TEXT,
    target_duration_seconds INTEGER,
    structure JSONB,                        -- intervals, zones, etc.
    source TEXT,                            -- 'manual', 'training_plan', 'ai_suggested'
    training_plan_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Link completed activities to planned workouts
CREATE TABLE IF NOT EXISTS workout_execution (
    activity_id TEXT PRIMARY KEY,
    planned_workout_id TEXT REFERENCES planned_workouts(id),
    structure_completion REAL,              -- 0.0 to 1.0
    zone_accuracy REAL,                     -- 0.0 to 1.0
    execution_notes JSONB,                  -- interval splits, zone compliance per segment
    matched_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

### Strava Format Selection Logic

```python
def get_strava_description(activity_id: str) -> str:
    """Generate appropriate Strava description based on workout type."""

    activity = get_activity(activity_id)
    analysis = get_analysis(activity_id)
    share_url = generate_share_url(activity_id)

    # Check if this was a planned workout
    execution = get_workout_execution(activity_id)

    if execution and execution.planned_workout_id:
        # Planned workout - use rich format
        planned = get_planned_workout(execution.planned_workout_id)
        return format_planned_workout_description(
            analysis=analysis,
            planned=planned,
            execution=execution,
            share_url=share_url
        )
    else:
        # Generic workout - use simple format
        return format_strava_description_simple(analysis, share_url)
```

---

### Roadmap: Generic → Planned

| Phase | Focus | Description Format |
|-------|-------|-------------------|
| **Now** | Generic workouts | Score + summary + link |
| **Next** | Manual workout tagging | User links activity to plan |
| **Later** | Auto-detection | Match activities to training plans |
| **Future** | AI workout suggestions | Full loop: suggest → execute → analyze → share |

---

## Next Steps

1. Create feature branch `workout-strava-integration`
2. Register app on [Strava Developer Portal](https://www.strava.com/settings/api)
3. Begin Phase 1: OAuth implementation
4. Set up development environment for webhook testing (ngrok/cloudflare tunnel)
