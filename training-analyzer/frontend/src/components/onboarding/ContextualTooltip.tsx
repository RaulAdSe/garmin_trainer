'use client';

import { useEffect, useState, useRef, useCallback, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@/lib/utils';

export type TooltipPosition = 'top' | 'bottom' | 'left' | 'right';

export interface ContextualTooltipProps {
  /** Unique identifier for persisting dismissal in localStorage */
  id: string;
  /** Title of the tooltip */
  title: string;
  /** Content/description of the tooltip */
  content: ReactNode;
  /** Position relative to target element */
  position?: TooltipPosition;
  /** Whether the tooltip is visible */
  isVisible: boolean;
  /** Callback when tooltip is dismissed */
  onDismiss: () => void;
  /** Target element to point to (via ref) */
  targetRef?: React.RefObject<HTMLElement>;
  /** Target element selector (alternative to ref) */
  targetSelector?: string;
  /** Dismiss button text */
  dismissText?: string;
  /** Optional action button */
  action?: {
    text: string;
    onClick: () => void;
  };
  /** Additional class name */
  className?: string;
  /** Z-index for the tooltip */
  zIndex?: number;
}

// Arrow styles for each position
const arrowStyles: Record<TooltipPosition, string> = {
  top: 'top-full left-1/2 -translate-x-1/2 border-t-gray-800 border-x-transparent border-b-transparent',
  bottom: 'bottom-full left-1/2 -translate-x-1/2 border-b-gray-800 border-x-transparent border-t-transparent',
  left: 'left-full top-1/2 -translate-y-1/2 border-l-gray-800 border-y-transparent border-r-transparent',
  right: 'right-full top-1/2 -translate-y-1/2 border-r-gray-800 border-y-transparent border-l-transparent',
};

export function ContextualTooltip({
  id,
  title,
  content,
  position = 'bottom',
  isVisible,
  onDismiss,
  targetRef,
  targetSelector,
  dismissText = 'Got it',
  action,
  className,
  zIndex = 1000,
}: ContextualTooltipProps) {
  const [tooltipPosition, setTooltipPosition] = useState<{ top: number; left: number } | null>(null);
  const [actualPosition, setActualPosition] = useState<TooltipPosition>(position);
  const [isAnimatingIn, setIsAnimatingIn] = useState(false);
  const [mounted, setMounted] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);

  // Get target element
  const getTargetElement = useCallback((): HTMLElement | null => {
    if (targetRef?.current) {
      return targetRef.current;
    }
    if (targetSelector) {
      return document.querySelector(targetSelector) as HTMLElement;
    }
    return null;
  }, [targetRef, targetSelector]);

  // Calculate position
  const calculatePosition = useCallback(() => {
    const target = getTargetElement();
    const tooltip = tooltipRef.current;

    if (!target || !tooltip || !isVisible) {
      return;
    }

    const targetRect = target.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();
    const padding = 12;
    const arrowSize = 8;

    let newPosition = position;
    let top = 0;
    let left = 0;

    // Calculate initial position based on preferred position
    switch (position) {
      case 'top':
        top = targetRect.top - tooltipRect.height - arrowSize - padding;
        left = targetRect.left + targetRect.width / 2 - tooltipRect.width / 2;
        break;
      case 'bottom':
        top = targetRect.bottom + arrowSize + padding;
        left = targetRect.left + targetRect.width / 2 - tooltipRect.width / 2;
        break;
      case 'left':
        top = targetRect.top + targetRect.height / 2 - tooltipRect.height / 2;
        left = targetRect.left - tooltipRect.width - arrowSize - padding;
        break;
      case 'right':
        top = targetRect.top + targetRect.height / 2 - tooltipRect.height / 2;
        left = targetRect.right + arrowSize + padding;
        break;
    }

    // Check if tooltip fits in viewport and adjust if needed
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // Flip vertically if needed
    if (position === 'top' && top < 0) {
      newPosition = 'bottom';
      top = targetRect.bottom + arrowSize + padding;
    } else if (position === 'bottom' && top + tooltipRect.height > viewportHeight) {
      newPosition = 'top';
      top = targetRect.top - tooltipRect.height - arrowSize - padding;
    }

    // Flip horizontally if needed
    if (position === 'left' && left < 0) {
      newPosition = 'right';
      left = targetRect.right + arrowSize + padding;
    } else if (position === 'right' && left + tooltipRect.width > viewportWidth) {
      newPosition = 'left';
      left = targetRect.left - tooltipRect.width - arrowSize - padding;
    }

    // Constrain to viewport
    left = Math.max(padding, Math.min(left, viewportWidth - tooltipRect.width - padding));
    top = Math.max(padding, Math.min(top, viewportHeight - tooltipRect.height - padding));

    setActualPosition(newPosition);
    setTooltipPosition({ top, left });
  }, [getTargetElement, isVisible, position]);

  // Set mounted state for portal
  useEffect(() => {
    setMounted(true);
  }, []);

  // Calculate position when visible
  useEffect(() => {
    if (isVisible && mounted) {
      // Small delay to ensure DOM is ready
      const timer = setTimeout(() => {
        calculatePosition();
        setIsAnimatingIn(true);
      }, 50);

      return () => clearTimeout(timer);
    } else {
      setIsAnimatingIn(false);
    }
  }, [isVisible, mounted, calculatePosition]);

  // Recalculate on resize/scroll
  useEffect(() => {
    if (!isVisible) return;

    const handleResize = () => calculatePosition();
    const handleScroll = () => calculatePosition();

    window.addEventListener('resize', handleResize);
    window.addEventListener('scroll', handleScroll, true);

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('scroll', handleScroll, true);
    };
  }, [isVisible, calculatePosition]);

  // Don't render if not mounted (SSR) or not visible
  if (!mounted || !isVisible) {
    return null;
  }

  const tooltipContent = (
    <>
      {/* Backdrop overlay */}
      <div
        className="fixed inset-0 bg-black/30 backdrop-blur-[1px]"
        style={{ zIndex: zIndex - 1 }}
        onClick={onDismiss}
        aria-hidden="true"
      />

      {/* Tooltip */}
      <div
        ref={tooltipRef}
        role="tooltip"
        aria-labelledby={`tooltip-title-${id}`}
        className={cn(
          'fixed max-w-xs sm:max-w-sm',
          'transition-all duration-300 ease-out',
          isAnimatingIn && tooltipPosition
            ? 'opacity-100 scale-100'
            : 'opacity-0 scale-95',
          className
        )}
        style={{
          zIndex,
          top: tooltipPosition?.top ?? 0,
          left: tooltipPosition?.left ?? 0,
        }}
      >
        {/* Card */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl shadow-2xl overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 bg-gray-900/50 border-b border-gray-700">
            <h3
              id={`tooltip-title-${id}`}
              className="font-semibold text-gray-100 text-sm sm:text-base"
            >
              {title}
            </h3>
          </div>

          {/* Content */}
          <div className="px-4 py-3">
            <div className="text-sm text-gray-300 leading-relaxed">
              {content}
            </div>
          </div>

          {/* Actions */}
          <div className="px-4 py-3 bg-gray-900/30 border-t border-gray-700 flex items-center justify-end gap-2">
            {action && (
              <button
                onClick={() => {
                  action.onClick();
                  onDismiss();
                }}
                className="px-3 py-1.5 text-sm font-medium text-teal-400 hover:text-teal-300 transition-colors"
              >
                {action.text}
              </button>
            )}
            <button
              onClick={onDismiss}
              className="px-4 py-1.5 text-sm font-medium bg-teal-600 hover:bg-teal-500 text-white rounded-lg transition-colors"
            >
              {dismissText}
            </button>
          </div>
        </div>

        {/* Arrow */}
        <div
          className={cn(
            'absolute w-0 h-0 border-[8px]',
            arrowStyles[actualPosition]
          )}
        />
      </div>
    </>
  );

  return createPortal(tooltipContent, document.body);
}

// Highlight wrapper to make target element stand out
interface HighlightWrapperProps {
  children: ReactNode;
  isActive: boolean;
  className?: string;
}

export function HighlightWrapper({ children, isActive, className }: HighlightWrapperProps) {
  return (
    <div
      className={cn(
        'relative transition-all duration-300',
        isActive && 'z-[999] ring-2 ring-teal-500 ring-offset-2 ring-offset-gray-900 rounded-lg',
        className
      )}
    >
      {children}
    </div>
  );
}

export default ContextualTooltip;
