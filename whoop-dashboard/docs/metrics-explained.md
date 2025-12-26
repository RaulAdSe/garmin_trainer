# Metrics Explained

This document provides a deep dive into how each metric in the WHOOP Dashboard is calculated and what it means for your training and recovery.

---

## The Core Philosophy

> **Raw physiology → Personal baseline → Physiological state → Single decision**

Unlike traditional dashboards that show raw numbers, this system:
1. Compares everything to **YOUR** personal baselines
2. Weights metrics by their physiological importance
3. Condenses complexity into **one actionable decision**

---

## Recovery Score (0-100%)

### What It Answers
> "How ready is my body today?"

### Calculation

Recovery is a weighted average of three factors:

```
Recovery = (HRV_score × 1.5 + Sleep_score × 1.0 + BB_score × 1.0) / 3.5
```

#### HRV Factor (Weight: 1.5x)

HRV is the **primary signal** for autonomic nervous system state.

```
hrv_ratio = today's_hrv / your_7day_avg_hrv
hrv_score = min(100, max(0, hrv_ratio × 80 + 20))
```

- **At baseline (ratio = 1.0)**: Score = 100
- **20% below baseline (ratio = 0.8)**: Score = 84
- **20% above baseline (ratio = 1.2)**: Score = 100 (capped)

#### Sleep Factor (Weight: 1.0x)

```
sleep_ratio = actual_hours / your_7day_avg_hours
sleep_score = min(100, max(0, sleep_ratio × 85 + 15))
```

- **At your baseline**: Score ≈ 100
- **25% below baseline**: Score ≈ 78
- **Sleep quality (deep/REM)** contributes to overall sleep hours effectiveness

#### Body Battery Factor (Weight: 1.0x)

Garmin's Body Battery (0-100) is used directly:
```
bb_score = body_battery_charged_overnight
```

### Recovery Zones

| Zone | Range | Interpretation |
|------|-------|----------------|
| 🟢 GREEN | 67-100% | Fully recovered, body primed for intensity |
| 🟡 YELLOW | 34-66% | Partially recovered, moderate effort safe |
| 🔴 RED | 0-33% | Under-recovered, focus on rest |

---

## Strain Score (0-21)

### What It Answers
> "How much did I stress my body today?"

### Calculation

Strain uses a **logarithmic-like scale** to prevent overtraining:

```
strain = 0
strain += min(8, steps / 2000)              # Max 8 from walking
strain += min(8, body_battery_drained / 12) # Max 8 from energy use
strain += min(5, intensity_minutes / 20)    # Max 5 from exercise
strain = min(21, total)
```

### Why Logarithmic?

Going from strain 5→6 is easy. Going from 18→19 is **extremely hard**. This prevents ego-driven overtraining.

| Strain | Effort Level | Example Day |
|--------|--------------|-------------|
| 0-8 | Light | Rest day, walking only |
| 8-14 | Moderate | Steady workout, active day |
| 14-18 | Hard | Tough training session |
| 18-21 | All-out | Race, competition, extreme effort |

### Strain Targets

Based on recovery, your target strain is:

| Recovery | Target Strain | Recommendation |
|----------|---------------|----------------|
| 🟢 67%+ | 14-21 | Intervals, racing, PRs |
| 🟡 34-66% | 8-14 | Steady cardio, technique |
| 🔴 <34% | 0-8 | Recovery activities only |

---

## Sleep Performance

### What It Answers
> "Did I recover enough for tomorrow?"

### Key Difference from Other Trackers

❌ Most apps: "You slept 6h 55m. Target: 8 hours."  
✅ This approach: "You needed 7h 42m based on yesterday's strain. You got 90%."

### Tonight's Sleep Target

Your personalized sleep need is calculated:

```
base_need = your_7day_avg_sleep
strain_adjustment = max(0, (yesterday_strain - 10) × 0.05)
debt_repayment = accumulated_debt / 7

tonight_target = base_need + strain_adjustment + debt_repayment
```

**Example:**
```
Base need (your baseline):     7h 00m
+ Strain adjustment (16.2):    + 31m
+ Debt repayment (1h 23m):     + 12m
────────────────────────────────────
Tonight's target:              7h 43m
```

### Sleep Stages

| Stage | Target % | Function |
|-------|----------|----------|
| Deep (N3) | 15-20% | Physical restoration, muscle repair, immune function |
| REM | 20-25% | Mental recovery, memory consolidation, emotional regulation |
| Light (N1/N2) | 55-60% | Transition between stages |

### Sleep Debt

Accumulated when you sleep less than your personal need:

```
sleep_debt = sum of (baseline - actual) for each day where actual < baseline
```

Sleep debt takes **multiple nights** to repay. The system recommends spreading repayment over 7 days.

---

## Heart Rate Variability (HRV)

### What It Answers
> "What state is my autonomic nervous system in?"

### Understanding HRV

HRV measures the variation in time between heartbeats (in milliseconds). It reflects the balance between:

- **Sympathetic** (fight-or-flight) → Lower HRV
- **Parasympathetic** (rest-and-digest) → Higher HRV

### Personal Baselines

**Critical**: Compare to YOUR baseline, not population averages.

```
hrv_7d_avg = rolling average of your last 7 days
hrv_30d_avg = rolling average of your last 30 days
```

### Direction Indicators

| Direction | Meaning |
|-----------|---------|
| ↑ Up (+5%+) | Trending above your baseline, good recovery |
| → Stable (±5%) | At your normal baseline |
| ↓ Down (-5%+) | Below baseline, possible stress/illness/overtraining |

### HRV Status (from Garmin)

| Status | Meaning |
|--------|---------|
| BALANCED | Within normal range |
| LOW | Below typical range |
| HIGH | Above typical range |
| UNBALANCED | Abnormal pattern detected |

---

## Resting Heart Rate (RHR)

### What It Answers
> "Is there an early warning sign of stress or illness?"

### Why It Matters

RHR is measured during sleep and is a reliable indicator of:
- Cardiovascular fitness (lower = fitter)
- Recovery state (elevated = stressed)
- Early illness detection (sudden spike)

### Direction (Inverse)

For RHR, **lower is better**, so the direction logic is inverted:

| Change | Indicator | Meaning |
|--------|-----------|---------|
| RHR down 5%+ | ✅ Green | Improving fitness/recovery |
| RHR stable | → Gray | Normal variation |
| RHR up 5%+ | ⚠️ Red | Stress, illness, or overtraining |

---

## Body Battery

### What It Answers
> "How much energy do I have available?"

### Understanding Body Battery

- **Range**: 0-100
- **Charges**: During rest and sleep
- **Drains**: During activity and stress

### Key Metrics

| Metric | Meaning |
|--------|---------|
| `body_battery_charged` | Energy gained overnight |
| `body_battery_drained` | Energy spent during day |
| Net = charged - drained | Daily energy balance |

### Morning Target

Aim to start the day with **60+ body battery** for optimal performance.

---

## Causality Engine (Phase 4)

### Correlations

The system learns YOUR patterns:

```typescript
{
  pattern_type: 'positive' | 'negative',
  title: "8k+ step days",
  description: "High step days correlate with +14% recovery",
  impact: 14.2,      // Percentage impact
  confidence: 0.85,  // 0-1 confidence score
  sample_size: 23    // Days analyzed
}
```

**Examples:**
- "Late workouts correlate with -18% recovery next day"
- "5+ days of 7h+ sleep: HRV baseline up 8%"
- "8k+ step days → +14% recovery the next morning"

### Streak Tracking

| Streak | Criteria |
|--------|----------|
| `green_days` | Consecutive days with 67%+ recovery |
| `sleep_consistency` | Consecutive days with 7h+ sleep |
| `step_goal` | Consecutive days hitting step goal |

### Trend Alerts

Detects multi-day trends requiring attention:

```typescript
{
  metric: 'HRV',
  direction: 'declining',
  days: 4,
  change_pct: -15.2,
  severity: 'warning'  // or 'concern' or 'positive'
}
```

---

## Putting It All Together

### Morning Decision Framework

When you wake up, the dashboard answers:

1. **Can I push today?** → Recovery % and zone
2. **How much should I push?** → Target strain range
3. **What limited me?** → Contributing factors

### Evening Planning

Before bed, understand:

1. **How much did I push?** → Today's strain
2. **How much sleep do I need?** → Personalized target
3. **Am I building or depleting?** → Weekly trend

---

## Reference: Threshold Values

| Metric | Green | Yellow | Red |
|--------|-------|--------|-----|
| Recovery | 67%+ | 34-66% | <34% |
| Strain Target (Green) | 14-21 | - | - |
| Strain Target (Yellow) | - | 8-14 | - |
| Strain Target (Red) | - | - | 0-8 |
| Sleep (minimum) | 7h+ | 6-7h | <6h |
| Deep Sleep % | 18%+ | 12-18% | <12% |
| REM Sleep % | 22%+ | 15-22% | <15% |
| Direction Threshold | ±5% | - | - |

