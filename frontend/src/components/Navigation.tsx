"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/src/context/AuthContext";

const linkClass = "rounded-md px-3 py-2 text-sm font-medium transition hover:bg-sky-50 hover:text-sky-700";

export function Navigation() {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, loading, logout } = useAuth();

  function handleLogout() {
    logout();
    router.push("/login");
  }

  function navClass(href: string) {
    return `${linkClass} ${pathname === href ? "bg-sky-50 text-sky-700" : "text-slate-600"}`;
  }

  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex min-h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link href="/" className="text-lg font-bold tracking-tight text-slate-950">Travel Booking</Link>
        <div className="flex items-center gap-1">
          <Link href="/" className={navClass("/")}>Home</Link>
          {!loading && !isAuthenticated && (
            <>
              <Link href="/register" className={navClass("/register")}>Register</Link>
              <Link href="/login" className={navClass("/login")}>Login</Link>
            </>
          )}
          {!loading && isAuthenticated && (
            <>
              <Link href="/profile" className={navClass("/profile")}>Profile</Link>
              <button type="button" onClick={handleLogout} className={`${linkClass} text-slate-600`}>Logout</button>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
