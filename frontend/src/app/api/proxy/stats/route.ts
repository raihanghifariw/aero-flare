import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_API_URL!;
const API_KEY = process.env.BACKEND_API_KEY!;

const HEADERS = {
  'X-API-Key': API_KEY,
  'Content-Type': 'application/json',
};

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
  // Today (UTC midnight → now)
  const now = new Date();
  const todayStart = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()),
  ).toISOString();

  const todayEnd = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 23, 59, 59, 999),
  ).toISOString();

  const [summaryRes, healthRes, eventsRes] = await Promise.all([
    fetch(
      `${BACKEND_URL}/api/v1/stats/summary?date_from=${encodeURIComponent(todayStart)}&date_to=${encodeURIComponent(todayEnd)}`,
      { headers: HEADERS, cache: 'no-store' },
    ),
    fetch(`${BACKEND_URL}/api/v1/health`, { cache: 'no-store' }),
    fetch(`${BACKEND_URL}/api/v1/events?limit=1&page=1`, {
      headers: HEADERS,
      cache: 'no-store',
    }),
  ]);

  if (!summaryRes.ok) {
    const err: unknown = await summaryRes.json().catch(() => ({}));
    return NextResponse.json(err, { status: summaryRes.status });
  }

  const summary = (await summaryRes.json()) as BackendStatsSummary;

  let pipelineHealthy = false;
  if (healthRes.ok) {
    const health = (await healthRes.json()) as BackendHealth;
    pipelineHealthy = health.status === 'healthy';
  }

  let lastIngestionAt: string | null = null;
  if (eventsRes.ok) {
    const events = (await eventsRes.json()) as BackendEventsPage;
    lastIngestionAt = events.data[0]?.detected_at ?? null;
  }

  return NextResponse.json({
    events_today: summary.total_events,
    confirmed_fires_today: summary.confirmed_fires,
    last_ingestion_at: lastIngestionAt,
    pipeline_healthy: pipelineHealthy,
  });
}
