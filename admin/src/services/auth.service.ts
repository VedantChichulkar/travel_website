import { api, ApiError } from "@/services/api";
import { tokenStorage } from "@/services/token-storage";
import type {
  AuthResponse,
  LoginRequest,
  RefreshTokenRequest,
  TokenResponse,
  User,
} from "@/types/auth";

export class AdminAccessError extends Error {
  constructor() {
    super("This account does not have administrator access.");
    this.name = "AdminAccessError";
  }
}

async function verifyAdminAccess(accessToken: string): Promise<void> {
  try {
    await api.get<{ status: string; message: string }>("/admin/test", accessToken);
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) throw new AdminAccessError();
    throw error;
  }
}

async function refreshToken(): Promise<string | null> {
  const tokens = tokenStorage.get();
  if (!tokens) return null;

  try {
    const response = await api.post<TokenResponse, RefreshTokenRequest>("/auth/refresh", {
      refresh_token: tokens.refreshToken,
    });
    tokenStorage.updateAccessToken(response.access_token);
    return response.access_token;
  } catch {
    tokenStorage.clear();
    return null;
  }
}

async function currentUserWithRefresh(): Promise<User | null> {
  const tokens = tokenStorage.get();
  if (!tokens) return null;

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
    const response = await api.post<AuthResponse, LoginRequest>("/auth/login", credentials);
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
      refreshToken: response.refresh_token,
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
  },
};
