/**
 * Database service using @capacitor/preferences for local wellness data storage.
 * Uses JSON storage instead of SQLite for better Capacitor compatibility.
 */

import { Preferences } from '@capacitor/preferences';

// Storage keys
const WELLNESS_DATA_KEY = 'wellness_data';

// Types
export interface DailyWellness {
  date: string;
  fetched_at: string;
  resting_heart_rate: number | null;
  training_readiness_score: number | null;
}

export interface SleepData {
  date: string;
  sleep_start: string | null;
  sleep_end: string | null;
  total_sleep_seconds: number;
  deep_sleep_seconds: number;
  light_sleep_seconds: number;
  rem_sleep_seconds: number;
  awake_seconds: number;
  sleep_score: number | null;
  sleep_efficiency: number | null;
  avg_spo2: number | null;
  avg_respiration: number | null;
}

export interface HRVData {
  date: string;
  hrv_weekly_avg: number | null;
  hrv_last_night_avg: number | null;
  hrv_last_night_5min_high: number | null;
  hrv_status: string | null;
  baseline_low: number | null;
  baseline_balanced_low: number | null;
  baseline_balanced_upper: number | null;
}

export interface StressData {
  date: string;
  avg_stress_level: number | null;
  max_stress_level: number | null;
  rest_stress_duration: number;
  low_stress_duration: number;
  medium_stress_duration: number;
  high_stress_duration: number;
  body_battery_charged: number | null;
  body_battery_drained: number | null;
  body_battery_high: number | null;
  body_battery_low: number | null;
}

export interface ActivityData {
  date: string;
  steps: number;
  steps_goal: number;
  total_distance_m: number;
  active_calories: number | null;
  total_calories: number | null;
  intensity_minutes: number;
  floors_climbed: number;
}

export interface WellnessRecord {
  date: string;
  wellness: DailyWellness | null;
  sleep: SleepData | null;
  hrv: HRVData | null;
  stress: StressData | null;
  activity: ActivityData | null;
}

// In-memory cache of wellness data, keyed by date
type WellnessDataStore = Record<string, WellnessRecord>;

class DatabaseService {
  private data: WellnessDataStore = {};
  private initialized = false;

  async initialize(): Promise<void> {
    if (this.initialized) return;

    try {
      const { value } = await Preferences.get({ key: WELLNESS_DATA_KEY });
      if (value) {
        this.data = JSON.parse(value);
      }
      this.initialized = true;
      console.log('Database initialized successfully');
    } catch (error) {
      console.error('Failed to initialize database:', error);
      this.data = {};
      this.initialized = true;
    }
  }

  private async save(): Promise<void> {
    await Preferences.set({
      key: WELLNESS_DATA_KEY,
      value: JSON.stringify(this.data),
    });
  }

  // Save wellness data for a date
  async saveWellness(record: WellnessRecord): Promise<void> {
    if (!this.initialized) await this.initialize();

    const existing = this.data[record.date] || { date: record.date };

    // Merge new data with existing
    this.data[record.date] = {
      date: record.date,
      wellness: record.wellness || existing.wellness || null,
      sleep: record.sleep || existing.sleep || null,
      hrv: record.hrv || existing.hrv || null,
      stress: record.stress || existing.stress || null,
      activity: record.activity || existing.activity || null,
    };

    await this.save();
  }

  // Get wellness data for a specific date
  async getWellness(date: string): Promise<WellnessRecord | null> {
    if (!this.initialized) await this.initialize();
    return this.data[date] || null;
  }

  // Get the most recent date with data
  async getLatestDate(): Promise<string | null> {
    if (!this.initialized) await this.initialize();

    const dates = Object.keys(this.data).sort().reverse();
    return dates[0] || null;
  }

  // Get wellness history for N days
  async getHistory(days: number): Promise<WellnessRecord[]> {
    if (!this.initialized) await this.initialize();

    const sortedDates = Object.keys(this.data).sort().reverse();
    const recentDates = sortedDates.slice(0, days);

    return recentDates.map(date => this.data[date]);
  }

  // Get database stats
  async getStats(): Promise<{ total_days: number; earliest_date: string | null; latest_date: string | null }> {
    if (!this.initialized) await this.initialize();

    const dates = Object.keys(this.data).sort();

    return {
      total_days: dates.length,
      earliest_date: dates[0] || null,
      latest_date: dates[dates.length - 1] || null,
    };
  }

  // Clear all data
  async clear(): Promise<void> {
    this.data = {};
    await Preferences.remove({ key: WELLNESS_DATA_KEY });
  }
}

// Singleton instance
export const db = new DatabaseService();
