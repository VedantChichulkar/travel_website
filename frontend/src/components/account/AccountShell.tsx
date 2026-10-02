"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/src/context/AuthContext";
import { isCustomerRole, portalForRole } from "@/src/lib/portal-routing";

const links = [
  ["/account", "Overview"], ["/account/bookings", "Bookings"], ["/account/safaris", "Safaris"],
  ["/account/payments", "Payments"], ["/account/reviews", "Reviews"], ["/account/messages", "Messages"],
  ["/account/notifications", "Notifications"], ["/account/profile", "Profile"],
] as const;

export function AccountShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname(); const router = useRouter(); const { loading, user } = useAuth();
  useEffect(() => {
    if (loading) return;
    if (!user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    else if (!isCustomerRole(user.role)) router.replace(portalForRole(user.role).href);
  }, [loading, pathname, router, user]);
  if (loading || !user || !isCustomerRole(user.role)) return <main className="container-shell py-14"><div className="grid gap-6 lg:grid-cols-[230px_1fr]"><div className="skeleton h-72 rounded-2xl" /><div className="skeleton h-96 rounded-2xl" /></div></main>;
  return <main className="container-shell py-8 sm:py-12"><div className="mb-6 lg:hidden"><label className="sr-only" htmlFor="account-nav">Account section</label><select id="account-nav" value={links.find(([href]) => href === pathname || (href !== "/account" && pathname.startsWith(`${href}/`)))?.[0] ?? "/account"} onChange={(event) => router.push(event.target.value)} className="field-input"><option disabled>Account navigation</option>{links.map(([href, label]) => <option key={href} value={href}>{label}</option>)}</select></div><div className="grid items-start gap-8 lg:grid-cols-[230px_minmax(0,1fr)]"><aside className="sticky top-24 hidden rounded-2xl border border-[var(--line)] bg-white p-3 lg:block"><p className="px-3 pb-3 pt-2 text-xs font-black uppercase tracking-[.15em] text-slate-400">Your account</p><nav aria-label="Customer account" className="grid gap-1">{links.map(([href, label]) => { const active = href === "/account" ? pathname === href : pathname.startsWith(href); return <Link key={href} href={href} aria-current={active ? "page" : undefined} className={`rounded-xl px-3 py-2.5 text-sm font-bold ${active ? "bg-[var(--accent-soft)] text-[var(--accent-strong)]" : "text-slate-600 hover:bg-[var(--surface-muted)]"}`}>{label}</Link>; })}</nav></aside><div className="min-w-0">{children}</div></div></main>;
}
