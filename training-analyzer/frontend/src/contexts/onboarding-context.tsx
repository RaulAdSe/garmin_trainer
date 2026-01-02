'use client';

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react';

// Constants
const ONBOARDING_KEY = 'ta_onboarding_state';
const FEATURE_INTRO_KEY = 'ta_feature_intro_week';

export type OnboardingStep = 'welcome' | 'connection' | 'profile' | 'complete';

export interface OnboardingProfile {
  // Goal settings
  primaryGoal?: 'race' | 'fitness' | 'health' | 'weight';
  raceDistance?: '5k' | '10k' | 'half_marathon' | 'marathon' | 'ultra';
  weeklyHours?: number;
  experienceLevel?: 'beginner' | 'intermediate' | 'advanced';

  // Zone calibration
  zoneMethod?: 'auto' | 'manual' | 'lthr' | 'max_hr';
  maxHr?: number;
  lthr?: number;

  // Preferences
  units?: 'metric' | 'imperial';
}

export interface OnboardingState {
  isComplete: boolean;
  currentStep: OnboardingStep;
  connectionType?: 'garmin' | 'strava' | 'manual' | 'skip';
  profile: OnboardingProfile;
  completedAt?: string;
}

export interface FeatureIntroState {
  currentWeek: number;
  startedAt: string;
  seenFeatures: string[];
}

interface OnboardingContextType {
  // Onboarding state
  state: OnboardingState;
  featureIntro: FeatureIntroState;
  isLoading: boolean;

  // Navigation
  goToStep: (step: OnboardingStep) => void;
  nextStep: () => void;
  previousStep: () => void;

  // Actions
  setConnectionType: (type: 'garmin' | 'strava' | 'manual' | 'skip') => void;
  updateProfile: (updates: Partial<OnboardingProfile>) => void;
  completeOnboarding: () => void;
  resetOnboarding: () => void;

  // Feature intro
  markFeatureSeen: (featureId: string) => void;
  hasSeenFeature: (featureId: string) => boolean;

  // Helpers
  shouldShowOnboarding: boolean;
  progress: number;
}

const defaultState: OnboardingState = {
  isComplete: false,
  currentStep: 'welcome',
  profile: {
    units: 'metric',
  },
};

const defaultFeatureIntro: FeatureIntroState = {
  currentWeek: 1,
  startedAt: new Date().toISOString(),
  seenFeatures: [],
};

const OnboardingContext = createContext<OnboardingContextType | null>(null);

const STEP_ORDER: OnboardingStep[] = ['welcome', 'connection', 'profile', 'complete'];

export function OnboardingProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<OnboardingState>(defaultState);
  const [featureIntro, setFeatureIntro] = useState<FeatureIntroState>(defaultFeatureIntro);
  const [isLoading, setIsLoading] = useState(true);

  // Load state from localStorage on mount
  useEffect(() => {
    try {
      const savedState = localStorage.getItem(ONBOARDING_KEY);
      if (savedState) {
        setState(JSON.parse(savedState));
      }

      const savedFeatureIntro = localStorage.getItem(FEATURE_INTRO_KEY);
      if (savedFeatureIntro) {
        const parsed = JSON.parse(savedFeatureIntro);
        // Calculate current week based on start date
        const startDate = new Date(parsed.startedAt);
        const now = new Date();
        const weeksDiff = Math.floor((now.getTime() - startDate.getTime()) / (7 * 24 * 60 * 60 * 1000));
        setFeatureIntro({
          ...parsed,
          currentWeek: Math.min(weeksDiff + 1, 4), // Cap at week 4
        });
      }
    } catch (error) {
      console.error('Failed to load onboarding state:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Save state to localStorage when it changes
  useEffect(() => {
    if (!isLoading) {
      try {
        localStorage.setItem(ONBOARDING_KEY, JSON.stringify(state));
      } catch (error) {
        console.error('Failed to save onboarding state:', error);
      }
    }
  }, [state, isLoading]);

  // Save feature intro state
  useEffect(() => {
    if (!isLoading) {
      try {
        localStorage.setItem(FEATURE_INTRO_KEY, JSON.stringify(featureIntro));
      } catch (error) {
        console.error('Failed to save feature intro state:', error);
      }
    }
  }, [featureIntro, isLoading]);

  const goToStep = useCallback((step: OnboardingStep) => {
    setState((prev) => ({ ...prev, currentStep: step }));
  }, []);

  const nextStep = useCallback(() => {
    setState((prev) => {
      const currentIndex = STEP_ORDER.indexOf(prev.currentStep);
      const nextIndex = Math.min(currentIndex + 1, STEP_ORDER.length - 1);
      return { ...prev, currentStep: STEP_ORDER[nextIndex] };
    });
  }, []);

  const previousStep = useCallback(() => {
    setState((prev) => {
      const currentIndex = STEP_ORDER.indexOf(prev.currentStep);
      const prevIndex = Math.max(currentIndex - 1, 0);
      return { ...prev, currentStep: STEP_ORDER[prevIndex] };
    });
  }, []);

  const setConnectionType = useCallback(
    (type: 'garmin' | 'strava' | 'manual' | 'skip') => {
      setState((prev) => ({ ...prev, connectionType: type }));
    },
    []
  );

  const updateProfile = useCallback((updates: Partial<OnboardingProfile>) => {
    setState((prev) => ({
      ...prev,
      profile: { ...prev.profile, ...updates },
    }));
  }, []);

  const completeOnboarding = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isComplete: true,
      currentStep: 'complete',
      completedAt: new Date().toISOString(),
    }));

    // Initialize feature intro when onboarding completes
    setFeatureIntro({
      currentWeek: 1,
      startedAt: new Date().toISOString(),
      seenFeatures: [],
    });
  }, []);

  const resetOnboarding = useCallback(() => {
    setState(defaultState);
    setFeatureIntro(defaultFeatureIntro);
    localStorage.removeItem(ONBOARDING_KEY);
    localStorage.removeItem(FEATURE_INTRO_KEY);
  }, []);

  const markFeatureSeen = useCallback((featureId: string) => {
    setFeatureIntro((prev) => ({
      ...prev,
      seenFeatures: prev.seenFeatures.includes(featureId)
        ? prev.seenFeatures
        : [...prev.seenFeatures, featureId],
    }));
  }, []);

  const hasSeenFeature = useCallback(
    (featureId: string) => featureIntro.seenFeatures.includes(featureId),
    [featureIntro.seenFeatures]
  );

  // Calculate progress (0-100)
  const progress =
    (STEP_ORDER.indexOf(state.currentStep) / (STEP_ORDER.length - 1)) * 100;

  const shouldShowOnboarding = !state.isComplete && !isLoading;

  return (
    <OnboardingContext.Provider
      value={{
        state,
        featureIntro,
        isLoading,
        goToStep,
        nextStep,
        previousStep,
        setConnectionType,
        updateProfile,
        completeOnboarding,
        resetOnboarding,
        markFeatureSeen,
        hasSeenFeature,
        shouldShowOnboarding,
        progress,
      }}
    >
      {children}
    </OnboardingContext.Provider>
  );
}

export function useOnboarding() {
  const context = useContext(OnboardingContext);
  if (!context) {
    throw new Error('useOnboarding must be used within OnboardingProvider');
  }
  return context;
}
