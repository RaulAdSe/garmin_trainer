'use client';

import { useState, useRef, useEffect, useCallback, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

type TooltipPosition = 'top' | 'bottom' | 'left' | 'right';

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  position?: TooltipPosition;
  delay?: number;
  className?: string;
  contentClassName?: string;
  disabled?: boolean;
}

export function Tooltip({
  content,
  children,
  position = 'top',
  delay = 200,
  className,
  contentClassName,
  disabled = false,
}: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [actualPosition, setActualPosition] = useState<TooltipPosition>(position);
  const triggerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Position styles
  const positionStyles: Record<TooltipPosition, string> = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-[70%] ml-2',
  };

  // Arrow styles
  const arrowStyles: Record<TooltipPosition, string> = {
    top: 'top-full left-1/2 -translate-x-1/2 border-t-gray-700 border-x-transparent border-b-transparent',
    bottom: 'bottom-full left-1/2 -translate-x-1/2 border-b-gray-700 border-x-transparent border-t-transparent',
    left: 'left-full top-1/2 -translate-y-1/2 border-l-gray-700 border-y-transparent border-r-transparent',
    right: 'right-full top-[70%] -translate-y-1/2 border-r-gray-700 border-y-transparent border-l-transparent',
  };

  // Check if tooltip fits in viewport and adjust position
  const adjustPosition = useCallback(() => {
    if (!triggerRef.current || !tooltipRef.current) return;

    const triggerRect = triggerRef.current.getBoundingClientRect();
    const tooltipRect = tooltipRef.current.getBoundingClientRect();
    const padding = 8;

    let newPosition = position;

    // Check if tooltip fits in the preferred position
    switch (position) {
      case 'top':
        if (triggerRect.top - tooltipRect.height - padding < 0) {
          newPosition = 'bottom';
        }
        break;
      case 'bottom':
        if (triggerRect.bottom + tooltipRect.height + padding > window.innerHeight) {
          newPosition = 'top';
        }
        break;
      case 'left':
        if (triggerRect.left - tooltipRect.width - padding < 0) {
          newPosition = 'right';
        }
        break;
      case 'right':
        if (triggerRect.right + tooltipRect.width + padding > window.innerWidth) {
          newPosition = 'left';
        }
        break;
    }

    setActualPosition(newPosition);
  }, [position]);

  useEffect(() => {
    if (isVisible) {
      adjustPosition();
    }
  }, [isVisible, adjustPosition]);

  const showTooltip = () => {
    if (disabled) return;
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true);
    }, delay);
  };

  const hideTooltip = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setIsVisible(false);
  };

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  if (disabled) {
    return <>{children}</>;
  }

  return (
    <div
      ref={triggerRef}
      className={cn('relative inline-block', className)}
      onMouseEnter={showTooltip}
      onMouseLeave={hideTooltip}
      onFocus={showTooltip}
      onBlur={hideTooltip}
    >
      {children}

      {/* Tooltip */}
      <div
        ref={tooltipRef}
        className={cn(
          'absolute z-50 pointer-events-none',
          'transition-all duration-150 ease-out',
          positionStyles[actualPosition],
          isVisible ? 'opacity-100 scale-100' : 'opacity-0 scale-95',
          contentClassName
        )}
        role="tooltip"
        aria-hidden={!isVisible}
      >
        <div className="bg-gray-700 text-gray-100 text-xs px-2.5 py-1.5 rounded-md shadow-lg whitespace-normal">
          {content}
        </div>
        {/* Arrow */}
        <div
          className={cn(
            'absolute w-0 h-0 border-4',
            arrowStyles[actualPosition]
          )}
        />
      </div>
    </div>
  );
}

// Info tooltip with question mark icon
interface InfoTooltipProps {
  content: ReactNode;
  position?: TooltipPosition;
  className?: string;
}

export function InfoTooltip({ content, position = 'top', className }: InfoTooltipProps) {
  return (
    <Tooltip content={content} position={position}>
      <span
        className={cn(
          'inline-flex items-center justify-center w-4 h-4 rounded-full',
          'bg-gray-700 text-gray-400 text-xs cursor-help',
          'hover:bg-gray-600 hover:text-gray-300 transition-colors',
          className
        )}
      >
        ?
      </span>
    </Tooltip>
  );
}

// Metric with tooltip explanation
interface MetricWithTooltipProps {
  label: string;
  value: string | number;
  explanation: string;
  unit?: string;
  className?: string;
}

export function MetricWithTooltip({
  label,
  value,
  explanation,
  unit,
  className,
}: MetricWithTooltipProps) {
  return (
    <div className={cn('flex items-center gap-1', className)}>
      <span className="text-gray-300 text-sm">{label}:</span>
      <span className="text-gray-100 font-medium">
        {value}
        {unit && <span className="text-gray-300 text-sm ml-0.5">{unit}</span>}
      </span>
      <InfoTooltip content={explanation} />
    </div>
  );
}

export default Tooltip;
