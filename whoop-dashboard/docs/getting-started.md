# Getting Started

This guide will help you set up and run the WHOOP Dashboard locally.

---

## Prerequisites

- **Python 3.10+** for the data fetching CLI
- **Node.js 18+** for the Next.js frontend
- **Garmin Connect account** with data from a Garmin wearable device

---

## Installation

### 1. Clone the Repository

```bash
cd /path/to/garmin_insights/whoop-dashboard
```

### 2. Install Python Dependencies

First, install the shared `garmin_client` package:

```bash
cd ../shared/garmin_client
pip install -e .
```

Then install the whoop-dashboard CLI:

```bash
cd ../../whoop-dashboard
pip install -e .
```

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
```

---

## Configuration

### Garmin Authentication

The CLI uses the `garth` library for Garmin Connect authentication. On first run, you'll need to authenticate:

```bash
whoop fetch
# Follow prompts to enter Garmin credentials
```

Tokens are stored in `../shared/.garth_tokens/` and reused for subsequent requests.

---

## Usage

### Step 1: Fetch Your Data

Populate the database with your Garmin data:

```bash
# Fetch last 14 days (recommended for initial setup)
whoop fetch --days 14

# Fetch today only
whoop fetch

# Fetch a specific date
whoop fetch --date 2024-12-25
```

### Step 2: Check Your Recovery (CLI)

Quick terminal view of your recovery:

```bash
whoop show
```

Output:
```
  ╔══════════════════════════════╗
  ║         2024-12-26          ║
  ╠══════════════════════════════╣
  ║                              ║
  ║      RECOVERY: 78%           ║
  ║                              ║
  ╠══════════════════════════════╣
  ║  Sleep: 7.25h              ║
  ║  Deep: 18% | REM: 22%    ║
  ║  HRV: 48ms (BALANCED)      ║
  ║  Energy: +72 / -58        ║
  ║  Steps: 8432 (84%)        ║
  ╚══════════════════════════════╝
```

### Step 3: Launch the Dashboard

Start the web interface:

```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Dashboard Views

### Overview Tab

The main view showing your daily status:

- **Hero Decision**: GO / MODERATE / RECOVER with explanation
- **Recovery Gauge**: Visual 0-100% score
- **Daily Stats**: Strain, Sleep, HRV, RHR cards
- **Weekly Summary**: Zone distribution, streaks, patterns

### Recovery Tab

Deep dive into recovery metrics:

- 14-day recovery trend chart
- Contributing factors with baselines
- Direction indicators (vs your average)

### Strain Tab

Activity and exertion analysis:

- Current strain vs target zone
- Strain breakdown (steps, calories, intensity)
- 14-day strain trend

### Sleep Tab

Sleep quality and debt tracking:

- Sleep duration with efficiency
- Tonight's personalized target calculation
- Sleep stage distribution
- Accumulated sleep debt

---

## Daily Workflow

### Morning Routine

1. Sync your Garmin device to Garmin Connect
2. Fetch today's data: `whoop fetch`
3. Check dashboard for your decision

### What to Look For

| Recovery Zone | What It Means | Action |
|---------------|---------------|--------|
| 🟢 GREEN (67-100%) | Body is primed | Push hard, high-intensity OK |
| 🟡 YELLOW (34-66%) | Moderate readiness | Technique work, steady cardio |
| 🔴 RED (0-33%) | Recovery needed | Rest, mobility, light yoga |

---

## Keeping Data Fresh

For the most accurate insights, fetch data daily:

```bash
# Add to your morning routine
whoop fetch
```

Or set up a cron job:

```bash
# Fetch at 8am daily
0 8 * * * cd /path/to/whoop-dashboard && whoop fetch
```

---

## Troubleshooting

### "No data available"

The database is empty. Run:
```bash
whoop fetch --days 14
```

### "Authentication failed"

Garmin tokens expired. Remove and re-authenticate:
```bash
rm -rf ../shared/.garth_tokens
whoop fetch
```

### Database Not Found

Ensure `wellness.db` exists in the `whoop-dashboard` directory:
```bash
whoop stats
# Should show database path and record count
```

### Frontend Can't Connect to DB

The frontend expects the database at `../wellness.db` relative to the `frontend` folder. Check your directory structure.

---

## Next Steps

- Read [VISION.md](../VISION.md) to understand the product philosophy
- Check [architecture.md](./architecture.md) for technical details
- See [metrics-explained.md](./metrics-explained.md) for metric deep-dives

