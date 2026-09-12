import { env } from '@/core/config/env';

/**
 * Resolves raw or relative evidence storage URIs to browser-loadable URLs.
 * Handles absolute URLs (http/https), data URIs, and backend-relative paths (/uploads/...).
 */
export function resolveMediaUrl(uri?: string | null): string | null {
  if (!uri || !uri.trim()) return null;
  const trimmed = uri.trim();

  // Already a full or scheme-specific URL
  if (
    trimmed.startsWith('http://') ||
    trimmed.startsWith('https://') ||
    trimmed.startsWith('data:') ||
    trimmed.startsWith('blob:')
  ) {
    return trimmed;
  }

  // Derive backend host origin from apiBaseUrl (e.g., http://localhost:8000 from http://localhost:8000/api/v1)
  const backendOrigin = env.apiBaseUrl.replace(/\/api\/v1\/?$/, '');

  if (trimmed.startsWith('/')) {
    return `${backendOrigin}${trimmed}`;
  }

  // Fallback for relative preview filenames
  return `${backendOrigin}/uploads/${trimmed}`;
}
