import { api, ApiError } from "@/src/services/api";
import { tokenStorage } from "@/src/services/token-storage";
import type {
  AuthResponse,
  LoginRequest,
  RefreshTokenRequest,
  RegisterRequest,
  TokenResponse,
  User,
} from "@/src/types/auth";

async function refreshToken(): Promise<string | null> {
  const tokens = tokenStorage.getTokens();
  if (!tokens?.refreshToken) return null;

  try {
    const response = await api.post<TokenResponse, RefreshTokenRequest>("/auth/refresh", {
      refresh_token: tokens.refreshToken,
    });
    tokenStorage.setAccessToken(response.access_token);
    return response.access_token;
  } catch {
    tokenStorage.clear();
    return null;
  }
}

export const authService = {
  register(data: RegisterRequest): Promise<User> {
    return api.post<User, RegisterRequest>("/auth/register", data);
  },

  async login(data: LoginRequest): Promise<User> {
    const response = await api.post<AuthResponse, LoginRequest>("/auth/login", data);
    tokenStorage.setTokens({
      accessToken: response.access_token,
      refreshToken: response.refresh_token,
    });
    return response.user;
  },

  async getCurrentUser(): Promise<User | null> {
    const tokens = tokenStorage.getTokens();
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
  },

  refreshToken,

  logout(): void {
    tokenStorage.clear();
  },
};
