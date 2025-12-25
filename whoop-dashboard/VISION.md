# WHOOP Dashboard Vision

**Your body generates thousands of data points daily. This project turns them into one decision: GO or RECOVER.**

Designed around one philosophy: **don't show data, tell me what to do.**

---

## The Vision: WHOOP-Style Actionable Intelligence

### Why Most Health Dashboards Fail

Traditional dashboards show you numbers:
- "Your HRV is 48ms"
- "You slept 6h 55m"
- "Stress level: 42"

But numbers don't answer the question you actually have:

> **"Should I push hard today, or take it easy?"**

### The WHOOP Philosophy (What We're Building)

WHOOP succeeds because of **brutal condensation**:

```
Thousands of raw data points
         ↓
    Personal baseline comparison
         ↓
    Physiological state estimation
         ↓
    ONE DECISION
```

**Core Principles:**

| Principle | Implementation |
|-----------|----------------|
| **One metric → one decision** | Recovery % tells you GO or STOP |
| **Personal baselines, not population averages** | Your HRV vs *your* 7-day avg, not "normal" |
| **State change > absolute value** | "↑12% from baseline" matters more than "48ms" |
| **Personalized targets** | "You need 7h42m tonight" not "get 8 hours" |
| **Causality framing** | "Late workouts drop your recovery -18%" |
| **Progressive disclosure** | Simple answer first, tap for details |

---

## The Three Core Metrics

### Recovery (0-100%)

**What it answers:** *"How ready is my body today?"*

**Inputs:**
- HRV (primary signal - autonomic nervous system state)
- Resting heart rate (deviation from baseline)
- Sleep quality (not just duration)
- Body Battery charged overnight
- Recent strain accumulation

**Zones:**
- 🟢 **GREEN (67-100%)**: Push hard. High-intensity training, competition, PRs.
- 🟡 **YELLOW (34-66%)**: Moderate effort. Technique work, steady cardio.
- 🔴 **RED (0-33%)**: Recovery focus. Rest, mobility, light yoga.

**The insight:**
> "Your body is primed for peak performance. Target strain: 14-18 today."

---

### Strain (0-21)

**What it answers:** *"How much did I stress my body?"*

**Inputs:**
- Heart rate zone distribution (time at each intensity)
- Body Battery drained
- Active calories burned
- Intensity minutes accumulated

**Scale is logarithmic on purpose:**
- 0-8: Light day (walking, easy activity)
- 8-14: Moderate (steady workout)
- 14-18: Hard (tough training session)
- 18-21: All-out (race, competition, extreme effort)

Going from 18→19 is **much harder** than 5→6. This prevents ego-driven overtraining.

**The insight:**
> "You hit 16.2 strain. Your body will need 7h 48m sleep to fully recover."

---

### Sleep Performance

**What it answers:** *"Did I recover enough for tomorrow?"*

**The key difference from other trackers:**

❌ Most apps: "You slept 6h 55m. Target: 8 hours."
✅ This approach: "You needed 7h 42m based on yesterday's strain. You got 90% of that."

**Inputs:**
- Time asleep (not time in bed)
- Sleep stages (deep/REM/light percentages)
- Sleep efficiency (time asleep / time in bed)
- Sleep debt accumulation
- Yesterday's strain (determines tonight's need)

**The insight:**
> "47 minute deficit. Tonight's target: 8h 29m to clear sleep debt."

---

## Current Garmin Data Sources

### What We're Fetching

| Endpoint | Data | Recovery Impact |
|----------|------|-----------------|
| `/wellness-service/wellness/dailySleep` | Duration, stages, efficiency, SPO2 | High |
| `/hrv-service/hrv/{date}` | Nightly HRV, weekly avg, baseline status | High |
| `/wellness-service/wellness/dailyStress/{date}` | Stress levels, time in zones | Medium |
| `/wellness-service/wellness/bodyBattery/reports/daily` | Charged/drained, high/low | High |
| `/usersummary-service/stats/steps/daily` | Steps, distance, calories | Strain |

### Untapped Data (Roadmap)

| Endpoint | Data | Why It Matters |
|----------|------|----------------|
| `/metrics-service/metrics/trainingreadiness/{date}` | Garmin's recovery score | Validation |
| `/metrics-service/metrics/trainingstatus/aggregated` | Productive/Peaking/Overreaching | Long-term trajectory |
| `/wellness-service/wellness/sleepNeed/{date}` | Personalized sleep target | Dynamic goals |
| `/wellness-service/wellness/dailyRespirationData/{date}` | Overnight breathing rate | Illness early warning |
| Activity HR zones | Time in each zone | True strain calculation |
| Training Effect | Aerobic/anaerobic load | Workout quality |
| VO2 Max trend | Fitness ceiling | Performance tracking |

---

## Actionable Insights Engine

### Daily Decision Framework

When you open the dashboard, you should know **in 2 seconds**:

```
┌─────────────────────────────────────────┐
│                                         │
│              TODAY                      │
│                                         │
│         🟢 GO FOR IT                    │
│                                         │
│   Your body is primed for intensity.    │
│   Target strain: 14-18                  │
│                                         │
│   Recovery: 78% ──────────────────→     │
│                                         │
└─────────────────────────────────────────┘
```

### Causality Insights (What Actually Moves the Needle)

The system learns YOUR patterns and surfaces them:

**Negative correlations:**
- "Workouts after 8pm correlate with -18% recovery next day"
- "Alcohol nights (detected via HRV crash) drop recovery by 23%"
- "Less than 6h sleep: next-day HRV drops 15% on average"

**Positive correlations:**
- "8k+ step days → +14% recovery the next morning"
- "Consistent 7h+ sleep for 5 days → HRV baseline up 8%"
- "Morning workouts correlate with +12% better sleep efficiency"

**Weekly patterns:**
- "This week: 4 green days (vs 2 last week)"
- "Sleep debt accumulated: 1h 23m"
- "HRV trending up +6% vs last 30 days"

### Personalized Targets

**Sleep need calculation:**
```
Base need (your personal baseline)     7h 00m
+ Yesterday's strain adjustment        + 35m  (strain was 16.2)
+ Sleep debt repayment                 + 12m  (1h 23m debt ÷ 7 days)
─────────────────────────────────────────────
Tonight's target                       7h 47m
```

**Strain target based on recovery:**
```
Recovery: 78% (Green zone)
Optimal strain range: 14-18
Recommendation: "Great day for intervals or a hard tempo run"
```

---

## Enhancement Roadmap

### Phase 1: Data Foundation ✓ (Current)
- [x] Core wellness data (sleep, HRV, stress, activity)
- [x] Body Battery integration
- [x] SQLite storage with history
- [x] Basic recovery calculation
- [x] Web dashboard with trends

### Phase 2: Personal Baselines (Next)
- [ ] 7-day and 30-day rolling averages for all metrics
- [ ] Replace fixed thresholds with personal baselines
- [ ] Add Training Readiness endpoint
- [ ] Add Sleep Need calculation
- [ ] Store direction indicators (↑↓ from baseline)

### Phase 3: Actionable Insights
- [ ] Daily strain target based on recovery
- [ ] Sleep debt accumulator
- [ ] Personalized sleep need calculation
- [ ] "GO/RECOVER" single-answer home screen
- [ ] One actionable insight per day

### Phase 4: Causality Engine
- [ ] Correlation detector (workout timing vs recovery)
- [ ] Pattern recognition (what improves YOUR recovery)
- [ ] Weekly behavioral summary
- [ ] Streak tracking (green days, sleep consistency)
- [ ] Trend alerts ("HRV dropping for 3 days")

### Phase 5: Training Integration
- [ ] Connect activities to strain calculation
- [ ] HR zone time → logarithmic strain (like WHOOP)
- [ ] Training Effect integration
- [ ] Recovery time recommendations
- [ ] Periodization insights

---

## The Core Philosophy

> **Raw physiology → Personal baseline → Physiological state → Single decision**

The goal isn't to show you more data. It's to show you **less**—but make every number *mean* something.

When you wake up, you should know:
1. **Can I push today?** (Recovery %)
2. **How much should I push?** (Target strain range)
3. **What limited me?** (Contributing factors)

When you go to bed, you should know:
1. **How much did I push?** (Today's strain)
2. **How much sleep do I need?** (Personalized target)
3. **Am I building or depleting?** (Weekly trend)

Everything else is progressive disclosure—tap to explore, but never overwhelming.

---

## Identity Shift

The subtle goal:

> From: "I work out a lot"
> To: **"I manage my recovery"**

This reframes:
- Rest as *productive*
- Sleep as *training*
- Saying no as *discipline*

Your body is the ultimate performance system. This dashboard helps you operate it intelligently.
