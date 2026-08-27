import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_API_URL!;
const API_KEY = process.env.BACKEND_API_KEY!;

export async function GET(
  _request: NextRequest,
  { params }: { params: { event_id: string } }
): Promise<NextResponse> {
  const response = await fetch(
    `${BACKEND_URL}/api/v1/events/${params.event_id}`,
    { headers: { 'X-API-Key': API_KEY }, cache: 'no-store' }
  );
  return NextResponse.json(await response.json(), { status: response.status });
}
