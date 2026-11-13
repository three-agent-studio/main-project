import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from './client';

afterEach(() => vi.unstubAllGlobals());
describe('API transport', () => {
  it('rejects absolute URLs before credentials can leave the origin', async () => {
    const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
    await expect(api('https://example.com')).rejects.toThrow();
    await expect(api('//example.com')).rejects.toThrow();
    expect(fetch).not.toHaveBeenCalled();
  });
  it('fetches a fresh CSRF token for writes and preserves the error status', async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ csrfToken: 'test-token' }), { headers: { 'content-type': 'application/json' } }))
      .mockResolvedValueOnce(new Response('{}', { status: 403, headers: { 'content-type': 'application/json' } }));
    vi.stubGlobal('fetch', fetch);
    await expect(api('/requests/', { method: 'POST', body: '{}' })).rejects.toBeInstanceOf(ApiError);
    expect(fetch.mock.calls[0][0]).toBe('/api/v1/csrf/');
    expect(fetch.mock.calls[1][1].headers.get('X-CSRFToken')).toBe('test-token');
    expect(fetch.mock.calls[1][1].credentials).toBe('same-origin');
  });
});
