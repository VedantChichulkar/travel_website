"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/src/context/AuthContext";
import { portalForRole } from "@/src/lib/portal-routing";

const PUBLIC_PARTNER_ROUTES = new Set(["/partner/login", "/partner/register"]);

export function PartnerRouteGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { loading, user } = useAuth();
  const isPublic = PUBLIC_PARTNER_ROUTES.has(pathname);

  useEffect(() => {
    if (!isPublic && !loading && !user) router.replace("/partner/login");
  }, [isPublic, loading, router, user]);

  if (isPublic) return children;
  if (loading || !user) {
    return <div className="grid min-h-screen place-items-center bg-[#f0f4f8] text-sm font-bold text-slate-500">Verifying partner access…</div>;
  }
  if (user.role !== "HOTEL_PARTNER") {
    const destination = portalForRole(user.role);
    return (
      <div className="grid min-h-screen place-items-center bg-[#f0f4f8] p-6">
        <section className="w-full max-w-md rounded-2xl border border-red-200 bg-white p-8 text-center shadow-sm" role="alert">
          <p className="text-xs font-black uppercase tracking-[.16em] text-red-600">Wrong portal</p>
          <h1 className="mt-3 text-2xl font-black text-[#0b163d]">Hotel Partner access required</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">This signed-in account does not belong to a hotel partner.</p>
          <Link href={destination.href} className="primary-button mt-6">Go to {destination.label}</Link>
        </section>
      </div>
    );
  }
  return children;
}
