import { NextRequest, NextResponse } from 'next/server';
import { getBackendConfig, getBackendHeaders } from '@/lib/proxy-helper';

export const dynamic = 'force-dynamic';

interface BackendStatsSummary {
  total_events: number;
  confirmed_fires: number;
  probable_fires: number;
  false_positives: number;
  industrial_sources: number;
  alerted_count: number;
  vlm_triage_count: number;
  rule_based_triage_count: number;
  date_from: string;
  date_to: string;
}

interface BackendHealth {
  status: string;
}

interface BackendEventsPage {
  data: Array<{ detected_at: string }>;
}

/**
 * GET /api/proxy/stats
 * Aggregates backend endpoints into the frontend `PipelineStats` shape:
 *   - GET /api/v1/stats/summary (today's range)  → events_today, confirmed_fires_today
 *   - GET /api/v1/health                          → pipeline_healthy
 *   - GET /api/v1/events?limit=1                  → last_ingestion_at
 */
export async function GET(_request: NextRequest): Promise<NextResponse> {
  try {
    const { backendUrl } = getBackendConfig();
    const headers = getBackendHeaders();

    // Active 48h window (matching default dashboard range)
    const now = new Date();
    const active48hStart = new Date(now.getTime() - 48 * 60 * 60 * 1000).toISOString();
    const nowIso = now.toISOString();

    const [summaryRes, healthRes, eventsRes] = await Promise.all([
      fetch(
        `${backendUrl}/api/v1/stats/summary?date_from=${encodeURIComponent(active48hStart)}&date_to=${encodeURIComponent(nowIso)}`,
        { headers, cache: 'no-store' },
      ).catch(() => null),
      fetch(`${backendUrl}/api/v1/health`, { cache: 'no-store' }).catch(() => null),
      fetch(`${backendUrl}/api/v1/events?limit=1&page=1`, {
        headers,
        cache: 'no-store',
      }).catch(() => null),
    ]);

    let summary: BackendStatsSummary | null = null;
    if (summaryRes && summaryRes.ok) {
      summary = (await summaryRes.json()) as BackendStatsSummary;
    }

    // Fallback: If 0 events in the last 24h, check 7-day range so historical/demo data is reflected
    if (!summary || summary.total_events === 0) {
      const fallbackRes = await fetch(`${backendUrl}/api/v1/stats/summary`, {
        headers,
        cache: 'no-store',
      }).catch(() => null);
      if (fallbackRes && fallbackRes.ok) {
        const fallbackSummary = (await fallbackRes.json()) as BackendStatsSummary;
        if (fallbackSummary.total_events > 0) {
          summary = fallbackSummary;
        }
      }
    }

    if (!summary) {
      const errText = summaryRes ? await summaryRes.text().catch(() => '') : 'Backend unreachable';
      let errData: unknown;
      try {
        errData = JSON.parse(errText);
      } catch {
        errData = { error: errText };
      }
      return NextResponse.json(errData, { status: summaryRes?.status ?? 502 });
    }

    let pipelineHealthy = false;
    if (healthRes && healthRes.ok) {
      const health = (await healthRes.json()) as BackendHealth;
      pipelineHealthy = health.status === 'healthy';
    }

    let lastIngestionAt: string | null = null;
    if (eventsRes && eventsRes.ok) {
      const events = (await eventsRes.json()) as BackendEventsPage;
      lastIngestionAt = events.data[0]?.detected_at ?? null;
    }

    return NextResponse.json({
      events_today: summary.total_events,
      confirmed_fires_today: summary.confirmed_fires,
      last_ingestion_at: lastIngestionAt,
      pipeline_healthy: pipelineHealthy,
    });
  } catch (error) {
    console.error('Proxy GET /api/proxy/stats failed:', error);
    return NextResponse.json(
      { error: 'Backend service unreachable or offline', details: String(error) },
      { status: 502 }
    );
  }
}
