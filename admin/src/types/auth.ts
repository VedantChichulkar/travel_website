export type UserRole = "CUSTOMER" | "USER" | "HOTEL_PARTNER" | "ADMIN";
export type UserStatus = "ACTIVE" | "INACTIVE" | "SUSPENDED";

export interface User {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  role: UserRole;
  status: UserStatus;
  is_active: boolean;
  is_email_verified: boolean;
  is_phone_verified: boolean;
  last_login_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
  portal?: UserRole;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface AuthResponse extends TokenResponse {
  user: User;
}

export interface RefreshTokenRequest {
  refresh_token?: string;
}
