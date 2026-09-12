import { describe, it, expect } from 'vitest';
import { resolveMediaUrl } from '@/core/utils/mediaUtils';
import { env } from '@/core/config/env';

describe('resolveMediaUrl', () => {
  it('returns null for null, undefined, or empty string', () => {
    expect(resolveMediaUrl(null)).toBeNull();
    expect(resolveMediaUrl(undefined)).toBeNull();
    expect(resolveMediaUrl('')).toBeNull();
    expect(resolveMediaUrl('   ')).toBeNull();
  });

  it('preserves absolute URLs', () => {
    expect(resolveMediaUrl('https://images.unsplash.com/photo-1')).toBe(
      'https://images.unsplash.com/photo-1'
    );
    expect(resolveMediaUrl('http://cdn.civicsense.org/img.png')).toBe(
      'http://cdn.civicsense.org/img.png'
    );
  });

  it('preserves data and blob URIs', () => {
    const dataUri = 'data:image/jpeg;base64,/9j/4AAQSkZJRg==';
    expect(resolveMediaUrl(dataUri)).toBe(dataUri);
    expect(resolveMediaUrl('blob:http://localhost:5173/uuid')).toBe(
      'blob:http://localhost:5173/uuid'
    );
  });

  it('resolves relative /uploads/ path against backend origin', () => {
    const origin = env.apiBaseUrl.replace(/\/api\/v1\/?$/, '');
    expect(resolveMediaUrl('/uploads/rep_1_preview.jpg')).toBe(
      `${origin}/uploads/rep_1_preview.jpg`
    );
  });

  it('resolves bare filename to /uploads/ against backend origin', () => {
    const origin = env.apiBaseUrl.replace(/\/api\/v1\/?$/, '');
    expect(resolveMediaUrl('preview.jpg')).toBe(
      `${origin}/uploads/preview.jpg`
    );
  });
});
