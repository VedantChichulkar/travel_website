"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { authService } from "@/services/auth.service";
import type { LoginRequest, User } from "@/types/auth";

interface AdminAuthContextValue {
  admin: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
  verifySession: () => Promise<User | null>;
}

const AdminAuthContext = createContext<AdminAuthContextValue | undefined>(undefined);

export function AdminAuthProvider({ children }: { children: React.ReactNode }) {
  const [admin, setAdmin] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const verifySession = useCallback(async () => {
    setLoading(true);
    try {
      const currentAdmin = await authService.verifySession();
      setAdmin(currentAdmin);
      return currentAdmin;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    void authService
      .verifySession()
      .then((currentAdmin) => {
        if (active) setAdmin(currentAdmin);
      })
      .catch(() => {
        if (active) setAdmin(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (credentials: LoginRequest) => {
    const currentAdmin = await authService.login(credentials);
    setAdmin(currentAdmin);
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setAdmin(null);
  }, []);

  const value = useMemo(
    () => ({ admin, isAuthenticated: Boolean(admin), loading, login, logout, verifySession }),
    [admin, loading, login, logout, verifySession],
  );

  return <AdminAuthContext.Provider value={value}>{children}</AdminAuthContext.Provider>;
}

export function useAdminAuth(): AdminAuthContextValue {
  const value = useContext(AdminAuthContext);
  if (!value) throw new Error("useAdminAuth must be used inside AdminAuthProvider");
  return value;
}
