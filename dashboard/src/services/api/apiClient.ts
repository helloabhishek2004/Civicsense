import { env } from '@/core/config/env';
import { RepositoryError } from './apiError';
import { BackendErrorResponse } from '@/types/api/backendContracts';

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
  params?: Record<string, string | number | boolean | undefined>;
}

export class ApiClient {
  private baseUrl: string;
  private defaultTimeoutMs: number;

  constructor(baseUrl: string = env.apiBaseUrl, defaultTimeoutMs: number = 10000) {
    this.baseUrl = baseUrl;
    this.defaultTimeoutMs = defaultTimeoutMs;
  }

  private generateRequestId(): string {
    return `req-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
  }

  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { timeoutMs = this.defaultTimeoutMs, params, ...fetchOptions } = options;

    let url = `${this.baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, val]) => {
        if (val !== undefined && val !== null && val !== '') {
          searchParams.append(key, String(val));
        }
      });
      const queryString = searchParams.toString();
      if (queryString) {
        url += (url.includes('?') ? '&' : '?') + queryString;
      }
    }

    const requestId = this.generateRequestId();
    const headers = new Headers(fetchOptions.headers || {});
    if (!headers.has('Content-Type') && !(fetchOptions.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }
    headers.set('Accept', 'application/json');
    headers.set('X-Request-ID', requestId);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...fetchOptions,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorData: BackendErrorResponse | null = null;
        let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;

        try {
          errorData = await response.json();
          if (errorData?.error?.message) {
            errorMessage = errorData.error.message;
          }
        } catch {
          // Response was not JSON
        }

        let kind: import('./apiError').RepositoryErrorKind = 'SERVER';
        if (response.status === 401) kind = 'UNAUTHORIZED';
        else if (response.status === 403) kind = 'FORBIDDEN';
        else if (response.status === 404) kind = 'NOT_FOUND';
        else if (response.status === 422 || response.status === 400) kind = 'VALIDATION';
        else if (response.status >= 500) kind = 'SERVER';

        throw new RepositoryError(errorMessage, kind, {
          statusCode: response.status,
          requestId: response.headers.get('X-Request-ID') || requestId,
          details: errorData?.error?.details,
        });
      }

      if (response.status === 204) {
        return undefined as unknown as T;
      }

      return (await response.json()) as T;
    } catch (err: unknown) {
      clearTimeout(timeoutId);

      if (RepositoryError.isRepositoryError(err)) {
        throw err;
      }

      if (err instanceof DOMException && err.name === 'AbortError') {
        throw new RepositoryError(
          `Request timed out after ${timeoutMs}ms`,
          'TIMEOUT',
          { requestId }
        );
      }

      throw new RepositoryError(
        err instanceof Error ? err.message : 'Network communication error',
        'NETWORK',
        { requestId, cause: err }
      );
    }
  }

  async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  async post<T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async patch<T>(endpoint: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }

  async checkHealth(): Promise<boolean> {
    try {
      await this.get('/health', { timeoutMs: 3000 });
      return true;
    } catch {
      return false;
    }
  }
}

export const apiClient = new ApiClient();
