export interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

const SIZE_CLASSES = {
  sm: 'h-4 w-4 border-2',
  md: 'h-8 w-8 border-2',
  lg: 'h-12 w-12 border-4',
};

/**
 * Simple CSS spinner used during data fetching.
 */
export function LoadingSpinner({ size = 'md', label = 'Loading…' }: LoadingSpinnerProps) {
  return (
    <div
      data-testid="loading-spinner"
      role="status"
      aria-label={label}
      className="flex items-center justify-center p-4"
    >
      <div
        className={`${SIZE_CLASSES[size]} rounded-full border-slate-300 border-t-orange-500 animate-spin`}
      />
      <span className="sr-only">{label}</span>
    </div>
  );
}
