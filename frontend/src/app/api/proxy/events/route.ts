import { NextRequest, NextResponse } from 'next/server';
import { getBackendConfig, getBackendHeaders } from '@/lib/proxy-helper';

export const dynamic = 'force-dynamic';

/**
 * GET /api/proxy/events
 * Proxies to backend GET /api/v1/events with server-side X-API-Key auth.
 */
export async function GET(request: NextRequest): Promise<NextResponse> {
  try {
    const { backendUrl } = getBackendConfig();
    const headers = getBackendHeaders();

    const { searchParams } = new URL(request.url);

    // Default to last 24 hours if no date_from provided
    if (!searchParams.has('date_from')) {
      const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
      searchParams.set('date_from', yesterday);
    }

    const targetUrl = `${backendUrl}/api/v1/events?${searchParams.toString()}`;

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
    console.error('Proxy GET /api/proxy/events failed:', error);
    return NextResponse.json(
      { error: 'Backend service unreachable or offline', details: String(error) },
      { status: 502 }
    );
  }
}
