import { ENV } from "../config/env";
import { logger } from "../utils/logger";

export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    request_id: string;
    details?: Array<{ field?: string; issue: string; type?: string }>;
  };
}

export class ApiError extends Error {
  public readonly code: string;
  public readonly requestId?: string;
  public readonly status: number;
  public readonly details?: Array<{ field?: string; issue: string; type?: string }>;

  constructor(status: number, errorData: ApiErrorResponse["error"]) {
    super(errorData.message || `API error with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.code = errorData.code || "UNKNOWN_ERROR";
    this.requestId = errorData.request_id;
    this.details = errorData.details;
  }
}

export interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

function generateRequestId(): string {
  return "mob-" + Math.random().toString(36).substring(2, 10);
}

export class ApiClient {
  private readonly baseUrl: string;

  constructor(baseUrl: string = ENV.API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const url = `${this.baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
    const requestId = generateRequestId();
    const timeout = options.timeoutMs ?? ENV.TIMEOUT_MS;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);

    const headers: Record<string, string> = {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-Request-ID": requestId,
      ...(options.headers as Record<string, string>),
    };

    logger.debug(`[HTTP] ${options.method || "GET"} ${url} [req:${requestId}]`);

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timer);

      if (!response.ok) {
        let errorBody: ApiErrorResponse | null = null;
        try {
          errorBody = (await response.json()) as ApiErrorResponse;
        } catch {
          // Response was not JSON
        }

        const errorPayload = errorBody?.error ?? {
          code: "HTTP_ERROR",
          message: `Request failed with status ${response.status}: ${response.statusText}`,
          request_id: requestId,
        };

        throw new ApiError(response.status, errorPayload);
      }

      const data = (await response.json()) as T;
      return data;
    } catch (err: unknown) {
      clearTimeout(timer);
      if (err instanceof ApiError) {
        throw err;
      }
      if (err instanceof Error && err.name === "AbortError") {
        throw new ApiError(408, {
          code: "TIMEOUT",
          message: `Request timed out after ${timeout}ms`,
          request_id: requestId,
        });
      }
      throw new ApiError(0, {
        code: "NETWORK_ERROR",
        message: err instanceof Error ? err.message : "Network connection failure",
        request_id: requestId,
      });
    }
  }

  public async get<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: "GET" });
  }

  public async post<T>(path: string, body: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: "POST",
      body: JSON.stringify(body),
    });
  }
}

export const apiClient = new ApiClient();
