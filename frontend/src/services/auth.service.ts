import { api, ApiError } from "@/src/services/api";
import { tokenStorage } from "@/src/services/token-storage";
import type {
  AuthResponse,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  User,
} from "@/src/types/auth";

async function refreshToken(): Promise<string | null> {
  try {
    const response = await api.post<TokenResponse, Record<string, never>>("/auth/refresh", {});
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

  forgotPassword(email: string): Promise<{ message: string }> {
    return api.post<{ message: string }, { email: string }>("/auth/forgot-password", { email });
  },

  resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
    return api.post<{ message: string }, { token: string; new_password: string }>("/auth/reset-password", { token, new_password: newPassword });
  },

  verifyEmail(token: string): Promise<User> {
    return api.post<User, { token: string }>("/auth/email-verification/confirm", { token });
  },

  async login(data: LoginRequest): Promise<User> {
    const response = await api.post<AuthResponse, LoginRequest>("/auth/login", data);
    tokenStorage.setTokens({
      accessToken: response.access_token,
    });
    return response.user;
  },

  async getCurrentUser(): Promise<User | null> {
    const tokens = tokenStorage.getTokens();
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
  },

  refreshToken,

  logout(): void {
    tokenStorage.clear();
    void api.post<void, Record<string, never>>("/auth/logout", {}).catch(() => undefined);
  },
};
