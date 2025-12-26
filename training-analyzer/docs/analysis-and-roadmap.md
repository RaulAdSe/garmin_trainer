# Training Analyzer: Comprehensive Analysis & Roadmap

**Date:** December 26, 2025
**Version:** 1.0

---

## Executive Summary

This document provides a comprehensive analysis of the training-analyzer application, identifying gaps, overcomplications, feature completeness, and strategic opportunities based on industry research. The app has a solid foundation for running-focused training but requires significant enhancements for multi-sport support and competitive positioning.

### Key Findings

| Area | Current State | Priority |
|------|---------------|----------|
| Core Running Features | 85% complete | Maintenance |
| Multi-Sport Support | 10% complete | **Critical** |
| Data Persistence | 60% (in-memory) | **Critical** |
| **LLM Model Config** | **Using GPT-4o instead of GPT-5** | **Critical** |
| **Data Adaptation** | **Running-only, no power/swim** | **Critical** |
| AI/Adaptive Training | Basic LLM analysis | High |
| Prompt Engineering | Good, but uses regex parsing | High |
| Power-Based Metrics | 0% | High |
| Mobile Experience | Responsive only | Medium |

---

## Part 1: Code Architecture Analysis

### 1.1 Critical Gaps

#### Inconsistent AthleteContext Models

**Problem:** Three different `AthleteContext` classes exist with overlapping but inconsistent fields:

| File | Location | Fields |
|------|----------|--------|
| `models/analysis.py:192-242` | `AthleteContext` (dataclass) | ctl, atl, tsb, acwr, risk_zone, hr_zones |
| `models/plans.py:262-285` | `AthleteContext` (dataclass) | current_ctl, current_atl, vdot |
| `models/workouts.py:240-331` | `AthleteContext` (dataclass) | ctl, atl, tsb, readiness_score, paces |

**Recommendation:** Create a single unified `AthleteContext` model in a dedicated file.

#### Missing Error Handling in API Routes

**Problem:** Custom exception hierarchy exists in `exceptions.py` but is rarely used in routes:

```python
# Current pattern (routes/workouts.py:288-291)
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")

# Should use custom exceptions
except WorkoutValidationError as e:
    raise  # Let exception handler convert to proper HTTP response
```

**Recommendation:** Create FastAPI exception handler that converts `ReactiveTrainingError` to HTTP responses.

#### BaseAgent Not Used Consistently

| Agent | Extends BaseAgent? |
|-------|-------------------|
| `AnalysisAgent` | No |
| `PlanAgent` | No |
| `WorkoutDesignAgent` | No |
| `AgentOrchestrator` | Yes |

**Recommendation:** Refactor all agents to extend `BaseAgent` for consistent behavior.

#### Frontend/Backend Field Name Mismatch

```typescript
// Frontend expects (WorkoutCard.tsx:188,205)
analysis.whatWentWell
analysis.improvements

// Backend sends (models/analysis.py:89-90)
what_worked_well: List[str]
observations: List[str]
```

**Recommendation:** Add response serialization to convert snake_case to camelCase.

---

### 1.2 Overcomplications

#### Over-Engineered LLM Response Parsing

**File:** `agents/analysis_agent.py:254-382`

- 60+ lines of regex parsing
- Fallback calls LLM again (doubles costs)
- Brittle string matching for ratings

**Recommendation:** Use OpenAI's JSON mode or function calling for structured responses.

#### Redundant to_dict/from_dict Methods

~200+ lines of boilerplate serialization across model files when `dataclasses.asdict()` or Pydantic's `.model_dump()` would suffice.

#### Orchestrator Over-Engineering

`AgentOrchestrator` is 427 lines but not used in any API routes. Each agent is called directly.

**Recommendation:** Either remove until needed or integrate into routes.

#### Quick Endpoints Duplication

Four nearly identical endpoints (`/quick/easy`, `/quick/tempo`, `/quick/intervals`, `/quick/long`) should be one parameterized endpoint: `/quick/{workout_type}`.

---

### 1.3 Technical Debt

#### In-Memory Storage (Critical)

```python
# routes/workouts.py:38
_workout_store: Dict[str, StructuredWorkout] = {}

# routes/plans.py:38
_plans_storage: Dict[str, Dict[str, Any]] = {}
```

**Impact:** Data lost on server restart, no horizontal scaling, no concurrent access safety.

**Recommendation:** Implement Repository pattern with database backing.

#### LLM Client Singleton Race Condition

```python
# providers.py:397-407 - sync version lacks locking
def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()  # Race condition!
    return _llm_client
```

#### Missing Frontend Data Layer

- `useWorkouts` manages its own Map state alongside React Query
- Manual pagination instead of `useInfiniteQuery`
- No central cache invalidation strategy

---

### 1.4 Priority Fixes Summary

| Priority | Issue | Impact |
|----------|-------|--------|
| **High** | In-memory storage | Data loss, no scaling |
| **High** | LLM singleton race condition | Production crashes |
| **High** | Frontend/backend field mismatch | Broken UI |
| **Medium** | Unify AthleteContext models | Maintainability |
| **Medium** | Use exception hierarchy | Better error handling |
| **Low** | Remove to_dict/from_dict boilerplate | Code quality |
| **Low** | Remove/utilize Orchestrator | Dead code |

---

## Part 1B: LLM & AI Agent Analysis

### 1B.1 Model Configuration Issue (CRITICAL)

**Problem:** The app is configured to use **GPT-4o series**, NOT GPT-5 mini/nano as intended.

**File:** `src/training_analyzer/config.py:35-36`
```python
# Current configuration - WRONG MODELS
llm_model_fast: str = "gpt-4o-mini"  # Should be gpt-5-nano
llm_model_smart: str = "gpt-4o"      # Should be gpt-5-mini
```

**File:** `src/training_analyzer/llm/providers.py:36-40` (misleading comments)
```python
class ModelType(Enum):
    FAST = "fast"    # Comment says GPT-5-nano but config uses gpt-4o-mini
    SMART = "smart"  # Comment says GPT-5-mini but config uses gpt-4o
```

**Impact:**
- Using older, more expensive models
- Missing GPT-5's improved reasoning capabilities
- Inconsistent documentation

**Fix Required:**
```python
# config.py - Update to GPT-5 models
llm_model_fast: str = "gpt-5-nano"   # For quick tasks
llm_model_smart: str = "gpt-5-mini"  # For complex analysis
```

---

### 1B.2 Prompt Engineering Analysis

#### Strengths (What's Working Well)

The prompts in `src/training_analyzer/llm/prompts.py` are well-designed:

| Prompt | Quality | Notes |
|--------|---------|-------|
| `WORKOUT_ANALYSIS_SYSTEM` | **Good** | Clear role, structured output format, athlete context injection |
| `PLAN_GENERATION_SYSTEM` | **Good** | Periodization principles, JSON output format |
| `WORKOUT_DESIGN_SYSTEM` | **Excellent** | Detailed interval guidelines, load considerations |
| `DAILY_BRIEFING_SYSTEM` | **Good** | Concise, actionable focus |

**Positive Patterns:**
- Clear role definition: "You are an experienced running coach..."
- Structured output format instructions with JSON schemas
- Athlete context placeholder: `{athlete_context}`
- Specific guidelines for different workout types
- Consideration of training load (TSB, ACWR, readiness)

#### Weaknesses (Needs Improvement)

| Issue | File:Line | Problem |
|-------|-----------|---------|
| **Regex parsing** | `analysis_agent.py:254-316` | 60+ lines of brittle regex instead of JSON mode |
| **Fallback LLM call** | `analysis_agent.py:347-382` | Doubles API costs when parsing fails |
| **Running-only context** | `prompts.py` | All prompts assume running (pace, not power) |
| **No JSON mode** | `providers.py` | Should use `response_format={"type": "json_object"}` |
| **Hardcoded model names** | `analysis_agent.py:439,467` | `model_used="gpt-5-mini"` doesn't reflect actual model |

**Example of Over-Engineered Parsing:**
```python
# analysis_agent.py:266-272 - Brittle regex parsing
summary_match = re.search(
    r"\*\*Summary\*\*:?\s*(.+?)(?=\n\n|\*\*|$)",
    text,
    re.DOTALL | re.IGNORECASE
)
```

**Should be:**
```python
# Use JSON mode instead
response = await self.llm_client.completion(
    system=system_prompt,
    user=user_prompt,
    response_format={"type": "json_object"},  # Force JSON output
)
parsed = json.loads(response)
```

---

### 1B.3 Context Building Analysis

**File:** `src/training_analyzer/llm/context_builder.py`

#### What's Included (Good)

| Context Section | Data Included | Quality |
|-----------------|---------------|---------|
| Fitness Metrics | CTL, ATL, TSB, ACWR, risk zone | **Excellent** |
| Physiology | Max HR, Rest HR, LTHR, age, gender | **Good** |
| HR Zones | 5-zone Karvonen calculation | **Good** |
| Race Goals | Distance, target time, race date, weeks away | **Good** |
| Training Paces | Easy, Long, Tempo, Threshold, Interval | **Good** |
| Readiness | Score, zone, recommendation | **Good** |
| Recent Training | Last 7 days summary, last 3 workouts | **Good** |

#### What's Missing (Gaps)

| Missing Context | Impact | Priority |
|-----------------|--------|----------|
| **Power data** | Cannot design cycling workouts | High |
| **FTP / power zones** | No cycling intensity guidance | High |
| **Swim metrics** | Cannot design swim workouts | High |
| **Historical trends** | Limited long-term perspective | Medium |
| **Weather/conditions** | Cannot adjust for heat/altitude | Low |
| **Equipment** | No bike/trainer awareness | Low |

**Current Context is Running-Centric:**
```python
# context_builder.py:88-107 - Only running paces
pace_multipliers = [
    ("Easy", 1.25),
    ("Long Run", 1.20),
    ("Tempo", 1.02),
    ("Threshold", 0.98),
    ("Interval", 0.92),
]
```

**Should Add for Multi-Sport:**
```python
# Power zones for cycling
power_zones = [
    ("Active Recovery", 0.55),
    ("Endurance", 0.75),
    ("Tempo", 0.90),
    ("Threshold", 1.00),  # FTP
    ("VO2max", 1.20),
    ("Anaerobic", 1.50),
    ("Neuromuscular", "max"),
]

# Swim paces
swim_paces = [
    ("Easy", css * 1.15),
    ("Aerobic", css * 1.05),
    ("Threshold (CSS)", css),
    ("VO2max", css * 0.95),
]
```

---

### 1B.4 Agent Architecture Analysis

#### Current Agent Usage

| Agent | Model Used | Context Injection | Output Parsing |
|-------|------------|-------------------|----------------|
| `AnalysisAgent` | SMART (gpt-4o) | `formatted_context` | Regex + fallback LLM |
| `PlanAgent` | SMART (gpt-4o) | Athlete context dict | JSON parsing |
| `WorkoutDesignAgent` | SMART (gpt-4o) | HR zones + paces | JSON parsing |
| `AgentOrchestrator` | SMART (gpt-4o) | Full context | N/A (unused) |

#### Recommendations for AI Improvements

1. **Switch to GPT-5 Models**
   ```python
   # config.py
   llm_model_fast: str = "gpt-5-nano"   # Quick summaries, parsing
   llm_model_smart: str = "gpt-5-mini"  # Complex analysis, planning
   ```

2. **Use JSON Mode for Structured Output**
   ```python
   # providers.py - Add JSON mode support
   async def completion_json(
       self,
       system: str,
       user: str,
       model: ModelType = ModelType.SMART,
   ) -> Dict[str, Any]:
       response = await self.client.chat.completions.create(
           model=self._get_model(model),
           messages=[...],
           response_format={"type": "json_object"},
       )
       return json.loads(response.choices[0].message.content)
   ```

3. **Add Function Calling for Actions**
   ```python
   # For workout design, use function calling
   tools = [{
       "type": "function",
       "function": {
           "name": "create_workout",
           "parameters": {
               "type": "object",
               "properties": {
                   "name": {"type": "string"},
                   "intervals": {"type": "array", ...},
               }
           }
       }
   }]
   ```

4. **Extend Context for Multi-Sport**
   - Add power zones and FTP to athlete context
   - Add swim CSS and stroke metrics
   - Include sport-specific training history

5. **Use FAST Model for Quick Tasks**
   ```python
   # Currently everything uses SMART - wasteful
   # Use FAST for:
   - Quick summaries
   - Response parsing/extraction
   - Simple Q&A

   # Use SMART for:
   - Workout analysis
   - Plan generation
   - Complex reasoning
   ```

---

### 1B.5 LLM Priority Fixes

| Priority | Issue | Fix |
|----------|-------|-----|
| **Critical** | Wrong model names in config | Change to `gpt-5-nano` / `gpt-5-mini` |
| **High** | No JSON mode | Add `response_format={"type": "json_object"}` |
| **High** | Regex parsing | Replace with JSON mode, remove fallback LLM |
| **Medium** | Running-only context | Add power zones, swim paces to context |
| **Medium** | Hardcoded model strings | Get from LLM client response metadata |
| **Low** | FAST model underutilized | Route simple tasks to FAST model |

---

## Part 1C: Multi-Sport Data Adaptation Analysis

### 1C.1 Current Data Model Limitations

The current `WorkoutData` class (`models/analysis.py:287-400`) only handles running-centric data:

```python
@dataclass
class WorkoutData:
    # What exists:
    activity_type: str = "running"  # Accepts any string but logic assumes running
    pace_sec_per_km: Optional[int] = None  # Running pace only
    cadence: Optional[int] = None  # Running cadence (spm)

    # What's MISSING:
    # avg_power: Optional[int] = None        # Cycling power (watts)
    # normalized_power: Optional[int] = None # NP for cycling
    # avg_speed_kmh: Optional[float] = None  # Speed for cycling/other
    # avg_stroke_rate: Optional[int] = None  # Swim strokes/min
    # avg_swolf: Optional[float] = None      # Swim efficiency
    # pool_length: Optional[int] = None      # 25m or 50m
    # total_strokes: Optional[int] = None    # Swim stroke count
```

### 1C.2 Data Availability Scenarios

The analyzer must handle various incoming data combinations:

| Sport | Scenario | Available Data | Current Handling |
|-------|----------|----------------|------------------|
| **Running** | Full Garmin | HR, pace, cadence, elevation, zones | Works well |
| **Running** | Basic watch | HR, pace only | Works (partial) |
| **Running** | Treadmill | HR only (no GPS) | Broken - assumes pace |
| **Cycling** | Power meter | Power, HR, speed, cadence | **NOT HANDLED** |
| **Cycling** | HR only | HR, speed, elevation | Partially works (HR-based) |
| **Cycling** | Speed only | Speed, cadence, elevation | **NOT HANDLED** |
| **Swimming** | Pool | Time, strokes, SWOLF, laps | **NOT HANDLED** |
| **Swimming** | Open water | HR, distance, time | **NOT HANDLED** |
| **Triathlon** | Brick | Multiple segments | **NOT HANDLED** |

### 1C.3 Database Schema Gaps

**Current schema (`db/schema.py`):**
```sql
CREATE TABLE IF NOT EXISTS activity_metrics (
    activity_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    activity_type TEXT,        -- 'running', 'cycling', etc. but unused
    hrss REAL,                 -- HR-based only
    trimp REAL,                -- HR-based only
    avg_hr INTEGER,
    max_hr INTEGER,
    duration_min REAL,
    distance_km REAL,
    pace_sec_per_km REAL,      -- Running-specific
    zone1_pct ... zone5_pct    -- HR zones only
    -- NO POWER DATA
    -- NO SWIM DATA
    -- NO SPEED DATA
);
```

**Required additions:**
```sql
-- Cycling power metrics
ALTER TABLE activity_metrics ADD COLUMN avg_power INTEGER;
ALTER TABLE activity_metrics ADD COLUMN max_power INTEGER;
ALTER TABLE activity_metrics ADD COLUMN normalized_power INTEGER;
ALTER TABLE activity_metrics ADD COLUMN power_tss REAL;        -- Power-based TSS
ALTER TABLE activity_metrics ADD COLUMN intensity_factor REAL;
ALTER TABLE activity_metrics ADD COLUMN variability_index REAL;

-- Speed-based metrics (cycling, skiing, etc.)
ALTER TABLE activity_metrics ADD COLUMN avg_speed_kmh REAL;
ALTER TABLE activity_metrics ADD COLUMN max_speed_kmh REAL;

-- Swim metrics
ALTER TABLE activity_metrics ADD COLUMN pool_length_m INTEGER;
ALTER TABLE activity_metrics ADD COLUMN total_strokes INTEGER;
ALTER TABLE activity_metrics ADD COLUMN avg_stroke_rate REAL;
ALTER TABLE activity_metrics ADD COLUMN avg_swolf REAL;
ALTER TABLE activity_metrics ADD COLUMN swim_css_pace INTEGER; -- Critical Swim Speed

-- Elevation metrics
ALTER TABLE activity_metrics ADD COLUMN elevation_gain_m REAL;
ALTER TABLE activity_metrics ADD COLUMN elevation_loss_m REAL;

-- Cadence (sport-specific meaning)
ALTER TABLE activity_metrics ADD COLUMN cadence INTEGER;      -- spm for run, rpm for bike
```

### 1C.4 Analyzer Adaptation Strategy

The workout analyzer should detect available data and adapt:

```python
class AdaptiveWorkoutAnalyzer:
    """
    Adapts analysis based on available data.
    """

    def detect_data_profile(self, workout: Dict) -> DataProfile:
        """Detect what data is available for analysis."""
        profile = DataProfile(sport=workout.get('activity_type', 'unknown'))

        # Core metrics
        profile.has_hr = workout.get('avg_hr') is not None
        profile.has_duration = workout.get('duration_min') is not None
        profile.has_distance = workout.get('distance_km') is not None

        # Running-specific
        profile.has_pace = workout.get('pace_sec_per_km') is not None
        profile.has_running_cadence = (
            profile.sport == 'running' and
            workout.get('cadence') is not None
        )

        # Cycling-specific
        profile.has_power = workout.get('avg_power') is not None
        profile.has_np = workout.get('normalized_power') is not None
        profile.has_cycling_cadence = (
            profile.sport == 'cycling' and
            workout.get('cadence') is not None
        )

        # Swim-specific
        profile.has_strokes = workout.get('total_strokes') is not None
        profile.has_swolf = workout.get('avg_swolf') is not None

        # Universal
        profile.has_elevation = workout.get('elevation_gain_m') is not None
        profile.has_speed = workout.get('avg_speed_kmh') is not None

        return profile

    def build_adaptive_prompt(self, workout: Dict, profile: DataProfile) -> str:
        """Build prompt based on available data."""

        if profile.sport == 'cycling':
            if profile.has_power:
                return self._build_power_analysis_prompt(workout)
            elif profile.has_hr:
                return self._build_cycling_hr_prompt(workout)
            else:
                return self._build_cycling_speed_prompt(workout)

        elif profile.sport == 'swimming':
            return self._build_swim_prompt(workout, profile)

        else:  # Running or unknown
            if profile.has_pace and profile.has_hr:
                return self._build_full_running_prompt(workout)
            elif profile.has_hr:
                return self._build_hr_only_prompt(workout)
            else:
                return self._build_minimal_prompt(workout)
```

### 1C.5 Sport-Specific Analysis Metrics

#### Running Analysis (Current - Works)
```python
RUNNING_METRICS = {
    'primary': ['pace', 'hr', 'zone_distribution'],
    'secondary': ['cadence', 'elevation', 'hr_drift'],
    'load': 'HRSS or TRIMP',
    'efficiency': 'pace vs HR (decoupling)',
}
```

#### Cycling Analysis (Needs Implementation)
```python
CYCLING_METRICS = {
    'power_available': {
        'primary': ['avg_power', 'normalized_power', 'intensity_factor'],
        'secondary': ['variability_index', 'power_zones', 'cadence'],
        'load': 'TSS (power-based)',
        'efficiency': 'power:HR ratio, aerobic decoupling',
    },
    'hr_only': {
        'primary': ['hr', 'hr_zones', 'speed'],
        'secondary': ['cadence', 'elevation', 'hr_drift'],
        'load': 'HRSS',
        'efficiency': 'speed vs HR',
    },
    'speed_only': {
        'primary': ['speed', 'elevation', 'cadence'],
        'secondary': ['elevation_per_km', 'speed_variability'],
        'load': 'Estimated from speed/elevation',
        'efficiency': 'speed vs elevation',
    }
}
```

#### Swimming Analysis (Needs Implementation)
```python
SWIMMING_METRICS = {
    'pool': {
        'primary': ['pace_per_100m', 'swolf', 'stroke_rate'],
        'secondary': ['stroke_count', 'rest_time', 'splits'],
        'load': 'Swim TSS (CSS-based)',
        'efficiency': 'SWOLF trend, stroke count stability',
    },
    'open_water': {
        'primary': ['pace', 'hr', 'distance'],
        'secondary': ['stroke_rate', 'sighting_frequency'],
        'load': 'HRSS or distance-based',
        'efficiency': 'pace consistency',
    }
}
```

### 1C.6 Prompt Adaptation Examples

#### Current Prompt (Running-Only)
```python
# prompts.py - Current WORKOUT_ANALYSIS_SYSTEM
"""You are an experienced running coach analyzing a workout...

KEY METRICS TO ANALYZE:
- Pace consistency and whether it matched the workout intent
- Heart rate response vs expected zones
...
"""
```

#### Proposed: Adaptive Sport Prompts

**Cycling with Power:**
```python
CYCLING_POWER_ANALYSIS_SYSTEM = """You are an experienced cycling coach analyzing a ride.

ATHLETE CONTEXT:
{athlete_context}

KEY METRICS TO ANALYZE:
- Power output: Average power, Normalized Power (NP), Intensity Factor (IF)
- Power zones: Time in each power zone, especially sweet spot and threshold
- Variability Index (VI): NP/Avg Power ratio - how steady was the effort?
- Aerobic decoupling: Power:HR ratio first half vs second half
- Cadence patterns: Self-selected vs optimal for terrain
- TSS accumulated vs planned

WHAT TO LOOK FOR:
- Power matching target zones for the workout intent
- VI < 1.05 for steady efforts, higher acceptable for variable terrain
- Decoupling < 5% indicates good aerobic fitness
- Cadence drops may indicate fatigue or incorrect gearing
"""

CYCLING_HR_ONLY_ANALYSIS_SYSTEM = """You are a cycling coach analyzing a ride without power data.

KEY METRICS TO ANALYZE:
- Heart rate zones and distribution
- HR:Speed ratio (pseudo-efficiency)
- Cardiac drift over the ride
- Elevation impact on HR response
- Recovery HR between efforts

NOTE: Without power data, intensity assessment is limited to HR-based metrics.
"""
```

**Swimming:**
```python
SWIM_POOL_ANALYSIS_SYSTEM = """You are an experienced swim coach analyzing a pool session.

ATHLETE CONTEXT:
{athlete_context}

KEY METRICS TO ANALYZE:
- Pace per 100m: Compare to CSS (Critical Swim Speed)
- SWOLF score: Strokes + time per length (efficiency indicator)
- Stroke rate: Consistency across the session
- Stroke count: Stability indicates technique maintenance
- Splits: Negative/positive split pattern
- Rest intervals: Adequate recovery between sets?

WHAT TO LOOK FOR:
- SWOLF staying consistent = maintaining efficiency
- Stroke count creeping up = fatigue affecting technique
- Pace relative to CSS: <CSS = aerobic, >CSS = threshold+
- Last 25m stroke count vs first = fatigue indicator
"""
```

### 1C.7 Implementation Priority

| Priority | Task | Effort |
|----------|------|--------|
| **1. Critical** | Add power fields to WorkoutData model | Low |
| **2. Critical** | Add power columns to database schema | Low |
| **3. High** | Create DataProfile detection class | Medium |
| **4. High** | Add cycling power prompt template | Low |
| **5. High** | Implement power-based TSS calculation | Medium |
| **6. Medium** | Add swim fields to WorkoutData model | Low |
| **7. Medium** | Add swim prompt templates | Low |
| **8. Medium** | Implement SWOLF/CSS calculations | Medium |
| **9. Low** | Add sport-specific context to prompts | Low |

### 1C.8 Recommended WorkoutData Model Update

```python
@dataclass
class WorkoutData:
    """Workout data for analysis - supports multiple sports."""

    # Core identifiers
    activity_id: str
    date: str
    activity_type: str = "running"  # running, cycling, swimming, etc.
    activity_name: str = ""

    # Universal metrics
    duration_min: float = 0.0
    distance_km: float = 0.0
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    calories: Optional[int] = None
    elevation_gain_m: Optional[float] = None
    elevation_loss_m: Optional[float] = None

    # HR zone distribution (universal)
    zone1_pct: float = 0.0
    zone2_pct: float = 0.0
    zone3_pct: float = 0.0
    zone4_pct: float = 0.0
    zone5_pct: float = 0.0

    # HR-based load (universal)
    hrss: Optional[float] = None
    trimp: Optional[float] = None

    # Running-specific
    pace_sec_per_km: Optional[int] = None
    running_cadence: Optional[int] = None  # steps per minute

    # Cycling-specific
    avg_power: Optional[int] = None        # watts
    max_power: Optional[int] = None
    normalized_power: Optional[int] = None
    power_tss: Optional[float] = None      # power-based TSS
    intensity_factor: Optional[float] = None
    variability_index: Optional[float] = None
    cycling_cadence: Optional[int] = None  # rpm
    avg_speed_kmh: Optional[float] = None

    # Swimming-specific
    pool_length_m: Optional[int] = None    # 25 or 50
    total_strokes: Optional[int] = None
    avg_stroke_rate: Optional[float] = None
    avg_swolf: Optional[float] = None
    swim_pace_per_100m: Optional[int] = None  # seconds

    # Computed properties
    @property
    def has_power_data(self) -> bool:
        return self.avg_power is not None

    @property
    def has_swim_data(self) -> bool:
        return self.avg_swolf is not None or self.total_strokes is not None

    @property
    def primary_load_metric(self) -> Optional[float]:
        """Return the best available load metric."""
        if self.power_tss is not None:
            return self.power_tss  # Power TSS is most accurate
        elif self.hrss is not None:
            return self.hrss
        elif self.trimp is not None:
            return self.trimp
        return None

    def to_prompt_data(self) -> str:
        """Convert to formatted string for LLM prompt - sport-adaptive."""
        lines = [
            f"Sport: {self.activity_type}",
            f"Date: {self.date}",
            f"Duration: {self.duration_min:.0f} minutes",
            f"Distance: {self.distance_km:.2f} km",
        ]

        # Add sport-specific metrics
        if self.activity_type == "cycling":
            lines.extend(self._format_cycling_metrics())
        elif self.activity_type == "swimming":
            lines.extend(self._format_swimming_metrics())
        else:  # Running or default
            lines.extend(self._format_running_metrics())

        # Add universal metrics
        lines.extend(self._format_universal_metrics())

        return "\n".join(line for line in lines if line)

    def _format_cycling_metrics(self) -> List[str]:
        lines = []
        if self.avg_power:
            lines.append(f"Avg Power: {self.avg_power} W")
        if self.normalized_power:
            lines.append(f"Normalized Power: {self.normalized_power} W")
        if self.intensity_factor:
            lines.append(f"Intensity Factor: {self.intensity_factor:.2f}")
        if self.power_tss:
            lines.append(f"TSS: {self.power_tss:.0f}")
        if self.avg_speed_kmh:
            lines.append(f"Avg Speed: {self.avg_speed_kmh:.1f} km/h")
        if self.cycling_cadence:
            lines.append(f"Cadence: {self.cycling_cadence} rpm")
        return lines

    def _format_swimming_metrics(self) -> List[str]:
        lines = []
        if self.swim_pace_per_100m:
            mins = self.swim_pace_per_100m // 60
            secs = self.swim_pace_per_100m % 60
            lines.append(f"Pace: {mins}:{secs:02d}/100m")
        if self.avg_swolf:
            lines.append(f"SWOLF: {self.avg_swolf:.0f}")
        if self.avg_stroke_rate:
            lines.append(f"Stroke Rate: {self.avg_stroke_rate:.0f} spm")
        if self.total_strokes:
            lines.append(f"Total Strokes: {self.total_strokes}")
        if self.pool_length_m:
            lines.append(f"Pool: {self.pool_length_m}m")
        return lines

    def _format_running_metrics(self) -> List[str]:
        lines = []
        if self.pace_sec_per_km:
            lines.append(f"Avg Pace: {self.format_pace()}")
        if self.running_cadence:
            lines.append(f"Cadence: {self.running_cadence} spm")
        return lines

    def _format_universal_metrics(self) -> List[str]:
        lines = []
        if self.avg_hr:
            lines.append(f"Avg HR: {self.avg_hr} bpm")
        if self.max_hr:
            lines.append(f"Max HR: {self.max_hr} bpm")
        if any([self.zone1_pct, self.zone2_pct, self.zone3_pct]):
            lines.append(f"HR Zones: {self.format_zone_distribution()}")
        if self.elevation_gain_m:
            lines.append(f"Elevation Gain: {self.elevation_gain_m:.0f} m")
        # Add best load metric
        load = self.primary_load_metric
        if load:
            lines.append(f"Training Load: {load:.0f}")
        return lines
```

---

## Part 2: Feature Completeness Analysis

### 2.1 Existing Features

| Feature | Completeness | Notes |
|---------|--------------|-------|
| LLM Workout Analysis | 85% | Missing persistent cache |
| Training Plans | 80% | In-memory only, no compliance tracking |
| Workout Design + FIT | 75% | No Garmin Connect push, no FIT import |
| Readiness Calculation | 90% | Requires Garmin wellness data |
| Core Metrics (TSS, CTL/ATL/TSB) | 95% | HR-based only, no power |

### 2.2 Underdeveloped Features

#### Goal Management
```typescript
// frontend/src/app/goals/page.tsx:178
// TODO: Call API to create goal
```
Frontend UI exists but API integration incomplete.

#### Plan Persistence
```python
# services/plan_service.py:667
# For now, create a placeholder
```

#### Garmin Connect Integration
- OAuth flow: Not implemented
- Workout push: Not implemented
- Only FIT file download works

#### Strava Integration
Type definitions mention `'strava'` but no actual API integration exists.

### 2.3 Missing Key Features

#### Multi-Sport Support (Critical Gap)

The data model technically supports three sports:
```python
class WorkoutSport(str, Enum):
    RUNNING = "running"
    CYCLING = "cycling"
    SWIMMING = "swimming"
```

**However, all business logic is running-centric:**

| Missing | Evidence |
|---------|----------|
| Cycling workout design | All methods reference pace, not power |
| Power-based TSS | Only HRSS exists |
| Swim metrics | No SWOLF, stroke rate, CSS |
| Triathlon plans | No brick workouts, no multi-sport days |

#### Power-Based Metrics (Cycling)

| Missing Metric | Description |
|----------------|-------------|
| FTP | Functional Threshold Power |
| IF | Intensity Factor |
| NP | Normalized Power |
| TSS | Power-based Training Stress Score |
| Power zones | Not defined |
| W' (W-prime) | Anaerobic capacity |

**Database schema has no power columns:**
```sql
-- Missing from activity_metrics:
avg_power INTEGER,
max_power INTEGER,
normalized_power INTEGER,
tss REAL,
intensity_factor REAL
```

#### Swim-Specific Metrics

| Missing | Description |
|---------|-------------|
| SWOLF | Strokes + time per length |
| Stroke rate | Strokes per minute |
| CSS | Critical Swim Speed (threshold) |
| Pool length | 25m vs 50m handling |

#### Other Missing Features

- Race predictions (VDOT, Riegel formula)
- Advanced periodization (block, mesocycles)
- Mobile PWA / offline support
- Push notifications
- Historical trend visualization

---

## Part 3: Industry Research & Competitive Analysis

### 3.1 Platform Comparison

| Platform | Multi-Sport | AI/Adaptive | Strength | Weakness |
|----------|-------------|-------------|----------|----------|
| **TrainingPeaks** | Excellent | None | Industry standard, coach tools | UI chaos, mobile lacks parity |
| **Strava** | Good | Basic AI summaries | Social, 120M users | AI feels gimmicky |
| **TrainerRoad** | Cycling only | Best-in-class | 27% better workout selection | No swim/run |
| **Intervals.icu** | Excellent | None | Free, powerful | Overwhelming UX |
| **Garmin Connect** | Good | Connect+ AI | Device ecosystem | Requires Garmin hardware |
| **Humango** | Excellent | ChatGPT-based | Triathlon native | "Scheduling not coaching" |
| **Runna** | Running only | Progress monitoring | Expert-designed plans | Expensive, no adaptation |

### 3.2 Must-Have Features

1. Multi-device sync (Garmin, Apple Watch, COROS, Suunto)
2. Training load metrics (TSS, CTL/ATL/TSB)
3. Calendar-based training view
4. Structured workout builder
5. Analytics dashboard
6. Mobile + web parity
7. FIT/GPX import/export
8. HR and power zone configuration
9. Progress tracking (PRs, trends)
10. Workout sync to devices

### 3.3 Market Gaps to Exploit

| Gap | Opportunity |
|-----|-------------|
| **No true adaptive multi-sport AI** | TrainerRoad is cycling-only; Humango is scheduling |
| **Recovery prediction is primitive** | Most apps reactive, not predictive |
| **Post-workout analysis is shallow** | AI summaries feel gimmicky |
| **No unified triathlon periodization** | Apps handle sports separately |
| **Workout building on mobile** | TrainingPeaks users desperately want this |
| **Apple Watch as first-class citizen** | Most prioritize Garmin |

### 3.4 Key Insight

> **No platform combines TrainerRoad-level AI adaptation with true multi-sport triathlon intelligence. This is the biggest market gap.**

---

## Part 4: Strategic Roadmap

### Phase 1: Foundation Fixes (4-6 weeks)

#### LLM Configuration (CRITICAL - Do First)
- [ ] Update `config.py` to use `gpt-5-nano` and `gpt-5-mini`
- [ ] Add JSON mode support to `LLMClient.completion()`
- [ ] Replace regex parsing with JSON mode in `AnalysisAgent`
- [ ] Remove fallback LLM parsing call (saves API costs)
- [ ] Fix hardcoded model names in agent responses

#### Database Persistence
- [ ] Implement Repository pattern
- [ ] Migrate workout storage to SQLite/PostgreSQL
- [ ] Migrate plan storage to database
- [ ] Add analysis result caching to database

#### Code Quality
- [ ] Unify AthleteContext models
- [ ] Fix frontend/backend field naming
- [ ] Add exception handlers for custom errors
- [ ] Fix LLM singleton race condition

#### API Improvements
- [ ] Standardize list response formats (pagination wrapper)
- [ ] Use proper HTTP status codes (201 for POST)
- [ ] Remove/mark unimplemented endpoints

### Phase 2: Multi-Sport Foundation (6-8 weeks)

#### Data Model Extensions
```sql
-- New columns for activity_metrics
ALTER TABLE activity_metrics ADD COLUMN sport_type TEXT;
ALTER TABLE activity_metrics ADD COLUMN avg_power INTEGER;
ALTER TABLE activity_metrics ADD COLUMN max_power INTEGER;
ALTER TABLE activity_metrics ADD COLUMN normalized_power INTEGER;
ALTER TABLE activity_metrics ADD COLUMN tss REAL;
ALTER TABLE activity_metrics ADD COLUMN intensity_factor REAL;

-- New table for power zones
CREATE TABLE power_zones (
    athlete_id TEXT PRIMARY KEY,
    ftp INTEGER,
    zone1_max INTEGER,
    zone2_max INTEGER,
    zone3_max INTEGER,
    zone4_max INTEGER,
    zone5_max INTEGER,
    zone6_max INTEGER,
    zone7_max INTEGER,
    updated_at TIMESTAMP
);

-- New table for swim metrics
CREATE TABLE swim_metrics (
    activity_id TEXT PRIMARY KEY,
    pool_length INTEGER,
    total_strokes INTEGER,
    avg_swolf REAL,
    avg_stroke_rate REAL,
    css_pace INTEGER
);
```

#### Power-Based Metrics Implementation
- [ ] Implement TSS from power data
- [ ] Implement Normalized Power (NP)
- [ ] Implement Intensity Factor (IF)
- [ ] Create power zone calculator
- [ ] Add FTP tracking and estimation

#### Swim Metrics Implementation
- [ ] Implement SWOLF calculation
- [ ] Add stroke rate tracking
- [ ] Implement CSS (Critical Swim Speed)
- [ ] Pool length detection/configuration

### Phase 3: Multi-Sport Workout Design (4-6 weeks)

#### Cycling Workouts
- [ ] Power-based interval design
- [ ] ERG mode workout export
- [ ] Cadence targets
- [ ] Cycling-specific templates (Sweet spot, VO2max, etc.)

#### Swimming Workouts
- [ ] Pool workout structure (sets, reps, rest)
- [ ] Drill integration
- [ ] Pace targets by stroke
- [ ] Swim-specific templates

#### Triathlon Integration
- [ ] Brick workout support
- [ ] Multi-sport day planning
- [ ] Fatigue carryover modeling
- [ ] Race-week tapering across disciplines

### Phase 4: Adaptive Training Intelligence (8-12 weeks)

#### Workout Adaptation Engine
- [ ] Track planned vs. completed workouts
- [ ] Analyze performance trends
- [ ] Predict workout outcomes (simulation)
- [ ] Auto-adjust upcoming workouts

#### Fatigue Prediction
- [ ] ML model on training load + HRV + RPE
- [ ] Predict burnout before it happens
- [ ] ACWR monitoring with alerts (>1.5 danger zone)
- [ ] Recovery time estimation

#### Conversational AI Coach
- [ ] Context-aware recommendations
- [ ] "Given your fatigue and upcoming race, here's what I recommend..."
- [ ] Natural language workout requests
- [ ] Post-workout coaching feedback

### Phase 5: Integration & Mobile (6-8 weeks)

#### Device Integrations
- [ ] Garmin Connect OAuth flow
- [ ] Workout push to Garmin devices
- [ ] Strava API integration
- [ ] Apple Health sync
- [ ] COROS/Suunto sync

#### Mobile Experience
- [ ] PWA configuration
- [ ] Offline workout viewing
- [ ] Mobile-first workout builder
- [ ] Push notifications
- [ ] Apple Watch companion

---

## Part 5: Competitive Positioning

### Recommended Position

> **"The AI training platform that adapts to YOUR life, not the other way around"**

### Target Market Gap

The intersection of:
- TrainerRoad's AI sophistication (but for multi-sport)
- Humango's life-adaptive scheduling (but with deeper coaching)
- Intervals.icu's powerful analytics (but with AI interpretation)
- Mobile-first experience (unlike TrainingPeaks)

### Key Differentiator

> "While other apps give you a plan and hope you follow it, or make you test every 8 weeks to know your fitness, we continuously learn from every workout to predict your optimal training - before you burn out, get injured, or plateau."

---

## Appendix A: File Reference

### Backend Critical Files
| File | Purpose |
|------|---------|
| `src/training_analyzer/config.py` | **Settings including LLM model names (NEEDS FIX)** |
| `src/training_analyzer/llm/providers.py` | LLM client with retry logic |
| `src/training_analyzer/llm/prompts.py` | All prompt templates (well-designed) |
| `src/training_analyzer/llm/context_builder.py` | Athlete context for prompts |
| `src/training_analyzer/agents/analysis_agent.py` | Workout analysis (uses regex parsing) |
| `src/training_analyzer/agents/plan_agent.py` | Plan generation |
| `src/training_analyzer/agents/workout_agent.py` | Workout design |
| `src/training_analyzer/models/*.py` | Data models (need unification) |
| `src/training_analyzer/api/routes/*.py` | FastAPI endpoints |
| `src/training_analyzer/metrics/*.py` | Fitness calculations |
| `src/training_analyzer/fit/encoder.py` | FIT file generation |
| `src/training_analyzer/db/schema.py` | Database schema (needs extension) |

### Frontend Critical Files
| File | Purpose |
|------|---------|
| `frontend/src/lib/types.ts` | TypeScript types |
| `frontend/src/lib/api-client.ts` | API client (660 lines) |
| `frontend/src/hooks/*.ts` | React Query hooks |
| `frontend/src/components/design/*.tsx` | Workout designer |
| `frontend/src/components/plans/*.tsx` | Plan management |

---

## Appendix B: Research Sources

- [TrainingPeaks Official](https://www.trainingpeaks.com/)
- [TrainerRoad Adaptive Training](https://www.trainerroad.com/adaptive-training)
- [Intervals.icu](https://intervals.icu/)
- [Humango AI Coach](https://humango.ai/)
- [Strava Features](https://support.strava.com/hc/en-us/articles/216917657)
- [Garmin Connect+](https://www.dcrainmaker.com/2025/03/garmin-connect-plus-subscription-walkthrough.html)
- [AI Endurance Training Research](https://umit.net/ai-endurance-training-research-summary/)
- [Triathlon Training Apps Review](https://www.triathlete.com/gear/tech-wearables/ai-triathlon-training-apps/)

---

*Document generated by Claude Code analysis agents*
