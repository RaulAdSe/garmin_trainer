import { clsx } from "clsx";

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return (
    <div
      className={clsx(
        "bg-gray-900 border border-gray-800 rounded-xl p-6",
        className
      )}
    >
      {children}
    </div>
  );
}
