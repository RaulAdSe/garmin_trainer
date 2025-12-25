# Training Analyzer

AI-powered workout analysis with per-activity coaching feedback, inspired by Runna's training methodology.

---

# Runna App Training Methodology Research

Comprehensive research on Runna's training methodology and algorithms for building a similar training tool.

## Executive Summary

Runna is a UK-based running training app founded in 2021 by Ben Parker (professional running coach, IRONMAN athlete) and Dom Maskell. The app was acquired by Strava in April 2025. It combines coach-designed training plans with AI-powered personalization and adaptive features. As of 2024-2025, the app generates approximately $2.75 million monthly from 250,000 downloads.

---

## 1. How Runna Creates Personalized Training Plans

### 26-Step Onboarding Process

Runna uses a comprehensive onboarding questionnaire that collects:

1. **Primary Goal**: Race distance, first 5K, general fitness, etc.
2. **Current Running Ability**: Beginner, Intermediate, Advanced, Elite (with clear definitions)
3. **Birthday/Age**: Used for age-based intensity adjustments and injury risk reduction
4. **Estimated Current Race Time**: Emphasizes CURRENT fitness, not old PBs
5. **Available Running Days**: Requires at least 4 days for optimal planning
6. **Start Date Selection**: Today, Tomorrow, Monday, or Custom
7. **Plan Length**: 6, 8, 12+ weeks with recommendations tied to goals

Each step explains WHY the information is needed (e.g., "age helps personalize intensity and reduce injury risk").

### Plan Generation Philosophy

**Key insight**: "We don't use AI to generate training plans. Instead, the programs are designed by a team of experts that consist of elite runners and Olympians."

- Plans are created by coaches, including British Olympian Steph Davis
- AI is used for monitoring progress and generating insights
- The "Running Engine" dynamically builds optimal training plans
- Engineers implement algorithms for personalized, adaptive training

### Ability Level Tiers

| Level | Description |
|-------|-------------|
| Beginner | Entry-level runners |
| Intermediate | Regular runners with some experience |
| Advanced | Experienced runners with racing background |
| Elite | Competitive runners with strong race times |

Increasing ability level increases run length and weekly mileage.

---

## 2. Workout Prescription (Paces, Intensities, Volumes)

### Pace Calculation Methodology

Paces are derived from **Estimated Current Race Time**:
- User provides one race time estimate (5K, 10K, or half marathon)
- Runna applies this fitness level across all distances automatically
- If you update your 5K time, your 10K and half marathon estimates adjust accordingly

**Pace Adjustment Recommendations**:
- If paces feel too hard: Increase estimated race time by 15-30 seconds
- If paces feel too easy: Decrease estimated race time by 15-30 seconds

### Workout Types

| Workout | Purpose | Description |
|---------|---------|-------------|
| **Intervals** | Speed & running economy | Short, fast bursts with recovery. Reps above lactate threshold. Example: 5x1K |
| **Tempo Runs** | Build lactate threshold | Sustained "comfortably hard" pace. Longer reps without complete rest |
| **Long Runs (Unstructured)** | Aerobic base | Easy pace, focus on time on feet |
| **Long Runs (Race Pace)** | Race preparation | Intervals at goal race pace with easy running between |
| **Easy/Recovery Runs** | Active recovery | Very short, very easy jogs for circulation and muscle recovery |
| **Strides** | Form & turnover | 10-20 second fast bursts to sharpen leg turnover |
| **Hill Reps** | Strength & power | Hard efforts uphill with easy jog/walk back |

### Intensity Metrics Used

| Metric | Role | Notes |
|--------|------|-------|
| **Pace Targets** | Primary | Provides race day confidence |
| **Heart Rate Zones** | Secondary | Calculated same as Strava |
| **RPE** | Alternative | Use if struggling with pace targets |
| **Conversational Pace** | Easy runs | Should be able to hold conversation |

**HR Zone Philosophy**: "HR is useful but we recommend primarily running to pace and using HR data as a secondary measure."

### Training Preferences Controls

Two independent controls:
1. **Training Volume**: How much running per week, peak mileage, build-up rate
2. **Plan Difficulty**: Quantity/difficulty of speed workouts, number of structured long runs

Reducing difficulty = fewer reps during intervals, but NOT slower interval paces.

---

## 3. How Runna Adapts Plans Based on Completed Workouts

### Current Adaptation Methods

**Manual Adjustments**:
- Training Volume and Difficulty preferences can be changed anytime
- Estimated Race Time can be updated to recalibrate paces
- Running ability level can be adjusted up/down

**Automatic Calendar Adjustments** (Non-date-based plans):
- If you skip/miss a workout, subsequent workouts automatically shift
- Future workouts shift forward until you complete or skip the missed session

**Pace Insights Feature**:
- AI monitors performance in speed sessions (intervals, tempo, time trials)
- Detects trends in pace consistency
- Provides statuses:
  - "Pace on point" - perfectly on track
  - "Ahead of the Pack" - recommends faster paces
  - "Let's Review Your Pace" - suggests decreasing pace for sustainability
- User has full control to accept or reject changes

### Current Limitations

**Critical insight from reviews**: "The app does not adjust week on week based on how actual training is going unless you update your pace time and repopulate your plan."

- Not fully automatic adaptation based on workout performance
- Requires user intervention to change settings
- Plans don't dynamically adjust if workouts are missed

### Planned Future Improvements

- Machine learning model adapting plans based on stats, usage, performance
- Integration of HRV, sleep, menstrual cycle data
- Automatic adaptation for illness/injury
- A/B testing different workouts across millions of users
- Better injury and improvement prediction

---

## 4. Use of Metrics (HR Zones, Pace Zones, Power)

### Heart Rate Zones

- Calculated same way as Strava for platform consistency
- Zone 2 (endurance zone) = 65.1-80% of max HR
- Used as secondary measure, not primary

**HR Zone Limitations Acknowledged**: "Two people who are the same age, same gender and have the same 5k PB might have different easy run HR zones."

### Pace Zones

Primary training metric. Zones derived from estimated race time:
- Easy/Recovery pace
- Sub-threshold pace
- Threshold/Tempo pace
- Interval/VO2max pace
- Race pace (for structured long runs)

### Power Running

**Finding**: No evidence of Stryd or power meter integration. Runna focuses on pace and HR rather than power-based training zones.

### Runna Score

A proprietary fitness metric:
- Measures estimated current running ability relative to current plan
- Based on estimated race times (5K, 10K, half marathon)
- Goal is to see score increase over time
- Cannot be manually changed (adjusts via race time changes)

---

## 5. Race Goal Setting and Periodization

### Goal Setting Philosophy

**Key insight**: "Runna does not currently offer the option to 'train toward a goal time.' Instead, they focus on steady, structured progress based on your actual ability."

This prevents:
- Overtraining
- Injury risk from unrealistic targets
- Training at inappropriate intensities

### Periodization Structure

```
+-------------------------------------------------------------+
|                    TRAINING PERIODIZATION                    |
+-----------------+---------------------+---------------------+
|   BASE PHASE    |     KEY BLOCK       |   TAPER PERIOD      |
|                 |    (8-20 weeks)     |                     |
+-----------------+---------------------+---------------------+
| Build foundation| Main fitness build  | Mileage reduction   |
| Volume building | Increasing intervals| Deload weeks        |
| Starting mileage| Progressive load    | Race preparation    |
+-----------------+---------------------+---------------------+
```

### B-Race Handling

- Can add secondary races to plan
- Runna calculates custom taper and recovery
- Adapts training while keeping on track for primary race
- Automatically adjusts surrounding workouts

### Mileage Progression

**10% Rule Applied**:
- Weekly mileage increases no more than ~10% per week
- "One of the most common causes of running-related injuries is increasing mileage too quickly"
- Progressive overload principle embedded in plans

---

## 6. Technical Details About Algorithms/Approaches

### Architecture Overview

**Tech Stack**:
- Serverless architectures with AWS
- Terraform/CDK/CloudFormation for IaC
- CI/CD pipelines
- iOS, Android, and Apple Watch apps
- Integrations: Garmin, Strava, Coros, Fitbit, Suunto

**Engineering Team**: Grown from 2 to 16+ engineers

### The "Running Engine"

Core algorithm components:
1. Dynamic plan building based on user inputs
2. Adaptation based on external inputs (previous workouts, recovery tracking)
3. Complex algorithms for personalized training
4. ML models for running training insights (in development)

### Race Time Prediction Algorithm

"Your race time prediction is based on the metrics that you've told Runna, such as your running ability and training schedule, as well as all of the data they've seen from runners just like you."

Uses aggregated data from user base for predictions.

### Pace Insights Algorithm

Monitors speed session performance:
- Analyzes intervals, tempo runs, time trials
- Detects trends in pace consistency
- Recommends pace adjustments when patterns detected
- User retains control over accepting changes

---

## 7. Cross-Training Integration

### Integrated Training Options

| Type | Description | Benefit |
|------|-------------|---------|
| **Strength Training** | 1-2 sessions/week | Improves running economy 8-12% |
| **Pilates** | 26 progressive sessions | Core strength, injury prevention |
| **Mobility** | Stretch & Stability series | Flexibility, recovery |
| **Cross-Training** | Cycling, swimming, rowing | Low-impact cardio maintenance |

### Injury Prevention Principles

1. **10% Rule**: Increase mileage max 10% per week
2. **Proper Warm-up**: Essential before speed work
3. **Strength Training**: Build resilient foundation
4. **Rest Days**: Allow adaptation to occur
5. **Sleep**: 8 hours recommended for recovery

---

## 8. User Feedback & Effectiveness

### Positive Results

- Users report 14-30+ minute marathon PR improvements
- App predicted one user's marathon at 3:35-3:40, finished at 3:38:21
- "Hands down the best running app I've used when it comes to coaching"
- Seamless watch integration praised
- Flexibility to move workouts around appreciated

### Key Strengths

1. Workouts sync directly to watch - "no thinking involved"
2. Flexible scheduling without "failed workout" guilt
3. Comprehensive approach (strength, mobility, pilates)
4. Clear pace targets build race day confidence
5. Works for beginners through advanced runners

### Criticisms & Limitations

| Category | Issue |
|----------|-------|
| **Intensity** | Too intense for beginners, potential injury risk |
| **Technical** | Syncing issues with various devices |
| **Customization** | Limited control, plans feel static |
| **Adaptation** | No automatic week-by-week adjustment based on performance |
| **Device Support** | No Samsung smartwatch support |

---

## 9. Industry-Standard Pace Zone Formulas

### Reference: Training Zone Percentages

| Zone | Description | % of Max HR | % of LTHR |
|------|-------------|-------------|-----------|
| Easy | Conversational | 65-78% | <85% |
| Sub-Threshold | Moderate | 78-85% | 85-89% |
| Threshold/Tempo | Comfortably hard | 85-90% | 90-94% |
| VO2max/Interval | Hard | 95-100% | 95-99% |
| Sprint | Maximum | 100%+ | 100%+ |

### Key Pace Definitions

**Threshold Pace**:
- 85-90% of VO2max
- Current best pace for ~1 hour time trial
- Between 10K and half marathon race pace

**Interval/VO2max Pace**:
- Fastest pace sustainable for 5-8 minutes
- 3-5 minute rep duration ideal

**Easy Pace**:
- Should be able to hold conversation
- 15-25% of weekly training volume

---

## 10. Key Takeaways for Building Similar Tool

### What Makes Runna Effective

1. **Comprehensive onboarding** capturing meaningful data
2. **Coach-designed plans** rather than purely algorithmic
3. **AI for insights/recommendations**, not plan generation
4. **Flexibility** - plans adapt to life, not punish missed workouts
5. **Holistic approach** - running + strength + mobility
6. **Clear communication** of pace targets
7. **Gamification** through streaks and scores
8. **Watch integration** - seamless workout execution

### Technical Considerations

1. Single race time input drives all pace calculations
2. Training preferences as independent controls (volume vs. difficulty)
3. Pace insights feature monitors trends, not individual workouts
4. Plan adjustment options when behind (skip, rearrange, restart)
5. B-race support with automatic taper calculation

### Areas for Improvement/Differentiation

1. **True adaptive training** based on workout performance data
2. **Power meter integration** (Stryd, Garmin Running Power)
3. **HRV/recovery integration** for training load management
4. **Automatic fatigue tracking** and adjustment
5. **Better device support** (Samsung watches)
6. **More granular pace adjustment** controls

---

## Runna Research Sources

### Primary Sources
- [Runna Official Website](https://www.runna.com)
- [Runna Support Documentation](https://support.runna.com)
- [Runna Training Plans](https://www.runna.com/training/training-plans)

### Founder Interviews
- [Antler - What It Really Takes: Ben Parker](https://www.antler.co/blog/what-it-really-takes-ben-parker-co-founder-runna)
- [Welltodo - Ben Parker and Dom Maskell](https://www.welltodoglobal.com/post/ben-parker-and-dom-maskell-co-founders-of-runna/)
- [The Nudge Group - Startup Stories: Ben Parker](https://thenudgegroup.com/blog/interviews/startup-stories-ben-parker-co-founder-head-coach-at-runna)
- [Great British Entrepreneur Awards - Runna Founders](https://greatbritishentrepreneurawards.com/2023/10/runna-founders-on-a-mission-to-make-running-more-accessible/)

### Technical & Business
- [Strava Acquisition Announcement](https://press.strava.com/articles/strava-to-acquire-runna-a-leading-running-training-app)
- [RevenueCat - Runna Case Study](https://www.revenuecat.com/customers/runna/)
- [ScreensDesign - Runna Onboarding Analysis](https://screensdesign.com/showcase/runna-running-training-plans)

### Reviews & User Feedback
- [Gritty Runners - Runna Review](https://grittyrunners.co.uk/2024/01/28/marathon-training-plans-why-i-chose-runna/)
- [The Runner Beans - Runna Coaching Review](https://therunnerbeans.com/runna-coaching-app-review/)
- [Trustpilot - Runna Reviews](https://www.trustpilot.com/review/runna.com)
- [Tom's Guide - 16 Week Review](https://www.tomsguide.com/news/i-used-this-running-app-for-16-weeks-and-i-broke-my-personal-record)
- [Women's Health - Runna Six Week Trial](https://www.womenshealthmag.com/fitness/a68152711/runna-app-controversy-review-i-tried-it/)

### Sports Science References
- [Jack Daniels Running Formula - Fellrnr](https://fellrnr.com/wiki/Jack_Daniels)
- [VDOT O2 Calculator](https://vdoto2.com/calculator)
- [TrainingPeaks - Joe Friel's Zone Guide](https://www.trainingpeaks.com/learn/articles/joe-friel-s-quick-guide-to-setting-zones/)
- [Runner's World - Progressive Overload](https://www.runnersworld.com/training/a44122396/progressive-overload/)
- [McMillan Running](https://www.mcmillanrunning.com/)
