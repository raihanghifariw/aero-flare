export interface ErrorAlertProps {
  message: string;
  onRetry?: () => void;
}

/**
 * Error banner displayed when an API request fails.
 */
export function ErrorAlert({ message, onRetry }: ErrorAlertProps) {
  return (
    <div
      data-testid="error-alert"
      role="alert"
      className="flex items-start gap-3 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800"
    >
      <span className="mt-0.5 text-base leading-none" aria-hidden="true">
        ⚠
      </span>
      <span className="flex-1">{message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="ml-2 font-medium underline hover:no-underline focus:outline-none"
        >
          Retry
        </button>
      )}
    </div>
  );
}
