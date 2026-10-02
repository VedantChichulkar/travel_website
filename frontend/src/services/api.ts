const API_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_URL) {
  throw new Error("NEXT_PUBLIC_API_URL is not configured");
}

interface ValidationIssue {
  loc?: Array<string | number>;
  msg?: string;
}

export interface PortalErrorDetail {
  code: "WRONG_PORTAL";
  account_role: "CUSTOMER" | "HOTEL_PARTNER" | "ADMIN";
  portal_path: string;
  message: string;
}

interface ErrorPayload {
  detail?: string | ValidationIssue[] | PortalErrorDetail;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly payload?: ErrorPayload,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions<TBody> {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: TBody;
  accessToken?: string;
  signal?: AbortSignal;
}

function errorMessage(payload: ErrorPayload | undefined, status: number): string {
  if (typeof payload?.detail === "string") return payload.detail;
  if (payload?.detail && !Array.isArray(payload.detail) && "message" in payload.detail) {
    return payload.detail.message;
  }
  if (Array.isArray(payload?.detail)) {
    return payload.detail
      .map((issue) => {
        const field = issue.loc?.at(-1);
        return field ? `${String(field)}: ${issue.msg ?? "Invalid value"}` : issue.msg;
      })
      .filter(Boolean)
      .join("; ");
  }
  return status >= 500 ? "The service is temporarily unavailable." : "Request failed.";
}

async function parseJson<T>(response: Response): Promise<T | undefined> {
  const text = await response.text();
  if (!text) return undefined;

  try {
    return JSON.parse(text) as T;
  } catch {
    return undefined;
  }
}

export async function apiRequest<TResponse, TBody = never>(
  path: string,
  options: RequestOptions<TBody> = {},
): Promise<TResponse> {
  const headers = new Headers({ Accept: "application/json" });
  if (options.body !== undefined && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (options.accessToken) headers.set("Authorization", `Bearer ${options.accessToken}`);

  const controller = new AbortController();
  let timedOut = false;
  const abortFromCaller = () => controller.abort();
  options.signal?.addEventListener("abort", abortFromCaller, { once: true });
  const timeout = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, 12_000);

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : options.body instanceof FormData ? options.body : JSON.stringify(options.body),
      signal: controller.signal,
      credentials: "include",
    });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    if (timedOut) throw new ApiError("The travel service took too long to respond. Please try again.", 0);
    throw new ApiError("Cannot connect to the travel service. Please try again.", 0);
  } finally {
    clearTimeout(timeout);
    options.signal?.removeEventListener("abort", abortFromCaller);
  }

  const payload = await parseJson<TResponse | ErrorPayload>(response);
  if (!response.ok) {
    const errorPayload = payload as ErrorPayload | undefined;
    throw new ApiError(errorMessage(errorPayload, response.status), response.status, errorPayload);
  }

  return payload as TResponse;
}

export const api = {
  get<TResponse>(path: string, accessToken?: string): Promise<TResponse> {
    return apiRequest<TResponse>(path, { accessToken });
  },

  post<TResponse, TBody>(path: string, body: TBody, accessToken?: string): Promise<TResponse> {
    return apiRequest<TResponse, TBody>(path, { method: "POST", body, accessToken });
  },
  patch<TResponse, TBody>(path: string, body: TBody, accessToken?: string): Promise<TResponse> {
    return apiRequest<TResponse, TBody>(path, { method: "PATCH", body, accessToken });
  },
  put<TResponse, TBody>(path: string, body: TBody, accessToken?: string): Promise<TResponse> {
    return apiRequest<TResponse, TBody>(path, { method: "PUT", body, accessToken });
  },
  delete<TResponse>(path: string, accessToken?: string): Promise<TResponse> {
    return apiRequest<TResponse>(path, { method: "DELETE", accessToken });
  },
};
