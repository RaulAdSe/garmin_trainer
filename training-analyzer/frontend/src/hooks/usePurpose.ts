'use client';

import { useState, useEffect, useCallback } from 'react';

// Purpose types
export type PurposeType =
  | 'first_5k'
  | 'first_10k'
  | 'first_half'
  | 'first_marathon'
  | 'beat_pb'
  | 'stay_healthy'
  | 'lose_weight'
  | 'enjoy_more'
  | 'custom';

export interface UserPurpose {
  type: PurposeType;
  customText?: string;
  setAt: string; // ISO date string
  lastRemindedAt?: string; // ISO date string
  dismissedCount: number;
}

// Storage keys
const PURPOSE_KEY = 'ta_user_purpose';
const ONBOARDING_COMPLETED_KEY = 'ta_onboarding_purpose_completed';

// Days without activity that triggers a reminder
const INACTIVE_DAYS_THRESHOLD = 3;

// Minimum days between reminders after dismissal
const REMINDER_COOLDOWN_DAYS = 7;

export function usePurpose() {
  const [purpose, setPurposeState] = useState<UserPurpose | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasCompletedOnboarding, setHasCompletedOnboarding] = useState(false);

  // Load purpose from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(PURPOSE_KEY);
    const onboardingCompleted = localStorage.getItem(ONBOARDING_COMPLETED_KEY);

    if (stored) {
      try {
        setPurposeState(JSON.parse(stored));
      } catch {
        console.error('Failed to parse stored purpose');
      }
    }

    setHasCompletedOnboarding(onboardingCompleted === 'true');
    setIsLoading(false);
  }, []);

  // Save purpose to localStorage
  const setPurpose = useCallback((newPurpose: UserPurpose) => {
    setPurposeState(newPurpose);
    localStorage.setItem(PURPOSE_KEY, JSON.stringify(newPurpose));
    localStorage.setItem(ONBOARDING_COMPLETED_KEY, 'true');
    setHasCompletedOnboarding(true);
  }, []);

  // Update purpose type with optional custom text
  const updatePurpose = useCallback((type: PurposeType, customText?: string) => {
    const newPurpose: UserPurpose = {
      type,
      customText: type === 'custom' ? customText : undefined,
      setAt: new Date().toISOString(),
      dismissedCount: 0,
    };
    setPurpose(newPurpose);
  }, [setPurpose]);

  // Clear purpose (reset)
  const clearPurpose = useCallback(() => {
    setPurposeState(null);
    localStorage.removeItem(PURPOSE_KEY);
    localStorage.removeItem(ONBOARDING_COMPLETED_KEY);
    setHasCompletedOnboarding(false);
  }, []);

  // Mark as reminded (for cooldown tracking)
  const markReminded = useCallback(() => {
    if (purpose) {
      const updated = {
        ...purpose,
        lastRemindedAt: new Date().toISOString(),
      };
      setPurposeState(updated);
      localStorage.setItem(PURPOSE_KEY, JSON.stringify(updated));
    }
  }, [purpose]);

  // Dismiss reminder (increment count for progressive cooldown)
  const dismissReminder = useCallback(() => {
    if (purpose) {
      const updated = {
        ...purpose,
        lastRemindedAt: new Date().toISOString(),
        dismissedCount: purpose.dismissedCount + 1,
      };
      setPurposeState(updated);
      localStorage.setItem(PURPOSE_KEY, JSON.stringify(updated));
    }
  }, [purpose]);

  // Skip onboarding without setting a purpose
  const skipOnboarding = useCallback(() => {
    localStorage.setItem(ONBOARDING_COMPLETED_KEY, 'true');
    setHasCompletedOnboarding(true);
  }, []);

  // Check if we should show reminder based on conditions
  const shouldShowReminder = useCallback((
    lastWorkoutDate?: string,
    currentStreak?: number
  ): boolean => {
    // No purpose set - no reminder
    if (!purpose) return false;

    // Check cooldown period
    if (purpose.lastRemindedAt) {
      const lastReminded = new Date(purpose.lastRemindedAt);
      const now = new Date();
      const daysSinceReminder = Math.floor(
        (now.getTime() - lastReminded.getTime()) / (1000 * 60 * 60 * 24)
      );

      // Progressive cooldown: more dismissals = longer cooldown
      const cooldownDays = REMINDER_COOLDOWN_DAYS * (purpose.dismissedCount + 1);
      if (daysSinceReminder < cooldownDays) {
        return false;
      }
    }

    // Show reminder if streak is broken (was active but now at 0)
    if (currentStreak === 0 && lastWorkoutDate) {
      const lastWorkout = new Date(lastWorkoutDate);
      const now = new Date();
      const daysSinceWorkout = Math.floor(
        (now.getTime() - lastWorkout.getTime()) / (1000 * 60 * 60 * 24)
      );

      if (daysSinceWorkout >= INACTIVE_DAYS_THRESHOLD) {
        return true;
      }
    }

    // Show reminder after a week for new users
    const purposeSetDate = new Date(purpose.setAt);
    const now = new Date();
    const daysSinceSet = Math.floor(
      (now.getTime() - purposeSetDate.getTime()) / (1000 * 60 * 60 * 24)
    );

    // First week check-in
    if (daysSinceSet >= 7 && !purpose.lastRemindedAt) {
      return true;
    }

    return false;
  }, [purpose]);

  // Get the display text for the purpose
  const getPurposeDisplayText = useCallback((t: (key: string) => string): string => {
    if (!purpose) return '';

    if (purpose.type === 'custom' && purpose.customText) {
      return purpose.customText;
    }

    return t(`purpose.options.${purpose.type}`);
  }, [purpose]);

  return {
    purpose,
    isLoading,
    hasCompletedOnboarding,
    setPurpose,
    updatePurpose,
    clearPurpose,
    markReminded,
    dismissReminder,
    skipOnboarding,
    shouldShowReminder,
    getPurposeDisplayText,
  };
}

// Export for use in other components
export type UsePurposeReturn = ReturnType<typeof usePurpose>;
