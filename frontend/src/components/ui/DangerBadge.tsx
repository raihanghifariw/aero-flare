import clsx from 'clsx';
import { DANGER_BADGE_CLASSES, DANGER_COLORS, DANGER_LABELS } from '@/lib/constants';

export interface DangerBadgeProps {
  level: number; // 1–5
  showLabel?: boolean;
}

/**
 * Color-coded badge representing a fire danger level (1–5).
 * Colors per plan/frontend_agent.md danger level table.
 */
export function DangerBadge({ level, showLabel = false }: DangerBadgeProps) {
  const classes = DANGER_BADGE_CLASSES[level] ?? 'bg-gray-200 text-gray-800';
  const label = DANGER_LABELS[level] ?? `Level ${level}`;
  const color = DANGER_COLORS[level];

  return (
    <span
      data-testid="danger-badge"
      className={clsx('inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold', classes)}
      style={color ? { backgroundColor: color } : undefined}
    >
      <span className="text-[10px] font-black">{level}</span>
      {showLabel && <span>{label}</span>}
    </span>
  );
}
