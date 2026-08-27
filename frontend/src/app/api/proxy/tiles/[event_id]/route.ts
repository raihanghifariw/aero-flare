import { NextRequest } from 'next/server';

const BACKEND_URL = process.env.BACKEND_API_URL!;
const API_KEY = process.env.BACKEND_API_KEY!;

export async function GET(
  _request: NextRequest,
  { params }: { params: { event_id: string } }
): Promise<Response> {
  const response = await fetch(`${BACKEND_URL}/api/v1/tiles/${params.event_id}`, {
    headers: { 'X-API-Key': API_KEY },
    cache: 'no-store',
    redirect: 'manual',
  });

  const location = response.headers.get('location');
  if (location) {
    return Response.redirect(location, 307);
  }
  return new Response(await response.text(), {
    status: response.status,
    headers: { 'Content-Type': response.headers.get('Content-Type') ?? 'text/plain' },
  });
}
