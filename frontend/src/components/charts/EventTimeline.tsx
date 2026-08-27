'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { format, parseISO, subDays, startOfDay } from 'date-fns';
import type { FireEvent } from '@/types/fire-event';

export interface EventTimelineProps {
  events: FireEvent[];
}

/**
 * Recharts LineChart showing fire event counts per day over the last 7 days.
 */
export function EventTimeline({ events }: EventTimelineProps) {
  // Build last-7-days buckets
  const today = startOfDay(new Date());
  const buckets: Record<string, number> = {};
  for (let i = 6; i >= 0; i--) {
    const day = subDays(today, i);
    buckets[format(day, 'MMM d')] = 0;
  }

  events.forEach((event) => {
    try {
      const day = format(startOfDay(parseISO(event.detected_at)), 'MMM d');
      if (day in buckets) {
        buckets[day]++;
      }
    } catch {
      // skip malformed dates
    }
  });

  const data = Object.entries(buckets).map(([date, count]) => ({ date, count }));

  return (
    <div data-testid="event-timeline">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Events per Day (last 7 days)
      </p>
      <ResponsiveContainer width="100%" height={140}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="date" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip contentStyle={{ fontSize: 12 }} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Line
            type="monotone"
            dataKey="count"
            name="Events"
            stroke="#EF4444"
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
