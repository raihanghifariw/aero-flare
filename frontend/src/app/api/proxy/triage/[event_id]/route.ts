import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_API_URL!;
const API_KEY = process.env.BACKEND_API_KEY!;

interface RouteParams {
  params: { event_id: string };
}

/**
 * GET /api/proxy/triage/[event_id]
 * Proxies to backend GET /api/v1/triage/{event_id} with server-side X-API-Key auth.
 */
export async function GET(
  _request: NextRequest,
  { params }: RouteParams
): Promise<NextResponse> {
  const backendUrl = `${BACKEND_URL}/api/v1/triage/${params.event_id}`;

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
