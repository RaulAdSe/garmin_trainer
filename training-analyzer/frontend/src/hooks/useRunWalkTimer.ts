'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import type {
  RunWalkInterval,
  RunWalkPhase,
  RunWalkTimerState,
} from '@/lib/types';

export interface UseRunWalkTimerOptions {
  intervals: RunWalkInterval;
  onIntervalComplete?: (intervalNumber: number, phase: RunWalkPhase) => void;
  onWorkoutComplete?: (totalDuration: number) => void;
  onPhaseChange?: (newPhase: RunWalkPhase, intervalNumber: number) => void;
}

export interface UseRunWalkTimerReturn {
  state: RunWalkTimerState;
  start: () => void;
  pause: () => void;
  resume: () => void;
  stop: () => void;
  reset: () => void;
  skipToNext: () => void;
  totalWorkoutDuration: number;
  formattedTimeRemaining: string;
  formattedTotalElapsed: string;
  progressPercent: number;
  intervalProgressPercent: number;
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function useRunWalkTimer(
  options: UseRunWalkTimerOptions
): UseRunWalkTimerReturn {
  const { intervals, onIntervalComplete, onWorkoutComplete, onPhaseChange } =
    options;

  const [state, setState] = useState<RunWalkTimerState>({
    phase: 'idle',
    currentInterval: 0,
    timeRemaining: intervals.runSeconds,
    totalElapsed: 0,
    isRunning: false,
    isPaused: false,
    isComplete: false,
  });

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);

  // Calculate total workout duration
  const totalWorkoutDuration =
    (intervals.runSeconds + intervals.walkSeconds) * intervals.repetitions;

  // Calculate progress percentages
  const progressPercent =
    totalWorkoutDuration > 0
      ? (state.totalElapsed / totalWorkoutDuration) * 100
      : 0;

  const currentPhaseDuration =
    state.phase === 'run' ? intervals.runSeconds : intervals.walkSeconds;
  const intervalProgressPercent =
    currentPhaseDuration > 0
      ? ((currentPhaseDuration - state.timeRemaining) / currentPhaseDuration) *
        100
      : 0;

  // Initialize audio context lazily
  const getAudioContext = useCallback(() => {
    if (typeof window !== 'undefined' && !audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext })
          .webkitAudioContext)();
    }
    return audioContextRef.current;
  }, []);

  // Play alert sound
  const playAlert = useCallback(
    (type: 'transition' | 'complete') => {
      const audioContext = getAudioContext();
      if (!audioContext) return;

      try {
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        if (type === 'transition') {
          // Short beep for phase transition
          oscillator.frequency.value = 880;
          oscillator.type = 'sine';
          gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
          gainNode.gain.exponentialRampToValueAtTime(
            0.01,
            audioContext.currentTime + 0.3
          );
          oscillator.start();
          oscillator.stop(audioContext.currentTime + 0.3);
        } else {
          // Longer celebratory tone for completion
          oscillator.frequency.value = 523.25; // C5
          oscillator.type = 'sine';
          gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);

          const now = audioContext.currentTime;
          oscillator.frequency.setValueAtTime(523.25, now);
          oscillator.frequency.setValueAtTime(659.25, now + 0.15); // E5
          oscillator.frequency.setValueAtTime(783.99, now + 0.3); // G5

          gainNode.gain.exponentialRampToValueAtTime(0.01, now + 0.5);
          oscillator.start();
          oscillator.stop(now + 0.5);
        }
      } catch {
        // Audio not available, silently fail
      }
    },
    [getAudioContext]
  );

  // Vibrate device if supported
  const vibrate = useCallback((pattern: number[]) => {
    if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
      navigator.vibrate(pattern);
    }
  }, []);

  // Advance to next phase
  const advancePhase = useCallback(() => {
    setState((prevState) => {
      if (prevState.isComplete) return prevState;

      const currentPhase = prevState.phase;
      const currentInterval = prevState.currentInterval;

      // Notify interval completion
      if (currentPhase !== 'idle') {
        onIntervalComplete?.(currentInterval, currentPhase);
      }

      // If we just finished a walk phase, move to next interval
      if (currentPhase === 'walk') {
        const nextInterval = currentInterval + 1;

        // Check if workout is complete
        if (nextInterval >= intervals.repetitions) {
          playAlert('complete');
          vibrate([200, 100, 200, 100, 400]);
          onWorkoutComplete?.(prevState.totalElapsed);

          return {
            ...prevState,
            phase: 'idle',
            isRunning: false,
            isComplete: true,
            timeRemaining: 0,
          };
        }

        // Move to next interval's run phase
        playAlert('transition');
        vibrate([200, 100, 200]);
        onPhaseChange?.('run', nextInterval);

        return {
          ...prevState,
          phase: 'run',
          currentInterval: nextInterval,
          timeRemaining: intervals.runSeconds,
        };
      }

      // If we just finished a run phase, move to walk
      if (currentPhase === 'run') {
        // If there's no walk time, skip directly to next interval
        if (intervals.walkSeconds === 0) {
          const nextInterval = currentInterval + 1;

          if (nextInterval >= intervals.repetitions) {
            playAlert('complete');
            vibrate([200, 100, 200, 100, 400]);
            onWorkoutComplete?.(prevState.totalElapsed);

            return {
              ...prevState,
              phase: 'idle',
              isRunning: false,
              isComplete: true,
              timeRemaining: 0,
            };
          }

          playAlert('transition');
          vibrate([200, 100, 200]);
          onPhaseChange?.('run', nextInterval);

          return {
            ...prevState,
            phase: 'run',
            currentInterval: nextInterval,
            timeRemaining: intervals.runSeconds,
          };
        }

        playAlert('transition');
        vibrate([200, 100, 200]);
        onPhaseChange?.('walk', currentInterval);

        return {
          ...prevState,
          phase: 'walk',
          timeRemaining: intervals.walkSeconds,
        };
      }

      return prevState;
    });
  }, [
    intervals,
    onIntervalComplete,
    onWorkoutComplete,
    onPhaseChange,
    playAlert,
    vibrate,
  ]);

  // Timer tick
  useEffect(() => {
    if (state.isRunning && !state.isPaused && !state.isComplete) {
      intervalRef.current = setInterval(() => {
        setState((prevState) => {
          if (prevState.timeRemaining <= 1) {
            // Time's up for this phase, advance
            setTimeout(() => advancePhase(), 0);
            return {
              ...prevState,
              timeRemaining: 0,
              totalElapsed: prevState.totalElapsed + 1,
            };
          }

          return {
            ...prevState,
            timeRemaining: prevState.timeRemaining - 1,
            totalElapsed: prevState.totalElapsed + 1,
          };
        });
      }, 1000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [state.isRunning, state.isPaused, state.isComplete, advancePhase]);

  // Cleanup audio context on unmount
  useEffect(() => {
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
    };
  }, []);

  // Start the timer
  const start = useCallback(() => {
    setState({
      phase: 'run',
      currentInterval: 0,
      timeRemaining: intervals.runSeconds,
      totalElapsed: 0,
      isRunning: true,
      isPaused: false,
      isComplete: false,
    });
    onPhaseChange?.('run', 0);
  }, [intervals.runSeconds, onPhaseChange]);

  // Pause the timer
  const pause = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isPaused: true,
    }));
  }, []);

  // Resume the timer
  const resume = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isPaused: false,
    }));
  }, []);

  // Stop the timer completely
  const stop = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isRunning: false,
      isPaused: false,
      phase: 'idle',
    }));
  }, []);

  // Reset the timer
  const reset = useCallback(() => {
    setState({
      phase: 'idle',
      currentInterval: 0,
      timeRemaining: intervals.runSeconds,
      totalElapsed: 0,
      isRunning: false,
      isPaused: false,
      isComplete: false,
    });
  }, [intervals.runSeconds]);

  // Skip to next phase
  const skipToNext = useCallback(() => {
    if (state.isRunning && !state.isComplete) {
      advancePhase();
    }
  }, [state.isRunning, state.isComplete, advancePhase]);

  return {
    state,
    start,
    pause,
    resume,
    stop,
    reset,
    skipToNext,
    totalWorkoutDuration,
    formattedTimeRemaining: formatTime(state.timeRemaining),
    formattedTotalElapsed: formatTime(state.totalElapsed),
    progressPercent,
    intervalProgressPercent,
  };
}

export default useRunWalkTimer;
