// Utility functions for the Reactive Training App

import { clsx, type ClassValue } from 'clsx';

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

// Format duration from seconds to human-readable string
export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

// Format pace from seconds per km to mm:ss
export function formatPace(secondsPerKm: number): string {
  const minutes = Math.floor(secondsPerKm / 60);
  const seconds = Math.floor(secondsPerKm % 60);
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

// Format distance from meters to km with decimals
export function formatDistance(meters: number, decimals: number = 2): string {
  const km = meters / 1000;
  return km.toFixed(decimals);
}

// Format date for display
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

// Format time for display
export function formatTime(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Get relative time (e.g., "2 days ago")
export function getRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours === 0) {
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      if (diffMinutes < 1) return 'Just now';
      return `${diffMinutes} minute${diffMinutes === 1 ? '' : 's'} ago`;
    }
    return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
  }

  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7);
    return `${weeks} week${weeks === 1 ? '' : 's'} ago`;
  }
  if (diffDays < 365) {
    const months = Math.floor(diffDays / 30);
    return `${months} month${months === 1 ? '' : 's'} ago`;
  }
  const years = Math.floor(diffDays / 365);
  return `${years} year${years === 1 ? '' : 's'} ago`;
}

// Get workout type label
export function getWorkoutTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    running: 'Running',
    trail_running: 'Trail Running',
    cycling: 'Cycling',
    swimming: 'Swimming',
    walking: 'Walking',
    hiking: 'Hiking',
    strength: 'Strength',
    hiit: 'HIIT',
    yoga: 'Yoga',
    skiing: 'Skiing',
    football: 'Football',
    tennis: 'Tennis',
    basketball: 'Basketball',
    golf: 'Golf',
    rowing: 'Rowing',
    surfing: 'Surfing',
    elliptical: 'Elliptical',
    climbing: 'Climbing',
    martial_arts: 'Martial Arts',
    skating: 'Skating',
    dance: 'Dance',
    triathlon: 'Triathlon',
    other: 'Activity',
  };
  return labels[type] || type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// Get workout type icon (emoji for now, can be replaced with proper icons)
export function getWorkoutTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    running: 'run',
    cycling: 'bike',
    swimming: 'swim',
    strength: 'dumbbell',
    hiit: 'flame',
    yoga: 'lotus',
    walking: 'walk',
    other: 'activity',
  };
  return icons[type] || 'activity';
}

// Get HR zone color
export function getHRZoneColor(zone: string): string {
  const colors: Record<string, string> = {
    zone1: '#6EE7B7', // Green
    zone2: '#93C5FD', // Blue
    zone3: '#FCD34D', // Yellow
    zone4: '#FB923C', // Orange
    zone5: '#F87171', // Red
  };
  return colors[zone] || '#9CA3AF';
}

// Get HR zone label
export function getHRZoneLabel(zone: string): string {
  const labels: Record<string, string> = {
    zone1: 'Recovery',
    zone2: 'Endurance',
    zone3: 'Tempo',
    zone4: 'Threshold',
    zone5: 'VO2 Max',
  };
  return labels[zone] || zone;
}

// Effort level colors
export function getEffortLevelColor(level: string): string {
  const colors: Record<string, string> = {
    easy: '#10B981',
    moderate: '#F59E0B',
    hard: '#F97316',
    very_hard: '#EF4444',
  };
  return colors[level] || '#6B7280';
}

// Effort level label
export function getEffortLevelLabel(level: string): string {
  const labels: Record<string, string> = {
    easy: 'Easy',
    moderate: 'Moderate',
    hard: 'Hard',
    very_hard: 'Very Hard',
  };
  return labels[level] || level;
}
