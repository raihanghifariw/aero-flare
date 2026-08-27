import { NextRequest, NextResponse } from 'next/server';

// Server-side only — BACKEND_API_KEY is NEVER a NEXT_PUBLIC_ variable
const BACKEND_URL = process.env.BACKEND_API_URL!;
const API_KEY = process.env.BACKEND_API_KEY!;

/**
 * GET /api/proxy/events
 * Proxies to backend GET /api/v1/events with server-side X-API-Key auth.
 * Query params (page, limit, status, danger_level_min) forwarded transparently.
 */
export async function GET(request: NextRequest): Promise<NextResponse> {
  const { searchParams } = new URL(request.url);
  const backendUrl = `${BACKEND_URL}/api/v1/events?${searchParams.toString()}`;

  const response = await fetch(backendUrl, {
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json',
    },
    cache: 'no-store',
  });

  const data: unknown = await response.json();
  return NextResponse.json(data, { status: response.status });
}
