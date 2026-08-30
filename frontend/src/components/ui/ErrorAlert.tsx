import { AlertOctagon, RotateCw } from 'lucide-react';

export interface ErrorAlertProps {
  message: string;
  onRetry?: () => void;
}

/**
 * Modern error banner displayed when an API or telemetry request fails.
 */
export function ErrorAlert({ message, onRetry }: ErrorAlertProps) {
  return (
    <div
      data-testid="error-alert"
      role="alert"
      className="flex items-center justify-between gap-3 rounded-2xl border border-red-200 bg-red-50/90 px-4 py-3 text-sm text-red-700 shadow-sm backdrop-blur"
    >
      <div className="flex items-center gap-2.5 min-w-0">
        <AlertOctagon size={18} className="shrink-0 text-red-500" aria-hidden="true" />
        <span className="truncate font-medium text-red-800">{message}</span>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-red-200 bg-white px-3 py-1 text-xs font-semibold text-red-700 shadow-sm transition-colors hover:bg-red-50"
        >
          <RotateCw size={12} aria-hidden="true" />
          <span>Retry</span>
        </button>
      )}
    </div>
  );
}

