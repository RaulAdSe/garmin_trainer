'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { analyzeWorkoutStream } from '@/lib/api-client';
import type { WorkoutAnalysis } from '@/lib/types';

interface UseLLMStreamOptions {
  onChunk?: (chunk: string, fullContent: string) => void;
  onComplete?: (analysis: WorkoutAnalysis) => void;
  onError?: (error: Error) => void;
}

interface UseLLMStreamReturn {
  content: string;
  isStreaming: boolean;
  isComplete: boolean;
  error: string | null;
  analysis: WorkoutAnalysis | null;
  startStream: (workoutId: string, regenerate?: boolean) => void;
  stopStream: () => void;
  reset: () => void;
}

export function useLLMStream(options: UseLLMStreamOptions = {}): UseLLMStreamReturn {
  const { onChunk, onComplete, onError } = options;

  const [content, setContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<WorkoutAnalysis | null>(null);

  // Ref to store the abort function
  const abortRef = useRef<(() => void) | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortRef.current) {
        abortRef.current();
      }
    };
  }, []);

  const startStream = useCallback(
    (workoutId: string, regenerate = false) => {
      // Reset state
      setContent('');
      setIsStreaming(true);
      setIsComplete(false);
      setError(null);
      setAnalysis(null);

      // Abort any existing stream
      if (abortRef.current) {
        abortRef.current();
      }

      // Start new stream
      const abort = analyzeWorkoutStream(
        {
          workoutId,
          includeContext: true,
          regenerate,
        },
        // On chunk
        (chunk) => {
          setContent((prev) => {
            const newContent = prev + chunk;
            onChunk?.(chunk, newContent);
            return newContent;
          });
        },
        // On done
        (analysisResult) => {
          setIsStreaming(false);
          setIsComplete(true);
          setAnalysis(analysisResult);
          onComplete?.(analysisResult);
        },
        // On error
        (err) => {
          setIsStreaming(false);
          setError(err.message);
          onError?.(err);
        }
      );

      abortRef.current = abort;
    },
    [onChunk, onComplete, onError]
  );

  const stopStream = useCallback(() => {
    if (abortRef.current) {
      abortRef.current();
      abortRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const reset = useCallback(() => {
    stopStream();
    setContent('');
    setIsComplete(false);
    setError(null);
    setAnalysis(null);
  }, [stopStream]);

  return {
    content,
    isStreaming,
    isComplete,
    error,
    analysis,
    startStream,
    stopStream,
    reset,
  };
}

// Hook for streaming with typing effect simulation
interface UseTypingStreamOptions extends UseLLMStreamOptions {
  typingSpeed?: number; // Characters per second
}

interface UseTypingStreamReturn extends Omit<UseLLMStreamReturn, 'content'> {
  displayedContent: string;
  fullContent: string;
}

export function useTypingStream(
  options: UseTypingStreamOptions = {}
): UseTypingStreamReturn {
  const { typingSpeed = 50, ...streamOptions } = options;

  const [fullContent, setFullContent] = useState('');
  const [displayedContent, setDisplayedContent] = useState('');
  const animationRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number>(0);

  const baseStream = useLLMStream({
    ...streamOptions,
    onChunk: (chunk, full) => {
      setFullContent(full);
      streamOptions.onChunk?.(chunk, full);
    },
  });

  // Typing animation effect
  useEffect(() => {
    if (!baseStream.isStreaming && displayedContent.length >= fullContent.length) {
      return;
    }

    const animate = (timestamp: number) => {
      if (!lastTimeRef.current) {
        lastTimeRef.current = timestamp;
      }

      const elapsed = timestamp - lastTimeRef.current;
      const charsToAdd = Math.floor((elapsed / 1000) * typingSpeed);

      if (charsToAdd > 0) {
        setDisplayedContent((prev) => {
          const targetLength = Math.min(prev.length + charsToAdd, fullContent.length);
          return fullContent.slice(0, targetLength);
        });
        lastTimeRef.current = timestamp;
      }

      if (displayedContent.length < fullContent.length) {
        animationRef.current = requestAnimationFrame(animate);
      }
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [fullContent, displayedContent.length, baseStream.isStreaming, typingSpeed]);

  // Reset displayed content when stream resets
  useEffect(() => {
    if (fullContent === '') {
      setDisplayedContent('');
    }
  }, [fullContent]);

  return {
    ...baseStream,
    displayedContent,
    fullContent,
  };
}

// Hook for managing multiple concurrent streams (e.g., for batch analysis)
interface UseMultiStreamState {
  [workoutId: string]: {
    content: string;
    isStreaming: boolean;
    isComplete: boolean;
    error: string | null;
    analysis: WorkoutAnalysis | null;
  };
}

interface UseMultiLLMStreamReturn {
  streams: UseMultiStreamState;
  startStream: (workoutId: string, regenerate?: boolean) => void;
  stopStream: (workoutId: string) => void;
  stopAllStreams: () => void;
  resetStream: (workoutId: string) => void;
  resetAllStreams: () => void;
}

export function useMultiLLMStream(): UseMultiLLMStreamReturn {
  const [streams, setStreams] = useState<UseMultiStreamState>({});
  const abortsRef = useRef<Map<string, () => void>>(new Map());

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortsRef.current.forEach((abort) => abort());
      abortsRef.current.clear();
    };
  }, []);

  const startStream = useCallback((workoutId: string, regenerate = false) => {
    // Initialize or reset stream state
    setStreams((prev) => ({
      ...prev,
      [workoutId]: {
        content: '',
        isStreaming: true,
        isComplete: false,
        error: null,
        analysis: null,
      },
    }));

    // Abort existing stream for this workout
    const existingAbort = abortsRef.current.get(workoutId);
    if (existingAbort) {
      existingAbort();
    }

    // Start new stream
    const abort = analyzeWorkoutStream(
      {
        workoutId,
        includeContext: true,
        regenerate,
      },
      (chunk) => {
        setStreams((prev) => ({
          ...prev,
          [workoutId]: {
            ...prev[workoutId],
            content: (prev[workoutId]?.content || '') + chunk,
          },
        }));
      },
      (analysis) => {
        setStreams((prev) => ({
          ...prev,
          [workoutId]: {
            ...prev[workoutId],
            isStreaming: false,
            isComplete: true,
            analysis,
          },
        }));
        abortsRef.current.delete(workoutId);
      },
      (err) => {
        setStreams((prev) => ({
          ...prev,
          [workoutId]: {
            ...prev[workoutId],
            isStreaming: false,
            error: err.message,
          },
        }));
        abortsRef.current.delete(workoutId);
      }
    );

    abortsRef.current.set(workoutId, abort);
  }, []);

  const stopStream = useCallback((workoutId: string) => {
    const abort = abortsRef.current.get(workoutId);
    if (abort) {
      abort();
      abortsRef.current.delete(workoutId);
    }
    setStreams((prev) => ({
      ...prev,
      [workoutId]: {
        ...prev[workoutId],
        isStreaming: false,
      },
    }));
  }, []);

  const stopAllStreams = useCallback(() => {
    abortsRef.current.forEach((abort) => abort());
    abortsRef.current.clear();
    setStreams((prev) => {
      const updated: UseMultiStreamState = {};
      for (const id in prev) {
        updated[id] = { ...prev[id], isStreaming: false };
      }
      return updated;
    });
  }, []);

  const resetStream = useCallback((workoutId: string) => {
    const abort = abortsRef.current.get(workoutId);
    if (abort) {
      abort();
      abortsRef.current.delete(workoutId);
    }
    setStreams((prev) => {
      const { [workoutId]: removed, ...rest } = prev;
      return rest;
    });
  }, []);

  const resetAllStreams = useCallback(() => {
    abortsRef.current.forEach((abort) => abort());
    abortsRef.current.clear();
    setStreams({});
  }, []);

  return {
    streams,
    startStream,
    stopStream,
    stopAllStreams,
    resetStream,
    resetAllStreams,
  };
}

export default useLLMStream;
