# Metrics Explained

This document provides a deep dive into how each training metric is calculated in the Training Analyzer.

---

## The Core Philosophy

> **Train smarter, not just harder.**

The Training Analyzer uses established sports science models to help you:
1. **Avoid overtraining** - Monitor injury risk with ACWR
2. **Optimize performance** - Peak at the right time with TSB
3. **Personalize training** - Use YOUR data, not population averages

---

## Fitness-Fatigue Model (Banister Model)

The foundation of the system is the **Impulse-Response Model** developed by Banister et al. This models training as having two effects:

1. **Fitness** - Positive effect, builds slowly, decays slowly
2. **Fatigue** - Negative effect, builds fast, decays fast

```
Performance = Fitness - Fatigue + Baseline
```

### CTL (Chronic Training Load) = "Fitness"

**What it measures:** Your long-term training load, representing accumulated fitness.

**Calculation:** 42-day Exponentially Weighted Moving Average (EWMA)

```python
decay = e^(-1/42)  # ≈ 0.9765
CTL_today = CTL_yesterday * decay + today's_load * (1 - decay)
```

**Interpretation:**
- Higher CTL = More trained, higher sustainable workload
- Building CTL takes weeks/months
- Dropping CTL quickly (>10%/week) risks detraining

| CTL Level | Training Status |
|-----------|-----------------|
| < 20 | Untrained/detrained |
| 20-40 | Recreational |
| 40-60 | Regular trainer |
| 60-80 | Serious athlete |
| 80-100 | Advanced |
| 100+ | Elite/Professional |

---

### ATL (Acute Training Load) = "Fatigue"

**What it measures:** Your short-term training load, representing accumulated fatigue.

**Calculation:** 7-day EWMA

```python
decay = e^(-1/7)  # ≈ 0.8668
ATL_today = ATL_yesterday * decay + today's_load * (1 - decay)
```

**Interpretation:**
- Higher ATL = More fatigued
- ATL responds quickly to training changes
- High ATL without recovery = overreaching

---

### TSB (Training Stress Balance) = "Form"

**What it measures:** The balance between fitness and fatigue, indicating readiness to perform.

**Calculation:**
```
TSB = CTL - ATL
```

**Interpretation:**

| TSB | State | Recommendation |
|-----|-------|----------------|
| > +25 | Very fresh | Risk of detraining if prolonged |
| +10 to +25 | Fresh | Good for racing/testing |
| 0 to +10 | Optimal | Balance of fitness and freshness |
| -10 to 0 | Neutral | Normal training state |
| -25 to -10 | Fatigued | Absorbing training, need recovery |
| < -25 | Very fatigued | Risk of overtraining |

**Taper Effect:**
To peak for a race, reduce training to let ATL drop while CTL stays high.
A 2-3 week taper typically yields TSB of +15 to +25.

---

### ACWR (Acute:Chronic Workload Ratio) = "Injury Risk"

**What it measures:** The ratio of recent training to long-term training, used to predict injury risk.

**Calculation:**
```
ACWR = ATL / CTL
```

**Interpretation:** Based on Gabbett (2016) research:

| ACWR | Zone | Risk Level |
|------|------|------------|
| < 0.8 | Undertrained | Low injury risk, but not optimally training |
| 0.8 - 1.3 | **Optimal** | Sweet spot for adaptation |
| 1.3 - 1.5 | Caution | Elevated injury risk |
| > 1.5 | Danger | High injury risk |

**Key insight:** The "optimal" zone allows for progressive overload while minimizing injury risk.

---

## Training Load Metrics

### HRSS (Heart Rate Stress Score)

**What it measures:** Training load based on heart rate intensity and duration.

**Calculation:**
```python
# Based on TRIMP (Training Impulse) modified for zones
# Using Stagno's modified method

# For each minute of exercise:
HRSS_per_minute = (HR_fraction)² * duration_minutes

# Where HR_fraction = (HR - rest_HR) / (max_HR - rest_HR)
```

**Example:**
- 60 min at 70% HR reserve ≈ HRSS 50
- 45 min at 85% HR reserve ≈ HRSS 60
- 30 min at 95% HR reserve ≈ HRSS 55

### TRIMP (Training Impulse)

**What it measures:** Volume × Intensity with exponential weighting.

**Calculation (Banister's formula):**
```python
TRIMP = duration_min * HR_fraction * 0.64 * e^(1.92 * HR_fraction)
```

Where `HR_fraction = (avg_HR - rest_HR) / (max_HR - rest_HR)`

---

## Heart Rate Zones

### Karvonen Method (Heart Rate Reserve)

Uses the "reserve" between resting and max HR for personalized zones.

**Calculation:**
```python
HR_reserve = max_HR - rest_HR
zone_hr = rest_HR + (HR_reserve * zone_percent)
```

**Zones:**

| Zone | % of HRR | Name | Purpose |
|------|----------|------|---------|
| 1 | 50-60% | Recovery | Active recovery, easy breathing |
| 2 | 60-70% | Aerobic | Base building, conversational |
| 3 | 70-80% | Tempo | Lactate threshold, comfortably hard |
| 4 | 80-90% | Threshold | Hard, 20-30 min sustainable |
| 5 | 90-100% | VO2max | Very hard, 3-8 min efforts |

**Example:** Max HR = 185, Rest HR = 55
- HR Reserve = 130
- Zone 2 (60-70%) = 133-146 bpm

### LTHR Method (Lactate Threshold)

Uses lactate threshold HR as the anchor point.

**Zones (Joe Friel's system):**

| Zone | % of LTHR | Name |
|------|-----------|------|
| 1 | 65-80% | Recovery |
| 2 | 80-89% | Aerobic |
| 3 | 89-93% | Tempo |
| 4 | 93-99% | Threshold |
| 5a | 99-102% | VO2max |
| 5b | 102-106% | Anaerobic |

---

## Readiness Score (0-100)

### What It Answers
> "How ready is my body to train hard today?"

### Calculation

Weighted average of multiple factors:

```python
readiness = (
    hrv_score * 0.25 +      # HRV vs baseline
    sleep_score * 0.20 +    # Sleep quality
    body_battery * 0.15 +   # Garmin Body Battery
    stress_score * 0.10 +   # Inverse of stress
    training_load * 0.20 +  # TSB/ACWR combined
    recovery_days * 0.10    # Days since hard workout
)
```

### Factor Details

#### HRV Score (25%)

```python
ratio = last_night_hrv / weekly_avg_hrv

if ratio >= 1.2:
    score = 100
elif ratio >= 1.0:
    score = 75 + (ratio - 1.0) * 125
elif ratio >= 0.7:
    score = 50 + (ratio - 0.7) * 83
else:
    score = max(0, ratio * 50)
```

#### Sleep Score (20%)

```python
# Duration component (85%)
duration_ratio = min(1.0, sleep_hours / target_hours)
duration_score = duration_ratio * 85

# Deep sleep component (15%)
deep_ratio = min(1.0, deep_sleep_pct / 20)
deep_score = deep_ratio * 15

score = duration_score + deep_score
```

#### Training Load Score (20%)

Combines TSB and ACWR:

```python
# TSB component (60%)
if tsb > 20:
    tsb_score = 100
elif tsb > 0:
    tsb_score = 70 + (tsb / 20) * 30
elif tsb > -10:
    tsb_score = 50 + (tsb / 10) * 20
else:
    tsb_score = max(0, 30 + (tsb + 25) * 2)

# ACWR component (40%)
if 0.8 <= acwr <= 1.3:
    acwr_score = 100 - abs(acwr - 1.0) * 50
elif acwr < 0.8:
    acwr_score = 50 + (acwr / 0.8) * 30
else:
    acwr_score = 60 - ((acwr - 1.3) / 0.2) * 30

score = tsb_score * 0.6 + acwr_score * 0.4
```

### Readiness Zones

| Zone | Score | Training Recommendation |
|------|-------|-------------------------|
| 🟢 Green | 67-100% | Great day for quality/hard training |
| 🟡 Yellow | 34-66% | Moderate intensity, avoid all-out |
| 🔴 Red | 0-33% | Rest or very light activity |

---

## Training Paces (VDOT-based)

### VDOT Calculation

Estimates running "velocity at VO2max" from race performance.

**From race time:**
```python
# Simplified Daniels' formula
vdot = f(race_distance, race_time)
```

### Training Paces from VDOT

| Pace Type | % of VDOT pace | Purpose |
|-----------|----------------|---------|
| Easy | 59-74% | Recovery, base building |
| Long | 67-79% | Extended aerobic endurance |
| Threshold | 83-88% | Lactate threshold improvement |
| Interval | 95-100% | VO2max development |
| Repetition | 105-110% | Speed and economy |

**Example:** VDOT 50 (≈ 40:00 10K)
- Easy pace: 5:30-6:00/km
- Threshold pace: 4:30-4:45/km
- Interval pace: 4:00-4:10/km

---

## Periodization

### Training Phases

| Phase | Focus | Load | Quality |
|-------|-------|------|---------|
| **Base** | Aerobic foundation | Building | Low intensity |
| **Build** | Specific fitness | Peak | Increasing intensity |
| **Peak** | Race-specific | Maintaining | High quality |
| **Taper** | Freshness | Decreasing | Sharpening |

### Load Progression (10% Rule)

Increase weekly load by no more than 10% per week to minimize injury risk.

```python
max_next_week_load = current_week_load * 1.10
```

### Cutback Weeks

Every 3-4 weeks, reduce load by 20-30% to allow adaptation.

```python
if week_number % 4 == 0:
    target_load = normal_load * 0.70  # Cutback week
```

---

## Key Formulas Reference

| Metric | Formula |
|--------|---------|
| CTL | `CTL_n = CTL_{n-1} × e^(-1/42) + load × (1 - e^(-1/42))` |
| ATL | `ATL_n = ATL_{n-1} × e^(-1/7) + load × (1 - e^(-1/7))` |
| TSB | `CTL - ATL` |
| ACWR | `ATL / CTL` |
| HR Zone | `rest_hr + (max_hr - rest_hr) × zone_pct` |
| HRSS | `Σ (HR_fraction² × duration)` |
| Max HR (Tanaka) | `208 - (0.7 × age)` |
| LTHR estimate | `max_hr × 0.90` |

---

## See Also

- [Architecture](./architecture.md) - How components work together
- [API Reference](./api-reference.md) - Access these metrics via API
- [Getting Started](./getting-started.md) - Start using the system



