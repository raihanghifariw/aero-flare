/**
 * Server-side helper for Next.js API proxy routes.
 * Safely resolves BACKEND_API_URL and BACKEND_API_KEY with defensive error handling.
 */

export function getBackendConfig(): { backendUrl: string; apiKey: string } {
  const rawUrl = process.env.BACKEND_API_URL || 'http://localhost:8000';
  const backendUrl = rawUrl.endsWith('/') ? rawUrl.slice(0, -1) : rawUrl;
  const apiKey = process.env.BACKEND_API_KEY || '';
  return { backendUrl, apiKey };
}

export function getBackendHeaders(): Record<string, string> {
  const { apiKey } = getBackendConfig();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }
  return headers;
}
