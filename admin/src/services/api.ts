const API_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_URL) throw new Error("NEXT_PUBLIC_API_URL is not configured");

export interface PortalErrorDetail {
  code: "WRONG_PORTAL";
  account_role: "CUSTOMER" | "HOTEL_PARTNER" | "ADMIN";
  portal_path: string;
  message: string;
}

interface ErrorPayload {
  detail?: string | Array<{ loc?: Array<string | number>; msg?: string }> | PortalErrorDetail;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly details?: ErrorPayload["detail"],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function messageFor(payload: ErrorPayload | undefined, status: number): string {
  if (typeof payload?.detail === "string") return payload.detail;
  if (payload?.detail && !Array.isArray(payload.detail) && "message" in payload.detail) return payload.detail.message;
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((item) => item.msg ?? "Invalid value").join("; ");
  }
  return status >= 500 ? "The admin service is temporarily unavailable." : "Request failed.";
}

async function request<TResponse, TBody = never>(
  path: string,
  options: { method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE"; body?: TBody; accessToken?: string } = {},
): Promise<TResponse> {
  const headers = new Headers({ Accept: "application/json" });
  if (options.body !== undefined && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (options.accessToken) headers.set("Authorization", `Bearer ${options.accessToken}`);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12_000);
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
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("The admin service took too long to respond. Please try again.", 0);
    }
    throw new ApiError("Cannot connect to the backend. Please try again.", 0);
  } finally {
    clearTimeout(timeout);
  }

  const text = await response.text();
  let payload: TResponse | ErrorPayload | undefined;
  try {
    payload = text ? (JSON.parse(text) as TResponse | ErrorPayload) : undefined;
  } catch {
    payload = undefined;
  }

  if (!response.ok) {
    const errorPayload = payload as ErrorPayload | undefined;
    throw new ApiError(messageFor(errorPayload, response.status), response.status, errorPayload?.detail);
  }
  return payload as TResponse;
}

export const api = {
  get<TResponse>(path: string, accessToken?: string): Promise<TResponse> {
    return request<TResponse>(path, { accessToken });
  },
  post<TResponse, TBody>(path: string, body: TBody): Promise<TResponse> {
    return request<TResponse, TBody>(path, { method: "POST", body });
  },
  postAuthorized<TResponse, TBody>(path: string, body: TBody, accessToken: string): Promise<TResponse> {
    return request<TResponse, TBody>(path, { method: "POST", body, accessToken });
  },
  patch<TResponse, TBody>(path: string, body: TBody, accessToken: string): Promise<TResponse> {
    return request<TResponse, TBody>(path, { method: "PATCH", body, accessToken });
  },
  put<TResponse, TBody>(path: string, body: TBody, accessToken: string): Promise<TResponse> {
    return request<TResponse, TBody>(path, { method: "PUT", body, accessToken });
  },
  delete<TResponse = void>(path: string, accessToken: string): Promise<TResponse> {
    return request<TResponse>(path, { method: "DELETE", accessToken });
  },
};
