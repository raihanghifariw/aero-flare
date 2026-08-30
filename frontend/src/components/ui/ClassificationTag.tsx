import clsx from 'clsx';
import { CLASSIFICATION_CLASSES, CLASSIFICATION_LABELS } from '@/lib/constants';
import type { Classification } from '@/types/triage-report';

export interface ClassificationTagProps {
  classification: Classification;
}

const DOT_COLORS: Record<Classification, string> = {
  CONFIRMED_FIRE: 'bg-red-500',
  PROBABLE_FIRE: 'bg-orange-500',
  FALSE_POSITIVE: 'bg-emerald-500',
  INDUSTRIAL_SOURCE: 'bg-sky-500',
};

/**
 * Modern SaaS badge representing a fire classification result.
 */
export function ClassificationTag({ classification }: ClassificationTagProps) {
  const classes = CLASSIFICATION_CLASSES[classification] ?? 'bg-slate-50 text-slate-700 border-slate-200';
  const label = CLASSIFICATION_LABELS[classification] ?? classification;
  const dotColor = DOT_COLORS[classification] ?? 'bg-slate-400';

  return (
    <span
      data-testid="classification-tag"
      className={clsx(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-tight shadow-sm',
        classes
      )}
    >
      <span className={clsx('h-1.5 w-1.5 rounded-full', dotColor)} aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}

