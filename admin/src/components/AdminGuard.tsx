"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAdminAuth } from "@/context/AdminAuthContext";

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { admin, verifySession } = useAdminAuth();
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void verifySession()
      .then((currentAdmin) => {
        if (!active) return;
        if (!currentAdmin) router.replace("/login");
      })
      .catch(() => {
        if (active) setError("Unable to verify administrator access. Check the backend and try again.");
      })
      .finally(() => {
        if (active) setChecking(false);
      });
    return () => {
      active = false;
    };
  }, [router, verifySession]);

  if (error) {
    return <div role="alert" className="mx-auto mt-16 max-w-xl rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>;
  }
  if (checking || !admin) {
    return <div className="flex min-h-[50vh] items-center justify-center text-slate-500">Verifying administrator access…</div>;
  }
  return children;
}
