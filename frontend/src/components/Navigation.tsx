"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/src/context/AuthContext";
import { isCustomerRole, portalForRole } from "@/src/lib/portal-routing";

const links = [
  { href: "/", label: "Home" },
  { href: "/destinations", label: "Destinations" },
  { href: "/hotels", label: "Hotels" },
  { href: "/safaris", label: "Safaris" },
  { href: "/experiences", label: "Experiences" },
  { href: "/advertise", label: "Advertise" },
  { href: "/contact", label: "Contact" },
] as const;

export function Navigation() {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, loading, logout, user } = useAuth();
  const [open, setOpen] = useState(false);

  function handleLogout() { logout(); setOpen(false); router.push("/login"); }
  function active(href: string) { return href === "/" ? pathname === "/" : !href.includes("#") && pathname.startsWith(href); }
  const accountHref = user && !isCustomerRole(user.role) ? portalForRole(user.role).href : "/account";

  if (pathname.startsWith("/partner")) return null;

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--line)] bg-white/95 backdrop-blur-xl">
      <nav aria-label="Primary navigation" className="container-shell flex min-h-18 items-center justify-between gap-4">
        <Link href="/" className="group flex shrink-0 items-center gap-2.5" onClick={() => setOpen(false)} aria-label="Maharashtra Tourist Places home">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[var(--brand)] text-sm font-black text-white">M</span>
          <span className="max-w-36 text-[11px] font-black uppercase leading-[1.05] tracking-[.11em] text-[var(--brand)] sm:max-w-none sm:text-xs">
            <span className="block">Maharashtra</span><span className="block">Tourist Places</span>
          </span>
        </Link>
        <div className="hidden items-center gap-0.5 xl:flex">
          {links.map((link) => <Link key={link.href} href={link.href} aria-current={active(link.href) ? "page" : undefined} className={`rounded-lg px-3 py-2 text-sm font-bold transition ${active(link.href) ? "bg-[var(--accent-soft)] text-[var(--accent-strong)]" : "text-slate-600 hover:bg-[var(--surface-muted)] hover:text-[var(--brand)]"}`}>{link.label}</Link>)}
        </div>
        <div className="hidden items-center gap-2 xl:flex">
          <Link href="/partner/register" className="mr-1 text-xs font-bold text-slate-500 hover:text-[var(--accent)]">Partner with us</Link>
          {!loading && !isAuthenticated && <><Link href="/login" className="secondary-button !min-h-10 !px-4">Log in</Link><Link href="/register" className="primary-button !min-h-10 !px-4">Create account</Link></>}
          {!loading && isAuthenticated && user && <details className="relative"><summary className="secondary-button !min-h-10 cursor-pointer list-none !px-4">Account</summary><div className="absolute right-0 mt-2 grid w-56 gap-1 rounded-xl border border-[var(--line)] bg-white p-2 shadow-[var(--shadow-lg)]"><Link href={accountHref} className="rounded-lg px-3 py-2 text-sm font-bold hover:bg-[var(--surface-muted)]">{isCustomerRole(user.role) ? "Account overview" : "Open portal"}</Link>{isCustomerRole(user.role) && <><Link href="/account/bookings" className="rounded-lg px-3 py-2 text-sm font-bold hover:bg-[var(--surface-muted)]">Bookings</Link><Link href="/account/safaris" className="rounded-lg px-3 py-2 text-sm font-bold hover:bg-[var(--surface-muted)]">Safaris</Link><Link href="/account/messages" className="rounded-lg px-3 py-2 text-sm font-bold hover:bg-[var(--surface-muted)]">Messages</Link><Link href="/account/notifications" className="rounded-lg px-3 py-2 text-sm font-bold hover:bg-[var(--surface-muted)]">Notifications</Link></>}{!isCustomerRole(user.role) && <Link href="/notifications" className="rounded-lg px-3 py-2 text-sm font-bold hover:bg-[var(--surface-muted)]">Notifications</Link>}<button type="button" onClick={handleLogout} className="rounded-lg px-3 py-2 text-left text-sm font-bold text-red-700 hover:bg-red-50">Log out</button></div></details>}
        </div>
        <button type="button" className="grid h-11 w-11 place-items-center rounded-xl border border-[var(--line)] text-[var(--brand)] xl:hidden" aria-expanded={open} aria-controls="mobile-navigation" aria-label={open ? "Close navigation" : "Open navigation"} onClick={() => setOpen((current) => !current)}><span aria-hidden className="text-xl leading-none">{open ? "×" : "☰"}</span></button>
      </nav>
      {open && <div id="mobile-navigation" className="border-t border-[var(--line)] bg-white px-4 py-4 shadow-[var(--shadow-lg)] xl:hidden"><div className="container-shell flex flex-col gap-1">{links.map((link) => { const isActive = active(link.href); return <Link key={link.href} href={link.href} aria-current={isActive ? "page" : undefined} onClick={() => setOpen(false)} className={`rounded-xl px-4 py-3 font-bold ${isActive ? "bg-[var(--accent-soft)] text-[var(--accent-strong)]" : "text-slate-700 hover:bg-[var(--surface-muted)]"}`}>{link.label}</Link>; })}<Link href="/partner/register" onClick={() => setOpen(false)} className="rounded-xl px-4 py-3 text-sm font-bold text-slate-500">Partner with us</Link>{!loading && !isAuthenticated && <><Link href="/login" onClick={() => setOpen(false)} className="secondary-button mt-2">Log in</Link><Link href="/register" onClick={() => setOpen(false)} className="primary-button">Create account</Link></>}{!loading && isAuthenticated && user && <><Link href={accountHref} onClick={() => setOpen(false)} className="rounded-xl px-4 py-3 font-bold text-slate-700">Account</Link>{isCustomerRole(user.role) && <><Link href="/account/bookings" onClick={() => setOpen(false)} className="rounded-xl px-4 py-3 font-bold text-slate-700">Bookings</Link><Link href="/account/safaris" onClick={() => setOpen(false)} className="rounded-xl px-4 py-3 font-bold text-slate-700">Safaris</Link><Link href="/account/notifications" onClick={() => setOpen(false)} className="rounded-xl px-4 py-3 font-bold text-slate-700">Notifications</Link></>}{!isCustomerRole(user.role) && <Link href="/notifications" onClick={() => setOpen(false)} className="rounded-xl px-4 py-3 font-bold text-slate-700">Notifications</Link>}<button type="button" onClick={handleLogout} className="secondary-button">Log out</button></>}</div></div>}
    </header>
  );
}
