import { NextRequest, NextResponse } from 'next/server';
import { getBackendConfig, getBackendHeaders } from '@/lib/proxy-helper';

export const dynamic = 'force-dynamic';

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
  try {
    const { backendUrl } = getBackendConfig();
    const headers = getBackendHeaders();
    const targetUrl = `${backendUrl}/api/v1/triage/${params.event_id}`;

    const response = await fetch(targetUrl, {
      headers,
      cache: 'no-store',
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => '');
      let errorData: unknown;
      try {
        errorData = JSON.parse(errorText);
      } catch {
        errorData = { error: errorText || `Backend returned status ${response.status}` };
      }
      return NextResponse.json(errorData, { status: response.status });
    }

    const data: unknown = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error(`Proxy GET /api/proxy/triage/${params.event_id} failed:`, error);
    return NextResponse.json(
      { error: 'Backend service unreachable or offline', details: String(error) },
      { status: 502 }
    );
  }
}
