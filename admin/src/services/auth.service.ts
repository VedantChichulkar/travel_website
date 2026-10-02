import { api, ApiError, type PortalErrorDetail } from "@/services/api";
import { tokenStorage } from "@/services/token-storage";
import type {
  AuthResponse,
  LoginRequest,
  TokenResponse,
  User,
} from "@/types/auth";

export class AdminAccessError extends Error {
  constructor(public readonly portal?: PortalErrorDetail) {
    super(portal?.message ?? "This account does not have administrator access.");
    this.name = "AdminAccessError";
  }
}

async function verifyAdminAccess(accessToken: string): Promise<void> {
  try {
    await api.get<{ users: Record<string, number> }>("/admin/control/overview", accessToken);
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) throw new AdminAccessError();
    throw error;
  }
}

async function refreshToken(): Promise<string | null> {
  try {
    const response = await api.post<TokenResponse, Record<string, never>>("/auth/refresh", {});
    tokenStorage.updateAccessToken(response.access_token);
    return response.access_token;
  } catch {
    tokenStorage.clear();
    return null;
  }
}

async function currentUserWithRefresh(): Promise<User | null> {
  const tokens = tokenStorage.get();
  if (!tokens) {
    const accessToken = await refreshToken();
    return accessToken ? api.get<User>("/users/me", accessToken) : null;
  }

  try {
    return await api.get<User>("/users/me", tokens.accessToken);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
  }

  const accessToken = await refreshToken();
  if (!accessToken) return null;
  try {
    return await api.get<User>("/users/me", accessToken);
  } catch {
    tokenStorage.clear();
    return null;
  }
}

export const authService = {
  async login(credentials: LoginRequest): Promise<User> {
    let response: AuthResponse;
    try {
      response = await api.post<AuthResponse, LoginRequest>("/auth/login", { ...credentials, portal: "ADMIN" });
    } catch (error) {
      const detail = error instanceof ApiError ? error.details : undefined;
      if (detail && !Array.isArray(detail) && typeof detail !== "string" && detail.code === "WRONG_PORTAL") {
        throw new AdminAccessError(detail);
      }
      throw error;
    }
    try {
      await verifyAdminAccess(response.access_token);
    } catch (error) {
      tokenStorage.clear();
      throw error;
    }
    if (response.user.role !== "ADMIN") {
      tokenStorage.clear();
      throw new AdminAccessError();
    }

    tokenStorage.set({
      accessToken: response.access_token,
    });
    return response.user;
  },

  async getCurrentUser(): Promise<User | null> {
    return currentUserWithRefresh();
  },

  refreshToken,
  verifyAdminAccess,

  async verifySession(): Promise<User | null> {
    const user = await currentUserWithRefresh();
    if (!user) {
      tokenStorage.clear();
      return null;
    }

    const accessToken = tokenStorage.get()?.accessToken;
    if (!accessToken) return null;
    try {
      await verifyAdminAccess(accessToken);
      if (user.role !== "ADMIN") throw new AdminAccessError();
      return user;
    } catch {
      tokenStorage.clear();
      return null;
    }
  },

  logout(): void {
    tokenStorage.clear();
    void api.post<void, Record<string, never>>("/auth/logout", {}).catch(() => undefined);
  },
};
