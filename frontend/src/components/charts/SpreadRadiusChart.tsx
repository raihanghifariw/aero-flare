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
import { ShieldAlert } from 'lucide-react';

export interface SpreadRadiusChartProps {
  prediction: Prediction;
}

const CHART_DATA_COLORS = ['#3B82F6', '#F59E0B', '#EF4444'];

/**
 * Recharts BarChart displaying fire spread radii at 6h, 12h, and 24h horizons.
 */
export function SpreadRadiusChart({ prediction }: SpreadRadiusChartProps) {
  const data = [
    { horizon: '6h', radius: prediction.radius_6h_km, label: 'Immediate 6h' },
    { horizon: '12h', radius: prediction.radius_12h_km, label: 'Tactical 12h' },
    { horizon: '24h', radius: prediction.radius_24h_km, label: 'Perimeter 24h' },
  ];

  const hasData = data.some((d) => d.radius > 0);

  if (!hasData) {
    return (
      <div data-testid="spread-radius-chart" className="rounded-2xl border border-edge bg-surface p-3.5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
            Spread Radius (km)
          </span>
          <span className="text-[10px] text-slate-400 font-medium">Predictive Model v{prediction.model_version}</span>
        </div>
        <div className="flex h-[120px] items-center justify-center rounded-xl border border-dashed border-edge text-xs text-slate-400">
          Spread prediction computing…
        </div>
      </div>
    );
  }

  return (
    <div data-testid="spread-radius-chart" className="rounded-2xl border border-edge bg-surface p-3.5 shadow-sm">
      <div className="mb-2.5 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <ShieldAlert size={14} className="text-brand" aria-hidden="true" />
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-700">
            Spread Horizon Expansion (km)
          </span>
        </div>
        <span className="rounded-full bg-blue-50 px-2 py-0.5 font-mono text-[9px] font-bold text-brand border border-blue-100">
          {prediction.spread_direction_deg.toFixed(0)}° AZIMUTH
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 mb-2 text-center">
        {data.map((item, idx) => (
          <div key={item.horizon} className="rounded-xl border border-edge bg-white p-2 shadow-sm">
            <span className="block text-[10px] font-semibold text-slate-400">{item.horizon}</span>
            <span
              className="text-xs font-black tabular-nums font-mono"
              style={{ color: CHART_DATA_COLORS[idx] }}
            >
              {item.radius.toFixed(1)} km
            </span>
          </div>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: -14, bottom: 0 }}>
          <CartesianGrid strokeDasharray="2 2" stroke="#E2E8F0" />
          <XAxis dataKey="horizon" tick={{ fontSize: 10, fill: '#64748B' }} stroke="#CBD5E1" />
          <YAxis tick={{ fontSize: 10, fill: '#64748B' }} stroke="#CBD5E1" unit="km" />
          <Tooltip
            formatter={(value: number) => [`${value.toFixed(1)} km`, 'Spread Radius']}
            contentStyle={{
              fontSize: 11,
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: 8,
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              color: '#0F172A',
            }}
            cursor={{ fill: 'rgba(24,119,242,0.06)' }}
          />
          <Bar dataKey="radius" radius={[4, 4, 0, 0]}>
            {data.map((_entry, index) => (
              <Cell key={index} fill={CHART_DATA_COLORS[index]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

