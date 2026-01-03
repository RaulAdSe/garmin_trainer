/**
 * Accessibility utilities for WCAG 2.1 AA compliance
 *
 * This module provides utilities for:
 * - Keyboard navigation for interactive elements
 * - ARIA attribute helpers
 * - Focus management
 * - Screen reader announcements
 */

import { KeyboardEvent, useCallback, useEffect, useRef, useState } from 'react';

// ============================================================================
// KEYBOARD NAVIGATION
// ============================================================================

/**
 * Key codes for keyboard navigation
 */
export const Keys = {
  ENTER: 'Enter',
  SPACE: ' ',
  ESCAPE: 'Escape',
  TAB: 'Tab',
  ARROW_LEFT: 'ArrowLeft',
  ARROW_RIGHT: 'ArrowRight',
  ARROW_UP: 'ArrowUp',
  ARROW_DOWN: 'ArrowDown',
  HOME: 'Home',
  END: 'End',
} as const;

/**
 * Check if a keyboard event is an activation key (Enter or Space)
 */
export function isActivationKey(event: KeyboardEvent): boolean {
  return event.key === Keys.ENTER || event.key === Keys.SPACE;
}

/**
 * Check if a keyboard event is an arrow key
 */
export function isArrowKey(event: KeyboardEvent): boolean {
  return [Keys.ARROW_LEFT, Keys.ARROW_RIGHT, Keys.ARROW_UP, Keys.ARROW_DOWN].includes(
    event.key as typeof Keys.ARROW_LEFT
  );
}

/**
 * Handler for keyboard navigation in a list of items
 * Returns the new index based on key pressed
 */
export function getNextIndex(
  currentIndex: number,
  totalItems: number,
  key: string,
  options: { wrap?: boolean; orientation?: 'horizontal' | 'vertical' } = {}
): number {
  const { wrap = true, orientation = 'horizontal' } = options;

  const prevKey = orientation === 'horizontal' ? Keys.ARROW_LEFT : Keys.ARROW_UP;
  const nextKey = orientation === 'horizontal' ? Keys.ARROW_RIGHT : Keys.ARROW_DOWN;

  let newIndex = currentIndex;

  switch (key) {
    case prevKey:
      newIndex = currentIndex - 1;
      if (newIndex < 0) {
        newIndex = wrap ? totalItems - 1 : 0;
      }
      break;
    case nextKey:
      newIndex = currentIndex + 1;
      if (newIndex >= totalItems) {
        newIndex = wrap ? 0 : totalItems - 1;
      }
      break;
    case Keys.HOME:
      newIndex = 0;
      break;
    case Keys.END:
      newIndex = totalItems - 1;
      break;
  }

  return newIndex;
}

/**
 * Props for keyboard-navigable elements
 */
export interface KeyboardNavigationProps {
  onKeyDown: (event: KeyboardEvent) => void;
  tabIndex: number;
  role?: string;
  'aria-label'?: string;
  'aria-selected'?: boolean;
}

/**
 * Hook for keyboard navigation in a list/grid of items
 */
export function useKeyboardNavigation<T extends HTMLElement>(options: {
  itemCount: number;
  onSelect?: (index: number) => void;
  orientation?: 'horizontal' | 'vertical';
  wrap?: boolean;
  initialIndex?: number;
}) {
  const { itemCount, onSelect, orientation = 'horizontal', wrap = true, initialIndex = 0 } = options;
  const [focusedIndex, setFocusedIndex] = useState(initialIndex);
  const itemRefs = useRef<(T | null)[]>([]);

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!isArrowKey(event) && event.key !== Keys.HOME && event.key !== Keys.END) {
      // Handle activation
      if (isActivationKey(event)) {
        event.preventDefault();
        onSelect?.(focusedIndex);
      }
      return;
    }

    event.preventDefault();
    const newIndex = getNextIndex(focusedIndex, itemCount, event.key, { wrap, orientation });

    if (newIndex !== focusedIndex) {
      setFocusedIndex(newIndex);
      itemRefs.current[newIndex]?.focus();
    }
  }, [focusedIndex, itemCount, orientation, wrap, onSelect]);

  const getItemProps = useCallback((index: number): KeyboardNavigationProps => ({
    tabIndex: index === focusedIndex ? 0 : -1,
    onKeyDown: handleKeyDown,
    role: 'option',
    'aria-selected': index === focusedIndex,
  }), [focusedIndex, handleKeyDown]);

  const setItemRef = useCallback((index: number) => (el: T | null) => {
    itemRefs.current[index] = el;
  }, []);

  return {
    focusedIndex,
    setFocusedIndex,
    handleKeyDown,
    getItemProps,
    setItemRef,
  };
}

// ============================================================================
// ARIA ATTRIBUTE HELPERS
// ============================================================================

/**
 * Generate props for a disabled/locked interactive element
 */
export function getLockedElementProps(options: {
  isLocked: boolean;
  lockedMessage?: string;
  unlockLevel?: number;
}): Record<string, string | boolean | number> {
  const { isLocked, lockedMessage, unlockLevel } = options;

  if (!isLocked) {
    return {};
  }

  const message = lockedMessage ?? (unlockLevel ? `Unlocks at level ${unlockLevel}` : 'This feature is locked');

  return {
    'aria-disabled': 'true',
    'aria-label': message,
    role: 'button',
    tabIndex: -1,
  };
}

/**
 * Generate props for decorative icons
 */
export function getDecorativeIconProps(): Record<string, string | boolean> {
  return {
    'aria-hidden': 'true',
    role: 'presentation',
  };
}

/**
 * Generate props for informative icons
 */
export function getInformativeIconProps(label: string): Record<string, string> {
  return {
    role: 'img',
    'aria-label': label,
  };
}

/**
 * Generate props for a chart container
 */
export function getChartContainerProps(options: {
  title: string;
  description?: string;
  dataPointCount?: number;
}): Record<string, string> {
  const { title, description, dataPointCount } = options;

  let ariaLabel = title;
  if (description) {
    ariaLabel += `. ${description}`;
  }
  if (dataPointCount !== undefined) {
    ariaLabel += `. ${dataPointCount} data points.`;
  }

  return {
    role: 'img',
    'aria-label': ariaLabel,
  };
}

/**
 * Generate props for an interactive chart with keyboard navigation
 */
export function getInteractiveChartProps(options: {
  title: string;
  description?: string;
  currentIndex?: number;
  totalPoints?: number;
  currentValue?: string;
}): Record<string, string | number> {
  const { title, description, currentIndex, totalPoints, currentValue } = options;

  let ariaLabel = `${title} chart`;
  if (description) {
    ariaLabel += `. ${description}`;
  }
  if (currentIndex !== undefined && totalPoints !== undefined) {
    ariaLabel += `. Point ${currentIndex + 1} of ${totalPoints}`;
    if (currentValue) {
      ariaLabel += `: ${currentValue}`;
    }
  }
  ariaLabel += `. Use arrow keys to navigate between data points.`;

  return {
    role: 'application',
    'aria-label': ariaLabel,
    'aria-roledescription': 'interactive chart',
    tabIndex: 0,
  };
}

// ============================================================================
// FOCUS MANAGEMENT
// ============================================================================

/**
 * CSS class for visible focus indicators that meet WCAG requirements
 */
export const focusRingClasses =
  'focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 focus:ring-offset-gray-900';

/**
 * CSS class for focus indicators on dark backgrounds
 */
export const focusRingDarkClasses =
  'focus:outline-none focus:ring-2 focus:ring-teal-400 focus:ring-offset-2 focus:ring-offset-gray-950';

/**
 * Generate focus-visible classes for keyboard-only focus indication
 */
export const focusVisibleClasses =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900';

// ============================================================================
// SCREEN READER UTILITIES
// ============================================================================

/**
 * CSS class for visually hidden but screen reader accessible content
 */
export const srOnlyClasses = 'sr-only';

/**
 * Create a live region announcement
 * Note: This should be called from a useEffect or event handler
 */
export function announceToScreenReader(message: string, priority: 'polite' | 'assertive' = 'polite'): void {
  const announcement = document.createElement('div');
  announcement.setAttribute('aria-live', priority);
  announcement.setAttribute('aria-atomic', 'true');
  announcement.setAttribute('class', 'sr-only');
  announcement.textContent = message;

  document.body.appendChild(announcement);

  // Remove after announcement is made
  setTimeout(() => {
    document.body.removeChild(announcement);
  }, 1000);
}

// ============================================================================
// CONTRAST UTILITIES
// ============================================================================

/**
 * WCAG 2.1 AA compliant text color classes for dark backgrounds
 * These replace text-gray-400 which has insufficient contrast on bg-gray-950
 */
export const contrastSafeTextClasses = {
  /** Use instead of text-gray-400 on dark backgrounds for body text */
  body: 'text-gray-300',
  /** Use instead of text-gray-500 on dark backgrounds for secondary text */
  secondary: 'text-gray-400',
  /** Use instead of text-gray-600 on dark backgrounds for muted text */
  muted: 'text-gray-500',
  /** High contrast text for important information */
  emphasis: 'text-gray-200',
  /** Interactive text that needs to be clearly visible */
  interactive: 'text-gray-200 hover:text-white',
} as const;

/**
 * Color combinations that pass WCAG AA contrast requirements
 */
export const wcagCompliantColors = {
  // Text colors on bg-gray-950 (4.5:1 or higher for AA)
  onDarkBackground: {
    primary: 'text-gray-100',     // 15.2:1 contrast
    secondary: 'text-gray-300',   // 7.5:1 contrast
    muted: 'text-gray-400',       // 4.5:1 contrast (minimum AA)
    accent: 'text-teal-400',      // 5.2:1 contrast
  },
  // Text colors on bg-gray-900
  onCard: {
    primary: 'text-gray-100',
    secondary: 'text-gray-300',
    muted: 'text-gray-400',
  },
} as const;

// ============================================================================
// CHART ACCESSIBILITY HELPERS
// ============================================================================

/**
 * Generate accessible description for a chart data point
 */
export function describeDataPoint(options: {
  label: string;
  value: number | string;
  unit?: string;
  index?: number;
  total?: number;
}): string {
  const { label, value, unit, index, total } = options;

  let description = `${label}: ${value}`;
  if (unit) {
    description += ` ${unit}`;
  }
  if (index !== undefined && total !== undefined) {
    description += ` (${index + 1} of ${total})`;
  }

  return description;
}

/**
 * Generate accessible chart summary
 */
export function generateChartSummary(options: {
  chartType: string;
  title: string;
  dataPoints: number;
  minValue?: number | string;
  maxValue?: number | string;
  avgValue?: number | string;
  unit?: string;
}): string {
  const { chartType, title, dataPoints, minValue, maxValue, avgValue, unit } = options;

  let summary = `${chartType} showing ${title} with ${dataPoints} data points.`;

  if (minValue !== undefined && maxValue !== undefined) {
    summary += ` Range: ${minValue}${unit ? ` ${unit}` : ''} to ${maxValue}${unit ? ` ${unit}` : ''}.`;
  }

  if (avgValue !== undefined) {
    summary += ` Average: ${avgValue}${unit ? ` ${unit}` : ''}.`;
  }

  return summary;
}

// ============================================================================
// FOCUS TRAP FOR MODALS
// ============================================================================

/**
 * Get all focusable elements within a container
 */
export function getFocusableElements(container: HTMLElement): HTMLElement[] {
  const focusableSelectors = [
    'button:not([disabled]):not([aria-hidden="true"])',
    'a[href]:not([aria-hidden="true"])',
    'input:not([disabled]):not([type="hidden"]):not([aria-hidden="true"])',
    'select:not([disabled]):not([aria-hidden="true"])',
    'textarea:not([disabled]):not([aria-hidden="true"])',
    '[tabindex]:not([tabindex="-1"]):not([aria-hidden="true"])',
  ].join(',');

  return Array.from(container.querySelectorAll<HTMLElement>(focusableSelectors));
}

/**
 * Hook for managing focus trap within a modal or dialog
 */
export function useFocusTrap(containerRef: React.RefObject<HTMLElement | null>, isActive: boolean) {
  const previousActiveElement = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isActive || !containerRef.current) return;

    // Store the currently focused element to restore later
    previousActiveElement.current = document.activeElement as HTMLElement;

    // Focus the first focusable element in the container
    const focusableElements = getFocusableElements(containerRef.current);
    if (focusableElements.length > 0) {
      focusableElements[0].focus();
    }

    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key !== 'Tab' || !containerRef.current) return;

      const focusableElements = getFocusableElements(containerRef.current);
      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (event.shiftKey) {
        // Shift + Tab: If on first element, go to last
        if (document.activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab: If on last element, go to first
        if (document.activeElement === lastElement) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      // Restore focus to the previously focused element
      if (previousActiveElement.current && previousActiveElement.current.focus) {
        previousActiveElement.current.focus();
      }
    };
  }, [isActive, containerRef]);
}

// ============================================================================
// FOCUS MANAGEMENT UTILITIES
// ============================================================================

/**
 * Move focus to a specific element with optional delay
 */
export function moveFocusTo(element: HTMLElement | null, delay = 0): void {
  if (!element) return;

  if (delay > 0) {
    setTimeout(() => {
      element.focus();
    }, delay);
  } else {
    element.focus();
  }
}

/**
 * Move focus to the first focusable element in a container
 */
export function moveFocusToFirst(container: HTMLElement | null): void {
  if (!container) return;
  const focusableElements = getFocusableElements(container);
  if (focusableElements.length > 0) {
    focusableElements[0].focus();
  }
}

/**
 * Check if an element is currently in the viewport
 */
export function isElementInViewport(element: HTMLElement): boolean {
  const rect = element.getBoundingClientRect();
  return (
    rect.top >= 0 &&
    rect.left >= 0 &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
  );
}

/**
 * Scroll element into view if not visible
 */
export function ensureVisible(element: HTMLElement): void {
  if (!isElementInViewport(element)) {
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

// ============================================================================
// CHART KEYBOARD NAVIGATION HOOK
// ============================================================================

export interface ChartKeyboardNavigationOptions {
  dataLength: number;
  onIndexChange: (index: number) => void;
  onSelect?: (index: number) => void;
  initialIndex?: number;
}

/**
 * Hook for keyboard navigation in charts
 * Supports arrow keys to navigate data points
 */
export function useChartKeyboardNavigation(options: ChartKeyboardNavigationOptions) {
  const { dataLength, onIndexChange, onSelect, initialIndex = 0 } = options;
  const [currentIndex, setCurrentIndex] = useState(initialIndex);

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    let newIndex = currentIndex;
    let handled = false;

    switch (event.key) {
      case Keys.ARROW_LEFT:
        newIndex = Math.max(0, currentIndex - 1);
        handled = true;
        break;
      case Keys.ARROW_RIGHT:
        newIndex = Math.min(dataLength - 1, currentIndex + 1);
        handled = true;
        break;
      case Keys.HOME:
        newIndex = 0;
        handled = true;
        break;
      case Keys.END:
        newIndex = dataLength - 1;
        handled = true;
        break;
      case Keys.ENTER:
      case Keys.SPACE:
        if (onSelect) {
          onSelect(currentIndex);
          handled = true;
        }
        break;
    }

    if (handled) {
      event.preventDefault();
      if (newIndex !== currentIndex) {
        setCurrentIndex(newIndex);
        onIndexChange(newIndex);
      }
    }
  }, [currentIndex, dataLength, onIndexChange, onSelect]);

  const getChartKeyboardProps = useCallback(() => ({
    tabIndex: 0,
    role: 'application' as const,
    'aria-roledescription': 'interactive chart',
    onKeyDown: handleKeyDown,
  }), [handleKeyDown]);

  return {
    currentIndex,
    setCurrentIndex,
    getChartKeyboardProps,
  };
}
