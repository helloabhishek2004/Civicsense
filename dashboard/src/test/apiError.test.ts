import { describe, it, expect } from 'vitest';
import { RepositoryError } from '@/services/api/apiError';

describe('RepositoryError', () => {
  it('instantiates with proper kind, message, and options', () => {
    const err = new RepositoryError('Backend unavailable', 'NETWORK', {
      statusCode: 503,
      requestId: 'req-12345',
      details: { service: 'reports' },
    });

    expect(err.message).toBe('Backend unavailable');
    expect(err.kind).toBe('NETWORK');
    expect(err.statusCode).toBe(503);
    expect(err.requestId).toBe('req-12345');
    expect(err.name).toBe('RepositoryError');
  });

  it('identifies instance via isRepositoryError guard', () => {
    const err = new RepositoryError('Not found', 'NOT_FOUND');
    const stdErr = new Error('Generic error');

    expect(RepositoryError.isRepositoryError(err)).toBe(true);
    expect(RepositoryError.isRepositoryError(stdErr)).toBe(false);
    expect(RepositoryError.isRepositoryError('some string')).toBe(false);
  });
});
