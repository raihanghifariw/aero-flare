import clsx from 'clsx';
import { Cpu } from 'lucide-react';
import type { TriageSource } from '@/types/triage-report';

export interface TriageSourceBadgeProps {
  source: TriageSource;
}

/**
 * Modern telemetry badge showing whether triage was performed by VLM (Vision AI)
 * or Rule-Based Fallback.
 */
export function TriageSourceBadge({ source }: TriageSourceBadgeProps) {
  const isVLM = source === 'VLM';

  return (
    <span
      data-testid="triage-source-badge"
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold',
        isVLM
          ? 'border-blue-200 bg-blue-50 text-blue-700'
          : 'border-amber-200 bg-amber-50 text-amber-700'
      )}
    >
      {isVLM ? (
        <>
          <Cpu size={12} className="text-blue-600" aria-hidden="true" />
          <span>VLM</span>
        </>
      ) : (
        <>
          <span aria-hidden="true" className="text-amber-600 font-bold">⚠</span>
          <span>Rule-Based</span>
        </>
      )}
    </span>
  );
}

