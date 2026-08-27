import clsx from 'clsx';
import type { TriageSource } from '@/types/triage-report';

export interface TriageSourceBadgeProps {
  source: TriageSource;
}

/**
 * Small badge showing whether triage was done by VLM (blue) or rule-based fallback (amber).
 * Per plan/frontend_agent.md TriageSourceBadge spec.
 */
export function TriageSourceBadge({ source }: TriageSourceBadgeProps) {
  const isVLM = source === 'VLM';

  return (
    <span
      data-testid="triage-source-badge"
      className={clsx(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold',
        isVLM
          ? 'bg-blue-100 text-blue-800 border border-blue-300'
          : 'bg-amber-100 text-amber-800 border border-amber-300'
      )}
    >
      {!isVLM && <span aria-label="Warning">⚠</span>}
      {isVLM ? 'VLM' : 'Rule-Based'}
    </span>
  );
}
