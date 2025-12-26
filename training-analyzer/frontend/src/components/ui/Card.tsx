'use client';

import { type ReactNode, forwardRef, type HTMLAttributes } from 'react';
import { clsx } from 'clsx';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  variant?: 'default' | 'elevated' | 'outlined' | 'interactive';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  as?: 'div' | 'article' | 'section';
}

const paddingStyles = {
  none: '',
  sm: 'p-3 sm:p-4',
  md: 'p-4 sm:p-6',
  lg: 'p-6 sm:p-8',
};

const variantStyles = {
  default: 'bg-gray-900 border border-gray-800',
  elevated: 'bg-gray-900 border border-gray-800 shadow-lg shadow-black/20',
  outlined: 'bg-transparent border border-gray-700',
  interactive:
    'bg-gray-900 border border-gray-800 hover:border-gray-700 hover:shadow-lg hover:shadow-black/10 transition-all cursor-pointer card-hover',
};

export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      children,
      className,
      variant = 'default',
      padding = 'md',
      as: Component = 'div',
      ...props
    },
    ref
  ) => {
    return (
      <Component
        ref={ref}
        className={clsx(
          'rounded-xl',
          variantStyles[variant],
          paddingStyles[padding],
          className
        )}
        {...props}
      >
        {children}
      </Component>
    );
  }
);

Card.displayName = 'Card';

// Card Header component
export function CardHeader({
  children,
  className,
  action,
}: {
  children: ReactNode;
  className?: string;
  action?: ReactNode;
}) {
  return (
    <div
      className={clsx(
        'flex items-start justify-between gap-4 mb-4',
        className
      )}
    >
      <div className="flex-1 min-w-0">{children}</div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

// Card Title component
export function CardTitle({
  children,
  className,
  as: Component = 'h3',
}: {
  children: ReactNode;
  className?: string;
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
}) {
  return (
    <Component
      className={clsx('text-lg font-semibold text-gray-100', className)}
    >
      {children}
    </Component>
  );
}

// Card Description component
export function CardDescription({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <p className={clsx('text-sm text-gray-400 mt-1', className)}>{children}</p>
  );
}

// Card Content component
export function CardContent({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={clsx('', className)}>{children}</div>;
}

// Card Footer component
export function CardFooter({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={clsx(
        'mt-4 pt-4 border-t border-gray-800 flex flex-wrap items-center gap-3',
        className
      )}
    >
      {children}
    </div>
  );
}

export default Card;
