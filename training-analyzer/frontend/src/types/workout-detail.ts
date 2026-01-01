// Types for detailed workout data with time series and GPS

export interface HeartRatePoint {
  timestamp: number;  // seconds from start
  hr: number;         // beats per minute
}

export interface PaceSpeedPoint {
  timestamp: number;  // seconds from start
  value: number;      // pace in sec/km for running, speed in km/h for cycling
}

export interface ElevationPoint {
  timestamp: number;  // seconds from start
  elevation: number;  // meters
}

export interface CadencePoint {
  timestamp: number;  // seconds from start
  cadence: number;    // steps/min for running, rpm for cycling
}

export interface PowerPoint {
  timestamp: number;  // seconds from start
  power: number;      // watts
}

export interface GPSCoordinate {
  lat: number;
  lon: number;
}

export interface SplitData {
  split_number: number;
  distance_m: number;
  duration_sec: number;
  avg_hr?: number;
  max_hr?: number;
  avg_pace_sec_km?: number;   // for running
  avg_speed_kmh?: number;     // for cycling
  elevation_gain_m?: number;
  elevation_loss_m?: number;
  avg_cadence?: number;
}

export interface ActivityTimeSeries {
  heart_rate: HeartRatePoint[];
  pace_or_speed: PaceSpeedPoint[];
  elevation: ElevationPoint[];
  cadence: CadencePoint[];
  power?: PowerPoint[];  // Optional - only available with power meters
}

export interface BasicActivityInfo {
  activity_id: string;
  name: string;
  activity_type: string;
  sport_type?: string;
  date: string;
  start_time?: string;
  duration_sec: number;
  distance_m?: number;
  avg_hr?: number;
  max_hr?: number;
  avg_pace_sec_km?: number;   // for running
  avg_speed_kmh?: number;     // for cycling
  elevation_gain_m?: number;
  calories?: number;
  training_effect?: number;
}

export interface ActivityDetailsResponse {
  basic_info: BasicActivityInfo;
  time_series: ActivityTimeSeries;
  gps_coordinates: GPSCoordinate[];
  splits: SplitData[];
  is_running: boolean;        // True for running (pace), False for cycling (speed)
  data_source: string;        // garmin, strava, etc.
  cached: boolean;
  cache_timestamp?: string;
}

// Chart-specific types
export interface ChartDataPoint {
  elapsedSeconds: number;
  elapsedMinutes: number;
  formattedTime: string;
  [key: string]: number | string;
}

export interface SyncedHoverState {
  activeIndex: number | null;
  activeLabel: string | null;
}
