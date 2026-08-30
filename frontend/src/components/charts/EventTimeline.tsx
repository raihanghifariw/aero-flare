'use client';

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { format, parseISO, subDays, startOfDay } from 'date-fns';
import type { FireEvent } from '@/types/fire-event';
import { TrendingUp } from 'lucide-react';

export interface EventTimelineProps {
  events: FireEvent[];
}

/**
 * AreaChart showing daily wildfire detection counts over the last 7 days.
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
  const total7d = data.reduce((acc, curr) => acc + curr.count, 0);

  return (
    <div data-testid="event-timeline" className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <TrendingUp size={14} className="text-brand" aria-hidden="true" />
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-700">
            Detections Volume (Last 7 Days)
          </span>
        </div>
        <span className="font-mono text-xs font-bold text-brand tabular-nums">
          {total7d} Total Incidents
        </span>
      </div>

      <ResponsiveContainer width="100%" height={130}>
        <AreaChart data={data} margin={{ top: 6, right: 8, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="brandGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#1877F2" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#1877F2" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 2" stroke="#E2E8F0" />
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748B' }} stroke="#CBD5E1" />
          <YAxis tick={{ fontSize: 10, fill: '#64748B' }} stroke="#CBD5E1" allowDecimals={false} />
          <Tooltip
            formatter={(value: number) => [`${value} detections`, 'Detections']}
            contentStyle={{
              fontSize: 11,
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: 8,
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              color: '#0F172A',
            }}
            cursor={{ stroke: '#1877F2', strokeDasharray: '3 3' }}
          />
          <Area
            type="monotone"
            dataKey="count"
            name="Events"
            stroke="#1877F2"
            strokeWidth={2.5}
            fillOpacity={1}
            fill="url(#brandGradient)"
            dot={{ r: 3, fill: '#1877F2', stroke: '#FFFFFF', strokeWidth: 1.5 }}
            activeDot={{ r: 5, fill: '#FFFFFF', stroke: '#1877F2', strokeWidth: 2.5 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

