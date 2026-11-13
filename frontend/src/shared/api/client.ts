export class ApiError extends Error {
  constructor(public readonly status: number, public readonly details: unknown) {
    super(`API request failed (${status})`);
  }
}

/** Relative URLs prevent accidentally sending session/CSRF credentials to another origin. */
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (!path.startsWith('/') || path.startsWith('//')) throw new Error('Use an API-relative path');
  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json');
  const method = (options.method ?? 'GET').toUpperCase();
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    // Obtain a fresh token: Django rotates it on login. Never persist credentials in localStorage.
    const csrf = await api<{ csrfToken: string }>('/csrf/', { signal: options.signal });
    headers.set('X-CSRFToken', csrf.csrfToken);
  }
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const response = await fetch(`/api/v1${path}`, {
    ...options, method, headers, credentials: 'same-origin', cache: 'no-store',
  });
  const json = response.headers.get('content-type')?.includes('application/json');
  const data: unknown = response.status === 204 ? undefined : json ? await response.json() : null;
  if (!response.ok) throw new ApiError(response.status, data);
  if (response.status !== 204 && !json) throw new Error('Expected a JSON API response');
  return data as T;
}
