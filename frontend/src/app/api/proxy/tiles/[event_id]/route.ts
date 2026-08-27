import { NextRequest } from 'next/server';
import { getBackendConfig, getBackendHeaders } from '@/lib/proxy-helper';

export const dynamic = 'force-dynamic';

export async function GET(
  _request: NextRequest,
  { params }: { params: { event_id: string } }
): Promise<Response> {
  try {
    const { backendUrl } = getBackendConfig();
    const headers = getBackendHeaders();

    const response = await fetch(`${backendUrl}/api/v1/tiles/${params.event_id}`, {
      headers,
      cache: 'no-store',
      redirect: 'manual',
    });

    const location = response.headers.get('location');
    if (location) {
      return Response.redirect(location, 307);
    }
    return new Response(await response.text().catch(() => ''), {
      status: response.status,
      headers: { 'Content-Type': response.headers.get('Content-Type') ?? 'text/plain' },
    });
  } catch (error) {
    console.error(`Proxy GET /api/proxy/tiles/${params.event_id} failed:`, error);
    return new Response(JSON.stringify({ error: 'Tile fetch failed', details: String(error) }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
