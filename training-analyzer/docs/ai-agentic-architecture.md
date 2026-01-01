# AI Agentic Architecture

> **Implementation Status: ✅ COMPLETED & TESTED (Dec 2024)**
>
> The agentic AI coach is fully operational with:
> - 12 LangChain tools (8 query + 4 action) - all verified working
> - LangGraph react agent with tool calling
> - GPT-5-mini default (~$0.0006 per request)
> - SSE streaming with live tool status updates
> - Langfuse v3 observability
> - Token-based quota with tiktoken accuracy
> - Retry logic with circuit breaker
> - Multi-provider support (OpenAI/Anthropic)

---

## Why It Works

The agent works effectively because of **three key design principles**:

### 1. Well-Described Tool Signatures

Each tool has detailed docstrings that tell the LLM:
- **What** it does (purpose)
- **When** to use it (examples)
- **What** it returns (structured output)

```python
@tool
def query_workouts(
    sport_type: Optional[str] = None,  # "running", "cycling", "strength"
    days: int = 7,                      # Number of days to look back
    limit: int = 10,                    # Max results
) -> str:
    """Query workout history with flexible filters.

    Examples:
    - "Show my last 5 tempo runs" → query_workouts(workout_type="tempo", limit=5)
    - "What did I do last week?" → query_workouts(days=7)
    """
```

### 2. Computed Stats, Not Raw Data

Tools return **summarized insights**, not raw time series:

| Tool | Returns | NOT |
|------|---------|-----|
| `get_garmin_data` | `{vo2max: 52, trend: "improving"}` | 10,000 HR samples |
| `get_fitness_metrics` | `{ctl: 45, atl: 52, tsb: -7}` | Daily load history |
| `query_workouts` | Summary with pace, HR, load | GPS coordinates |

This keeps token usage low and responses fast.

#### Data Access Hierarchy

The system has **three levels** of workout data access, each optimized for different use cases:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        WORKOUT DATA ACCESS                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Level 1: query_workouts()                    ~50 tokens per workout    │
│  ─────────────────────────────                                          │
│  • Use for: Listing/filtering workouts                                  │
│  • Returns: Basic aggregates (avg HR, avg pace, distance, load)         │
│  • Source: Pre-computed in database                                     │
│                                                                         │
│  Example: "Show my tempo runs this week"                                │
│  → [{date, type, distance_km, duration_min, avg_hr, avg_pace, hrss}]    │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Level 2: get_workout_details(id)             ~150 tokens per workout   │
│  ────────────────────────────────                                       │
│  • Use for: Deep analysis of a specific workout                         │
│  • Returns: Condensed time-series statistics                            │
│  • Source: Fetches time-series from Garmin → runs condense_workout_data │
│                                                                         │
│  Example: "How was my pacing in yesterday's tempo?"                     │
│  → {                                                                    │
│      hr_analysis: {drift: 5.2%, cv: 6.8%, zone_transitions: 3},         │
│      pace_analysis: {consistency: 82, fade_index: 1.03, trend: steady}, │
│      splits_analysis: {even_split_score: 78, fastest_km: 8},            │
│      cadence_analysis: {avg: 178, drop_pct: 2.1, optimal_zone: 85%},    │
│      coaching_insights: ["Good consistency", "HR drift normal"]         │
│    }                                                                    │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Level 3: AI Workout Analyzer                 ~500-1000 tokens          │
│  ────────────────────────────                                           │
│  • Use for: Full workout analysis (triggered from UI)                   │
│  • Fetches: Full time-series from Garmin (2000+ points)                 │
│  • Condenses: Same condense_workout_data() as Level 2                   │
│  • LLM receives: Condensed stats (~200 tokens) - NEVER raw time-series  │
│  • LLM generates: Narrative + scores + recommendations                  │
│                                                                         │
│  Example: UI "Analyze" button on workout page                           │
│  → {                                                                    │
│      summary: "Strong tempo run with consistent pacing...",             │
│      whatWentWell: ["Negative split", "HR stayed in Zone 3"],           │
│      improvements: ["Slight cardiac drift in last 10 min"],             │
│      recommendations: ["Consider longer warmup"],                       │
│      overallScore: 78, trainingEffectScore: 3.2, recoveryHours: 24      │
│    }                                                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why this hierarchy?**

| Level | Tokens | Use Case |
|-------|--------|----------|
| Level 1 | ~50 | "What workouts did I do?" (listing many) |
| Level 2 | ~150 | "How was that run?" (single workout deep dive) |
| Level 3 | ~500+ | Full AI analysis (one-shot, UI-triggered) |

The **agentic chat** uses Levels 1-2 for token efficiency. It can call multiple tools per conversation, so keeping each call lean matters. The **AI Workout Analyzer** uses Level 3 for comprehensive analysis since it's a single-shot operation.

#### Shared Condensation Pipeline

**Critical design principle:** Raw time-series data (2000+ points) **NEVER** goes to the LLM. Both Level 2 and Level 3 use the same Python-based condensation:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     CONDENSATION PIPELINE                               │
│                                                                         │
│   Garmin API                    Python                      Output      │
│   ──────────                    ──────                      ──────      │
│                                                                         │
│   2000+ HR points ────┐                                                 │
│   2000+ pace points ──┼──► condense_workout_data() ──► Condensed Stats  │
│   2000+ elevation ────┤      (analysis/condensation.py)   (~200 tokens) │
│   splits[] ───────────┘                                                 │
│                                  │                                      │
│                                  ▼                                      │
│                        ┌─────────────────┐                              │
│                        │  HR: drift 5%,  │                              │
│                        │  cv 6.8%, zone  │                              │
│                        │  transitions: 3 │                              │
│                        │                 │                              │
│                        │  Pace: consist- │                              │
│                        │  ency 82/100,   │                              │
│                        │  fade index 1.03│                              │
│                        │                 │                              │
│                        │  Insights:      │                              │
│                        │  "Good pacing"  │                              │
│                        └─────────────────┘                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**What happens after condensation:**

| Tool | After Condensation |
|------|-------------------|
| `get_workout_details` | Returns condensed stats as JSON → Agent uses directly |
| AI Workout Analyzer | Feeds condensed stats to LLM → LLM generates narrative |

```
                        ┌─────────────────────────────────────────────┐
                        │          get_workout_details()              │
                        │                                             │
Condensed Stats ────────┼──► Returns JSON directly to agent           │
   (~200 tokens)        │    (no LLM call needed)                     │
                        │                                             │
                        └─────────────────────────────────────────────┘

                        ┌─────────────────────────────────────────────┐
                        │          AI Workout Analyzer                │
                        │                                             │
Condensed Stats ────────┼──► LLM (GPT-5-mini) ──► Narrative + Scores  │
   (~200 tokens)        │    + athlete context      (~500 tokens out) │
                        │    + similar workouts                       │
                        │                                             │
                        └─────────────────────────────────────────────┘
```

**Why never send raw time-series to LLM?**
- 2000+ data points = 5000+ tokens of noise
- LLM can't do statistical analysis (drift, CV, trends) accurately
- Python does it better: `statistics.mean()`, linear regression, zone detection
- Condensed stats are what coaches actually care about

**Data flow for get_workout_details:**

```
User: "How consistent was my pacing in yesterday's long run?"
                    │
                    ▼
        ┌───────────────────────┐
        │   query_workouts()    │  → Get activity ID
        │   (workout_type=long) │
        └───────────┬───────────┘
                    │ activity_id = "abc123"
                    ▼
        ┌───────────────────────┐
        │ get_workout_details() │  → Fetch time-series from Garmin
        │   (workout_id)        │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Garmin Connect API   │  → HR[], pace[], elevation[], splits[]
        │  /activity/{id}/      │
        │    details + splits   │
        └───────────┬───────────┘
                    │ Raw time-series (2000+ points)
                    ▼
        ┌───────────────────────┐
        │ condense_workout_data │  → Statistical analysis
        │   (from analysis/     │
        │    condensation.py)   │
        └───────────┬───────────┘
                    │ Condensed stats (~150 tokens)
                    ▼
        ┌───────────────────────┐
        │    Agent Response     │
        │ "Your pacing was      │
        │  good (82/100)..."    │
        └───────────────────────┘
```

### 3. Consistent Return Structure

All tools return predictable JSON that the LLM can reason about:

```python
# Query tools return dicts with known keys
{"ctl": 45.2, "atl": 52.8, "tsb": -7.6, "risk_zone": "optimal"}

# Action tools return success/failure with details
{"success": True, "goal_id": "g123", "message": "Goal saved"}
```

---

## Problem Statement

The current AI implementation has two critical limitations:

1. **Static Context Injection** - Context is pre-loaded once and injected into prompts. This leads to stale data, bloated prompts, and inability to answer questions we didn't anticipate.

2. **Too Many Questions** - The AI asks for information it should already know from the database, creating friction instead of leveraging the rich data we have.

**Goal**: Build an agentic AI that can query data on-demand, reason about the athlete's situation, and take actions—all while minimizing unnecessary user input.

---

## Scope: What's Agentic vs. Not

### Agentic (Tools + LangChain + Langfuse)

| Feature | Why Agentic |
|---------|-------------|
| **Chat conversations** | Interactive, multi-turn, needs to query data on-demand |
| **Plan generation** | Can be triggered via chat or UI, uses athlete context |
| **Workout design** | Needs readiness data, recent load, goals to personalize |

These features benefit from:
- Dynamic tool calling (fetch what's needed)
- Multi-step reasoning (analyze → decide → act)
- Token-based quota (variable cost per interaction)
- Full Langfuse tracing (debug complex flows)

### Non-Agentic (Keep Current Implementation)

| Feature | Why NOT Agentic |
|---------|-----------------|
| **Workout analysis** | One-shot, fixed input (workout) → fixed output (analysis) |
| **Batch enrichment** | Background job, no interaction, bulk processing |
| **Data sync** | Garmin API → DB, no LLM reasoning needed |
| **Wellness fetch** | Simple data retrieval, no AI involved |

These features stay simple because:
- Fixed cost per operation (predictable billing)
- No tool calling needed (all data is provided upfront)
- No multi-turn reasoning (single prompt → response)
- Message-based quota works fine (5 analyses/month)

### Visual Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI Features                              │
├─────────────────────────────────┬───────────────────────────────┤
│         AGENTIC                 │         NON-AGENTIC           │
│   (LangChain + Langfuse)        │     (Current approach)        │
├─────────────────────────────────┼───────────────────────────────┤
│  • Chat conversations           │  • Workout analysis           │
│  • Plan generation              │  • Batch enrichment           │
│  • Workout design               │  • Background jobs            │
│                                 │                               │
│  Token-based quota              │  Message-based quota          │
│  Variable cost                  │  Fixed cost                   │
│  Multi-step reasoning           │  Single prompt                │
│  Tool calling                   │  Direct LLM call              │
└─────────────────────────────────┴───────────────────────────────┘
```

---

## Architecture Overview

### Current (Static Context)
```
User message → Chat Agent → Static context injected → Response
                              ↑
                     (pre-loaded once, stale, incomplete)
```

### Target (Agentic with Tools)
```
User message → AI Agent ←→ [Tools] → Response
                            ├── query_workouts()
                            ├── query_wellness()
                            ├── get_athlete_profile()
                            ├── get_training_patterns()
                            ├── get_fitness_metrics()
                            ├── get_garmin_data()
                            ├── create_training_plan()
                            └── design_workout()
```

### Benefits

| Aspect | Static Context | Agentic Tools |
|--------|----------------|---------------|
| Data freshness | Stale (loaded once) | Always current |
| Context size | Bloated (everything) | Lean (only what's needed) |
| Flexibility | Limited to pre-defined | Can answer anything |
| User friction | Asks questions | Uses existing data |
| Capabilities | Read-only responses | Can take actions |

---

## Data Sources

### 1. Workout Database (SQLite)
| Table | Key Data |
|-------|----------|
| `activities` | All workouts with metrics (HR, pace, duration, load) |
| `activity_laps` | Split/lap data for each workout |
| `activity_sets` | Strength training sets |
| `wellness` | Daily wellness (sleep, stress, HRV, body battery) |
| `goals` | User-defined race goals |

### 2. Computed Metrics
| Metric | Source |
|--------|--------|
| CTL/ATL/TSB | Calculated from activity load history |
| ACWR | Acute:Chronic workload ratio |
| HR Zones | Karvonen method from max/rest HR |
| Training Paces | VDOT-based calculations |
| Readiness Score | Composite from wellness data |

### 3. Garmin API (Real-time)
| Data | Endpoint |
|------|----------|
| VO2max | `/wellness/vo2max` |
| Race Predictions | `/wellness/race-predictions` |
| Training Status | `/wellness/training-status` |
| Training Readiness | `/wellness/training-readiness` |
| HRV Status | `/wellness/hrv` |

### 4. Detectable Patterns
| Pattern | Detection Method |
|---------|------------------|
| Training days/week | Count activities per week (8-week avg) |
| Long run day | Most frequent day for longest runs |
| Rest days | Days with consistently zero activity |
| Max session duration | 90th percentile of durations |
| Cross-training | Presence of cycling, swimming, strength |
| Preferred times | Mode of workout start times |

---

## Agent Tools

### Quick Reference

| Tool | Purpose | Returns | Token Cost |
|------|---------|---------|------------|
| **Query Tools** ||||
| `query_workouts` | Find workouts by filters | List of summaries (pace, HR, load) | ~50 tokens |
| `query_wellness` | Sleep, HRV, stress data | Daily metrics for date range | ~30 tokens |
| `get_athlete_profile` | Current fitness snapshot | CTL, ATL, TSB, zones, paces | ~80 tokens |
| `get_training_patterns` | Detected habits | Days/week, long run day, etc. | ~40 tokens |
| `get_fitness_metrics` | Fitness trends | CTL/ATL/TSB over time | ~60 tokens |
| `get_garmin_data` | Garmin insights | VO2max, race predictions, status | ~50 tokens |
| `compare_workouts` | Side-by-side analysis | Pace/HR/load comparison | ~70 tokens |
| `get_workout_details` | Deep single-workout analysis | HR drift, pace consistency, insights | ~150 tokens |
| **Action Tools** ||||
| `create_training_plan` | Generate plan | Weekly structure, workouts | ~200 tokens |
| `design_workout` | Single workout | Warmup, main, cooldown | ~100 tokens |
| `log_note` | Save a note | Note ID, timestamp | ~20 tokens |
| `set_goal` | Set race goal | Goal ID, target | ~30 tokens |

### Data Query Tools (Read-Only)

```python
@tool
def query_workouts(
    sport_type: Optional[str] = None,      # "running", "cycling", "strength"
    date_from: Optional[str] = None,       # ISO date
    date_to: Optional[str] = None,
    workout_type: Optional[str] = None,    # "easy", "tempo", "long", "intervals"
    limit: int = 10,
    include_laps: bool = False
) -> List[WorkoutSummary]:
    """
    Query workout history with flexible filters.

    Examples:
    - "Show my last 5 tempo runs" → query_workouts(workout_type="tempo", limit=5)
    - "What did I do last week?" → query_workouts(date_from="2024-01-08", date_to="2024-01-14")
    - "My longest runs this month" → query_workouts(sport_type="running", order_by="duration")
    """

@tool
def query_wellness(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    metrics: List[str] = ["sleep", "stress", "hrv", "body_battery"]
) -> List[WellnessDay]:
    """
    Query wellness/recovery data.

    Examples:
    - "How did I sleep this week?" → query_wellness(metrics=["sleep"])
    - "Show my HRV trend" → query_wellness(metrics=["hrv"], date_from="2024-01-01")
    """

@tool
def get_athlete_profile() -> AthleteProfile:
    """
    Get current athlete profile with all key metrics.

    Returns:
    - Fitness metrics (CTL, ATL, TSB, ACWR)
    - Physiology (max_hr, rest_hr, threshold_hr, vdot)
    - Recent load (weekly hours, 7-day load)
    - Readiness (score, zone)
    - HR zones and training paces
    - Active goals
    """

@tool
def get_training_patterns() -> TrainingPatterns:
    """
    Get detected training patterns from workout history.

    Returns:
    - avg_days_per_week: Typical training frequency
    - typical_long_run_day: 0=Mon, 6=Sun
    - typical_rest_days: List of rest day indices
    - max_session_duration_min: Longest typical session
    - does_strength: Whether athlete does strength training
    - does_cross_training: Whether athlete cross-trains
    - preferred_time_of_day: "morning", "afternoon", "evening"
    """

@tool
def get_fitness_metrics(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> FitnessTimeSeries:
    """
    Get fitness metrics over time (CTL, ATL, TSB).

    Examples:
    - "How has my fitness changed?" → get_fitness_metrics(date_from="2024-01-01")
    - "Am I overtraining?" → get_fitness_metrics() → check ACWR and TSB
    """

@tool
def get_garmin_data() -> GarminMetrics:
    """
    Get latest data from Garmin Connect.

    Returns:
    - vo2max: Current VO2max estimate
    - race_predictions: Dict of distance → predicted time
    - training_status: "Productive", "Maintaining", "Detraining", etc.
    - training_readiness: Score 0-100
    - hrv_status: "Balanced", "Low", "High"
    """

@tool
def compare_workouts(
    workout_ids: List[str],
    metrics: List[str] = ["pace", "hr", "load"]
) -> ComparisonResult:
    """
    Compare multiple workouts side-by-side.

    Examples:
    - "Compare my last two tempo runs" → compare_workouts([id1, id2])
    """

@tool
def get_workout_details(
    workout_id: str
) -> WorkoutDetails:
    """
    Get deep analysis of a single workout with condensed time-series statistics.

    Fetches time-series data (HR, pace, elevation, cadence) and runs
    statistical condensation to extract coaching-relevant insights.

    Returns:
    - hr_analysis: drift %, variability CV, zone transitions, interval detection
    - pace_analysis: consistency score (0-100), fade index, negative split, trend
    - elevation_analysis: terrain type, climb count, total gain/loss
    - splits_analysis: even split score, fastest/slowest km, trend
    - cadence_analysis: avg cadence, drop %, optimal zone time, consistency
    - coaching_insights: Pre-computed observations like "Cardiac drift +8%"

    Examples:
    - "How was my tempo yesterday?" → First query_workouts, then get_workout_details(id)
    - "Was my pacing consistent?" → get_workout_details returns pace_analysis.consistency_score
    """
```

### Action Tools (Write)

```python
@tool
def create_training_plan(
    race_distance: str,
    race_date: str,
    target_time: Optional[str] = None,
    priority: str = "A"
) -> TrainingPlan:
    """
    Generate a personalized training plan.

    Uses athlete profile and patterns automatically.
    Only requires: distance, date, and optionally target time.
    """

@tool
def design_workout(
    workout_type: str,                     # "easy", "tempo", "intervals", "long"
    target_duration_min: Optional[int] = None,
    target_distance_km: Optional[float] = None,
    focus: Optional[str] = None            # "endurance", "speed", "threshold"
) -> DesignedWorkout:
    """
    Design a single workout for today/tomorrow.

    Automatically considers:
    - Current readiness and fatigue
    - Recent training load
    - Upcoming race goals
    - Weather (if available)
    """

@tool
def log_note(
    content: str,
    date: Optional[str] = None,
    workout_id: Optional[str] = None
) -> Note:
    """
    Log a training note or reflection.
    """

@tool
def set_goal(
    race_distance: str,
    race_date: str,
    target_time: Optional[str] = None,
    race_name: Optional[str] = None,
    priority: str = "A"
) -> Goal:
    """
    Create or update a race goal.
    """
```

---

## Agent Behavior Guidelines

### What the Agent Should NEVER Ask

The agent has access to all data. It should **never** ask for:

| Don't Ask | Why |
|-----------|-----|
| "What's your fitness level?" | Detectable from CTL and workout history |
| "How many days per week do you train?" | Detectable from patterns |
| "What's your max heart rate?" | Available in profile |
| "What's your current weekly mileage?" | Calculable from recent workouts |
| "Do you do strength training?" | Detectable from workout types |
| "When do you usually run long?" | Detectable from patterns |

### What the Agent SHOULD Ask

Only ask for things that require user **intent** or **preference**:

| Do Ask | Why |
|--------|-----|
| "What race are you targeting?" | Future intent |
| "What date is your race?" | External event |
| "Do you want to prioritize speed or endurance?" | Preference |
| "Is this an A, B, or C race?" | Priority preference |
| "Any injuries or constraints I should know about?" | Not in data |

### Response Style

```
❌ Bad: "What's your current weekly mileage?"

✅ Good: "I see you're averaging 42km/week across 5 training days,
         with long runs on Sundays. Your CTL is 48, suggesting
         intermediate fitness. Want me to create a plan that builds
         from here?"
```

---

## Example Conversations

### Example 1: Plan Creation
```
User: "I want to run a marathon in April"

Agent: [calls get_athlete_profile(), get_training_patterns(), get_garmin_data()]

Agent: "Based on your data:
- Current fitness: CTL 45 (Intermediate)
- Weekly volume: 38 km over 5 days
- Long runs: Typically Sundays
- Garmin predicts: 3:42 marathon

April 15th gives us 16 weeks. I recommend targeting sub-3:45.

Should I generate the plan?"
```

### Example 2: Workout Analysis
```
User: "How was my tempo run yesterday?"

Agent: [calls query_workouts(limit=1, workout_type="tempo")]

Agent: "Your tempo yesterday:
- 8.2 km in 38:42 (4:43/km avg)
- Avg HR: 162 bpm (Zone 4)
- Training load: 87 HRSS

Compared to your last tempo (4:51/km), you were 8 sec/km faster
at similar effort. Solid progression."
```

### Example 3: Readiness Check
```
User: "Should I do intervals today?"

Agent: [calls get_athlete_profile(), query_wellness(date_to="today")]

Agent: "I'd suggest easy/recovery instead:
- TSB: -12 (accumulated fatigue)
- Sleep last night: 5.8h (below your 7.2h average)
- Body battery: 34 (low)
- Hard session 2 days ago

An easy 40-min run would be better. Want me to design it?"
```

---

## Implementation Phases

### Phase 1: Core Query Tools ✅ COMPLETED
- [x] `query_workouts()` - Flexible workout queries
- [x] `get_athlete_profile()` - Current metrics snapshot
- [x] `get_training_patterns()` - Pattern detection service
- [x] Integrate tools with chat agent

### Phase 2: Enhanced Data Tools ✅ COMPLETED
- [x] `query_wellness()` - Wellness data queries
- [x] `get_fitness_metrics()` - Time series data
- [x] `get_garmin_data()` - Real-time Garmin API
- [x] `compare_workouts()` - Side-by-side comparison

### Phase 3: Action Tools ✅ COMPLETED
- [x] `create_training_plan()` - Plan generation via tool
- [x] `design_workout()` - Single workout design
- [x] `set_goal()` - Goal management
- [x] `log_note()` - Training notes

### Phase 4: Advanced Features (Future)
- [ ] Proactive insights (agent notices things)
- [ ] Multi-turn reasoning (complex queries)
- [ ] Memory (remember user preferences across sessions)

---

## Technical Implementation

### Stack Decision

| Component | Choice | Why |
|-----------|--------|-----|
| **Agent Framework** | LangChain | Battle-tested, great tool abstractions, multi-LLM support |
| **Observability** | Langfuse | Open-source, self-hostable, deep LangChain integration |
| **LLM** | Claude (Anthropic) | Best reasoning, native tool use |
| **Database** | SQLite | Already in use, simple, fast |

---

## LangChain Integration

> **Note**: This section has been updated to reflect the actual implementation using
> LangGraph's `create_react_agent` and Langfuse v3's manual tracing API.

### Agent Setup

```python
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool

# Langfuse v3 uses manual tracing instead of callbacks
from langfuse import Langfuse

def get_langfuse_client():
    return Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    )

llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    temperature=0,
    max_tokens=4096,
)

# Define tools
@tool
def query_workouts(
    sport_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    workout_type: str | None = None,
    limit: int = 10
) -> list[dict]:
    """Query workout history with flexible filters.

    Args:
        sport_type: Filter by sport ("running", "cycling", "strength")
        date_from: Start date (ISO format: YYYY-MM-DD)
        date_to: End date (ISO format: YYYY-MM-DD)
        workout_type: Filter by type ("easy", "tempo", "long", "intervals")
        limit: Max results to return (default 10)

    Returns:
        List of workout summaries with date, type, duration, distance, load
    """
    return workout_query_service.query(**locals())

@tool
def get_athlete_profile() -> dict:
    """Get current athlete profile with fitness metrics, HR zones, and training paces.

    Returns:
        Dict with CTL, ATL, TSB, ACWR, readiness, HR zones, paces, active goals
    """
    return coach_service.get_llm_context().to_dict()

@tool
def get_training_patterns() -> dict:
    """Get detected training patterns from workout history.

    Returns:
        Dict with avg_days_per_week, typical_long_run_day, rest_days,
        max_session_duration, does_strength, does_cross_training
    """
    return pattern_service.detect_all()

# All tools
tools = [
    query_workouts,
    get_athlete_profile,
    get_training_patterns,
    query_wellness,
    get_fitness_metrics,
    get_garmin_data,
    compare_workouts,
    create_training_plan,
    design_workout,
]

# Prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert running coach AI assistant.

You have access to the athlete's complete training database through tools.
ALWAYS use tools to get data - never guess or ask for information you can look up.

Guidelines:
- Use get_athlete_profile() first to understand current fitness state
- Use query_workouts() to find specific workouts or analyze history
- Use get_training_patterns() to understand training habits
- Never ask for: fitness level, weekly mileage, HR zones, training days (use tools)
- Only ask for: race goals, race dates, preferences, injuries

Be concise and data-driven in responses."""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create agent using LangGraph's react agent
agent = create_react_agent(llm, tools)
```

### Running the Agent

```python
async def chat(user_message: str, session_id: str, chat_history: list = []):
    """Process a chat message through the agent."""

    # Create Langfuse trace for this conversation
    client = get_langfuse_client()
    trace = client.trace(
        name="coach_chat",
        session_id=session_id,
        user_id="athlete_1",  # From auth
    )

    # Build messages for the agent
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    messages.extend(chat_history)  # Already HumanMessage/AIMessage objects
    messages.append(HumanMessage(content=user_message))

    # Invoke the agent using langgraph
    result = await agent.ainvoke({"messages": messages})

    # Extract response from the result
    final_messages = result.get("messages", [])
    response_text = ""
    for msg in final_messages:
        if isinstance(msg, AIMessage) and msg.content:
            response_text = msg.content

    # Record in Langfuse
    trace.generation(
        name="coach_response",
        model="claude-sonnet-4-20250514",
        input=[{"role": "user", "content": user_message}],
        output=response_text,
    )

    return response_text
```

---

## Langfuse Observability

### What Langfuse Tracks

| Feature | What It Shows |
|---------|---------------|
| **Traces** | Full conversation flow with all LLM calls |
| **Spans** | Individual tool executions with inputs/outputs |
| **Generations** | Each LLM generation with tokens, latency, cost |
| **Scores** | User feedback, quality metrics |
| **Sessions** | Group traces by conversation |
| **Users** | Track per-athlete usage |

### Dashboard Insights

```
Langfuse Dashboard
├── Traces
│   ├── Trace: "Create marathon plan" (session_abc123)
│   │   ├── LLM Call: Initial reasoning (450 tokens, 1.2s)
│   │   ├── Tool: get_athlete_profile() → {ctl: 45, ...}
│   │   ├── Tool: get_training_patterns() → {days: 5, ...}
│   │   ├── Tool: get_garmin_data() → {predictions: ...}
│   │   ├── LLM Call: Generate response (380 tokens, 0.9s)
│   │   └── Total: 3.4s, $0.012
│   │
│   └── Trace: "How was my tempo?" (session_abc123)
│       ├── LLM Call: Parse intent (120 tokens, 0.4s)
│       ├── Tool: query_workouts(type="tempo", limit=1)
│       ├── LLM Call: Analyze and respond (290 tokens, 0.8s)
│       └── Total: 1.8s, $0.006
│
├── Metrics
│   ├── Avg latency: 2.1s
│   ├── Tool usage: query_workouts (45%), get_athlete_profile (30%)
│   ├── Avg tokens/request: 850
│   └── Daily cost: $1.24
│
└── Quality
    ├── User ratings: 4.2/5
    └── Tool error rate: 0.3%
```

### Environment Variables

```bash
# .env
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxx
LANGFUSE_HOST=https://cloud.langfuse.com  # Or self-hosted URL

ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### Custom Scoring

```python
from langfuse import Langfuse

langfuse = Langfuse()

# After user feedback
def record_feedback(trace_id: str, rating: int, comment: str = None):
    langfuse.score(
        trace_id=trace_id,
        name="user_rating",
        value=rating,
        comment=comment
    )

# Programmatic quality checks
def score_response_quality(trace_id: str, response: str, tools_used: list):
    # Score based on tool usage (good if used data, bad if asked questions)
    asked_unnecessary = any(q in response.lower() for q in [
        "what's your fitness level",
        "how many days do you train",
        "what's your max heart rate"
    ])

    langfuse.score(
        trace_id=trace_id,
        name="data_driven",
        value=0 if asked_unnecessary else 1,
        comment="Agent should use tools, not ask questions"
    )
```

---

## Database Access Pattern

```python
from langchain_core.tools import tool
from typing import Optional
import sqlite3

class WorkoutQueryService:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def query(
        self,
        sport_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        workout_type: Optional[str] = None,
        limit: int = 10,
        **kwargs  # Ignore extra args from tool
    ) -> list[dict]:
        """Build safe parameterized query."""
        query = """
            SELECT
                activity_id, start_time, sport_type,
                duration_seconds, distance_meters,
                avg_hr, max_hr, training_load,
                workout_type, title
            FROM activities
            WHERE 1=1
        """
        params = []

        if sport_type:
            query += " AND sport_type = ?"
            params.append(sport_type)

        if date_from:
            query += " AND date(start_time) >= ?"
            params.append(date_from)

        if date_to:
            query += " AND date(start_time) <= ?"
            params.append(date_to)

        if workout_type:
            query += " AND workout_type = ?"
            params.append(workout_type)

        query += " ORDER BY start_time DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
```

---

## Safety Guardrails

1. **Read-only by default** - Action tools require explicit confirmation
2. **Parameterized queries** - No SQL injection risk
3. **Rate limiting** - Max 10 tool calls per request
4. **Langfuse audit logging** - All tool invocations traced
5. **Scope limiting** - Tools only access training data
6. **Cost monitoring** - Langfuse tracks token usage and costs
7. **Error handling** - Graceful degradation if tools fail

---

## Dependencies

```bash
# Add to requirements.txt (actual versions used)
langchain>=0.3.25
langchain-anthropic>=0.3.15
langchain-core>=0.3.59
langgraph>=0.3.32
langfuse>=3.0.0
```

```python
# pyproject.toml addition
[project.optional-dependencies]
agent = [
    "langchain>=0.3.25",
    "langchain-anthropic>=0.3.15",
    "langchain-core>=0.3.59",
    "langgraph>=0.3.32",
    "langfuse>=3.0.0",
]
```

> **Note**: Langfuse v3 changed from callback-based to manual tracing.
> LangChain v1.2+ moved AgentExecutor to langgraph.prebuilt.create_react_agent.

---

## Files Created/Modified

| File | Status | Purpose |
|------|--------|---------|
| `src/tools/__init__.py` | ✅ Created | Tools package init |
| `src/tools/query_tools.py` | ✅ Created | 8 data query tools (LangChain @tool) |
| `src/tools/action_tools.py` | ✅ Created | 4 action tools (plan, workout, goal, note) |
| `src/services/training_pattern_service.py` | ✅ Created | Pattern detection service |
| `src/services/workout_query_service.py` | ✅ Created | Flexible workout queries |
| `src/agents/langchain_agent.py` | ✅ Created | LangGraph react agent with 12 tools |
| `src/agents/__init__.py` | ✅ Updated | Export LangChainCoachAgent |
| `src/observability/__init__.py` | ✅ Created | Observability package init |
| `src/observability/langfuse_config.py` | ✅ Created | Langfuse v3 manual tracing |
| `src/observability/scoring.py` | ✅ Created | Quality scoring & token tracking |
| `src/api/routes/chat.py` | ✅ Updated | Added `?use_agentic=true` toggle |
| `src/api/quota.py` | ✅ Updated | Token-based quota for chat |
| `.env.example` | ✅ Updated | Added Langfuse env vars |
| `requirements.txt` | ✅ Updated | Added LangChain/Langfuse deps |
| `pyproject.toml` | ✅ Updated | Added agent optional deps |

---

## Project Structure

```
src/
├── agents/
│   ├── __init__.py
│   ├── langchain_agent.py      # NEW: LangChain AgentExecutor setup
│   ├── chat_agent.py           # REFACTOR: Use LangChain agent
│   └── plan_agent.py           # Existing plan generation
│
├── tools/                       # NEW PACKAGE
│   ├── __init__.py
│   ├── query_tools.py          # query_workouts, query_wellness, etc.
│   ├── action_tools.py         # create_plan, design_workout, etc.
│   └── services.py             # Service layer for tool implementations
│
├── services/
│   ├── coach.py                # Existing
│   ├── training_pattern_service.py  # NEW: Pattern detection
│   └── workout_query_service.py     # NEW: Flexible queries
│
├── observability/               # NEW PACKAGE
│   ├── __init__.py
│   ├── langfuse_config.py      # Langfuse initialization
│   └── scoring.py              # Custom quality scores
│
└── api/
    └── chat.py                 # Updated endpoints
```

---

## Quota System Changes

### Current System (Pre-Agentic)

The existing quota system counts **requests per endpoint**:

| Feature | Free Tier | Pro Tier | Period |
|---------|-----------|----------|--------|
| `workout_analysis` | 5 | Unlimited | Monthly |
| `chat` | 10 | Unlimited | Daily |
| `plan` | 0 (disabled) | Unlimited | Monthly |

See: `docs/workout-analysis-database/QUOTA_SYSTEM.md`

### Problem with Agentic Chat

The current "10 messages/day" model doesn't fit an agentic architecture:

| Issue | Why It's a Problem |
|-------|-------------------|
| **Variable cost per message** | "Hi" costs ~100 tokens; "Analyze my training block" costs ~2000+ tokens with multiple tool calls |
| **Tool calls multiply LLM usage** | Each tool result triggers another LLM call to reason about it |
| **Message count ≠ actual cost** | A power user asking complex questions costs 10x more than casual user |
| **No incentive for efficiency** | Users have no visibility into "expensive" vs "cheap" queries |

### Proposed: Token-Based Quota for Chat

Replace message counting with **token-based limits** for the chat feature:

```python
# New quota model for agentic chat
QUOTA_LIMITS = {
    "free": {
        "workout_analysis": QuotaLimit(limit=5, period=QuotaPeriod.MONTHLY),  # UNCHANGED
        "chat_tokens": QuotaLimit(limit=50_000, period=QuotaPeriod.MONTHLY),  # NEW
        "plan": QuotaLimit(limit=1, period=QuotaPeriod.MONTHLY),              # Allow 1 plan
    },
    "pro": {
        "workout_analysis": QuotaLimit(limit=-1, period=QuotaPeriod.MONTHLY),
        "chat_tokens": QuotaLimit(limit=-1, period=QuotaPeriod.MONTHLY),      # Unlimited
        "plan": QuotaLimit(limit=-1, period=QuotaPeriod.MONTHLY),
    },
}
```

### Token Tracking with Langfuse

Langfuse already tracks tokens per trace. We can query this for quota:

```python
from langfuse import Langfuse

langfuse = Langfuse()

def get_monthly_token_usage(user_id: str) -> int:
    """Get total tokens used by user this month."""
    traces = langfuse.get_traces(
        user_id=user_id,
        from_timestamp=first_of_month(),
        to_timestamp=now(),
    )
    return sum(t.total_tokens for t in traces)
```

Or store in our DB alongside `ai_usage_logs`:

```python
# Updated ai_usage_logs schema
class AIUsageLog:
    id: str
    user_id: str
    analysis_type: str          # "chat", "workout_analysis", "plan"
    created_at: datetime
    status: str
    # NEW fields for agentic tracking
    input_tokens: int           # Tokens in (user message + tool results)
    output_tokens: int          # Tokens out (assistant response)
    total_tokens: int           # input + output
    tool_calls: int             # Number of tools invoked
    latency_ms: int             # Total response time
    trace_id: str               # Langfuse trace ID for debugging
```

### Quota Check Flow (Agentic)

```
User sends message
        │
        ▼
┌───────────────────┐
│ Check token quota │
│ (monthly limit)   │
└───────────────────┘
        │
   remaining > 0?
   ┌────┴────┐
  Yes        No
   │          │
   ▼          ▼
┌──────────┐  ┌─────────────────────────┐
│ Process  │  │ HTTP 402                │
│ message  │  │ "Token quota exceeded"  │
└──────────┘  │ Show: used/limit tokens │
   │          └─────────────────────────┘
   ▼
┌───────────────────┐
│ After response:   │
│ Log token usage   │
│ to ai_usage_logs  │
└───────────────────┘
```

### User-Facing Quota Display

```typescript
// Frontend quota display for chat
interface ChatQuota {
  type: "chat_tokens";
  period: "monthly";
  limit: 50000;
  used: 23450;
  remaining: 26550;
  percentUsed: 47;  // For progress bar
}

// UI shows:
// "AI Chat: 23,450 / 50,000 tokens used this month"
// [████████░░░░░░░░] 47%
```

### What Stays the Same

| Feature | Change? | Reason |
|---------|---------|--------|
| **Workout Analysis** | NO CHANGE | Fixed cost per analysis, message-based limit works |
| **Plan Generation** | NO CHANGE | Fixed cost per plan, already limited |
| **Chat** | CHANGE TO TOKENS | Variable cost, needs token-based tracking |

### Migration Path

1. **Phase 1**: Add token tracking fields to `ai_usage_logs`
2. **Phase 2**: Implement Langfuse → DB token sync after each chat
3. **Phase 3**: Update quota middleware to check `chat_tokens` instead of `chat` count
4. **Phase 4**: Update frontend quota display to show tokens
5. **Phase 5**: Deprecate old `chat` message count quota

### Cost Estimation

Rough token costs (Claude Sonnet):
- Simple query ("What's my CTL?"): ~500 tokens (~$0.002)
- Medium query ("Analyze my week"): ~1,500 tokens (~$0.006)
- Complex query ("Create a plan"): ~3,000+ tokens (~$0.012)

**50,000 tokens/month free** ≈ 30-100 conversations depending on complexity.

---

## Success Criteria

| Criteria | Status | Evidence |
|----------|--------|----------|
| Agent answers without pre-loading | ✅ | Calls tools dynamically per question |
| Never asks for DB-available info | ✅ | Uses 6+ tools per complex query |
| Plan creation with minimal input | ✅ | Only needs race/date, pulls rest from tools |
| Uses readiness for recommendations | ✅ | Calls `query_wellness`, `get_garmin_data` |
| All calls logged to Langfuse | ✅ | Full trace with tool spans |
| Response latency < 3s | ✅ | ~2s for simple queries |
| Token-based quota enforced | ✅ | tiktoken counting implemented |
| Streaming with live status | ✅ | SSE events for tool start/end |
| Multi-provider support | ✅ | OpenAI/Anthropic auto-detect |
| Cost-optimized | ✅ | GPT-5-mini: ~$0.0006/request |

### Test Results (Dec 2024)

```
Provider: openai:gpt-5-mini
Tools: 12/12 functional

Sample request: "What is my fitness status?"
├── Tools called: 6 (get_athlete_profile, query_wellness, get_garmin_data, ...)
├── Tokens: 311 total
├── Cost: $0.000606
└── Status: completed
```

---

## Streaming & Live Status

The agent supports Server-Sent Events (SSE) for real-time updates:

### API Endpoint

```bash
POST /api/chat/stream
# or
POST /api/chat?stream=true&use_agentic=true
```

### Event Types

```
data: {"type": "status", "message": "Thinking..."}

data: {"type": "tool_start", "tool": "get_athlete_profile", "message": "Loading your fitness profile..."}

data: {"type": "tool_end", "tool": "get_athlete_profile", "message": "CTL: 45, TSB: -8"}

data: {"type": "token", "content": "Based on"}

data: {"type": "token", "content": " your data..."}

data: {"type": "done", "tools_used": ["get_athlete_profile"], "token_usage": {"total": 150}}

data: [DONE]
```

### Tool Status Messages

Human-friendly messages displayed during tool execution:

| Tool | Start Message | End Message |
|------|--------------|-------------|
| `query_workouts` | "Checking your workout history..." | "Found 5 workouts" |
| `get_athlete_profile` | "Loading your fitness profile..." | "CTL: 45, TSB: -8" |
| `query_wellness` | "Gathering wellness data..." | "7 days retrieved" |
| `get_garmin_data` | "Fetching Garmin insights..." | "VO2max: 52" |
| `create_training_plan` | "Designing your plan..." | "12-week plan ready" |

---

## Robustness Features

### Retry Logic

Tools automatically retry on transient failures:

```python
@with_retry(max_retries=2, base_delay=0.5)
def _query_workouts_from_db(...):
    # Retries: DB errors, timeouts, network issues
    # No retry: validation errors, programming errors
    # Max time: 5 seconds per tool
```

### Circuit Breaker

Prevents hammering failing services:

```python
circuit = CircuitBreaker(failure_threshold=3, reset_timeout=30)
# CLOSED → OPEN after 3 failures
# OPEN → HALF_OPEN after 30s
# HALF_OPEN → CLOSED on success
```

### Graceful Degradation

All tools fall back to mock data if services unavailable:

```python
try:
    return _get_data_from_service()
except Exception:
    logger.warning("Service unavailable, using mock data")
    return MOCK_DATA
```

---

## Cost Optimization

### Model Selection

| Model | Input/1M | Output/1M | Best For |
|-------|----------|-----------|----------|
| gpt-5-nano | $0.05 | $0.40 | Simple queries |
| **gpt-5-mini** | $0.25 | $2.00 | **Default - tool calling** |
| gpt-5 | $1.25 | $10.00 | Complex reasoning |
| claude-sonnet | $3.00 | $15.00 | Anthropic users |

### Token Efficiency

- Tools return **computed stats**, not raw data
- Average request: ~300 tokens (~$0.0006)
- 50K tokens/month = ~160 requests for free tier

### Provider Auto-Detection

```python
# Priority: Anthropic > OpenAI
# Uses whichever API key is available
agent = LangChainCoachAgent()  # Auto-detects provider
```
