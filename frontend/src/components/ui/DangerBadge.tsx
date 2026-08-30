import clsx from 'clsx';
import { DANGER_COLORS, DANGER_TEXT_COLORS, DANGER_LABELS } from '@/lib/constants';

export interface DangerBadgeProps {
  level: number; // 1–5
  showLabel?: boolean;
}

/**
 * Color-coded pill badge representing a fire danger level (1–5).
 * Colors come exclusively from DANGER_COLORS in lib/constants.ts.
 */
export function DangerBadge({ level, showLabel = false }: DangerBadgeProps) {
  const bg = DANGER_COLORS[level] ?? '#374151';
  const fg = DANGER_TEXT_COLORS[level] ?? '#FFFFFF';
  const label = DANGER_LABELS[level] ?? `Level ${level}`;
  const isCritical = level >= 4;

  return (
    <span
      data-testid="danger-badge"
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-bold tracking-tight shadow-sm transition-transform',
        isCritical && 'ring-1 ring-black/10'
      )}
      style={{ backgroundColor: bg, color: fg }}
    >
      <span className="font-mono text-[11px] font-black leading-none">{level}</span>
      {showLabel && <span className="font-semibold">{label}</span>}
    </span>
  );
}

