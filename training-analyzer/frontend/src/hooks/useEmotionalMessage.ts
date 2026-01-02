'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useCallback, useMemo } from 'react';
import { authFetch } from '@/lib/auth-fetch';
import type {
  EmotionalContext,
  MessageTone,
  EmotionalMessage,
  AthleteContextData,
} from '@/lib/emotional-messages';
import {
  detectEmotionalContext,
  getRandomMessage,
  getAllMessages,
} from '@/lib/emotional-messages';

const API_BASE = 'http://localhost:8000/api/v1';

// =============================================================================
// Types
// =============================================================================

export interface EmotionalMessageResponse {
  context: string;
  message: string;
  tone: string;
  actionSuggestion?: string;
  recoveryTips?: string[];
  alternativeActivities?: string[];
}

export interface DetectedContextResponse {
  detectedContext: string | null;
  message: EmotionalMessageResponse | null;
}

export interface DismissedMessage {
  context: EmotionalContext;
  dismissedAt: number;
}

// =============================================================================
// API Functions
// =============================================================================

async function fetchEmotionalMessage(
  context: EmotionalContext,
  includeTips: boolean = true,
  tone?: MessageTone
): Promise<EmotionalMessageResponse> {
  const params = new URLSearchParams();
  params.set('context', context);
  params.set('include_tips', String(includeTips));
  if (tone) params.set('tone', tone);

  const response = await authFetch(`${API_BASE}/emotional/message?${params.toString()}`);
  if (!response.ok) {
    throw new Error('Failed to fetch emotional message');
  }
  return response.json();
}

async function fetchDetectedContext(): Promise<DetectedContextResponse> {
  const response = await authFetch(`${API_BASE}/emotional/detect`);
  if (!response.ok) {
    throw new Error('Failed to detect emotional context');
  }
  return response.json();
}

async function fetchAvailableContexts(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/emotional/contexts`);
  if (!response.ok) {
    throw new Error('Failed to fetch available contexts');
  }
  const data = await response.json();
  return data.contexts;
}

async function fetchRecoveryMessage(
  readinessScore: number
): Promise<EmotionalMessageResponse | null> {
  const response = await authFetch(
    `${API_BASE}/emotional/recovery?readiness_score=${readinessScore}`
  );
  if (!response.ok) {
    throw new Error('Failed to fetch recovery message');
  }
  return response.json();
}

// =============================================================================
// Query Keys
// =============================================================================

export const emotionalMessageKeys = {
  all: ['emotional-messages'] as const,
  message: (context: EmotionalContext) => [...emotionalMessageKeys.all, 'message', context] as const,
  detect: () => [...emotionalMessageKeys.all, 'detect'] as const,
  contexts: () => [...emotionalMessageKeys.all, 'contexts'] as const,
  recovery: (score: number) => [...emotionalMessageKeys.all, 'recovery', score] as const,
};

// =============================================================================
// Hooks
// =============================================================================

/**
 * Hook for fetching a contextual emotional message from the API
 */
export function useEmotionalMessageAPI(
  context: EmotionalContext,
  options?: {
    includeTips?: boolean;
    tone?: MessageTone;
    enabled?: boolean;
  }
) {
  const { includeTips = true, tone, enabled = true } = options || {};

  return useQuery({
    queryKey: emotionalMessageKeys.message(context),
    queryFn: () => fetchEmotionalMessage(context, includeTips, tone),
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook for auto-detecting the appropriate emotional context
 */
export function useDetectEmotionalContext(enabled: boolean = true) {
  return useQuery({
    queryKey: emotionalMessageKeys.detect(),
    queryFn: fetchDetectedContext,
    enabled,
    staleTime: 60 * 1000, // 1 minute
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook for getting available contexts
 */
export function useAvailableContexts() {
  return useQuery({
    queryKey: emotionalMessageKeys.contexts(),
    queryFn: fetchAvailableContexts,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
  });
}

/**
 * Hook for getting a recovery message based on readiness score
 */
export function useRecoveryMessage(readinessScore: number, enabled: boolean = true) {
  return useQuery({
    queryKey: emotionalMessageKeys.recovery(readinessScore),
    queryFn: () => fetchRecoveryMessage(readinessScore),
    enabled: enabled && readinessScore > 0,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
}

/**
 * Main hook for emotional messaging with local detection and dismissal tracking
 */
export function useEmotionalMessage(athleteData?: AthleteContextData) {
  const [dismissedMessages, setDismissedMessages] = useState<DismissedMessage[]>(() => {
    // Load from localStorage on mount
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('dismissed-emotional-messages');
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          // Filter out messages dismissed more than 24 hours ago
          const now = Date.now();
          const dayMs = 24 * 60 * 60 * 1000;
          return parsed.filter((m: DismissedMessage) => now - m.dismissedAt < dayMs);
        } catch {
          return [];
        }
      }
    }
    return [];
  });

  // Detect context locally
  const detectedContext = useMemo(() => {
    if (!athleteData) return null;
    return detectEmotionalContext(athleteData);
  }, [athleteData]);

  // Check if context is dismissed
  const isContextDismissed = useCallback(
    (context: EmotionalContext): boolean => {
      return dismissedMessages.some((m) => m.context === context);
    },
    [dismissedMessages]
  );

  // Get current message (if not dismissed)
  const currentMessage = useMemo(() => {
    if (!detectedContext || isContextDismissed(detectedContext)) {
      return null;
    }
    const messageData = getRandomMessage(detectedContext);
    if (!messageData) return null;
    return {
      context: detectedContext,
      ...messageData,
    } as EmotionalMessage;
  }, [detectedContext, isContextDismissed]);

  // Dismiss a message
  const dismissMessage = useCallback((context: EmotionalContext) => {
    setDismissedMessages((prev) => {
      const newDismissed = [...prev, { context, dismissedAt: Date.now() }];
      // Save to localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('dismissed-emotional-messages', JSON.stringify(newDismissed));
      }
      return newDismissed;
    });
  }, []);

  // Get a new message for the same context (when user wants variation)
  const refreshMessage = useCallback(() => {
    if (!detectedContext) return null;
    return getRandomMessage(detectedContext);
  }, [detectedContext]);

  // Clear all dismissed messages
  const clearDismissed = useCallback(() => {
    setDismissedMessages([]);
    if (typeof window !== 'undefined') {
      localStorage.removeItem('dismissed-emotional-messages');
    }
  }, []);

  return {
    context: detectedContext,
    message: currentMessage,
    isContextDismissed,
    dismissMessage,
    refreshMessage,
    clearDismissed,
    allMessagesForContext: detectedContext ? getAllMessages(detectedContext) : [],
  };
}

export default useEmotionalMessage;
