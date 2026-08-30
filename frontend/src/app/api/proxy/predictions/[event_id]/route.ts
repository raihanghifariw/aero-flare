import { NextRequest, NextResponse } from 'next/server';
import { getBackendConfig, getBackendHeaders } from '@/lib/proxy-helper';

export const dynamic = 'force-dynamic';

interface RouteParams {
  params: { event_id: string };
}

/**
 * GET /api/proxy/predictions/[event_id]
 * Proxies to backend GET /api/v1/predictions/{event_id} with server-side X-API-Key auth.
 */
export async function GET(
  _request: NextRequest,
  { params }: RouteParams
): Promise<NextResponse> {
  try {
    const { backendUrl } = getBackendConfig();
    const headers = getBackendHeaders();
    const targetUrl = `${backendUrl}/api/v1/predictions/${params.event_id}`;

    const response = await fetch(targetUrl, {
      headers,
      cache: 'no-store',
    });

    if (response.status === 404) {
      return NextResponse.json(null, { status: 200 });
    }

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
    console.error(`Proxy GET /api/proxy/predictions/${params.event_id} failed:`, error);
    return NextResponse.json(
      { error: 'Backend service unreachable or offline', details: String(error) },
      { status: 502 }
    );
  }
}
