// API client — calls internal Next.js proxy routes ONLY.
// The actual backend URL and X-API-Key are handled server-side in route.ts files.
// NEVER import this into server components that already have direct backend access.

/**
 * Fetch data from a Next.js API proxy route.
 *
 * @param path  Starts with / — e.g. '/events', '/triage/abc-123', '/stats'
 *              Maps to /api/proxy/events, /api/proxy/triage/abc-123, etc.
 * @param options  Optional RequestInit overrides (method, body, etc.)
 */
export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const proxyPath = `/api/proxy${path}`;

  const response = await fetch(proxyPath, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
      // NO X-API-Key here — added server-side in the proxy route.ts
    },
  });

  if (!response.ok) {
    throw new Error(`API Error ${response.status}: ${path}`);
  }

  return response.json() as Promise<T>;
}
