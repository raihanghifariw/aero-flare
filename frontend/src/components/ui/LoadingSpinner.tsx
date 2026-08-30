export interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  showText?: boolean;
}

const SIZE_CLASSES = {
  sm: 'h-4 w-4 border-2',
  md: 'h-7 w-7 border-2',
  lg: 'h-10 w-10 border-[3px]',
};

/**
 * Modern radar pulse spinner used during telemetry and data fetching.
 */
export function LoadingSpinner({ size = 'md', label = 'Loading…', showText = false }: LoadingSpinnerProps) {
  return (
    <div
      data-testid="loading-spinner"
      role="status"
      aria-label={label}
      className="flex flex-col items-center justify-center gap-2.5 p-4"
    >
      <div className="relative flex items-center justify-center">
        <div
          className={`${SIZE_CLASSES[size]} animate-spin rounded-full border-slate-200 border-t-brand border-r-brand/40`}
        />
        <div className="absolute h-1.5 w-1.5 rounded-full bg-brand animate-ping-slow" />
      </div>
      {showText && <span className="text-xs font-medium text-ink-muted">{label}</span>}
      <span className="sr-only">{label}</span>
    </div>
  );
}

