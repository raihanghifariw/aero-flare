import clsx from 'clsx';
import { CLASSIFICATION_CLASSES, CLASSIFICATION_LABELS } from '@/lib/constants';
import type { Classification } from '@/types/triage-report';

export interface ClassificationTagProps {
  classification: Classification;
}

/**
 * Colored pill tag representing a fire classification result.
 */
export function ClassificationTag({ classification }: ClassificationTagProps) {
  const classes = CLASSIFICATION_CLASSES[classification] ?? 'bg-gray-100 text-gray-700 border-gray-300';
  const label = CLASSIFICATION_LABELS[classification] ?? classification;

  return (
    <span
      data-testid="classification-tag"
      className={clsx(
        'inline-block px-2 py-0.5 rounded-full border text-xs font-medium',
        classes
      )}
    >
      {label}
    </span>
  );
}
