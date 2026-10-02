import { ApiError, api } from "@/services/api";
import { authService } from "@/services/auth.service";
import { tokenStorage } from "@/services/token-storage";

type Method = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

async function call<TResponse, TBody>(method: Method, path: string, body?: TBody): Promise<TResponse> {
  let accessToken = tokenStorage.get()?.accessToken;
  if (!accessToken) throw new ApiError("Your session has expired. Please sign in again.", 401);

  const send = (token: string) => {
    if (method === "GET") return api.get<TResponse>(path, token);
    if (method === "POST") return api.postAuthorized<TResponse, TBody>(path, body as TBody, token);
    if (method === "PATCH") return api.patch<TResponse, TBody>(path, body as TBody, token);
    if (method === "PUT") return api.put<TResponse, TBody>(path, body as TBody, token);
    return api.delete<TResponse>(path, token);
  };

  try {
    return await send(accessToken);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
    accessToken = (await authService.refreshToken()) ?? undefined;
    if (!accessToken) throw error;
    return send(accessToken);
  }
}

export const authorizedApi = {
  get: <T>(path: string) => call<T, never>("GET", path),
  post: <T, B>(path: string, body: B) => call<T, B>("POST", path, body),
  patch: <T, B>(path: string, body: B) => call<T, B>("PATCH", path, body),
  put: <T, B>(path: string, body: B) => call<T, B>("PUT", path, body),
  delete: <T = void>(path: string) => call<T, never>("DELETE", path),
};
