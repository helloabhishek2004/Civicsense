export type RepositoryErrorKind =
  | 'NETWORK'
  | 'TIMEOUT'
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'VALIDATION'
  | 'INVALID_TRANSITION'
  | 'SERVER'
  | 'UNKNOWN';

export class RepositoryError extends Error {
  readonly kind: RepositoryErrorKind;
  readonly statusCode?: number;
  readonly requestId?: string;
  readonly details?: unknown;
  readonly cause?: unknown;

  constructor(
    message: string,
    kind: RepositoryErrorKind = 'UNKNOWN',
    options?: {
      statusCode?: number;
      requestId?: string;
      details?: unknown;
      cause?: unknown;
    }
  ) {
    super(message);
    this.name = 'RepositoryError';
    this.kind = kind;
    this.statusCode = options?.statusCode;
    this.requestId = options?.requestId;
    this.details = options?.details;
    if (options?.cause) {
      this.cause = options.cause;
    }
  }

  static isRepositoryError(err: unknown): err is RepositoryError {
    return err instanceof RepositoryError;
  }
}
