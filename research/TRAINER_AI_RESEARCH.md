# Building an AI Training Coach: Comprehensive Research Report

*Research completed December 25, 2025*

---

## Executive Summary

This document synthesizes research on building a workout analysis tool that acts as a personal trainer. The key insight from studying Runna and competitors is:

> **The best training tools are decision tools, not analysis tools.**

Garmin already provides raw data. The opportunity is to **interpret that data into actionable decisions**: "What should I do next to improve?"

### Your Existing Foundation

You already have:
- **Garmin data ingestion** via garth library + n8n workflows
- **Wellness metrics**: sleep, HRV, stress, Body Battery, resting HR
- **Activity data**: pace, HR, cadence, distance, Training Effect, VO2max
- **WHOOP-style recovery scoring** (already implemented!)
- **SQLite + n8n tables** for storage
- **Next.js dashboard** ready for expansion

This is a solid foundation. The next step is building the **intelligence layer**.

---

## Part 1: What to Learn from Runna

### The Core Philosophy

Runna succeeds because it answers one question extremely well:

> "What should I do today to reach my goal?"

Key design decisions:
1. **Opinionated over flexible** — tells users exactly what to do
2. **Invisible complexity** — algorithms hidden behind simple outputs
3. **Garmin as sensor, not brain** — pulls data, pushes workouts, but owns the thinking
4. **Success = completion** — not optimization of metrics

### How Runna Actually Works

**Plan Generation:**
- 26-step onboarding collects: goal race, distance, date, current ability, available days
- A single race time (5K/10K/half) drives ALL pace calculations (similar to VDOT)
- Coaches design the plan templates; AI handles monitoring and insights

**Pace Calculation:**
All paces derived from one input:
```
Easy Pace = Race Pace + 60-90 sec/km
Tempo Pace = Race Pace + 20-30 sec/km
Interval Pace = Race Pace - 10-20 sec/km
Long Run Pace = Race Pace + 45-75 sec/km
```

**Adaptation (Current Limitations):**
- Does NOT auto-adjust based on workout performance
- Users must manually update race time estimate
- "Pace Insights" AI monitors trends and recommends adjustments
- Athletes accept or reject suggested changes

### Runna's Gaps (Your Opportunities)

| Runna Weakness | Your Opportunity |
|----------------|------------------|
| No automatic adaptation | True adaptive training from actual workout data |
| No HRV/recovery integration | Use your existing WHOOP-style recovery |
| No power meter support | Integrate Stryd/Garmin Running Power |
| Doesn't account for fatigue | Factor in Body Battery, sleep, stress |
| Black-box decisions | Explainable AI: "Why this workout?" |

---

## Part 2: Sports Science Foundations

### Training Load Management (Critical to Implement)

**Acute:Chronic Workload Ratio (ACWR)**
```python
ACWR = acute_load_7_days / chronic_load_28_days

# Risk zones:
# < 0.8  = Undertrained (detraining risk)
# 0.8-1.3 = Sweet spot (optimal)
# > 1.3  = Danger zone (injury risk)
# > 1.5  = High danger (significantly elevated risk)
```

**Training Stress Score (TSS) / TRIMP**
```python
# Heart rate-based TRIMP (simpler to implement)
def calculate_trimp(duration_min, avg_hr, rest_hr, max_hr):
    delta_hr = (avg_hr - rest_hr) / (max_hr - rest_hr)
    # Men's formula (use 0.86, 1.67 for women)
    return duration_min * delta_hr * 0.64 * math.exp(1.92 * delta_hr)
```

**Fitness-Fatigue Model (CTL/ATL/TSB)**
```python
# Chronic Training Load (Fitness) - 42-day decay
CTL_today = CTL_yesterday * exp(-1/42) + TSS_today * (1 - exp(-1/42))

# Acute Training Load (Fatigue) - 7-day decay
ATL_today = ATL_yesterday * exp(-1/7) + TSS_today * (1 - exp(-1/7))

# Training Stress Balance (Form)
TSB = CTL - ATL

# TSB Guidelines:
# -10 to -30: Normal training
# 0 to +15: Recovery/race ready
# +5 to +15: Optimal race day form
```

### Heart Rate Zones (Multiple Methods)

**Karvonen (Heart Rate Reserve)**
```python
def karvonen_zone(intensity_pct, max_hr, rest_hr):
    return ((max_hr - rest_hr) * intensity_pct) + rest_hr

# Zones:
# Z1: 50-60% HRR (Recovery)
# Z2: 60-70% HRR (Aerobic base)
# Z3: 70-80% HRR (Tempo)
# Z4: 80-90% HRR (Threshold)
# Z5: 90-100% HRR (VO2max)
```

**LTHR-Based (More Accurate)**
```python
# From 30-min time trial: LTHR = avg_hr_last_20_min * 0.95
# Zones as % of LTHR:
# Z1: <80%, Z2: 81-89%, Z3: 90-93%, Z4: 94-99%, Z5: 100%+
```

### Race Time Prediction

**Riegel Formula**
```python
def predict_race_time(known_time_sec, known_dist_km, target_dist_km, exponent=1.06):
    return known_time_sec * (target_dist_km / known_dist_km) ** exponent

# Exponent variations:
# 1.06 = Standard recreational
# 1.07 = World record extrapolation
# 1.15 = Conservative for marathons
```

**VDOT-Based Paces**
From a race performance, derive all training paces:
- Easy: 59-74% VO2max
- Marathon: 75-84% VO2max
- Threshold: 83-88% VO2max
- Interval: 95-100% VO2max
- Repetition: 105-120% VO2max

### Periodization Models

**Polarized Training (80/20)** — Most evidence-based for endurance:
- 75-80% of training at low intensity (Zone 1-2)
- ~5% at threshold (Zone 3)
- 15-20% at high intensity (Zone 4-5)

**Recovery Indicators**
```python
# HRV-based training adjustment:
# - If HRV below SWC (Smallest Worthwhile Change): reduce intensity
# - If HRV stable/rising: proceed as planned
# - Use 7-day rolling average, not daily values

# Heart Rate Recovery (fitness indicator):
HRR = peak_hr - hr_at_1_min_post_exercise
# >18 bpm = good recovery
# >30 bpm = elite level
```

---

## Part 3: Garmin Data That Actually Matters

### Tier 1: Essential (High Confidence)

| Metric | Why It Matters | Implementation |
|--------|----------------|----------------|
| **Heart Rate** | Training intensity | Calculate zones, time-in-zone |
| **Pace** | Performance tracking | Trend analysis, zone compliance |
| **Distance/Duration** | Volume tracking | Weekly totals, load calculation |
| **Cadence** | Form consistency | Track changes over time |
| **Training Effect** | Workout classification | Already in your data! |
| **VO2max Trend** | Fitness direction | Track 7-day rolling average |

### Tier 2: Useful Context (Use With Caution)

| Metric | Caveats | How to Use |
|--------|---------|------------|
| **HRV Status** | Sleep-only, needs 3-week baseline | 7-day trends, not daily values |
| **Body Battery** | No validation, subjective | Recovery indicator input |
| **Recovery Time** | Directional only | Combine with other signals |
| **Training Load** | EPOC-based, reasonable | ACWR calculation |

### Tier 3: Ignore for Training Decisions

- **Sleep Stages**: 40-50% accuracy (worst performing metric)
- **Absolute VO2max**: 1-13.5% error; only track *direction*
- **Training Status**: Too composite, black-box

### Data You Already Collect (Your Advantage)

From your codebase analysis:

**Wellness (daily):**
- Sleep: total hours, deep/light/REM, sleep score, efficiency
- HRV: weekly average, last night, baseline comparisons
- Stress: average, max, duration by level
- Body Battery: charged/drained amounts
- Resting HR: end-of-day baseline
- Training Readiness score

**Activities (per workout):**
- Distance, duration, pace
- HR: avg, max
- Cadence
- Elevation gain/loss
- Training Effect (aerobic + anaerobic)
- VO2max estimate
- Full raw JSON for enrichment

---

## Part 4: Competitive Landscape

### Competitor Positioning

| Platform | Philosophy | Key Innovation | Weakness |
|----------|------------|----------------|----------|
| **TrainingPeaks** | Quantified stress (TSS/CTL) | Industry-standard metrics | Steep learning curve |
| **TrainerRoad** | ML-adaptive intervals | Progression Levels | Indoor cycling only |
| **Whoop** | Recovery-first | HRV readiness | No workout prescription |
| **Strava** | Social motivation | Community/segments | Weak coaching |
| **Runna** | Opinionated plans | Simple execution | No auto-adaptation |
| **Humango** | AI-first planning | Schedule flexibility | Overwhelming UX |

### Market Gaps (Your Opportunities)

1. **Transparency**: Users hate "black box" algorithms
2. **Holistic stress**: No one integrates work/life stress with training
3. **Beginner-friendly**: Most tools optimize for advanced athletes
4. **Multi-source aggregation**: Athletes use multiple tools
5. **True adaptation**: Runna doesn't auto-adjust; TrainerRoad is cycling-only

---

## Part 5: Product Architecture Recommendations

### Core Philosophy

```
┌─────────────────────────────────────────────────────────────┐
│                     YOUR PRODUCT                             │
│                                                              │
│   ┌─────────┐    ┌─────────────┐    ┌──────────────────┐    │
│   │ SENSORS │ →  │ INTELLIGENCE│ →  │    DECISIONS     │    │
│   │ (Garmin)│    │   (You)     │    │     (You)        │    │
│   └─────────┘    └─────────────┘    └──────────────────┘    │
│        ↓              ↓                    ↓                 │
│   Raw metrics    Interpretation      "Do this today"        │
│   HR, pace,      Load, recovery,     Easy 5K because        │
│   power, HRV     readiness, trends   yesterday was hard     │
└─────────────────────────────────────────────────────────────┘
```

### Recommended System Architecture

```
Layer 1: Data Ingestion (DONE)
├── Garmin wellness data (via garth)
├── Garmin activities (via n8n)
└── Historical data (backfill workflow)

Layer 2: Feature Calculation (BUILD NEXT)
├── Daily TSS/TRIMP from workouts
├── Rolling CTL (42-day) and ATL (7-day)
├── ACWR with risk zones
├── HR zone time distribution
├── Weekly volume trends
├── Performance benchmarks (pace at HR)

Layer 3: Recovery Assessment (PARTIALLY DONE)
├── WHOOP-style recovery score (EXISTS!)
├── + Sleep quality factor
├── + HRV trend analysis
├── + Training load factor
└── Combined "Readiness Score"

Layer 4: Decision Engine (BUILD)
├── Today's workout type (easy/tempo/intervals/rest)
├── Target intensity (pace/HR zones)
├── Duration recommendation
├── "Why this workout" explanation

Layer 5: Presentation (ENHANCE)
├── Dashboard with today's recommendation
├── Weekly view with load visualization
├── Trend analysis (fitness, fatigue, form)
└── Natural language summaries
```

### Key Algorithms to Implement

**1. Daily Readiness Score (0-100)**
```python
def calculate_readiness(wellness_data, recent_activities):
    # Weight factors (tune based on research)
    WEIGHTS = {
        'hrv_vs_baseline': 0.25,
        'sleep_score': 0.20,
        'body_battery': 0.15,
        'training_load_balance': 0.20,
        'acwr': 0.20
    }

    # HRV factor (your existing calculation)
    hrv_factor = hrv_vs_baseline_ratio * 100

    # Sleep factor
    sleep_factor = min(100, (sleep_hours / 8) * sleep_quality)

    # Body Battery factor
    bb_factor = body_battery_morning  # Already 0-100

    # Training load balance (inverse of absolute TSB)
    tsb_factor = 100 - min(100, abs(tsb) * 2)

    # ACWR factor (optimal at 1.0)
    acwr_factor = 100 - (abs(acwr - 1.0) * 50)

    return weighted_average(factors, WEIGHTS)
```

**2. Workout Type Decision**
```python
def recommend_workout(readiness, acwr, last_workouts):
    # If recovering, always easy
    if readiness < 40:
        return "rest_or_easy"

    # If overreaching, back off
    if acwr > 1.3:
        return "easy"

    # Count hard days in last 7
    hard_days = count_hard_workouts(last_workouts, days=7)

    # Follow hard/easy patterns
    if yesterday_was_hard(last_workouts):
        return "easy"

    # If undertraining, can push
    if acwr < 0.8 and readiness > 70:
        return "tempo_or_intervals"

    # Normal training logic based on plan phase
    return select_from_periodization(phase, day_of_week)
```

**3. Natural Language Explanation**
```python
def explain_workout(workout_type, factors):
    reasons = []

    if factors['acwr'] > 1.2:
        reasons.append(f"Your training load is elevated (ACWR: {factors['acwr']:.1f})")

    if factors['sleep_hours'] < 7:
        reasons.append(f"You only got {factors['sleep_hours']:.1f} hours of sleep")

    if factors['yesterday_was_hard']:
        reasons.append("Yesterday was a hard session")

    if workout_type == "easy":
        return f"Today is an easy day because: {'; '.join(reasons)}"
    else:
        return f"You're ready for quality work: recovery is good, load is balanced"
```

---

## Part 6: Feature Prioritization

### Phase 1: Foundation (Weeks 1-2)
*Build the intelligence layer*

- [ ] Calculate daily TSS/TRIMP from activity data
- [ ] Implement CTL/ATL/TSB rolling calculations
- [ ] Calculate ACWR with risk zone alerts
- [ ] HR zone time-in-zone analysis per workout
- [ ] Enhance recovery score with load factor

### Phase 2: Decision Engine (Weeks 3-4)
*Turn analysis into recommendations*

- [ ] Daily workout type recommendation
- [ ] Target HR/pace zones for recommended workout
- [ ] "Why this workout" natural language explanation
- [ ] Weekly load targets and progress

### Phase 3: Planning (Weeks 5-6)
*Goal-oriented training*

- [ ] Race goal setting (distance, date, target time)
- [ ] VDOT-based pace zone calculation
- [ ] Periodization phase detection
- [ ] Countdown to race with readiness projection

### Phase 4: Intelligence (Weeks 7-8)
*Learn from your training*

- [ ] Performance trend analysis (pace at HR over time)
- [ ] Pattern recognition (best training days, optimal load)
- [ ] Anomaly detection (unusual workouts, concerning trends)
- [ ] AI-generated weekly summaries

### Features to NOT Build (Deliberately)

Based on Runna's success with constraints:

| Don't Build | Why |
|-------------|-----|
| Complex charts during workout | Decision fatigue |
| Deep post-run analysis screens | Redundant with Garmin |
| "Choose your own adventure" plans | Users don't want to think |
| Detailed sleep stage analysis | Garmin's accuracy is poor |
| Calorie counting/nutrition | Out of scope, solved elsewhere |
| Social features | Strava owns this |

---

## Part 7: Differentiation Strategy

### Your Unique Position

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│   TrainingPeaks         Runna           YOUR TOOL          │
│   ─────────────         ─────           ─────────          │
│   "Analyze deeply"      "Just follow"   "Understand &      │
│   (for coaches)         (for beginners)  master"           │
│                                         (for engaged       │
│                                          athletes)         │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Key Differentiators

1. **Transparent AI**
   - "Why this workout" explanations
   - Show the math behind recommendations
   - Build trust through understanding

2. **True Adaptation**
   - Automatically adjust based on actual performance
   - Factor in recovery (you already have the data!)
   - No manual race time updates needed

3. **Holistic Readiness**
   - Combine training load + recovery + wellness
   - Already have HRV, sleep, Body Battery, stress
   - Unified readiness score

4. **Coach-Like Narrative**
   - Weekly summaries in natural language
   - Pattern recognition over months
   - "Here's what's working, here's what to adjust"

5. **Multi-Source Intelligence**
   - Garmin data as primary source
   - Room to add Whoop, Oura, etc.
   - Best-in-class for each signal

---

## Part 8: Implementation Checklist

### Immediate Next Steps

```
□ Stage 2 (per PROJECT_PLAN.md): Enrich activity data
  ├── HR zone time calculation
  ├── Pace zone compliance
  ├── Cardiac drift analysis
  └── Per-workout TSS/TRIMP

□ Build fitness-fatigue model
  ├── Daily TSS calculation
  ├── CTL (42-day rolling)
  ├── ATL (7-day rolling)
  └── TSB and ACWR

□ Enhance recovery score
  ├── Add training load factor
  ├── Add ACWR influence
  └── Unified "Readiness" output

□ Build decision engine
  ├── Workout type selector
  ├── Intensity recommender
  └── Explanation generator
```

### Database Schema Additions

```sql
-- Add to activity processing
ALTER TABLE activities ADD COLUMN tss REAL;
ALTER TABLE activities ADD COLUMN trimp REAL;
ALTER TABLE activities ADD COLUMN hr_zone_1_pct REAL;
ALTER TABLE activities ADD COLUMN hr_zone_2_pct REAL;
ALTER TABLE activities ADD COLUMN hr_zone_3_pct REAL;
ALTER TABLE activities ADD COLUMN hr_zone_4_pct REAL;
ALTER TABLE activities ADD COLUMN hr_zone_5_pct REAL;

-- New table for fitness tracking
CREATE TABLE fitness_metrics (
    date TEXT PRIMARY KEY,
    ctl REAL,           -- Chronic Training Load
    atl REAL,           -- Acute Training Load
    tsb REAL,           -- Training Stress Balance
    acwr REAL,          -- Acute:Chronic Workload Ratio
    readiness_score REAL,
    recommended_workout TEXT,
    recommendation_reason TEXT
);
```

---

## Appendix: Key Formulas Reference

```python
# TSS (Training Stress Score)
TSS = (duration_sec * NP * IF) / (FTP * 3600) * 100

# TRIMP (simpler, HR-based)
delta_hr = (avg_hr - rest_hr) / (max_hr - rest_hr)
TRIMP = duration_min * delta_hr * 0.64 * exp(1.92 * delta_hr)

# CTL (Chronic Training Load, 42-day)
CTL = CTL_prev * exp(-1/42) + TSS * (1 - exp(-1/42))

# ATL (Acute Training Load, 7-day)
ATL = ATL_prev * exp(-1/7) + TSS * (1 - exp(-1/7))

# TSB (Training Stress Balance)
TSB = CTL - ATL

# ACWR (Acute:Chronic Workload Ratio)
ACWR = ATL / CTL  # or sum of 7-day / avg of 28-day

# Riegel Race Predictor
T2 = T1 * (D2/D1)^1.06

# Karvonen HR Zone
target_hr = ((max_hr - rest_hr) * intensity_pct) + rest_hr

# Max HR estimate
max_hr = 208 - (0.7 * age)  # Tanaka formula
```

---

## Sources

### Sports Science
- Banister et al. (1976) - Fitness-Fatigue Model
- Coggan & Allen - TSS/Power-based training
- Jack Daniels - VDOT Running Formula
- Tim Gabbett - ACWR Research
- Seiler - Polarized Training Model

### Competitors
- TrainingPeaks documentation
- TrainerRoad Adaptive Training
- Whoop methodology
- Runna user research

### Garmin
- Firstbeat Analytics whitepapers
- Garmin FIT SDK documentation
- garminconnect Python library

---

*This research document serves as the foundation for building an AI training coach that goes beyond analysis to become a true decision tool.*
