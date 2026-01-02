'use client';

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react';
import {
  getUserPreferences,
  updateUserPreferences,
  toggleBeginnerMode as apiToggleBeginnerMode,
} from '@/lib/api-client';
import type {
  UserPreferences,
  UpdatePreferencesRequest,
  IntensityScale,
} from '@/lib/types';
import { useAuth } from '@/contexts/auth-context';

interface PreferencesContextType {
  // State
  preferences: UserPreferences | null;
  isLoading: boolean;
  error: string | null;

  // Derived state for easy access
  beginnerModeEnabled: boolean;
  showHRMetrics: boolean;
  showAdvancedMetrics: boolean;
  preferredIntensityScale: IntensityScale;
  weeklyMileageCapEnabled: boolean;

  // Actions
  toggleBeginnerMode: () => Promise<boolean>;
  updatePreferences: (prefs: UpdatePreferencesRequest) => Promise<void>;
  refreshPreferences: () => Promise<void>;
}

const PreferencesContext = createContext<PreferencesContextType | null>(null);

// Default preferences for when not logged in or loading
const defaultPreferences: UserPreferences = {
  user_id: '',
  beginner_mode_enabled: false,
  beginner_mode_start_date: null,
  show_hr_metrics: true,
  show_advanced_metrics: true,
  preferred_intensity_scale: 'hr',
  weekly_mileage_cap_enabled: false,
};

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch preferences from API
  const fetchPreferences = useCallback(async () => {
    if (!isAuthenticated) {
      setPreferences(defaultPreferences);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const prefs = await getUserPreferences();
      setPreferences(prefs);
    } catch (err) {
      console.error('Failed to fetch preferences:', err);
      setError(err instanceof Error ? err.message : 'Failed to load preferences');
      // Use defaults on error
      setPreferences(defaultPreferences);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  // Load preferences when auth state changes
  useEffect(() => {
    if (!authLoading) {
      fetchPreferences();
    }
  }, [authLoading, isAuthenticated, fetchPreferences]);

  // Toggle beginner mode
  const toggleBeginnerMode = useCallback(async (): Promise<boolean> => {
    if (!isAuthenticated) {
      throw new Error('Must be logged in to change preferences');
    }

    try {
      setError(null);
      const response = await apiToggleBeginnerMode();

      // Update local state
      setPreferences((prev) =>
        prev
          ? {
              ...prev,
              beginner_mode_enabled: response.beginner_mode_enabled,
              beginner_mode_start_date: response.beginner_mode_enabled
                ? new Date().toISOString()
                : null,
            }
          : null
      );

      return response.beginner_mode_enabled;
    } catch (err) {
      console.error('Failed to toggle beginner mode:', err);
      setError(err instanceof Error ? err.message : 'Failed to toggle beginner mode');
      throw err;
    }
  }, [isAuthenticated]);

  // Update preferences
  const updatePreferencesHandler = useCallback(
    async (updates: UpdatePreferencesRequest): Promise<void> => {
      if (!isAuthenticated) {
        throw new Error('Must be logged in to change preferences');
      }

      try {
        setError(null);
        const updatedPrefs = await updateUserPreferences(updates);
        setPreferences(updatedPrefs);
      } catch (err) {
        console.error('Failed to update preferences:', err);
        setError(err instanceof Error ? err.message : 'Failed to update preferences');
        throw err;
      }
    },
    [isAuthenticated]
  );

  // Refresh preferences
  const refreshPreferences = useCallback(async () => {
    await fetchPreferences();
  }, [fetchPreferences]);

  // Derived state with fallbacks
  const currentPrefs = preferences || defaultPreferences;

  const value: PreferencesContextType = {
    preferences,
    isLoading,
    error,

    // Derived state
    beginnerModeEnabled: currentPrefs.beginner_mode_enabled,
    showHRMetrics: currentPrefs.show_hr_metrics,
    showAdvancedMetrics: currentPrefs.show_advanced_metrics,
    preferredIntensityScale: currentPrefs.preferred_intensity_scale,
    weeklyMileageCapEnabled: currentPrefs.weekly_mileage_cap_enabled,

    // Actions
    toggleBeginnerMode,
    updatePreferences: updatePreferencesHandler,
    refreshPreferences,
  };

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
}

export function usePreferences() {
  const context = useContext(PreferencesContext);
  if (!context) {
    throw new Error('usePreferences must be used within PreferencesProvider');
  }
  return context;
}

/**
 * Hook to check if beginner mode is enabled.
 * Returns false while loading to prevent flash of content.
 */
export function useBeginnerMode() {
  const { beginnerModeEnabled, isLoading } = usePreferences();
  return {
    isBeginnerMode: !isLoading && beginnerModeEnabled,
    isLoading,
  };
}
