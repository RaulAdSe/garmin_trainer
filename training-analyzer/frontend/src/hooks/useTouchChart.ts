'use client';

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import type {
  TouchState,
  PinnedTooltip,
  PinchState,
  TimeRange,
  TouchChartConfig,
  UseTouchChartReturn,
} from '@/types/touch-chart';

const DEFAULT_CONFIG: Required<TouchChartConfig> = {
  swipeThreshold: 10,
  enablePinchZoom: true,
  enableTapToPin: true,
  enableSwipeScrub: true,
  minZoom: 0.1, // 10% of total range minimum
  maxZoom: 1.0, // 100% of total range maximum
  touchMoveDebounce: 16, // ~60fps
};

// Haptic feedback for supported devices
const triggerHapticFeedback = (type: 'light' | 'medium' | 'heavy' = 'light') => {
  if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
    const patterns = {
      light: [5],
      medium: [10],
      heavy: [20],
    };
    navigator.vibrate(patterns[type]);
  }
};

const INITIAL_TOUCH_STATE: TouchState = {
  isTouching: false,
  startX: 0,
  startY: 0,
  currentX: 0,
  currentY: 0,
  touchCount: 0,
};

const INITIAL_PINCH_STATE: PinchState = {
  isPinching: false,
  initialDistance: 0,
  currentDistance: 0,
  centerX: 0,
  centerY: 0,
};

/**
 * Calculate distance between two touch points
 */
function getTouchDistance(touch1: React.Touch, touch2: React.Touch): number {
  const dx = touch2.clientX - touch1.clientX;
  const dy = touch2.clientY - touch1.clientY;
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Calculate center point between two touches
 */
function getTouchCenter(touch1: React.Touch, touch2: React.Touch): { x: number; y: number } {
  return {
    x: (touch1.clientX + touch2.clientX) / 2,
    y: (touch1.clientY + touch2.clientY) / 2,
  };
}

/**
 * Hook for managing touch interactions on Recharts components
 * Supports tap-to-pin tooltips, swipe scrubbing, and pinch-to-zoom
 *
 * @param dataLength - Total number of data points
 * @param fullTimeRange - Full time range of the data
 * @param config - Configuration options
 * @param hintStorageKey - LocalStorage key for hint dismissal
 * @param syncedIndex - External active index for synced charts
 * @param onSyncedIndexChange - Callback when index changes for sync
 */
export function useTouchChart(
  dataLength: number,
  fullTimeRange: TimeRange,
  config: TouchChartConfig = {},
  hintStorageKey = 'touch-chart-hint-dismissed',
  syncedIndex?: number | null,
  onSyncedIndexChange?: (index: number | null) => void
): UseTouchChartReturn {
  const mergedConfig = { ...DEFAULT_CONFIG, ...config };

  // Determine if we're in synced mode
  const isSynced = syncedIndex !== undefined && onSyncedIndexChange !== undefined;

  // State
  const [touchState, setTouchState] = useState<TouchState>(INITIAL_TOUCH_STATE);
  const [pinnedTooltip, setPinnedTooltip] = useState<PinnedTooltip | null>(null);
  const [pinchState, setPinchState] = useState<PinchState>(INITIAL_PINCH_STATE);
  const [timeRange, setTimeRange] = useState<TimeRange | null>(null);
  const [scrubIndex, setScrubIndex] = useState<number | null>(null);
  const [showHint, setShowHint] = useState(false);
  const [internalActiveIndex, setInternalActiveIndex] = useState<number | null>(null);

  // Refs for tracking gesture state
  const touchStartTime = useRef<number>(0);
  const isTap = useRef<boolean>(false);
  const containerRef = useRef<DOMRect | null>(null);
  const lastMoveTime = useRef<number>(0);
  const initialTimeRange = useRef<TimeRange | null>(null);

  // Use synced index if provided, otherwise use internal state
  const activeIndex = isSynced ? syncedIndex : internalActiveIndex;

  // Function to update active index (handles both synced and non-synced modes)
  const setActiveIndex = useCallback((index: number | null) => {
    if (isSynced && onSyncedIndexChange) {
      onSyncedIndexChange(index);
    } else {
      setInternalActiveIndex(index);
    }
  }, [isSynced, onSyncedIndexChange]);

  // Check localStorage for hint dismissal on mount
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const dismissed = localStorage.getItem(hintStorageKey);
    if (!dismissed) {
      setShowHint(true);
    }
  }, [hintStorageKey]);

  /**
   * Convert X coordinate to data index
   */
  const xToDataIndex = useCallback(
    (x: number, containerWidth: number): number => {
      if (dataLength === 0 || containerWidth === 0) return 0;
      const ratio = Math.max(0, Math.min(1, x / containerWidth));
      return Math.round(ratio * (dataLength - 1));
    },
    [dataLength]
  );

  /**
   * Pin tooltip at specific position
   */
  const pinTooltip = useCallback((dataIndex: number, x: number, y: number) => {
    if (!mergedConfig.enableTapToPin) return;
    setPinnedTooltip({ dataIndex, x, y });
    setActiveIndex(dataIndex);
    // Haptic feedback on pin
    triggerHapticFeedback('medium');
  }, [mergedConfig.enableTapToPin, setActiveIndex]);

  /**
   * Unpin current tooltip
   */
  const unpinTooltip = useCallback(() => {
    setPinnedTooltip(null);
    setActiveIndex(null);
    triggerHapticFeedback('light');
  }, [setActiveIndex]);

  /**
   * Reset zoom to full range
   */
  const resetZoom = useCallback(() => {
    setTimeRange(null);
    initialTimeRange.current = null;
  }, []);

  /**
   * Dismiss the hint
   */
  const dismissHint = useCallback(() => {
    setShowHint(false);
    if (typeof window !== 'undefined') {
      localStorage.setItem(hintStorageKey, 'true');
    }
  }, [hintStorageKey]);

  /**
   * Set zoom range programmatically
   */
  const setZoomRange = useCallback((range: TimeRange) => {
    const fullDuration = fullTimeRange.end - fullTimeRange.start;
    const newDuration = range.end - range.start;
    const zoomLevel = newDuration / fullDuration;

    // Clamp to min/max zoom
    if (zoomLevel < mergedConfig.minZoom || zoomLevel > mergedConfig.maxZoom) {
      return;
    }

    setTimeRange(range);
  }, [fullTimeRange, mergedConfig.minZoom, mergedConfig.maxZoom]);

  /**
   * Handle touch start
   */
  const onTouchStart = useCallback((e: React.TouchEvent) => {
    const touches = e.touches;
    const target = e.currentTarget as HTMLElement;
    containerRef.current = target.getBoundingClientRect();

    touchStartTime.current = Date.now();
    isTap.current = true;

    // Dismiss hint on first interaction
    if (showHint) {
      dismissHint();
    }

    if (touches.length === 1) {
      // Single touch - potential tap or scrub
      const touch = touches[0];
      const rect = containerRef.current;
      const x = touch.clientX - rect.left;
      const y = touch.clientY - rect.top;

      setTouchState({
        isTouching: true,
        startX: x,
        startY: y,
        currentX: x,
        currentY: y,
        touchCount: 1,
      });
    } else if (touches.length === 2 && mergedConfig.enablePinchZoom) {
      // Two touches - pinch gesture
      const distance = getTouchDistance(touches[0], touches[1]);
      const center = getTouchCenter(touches[0], touches[1]);

      setPinchState({
        isPinching: true,
        initialDistance: distance,
        currentDistance: distance,
        centerX: center.x,
        centerY: center.y,
      });

      // Store current time range for pinch calculations
      initialTimeRange.current = timeRange || fullTimeRange;

      setTouchState(prev => ({
        ...prev,
        isTouching: true,
        touchCount: 2,
      }));

      isTap.current = false;
    }
  }, [showHint, dismissHint, mergedConfig.enablePinchZoom, timeRange, fullTimeRange]);

  /**
   * Handle touch move
   */
  const onTouchMove = useCallback((e: React.TouchEvent) => {
    const now = Date.now();
    if (now - lastMoveTime.current < mergedConfig.touchMoveDebounce) {
      return;
    }
    lastMoveTime.current = now;

    const touches = e.touches;
    const rect = containerRef.current;
    if (!rect) return;

    if (touches.length === 1 && !pinchState.isPinching) {
      // Single touch move - scrubbing
      const touch = touches[0];
      const x = touch.clientX - rect.left;
      const y = touch.clientY - rect.top;

      const deltaX = Math.abs(x - touchState.startX);
      const deltaY = Math.abs(y - touchState.startY);

      // Check if this is a horizontal swipe (scrub)
      if (deltaX > mergedConfig.swipeThreshold && deltaX > deltaY) {
        isTap.current = false;

        if (mergedConfig.enableSwipeScrub) {
          // Calculate data index from X position
          const index = xToDataIndex(x, rect.width);
          setScrubIndex(index);
          setActiveIndex(index);

          // Unpin tooltip during scrub
          if (pinnedTooltip) {
            unpinTooltip();
          }
        }
      }

      setTouchState(prev => ({
        ...prev,
        currentX: x,
        currentY: y,
      }));
    } else if (touches.length === 2 && pinchState.isPinching && mergedConfig.enablePinchZoom) {
      // Pinch move - zooming
      const distance = getTouchDistance(touches[0], touches[1]);
      const center = getTouchCenter(touches[0], touches[1]);

      setPinchState(prev => ({
        ...prev,
        currentDistance: distance,
        centerX: center.x,
        centerY: center.y,
      }));

      // Calculate zoom
      const zoomFactor = distance / pinchState.initialDistance;
      const initialRange = initialTimeRange.current;

      if (initialRange) {
        const initialDuration = initialRange.end - initialRange.start;
        const fullDuration = fullTimeRange.end - fullTimeRange.start;

        // New duration is inversely proportional to zoom factor
        let newDuration = initialDuration / zoomFactor;

        // Clamp duration to min/max zoom levels
        const minDuration = fullDuration * mergedConfig.minZoom;
        const maxDuration = fullDuration * mergedConfig.maxZoom;
        newDuration = Math.max(minDuration, Math.min(maxDuration, newDuration));

        // Calculate center point in time
        const centerRatio = (center.x - rect.left) / rect.width;
        const initialCenter = initialRange.start + centerRatio * initialDuration;

        // Calculate new range centered on pinch center
        let newStart = initialCenter - centerRatio * newDuration;
        let newEnd = newStart + newDuration;

        // Clamp to full range bounds
        if (newStart < fullTimeRange.start) {
          newStart = fullTimeRange.start;
          newEnd = newStart + newDuration;
        }
        if (newEnd > fullTimeRange.end) {
          newEnd = fullTimeRange.end;
          newStart = newEnd - newDuration;
        }

        setTimeRange({ start: newStart, end: newEnd });
      }
    }
  }, [
    touchState.startX,
    touchState.startY,
    pinchState,
    pinnedTooltip,
    unpinTooltip,
    xToDataIndex,
    fullTimeRange,
    mergedConfig,
  ]);

  /**
   * Handle touch end
   */
  const onTouchEnd = useCallback((e: React.TouchEvent) => {
    const touchDuration = Date.now() - touchStartTime.current;
    const rect = containerRef.current;

    // Check if this was a tap (short duration, minimal movement)
    if (
      isTap.current &&
      touchDuration < 300 &&
      touchState.touchCount === 1 &&
      mergedConfig.enableTapToPin &&
      rect
    ) {
      const deltaX = Math.abs(touchState.currentX - touchState.startX);
      const deltaY = Math.abs(touchState.currentY - touchState.startY);

      if (deltaX < mergedConfig.swipeThreshold && deltaY < mergedConfig.swipeThreshold) {
        // This was a tap
        if (pinnedTooltip) {
          // Tap elsewhere to unpin
          unpinTooltip();
        } else {
          // Pin tooltip at tap location
          const index = xToDataIndex(touchState.currentX, rect.width);
          pinTooltip(index, touchState.currentX, touchState.currentY);
        }
      }
    }

    // Reset scrub index on touch end
    setScrubIndex(null);
    // Clear active index if we were scrubbing (not pinned)
    if (!pinnedTooltip) {
      setActiveIndex(null);
    }

    // Check remaining touches
    if (e.touches.length === 0) {
      // All touches ended
      setTouchState(INITIAL_TOUCH_STATE);
      setPinchState(INITIAL_PINCH_STATE);
      initialTimeRange.current = null;
    } else if (e.touches.length === 1) {
      // One touch remaining after pinch
      setPinchState(INITIAL_PINCH_STATE);
      const touch = e.touches[0];
      if (rect) {
        setTouchState({
          isTouching: true,
          startX: touch.clientX - rect.left,
          startY: touch.clientY - rect.top,
          currentX: touch.clientX - rect.left,
          currentY: touch.clientY - rect.top,
          touchCount: 1,
        });
      }
    }
  }, [
    touchState,
    pinnedTooltip,
    unpinTooltip,
    pinTooltip,
    xToDataIndex,
    mergedConfig,
  ]);

  /**
   * Handle touch cancel
   */
  const onTouchCancel = useCallback(() => {
    setTouchState(INITIAL_TOUCH_STATE);
    setPinchState(INITIAL_PINCH_STATE);
    setScrubIndex(null);
    initialTimeRange.current = null;
  }, []);

  return {
    touchState,
    pinnedTooltip,
    pinchState,
    timeRange,
    showHint,
    handlers: {
      onTouchStart,
      onTouchMove,
      onTouchEnd,
      onTouchCancel,
    },
    pinTooltip,
    unpinTooltip,
    resetZoom,
    dismissHint,
    scrubIndex,
    setZoomRange,
    activeIndex,
    setActiveIndex,
    isSynced,
  };
}

export default useTouchChart;
