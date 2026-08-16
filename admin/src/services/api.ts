const API_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_URL) throw new Error("NEXT_PUBLIC_API_URL is not configured");

interface ErrorPayload {
  detail?: string | Array<{ loc?: Array<string | number>; msg?: string }>;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function messageFor(payload: ErrorPayload | undefined, status: number): string {
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((item) => item.msg ?? "Invalid value").join("; ");
  }
  return status >= 500 ? "The admin service is temporarily unavailable." : "Request failed.";
}

async function request<TResponse, TBody = never>(
  path: string,
  options: { method?: "GET" | "POST"; body?: TBody; accessToken?: string } = {},
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
    });
  } catch {
    throw new ApiError("Cannot connect to the backend. Please try again.", 0);
  }

  const text = await response.text();
  let payload: TResponse | ErrorPayload | undefined;
  try {
    payload = text ? (JSON.parse(text) as TResponse | ErrorPayload) : undefined;
  } catch {
    payload = undefined;
  }

  if (!response.ok) {
    throw new ApiError(messageFor(payload as ErrorPayload | undefined, response.status), response.status);
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
};
