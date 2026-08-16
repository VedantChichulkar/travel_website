"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAdminAuth } from "@/context/AdminAuthContext";

export function AdminNavigation() {
  const router = useRouter();
  const { logout } = useAdminAuth();

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  return (
    <header className="border-b border-slate-800 bg-slate-950 text-white">
      <nav className="mx-auto flex min-h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/dashboard" className="font-bold tracking-tight">Travel Booking Admin</Link>
        <div className="flex items-center gap-2">
          <Link href="/dashboard" className="rounded-md px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800">Dashboard</Link>
          <button type="button" onClick={handleLogout} className="rounded-md px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800">Logout</button>
        </div>
      </nav>
    </header>
  );
}
