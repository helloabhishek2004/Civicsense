import { describe, it, expect } from 'vitest';
import { env } from '@/core/config/env';

describe('Environment Configuration', () => {
  it('loads valid dataMode', () => {
    expect(['api', 'mock']).toContain(env.dataMode);
  });

  it('provides configured API base URL without trailing slashes', () => {
    expect(env.apiBaseUrl).toBeDefined();
    expect(env.apiBaseUrl.endsWith('/')).toBe(false);
  });

  it('provides map tile and attribution configuration', () => {
    expect(env.mapTileUrl).toBeDefined();
    expect(env.mapAttribution).toBeDefined();
  });

  it('correctly sets boolean mode helpers', () => {
    if (env.dataMode === 'mock') {
      expect(env.isMock).toBe(true);
      expect(env.isApi).toBe(false);
    } else {
      expect(env.isApi).toBe(true);
      expect(env.isMock).toBe(false);
    }
  });
});
