'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import type { Prediction } from '@/types/prediction';

export interface SpreadRadiusChartProps {
  prediction: Prediction;
}

const CHART_DATA_COLORS = ['#FCD34D', '#FB923C', '#EF4444'];

/**
 * Recharts BarChart displaying fire spread radii at 6h, 12h, and 24h horizons.
 */
export function SpreadRadiusChart({ prediction }: SpreadRadiusChartProps) {
  const data = [
    { horizon: '6h', radius: prediction.radius_6h_km },
    { horizon: '12h', radius: prediction.radius_12h_km },
    { horizon: '24h', radius: prediction.radius_24h_km },
  ];

  return (
    <div data-testid="spread-radius-chart">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Spread Radius (km)
      </p>
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="horizon" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} unit=" km" />
          <Tooltip
            formatter={(value: number) => [`${value.toFixed(1)} km`, 'Radius']}
            contentStyle={{ fontSize: 12 }}
          />
          <Bar dataKey="radius" radius={[3, 3, 0, 0]}>
            {data.map((_entry, index) => (
              <Cell key={index} fill={CHART_DATA_COLORS[index]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
