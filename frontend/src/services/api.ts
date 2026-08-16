const API_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_URL) {
  throw new Error("NEXT_PUBLIC_API_URL is not configured");
}

interface ValidationIssue {
  loc?: Array<string | number>;
  msg?: string;
}

interface ErrorPayload {
  detail?: string | ValidationIssue[];
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
  method?: "GET" | "POST";
  body?: TBody;
  accessToken?: string;
  signal?: AbortSignal;
}

function errorMessage(payload: ErrorPayload | undefined, status: number): string {
  if (typeof payload?.detail === "string") return payload.detail;
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
  if (options.body !== undefined) headers.set("Content-Type", "application/json");
  if (options.accessToken) headers.set("Authorization", `Bearer ${options.accessToken}`);

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("Cannot connect to the travel service. Please try again.", 0);
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
};
