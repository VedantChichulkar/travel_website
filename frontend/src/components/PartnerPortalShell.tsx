"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/src/context/AuthContext";
import { partnerService } from "@/src/services/partner.service";

const UNSHELLED_ROUTES = new Set([
  "/partner/login",
  "/partner/register",
  "/partner/onboarding",
  "/partner/verification",
  "/partner/room-types",
  "/partner/rooms",
]);

const navItems = [
  ["/partner/dashboard", "Dashboard", "grid"],
  ["/partner/property", "Property", "building"],
  ["/partner/rooms", "Rooms", "bed"],
  ["/partner/inventory", "Inventory", "calendar"],
  ["/partner/bookings", "Bookings", "book"],
  ["/partner/operations", "Operations", "check"],
  ["/partner/settlements", "Settlements", "rupee"],
  ["/partner/advertising", "Advertising", "megaphone"],
  ["/partner/messages", "Messages", "message"],
  ["/partner/notifications", "Notifications", "bell"],
  ["/partner/reviews", "Reviews", "star"],
  ["/partner/verification", "Verification", "shield"],
  ["/partner/settings", "Settings", "settings"],
] as const;

export function PartnerPortalShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [hotelName, setHotelName] = useState("Your Hotel");
  const [mobileOpen, setMobileOpen] = useState(false);
  const unshelled = UNSHELLED_ROUTES.has(pathname);

  useEffect(() => {
    if (unshelled || !user) return;
    let active = true;
    void partnerService.getOverview().then((overview) => {
      if (active && overview.hotel?.name) setHotelName(overview.hotel.name);
    }).catch(() => undefined);
    return () => { active = false; };
  }, [unshelled, user]);

  if (unshelled) return children;

  const initials = user?.full_name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "HP";
  function signOut() { logout(); router.replace("/partner/login"); }
  const navigation = <div className="flex h-full flex-col">
    <div className="border-b border-[var(--line)] px-5 py-5"><div className="flex items-center gap-3"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[var(--brand)] text-sm font-black text-white">M</div><div className="min-w-0"><p className="text-xs font-black leading-tight tracking-tight text-[var(--brand)]">Maharashtra Tourist Places<br />Partner</p><p className="mt-1 truncate text-xs text-slate-500">{hotelName}</p></div></div></div>
    <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4" aria-label="Hotel partner navigation">{navItems.map(([href, label, icon]) => { const aliases = href === "/partner/property" ? ["/partner/hotel-profile"] : href === "/partner/rooms" ? ["/partner/room-types"] : []; const active = pathname === href || aliases.includes(pathname) || (href !== "/partner/dashboard" && pathname.startsWith(`${href}/`)); return <Link key={href} href={href} onClick={() => setMobileOpen(false)} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-bold transition ${active ? "bg-[var(--brand)] text-white" : "text-slate-600 hover:bg-[var(--surface-muted)] hover:text-[var(--brand)]"}`}><NavIcon name={icon} /><span>{label}</span></Link>; })}</nav>
    <div className="space-y-1 border-t border-[var(--line)] px-3 py-4"><div className="flex items-center gap-3 px-3 py-2"><div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[var(--accent)] text-xs font-black text-white">{initials}</div><span className="truncate text-sm font-semibold text-slate-700">{user?.full_name ?? "Hotel partner"}</span></div><button type="button" onClick={signOut} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-bold text-slate-500 hover:bg-red-50 hover:text-red-700"><NavIcon name="logout" />Log out</button></div>
  </div>;

  return <div className="flex min-h-screen bg-[var(--surface-muted)]"><aside className="sticky top-0 hidden h-screen w-64 shrink-0 overflow-y-auto border-r border-[var(--line)] bg-white lg:block">{navigation}</aside>{mobileOpen && <><button type="button" aria-label="Close navigation" className="fixed inset-0 z-40 bg-slate-950/40 lg:hidden" onClick={() => setMobileOpen(false)} /><aside className="fixed inset-y-0 left-0 z-50 w-72 bg-white shadow-xl lg:hidden">{navigation}</aside></>}<div className="min-w-0 flex-1"><header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-[var(--line)] bg-white px-4 lg:hidden"><button type="button" onClick={() => setMobileOpen(true)} aria-label="Open navigation" aria-expanded={mobileOpen} className="rounded-lg p-2 text-slate-600 hover:bg-[var(--surface-muted)]"><NavIcon name="menu" /></button><span className="max-w-48 text-center text-xs font-black leading-tight text-[var(--brand)]">Maharashtra Tourist Places Partner</span><div className="grid h-8 w-8 place-items-center rounded-full bg-[var(--accent)] text-xs font-black text-white">{initials}</div></header>{children}</div></div>;
}

function NavIcon({ name }: { name: string }) {
  if (name === "rupee") return <span className="grid h-5 w-5 place-items-center text-base">₹</span>;
  if (name === "star") return <span className="grid h-5 w-5 place-items-center text-base">★</span>;
  const paths: Record<string, React.ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /></>,
    building: <><path d="M6 22V4a2 2 0 012-2h8a2 2 0 012 2v18z" /><path d="M6 12H4a2 2 0 00-2 2v8h4M18 9h2a2 2 0 012 2v11h-4M10 6h4M10 10h4M10 14h4M10 18h4" /></>,
    bed: <><path d="M2 4v16M2 8h18a2 2 0 012 2v10M2 17h20M6 8v9" /></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18"/></>,
    book: <><path d="M4 19.5A2.5 2.5 0 016.5 17H20V3H6.5A2.5 2.5 0 004 5.5z"/><path d="M4 5.5v14"/></>,
    check: <polyline points="20 6 9 17 4 12" />,
    message: <><path d="M21 15a4 4 0 01-4 4H8l-5 3V7a4 4 0 014-4h10a4 4 0 014 4z" /></>,
    bell: <><path d="M18 8a6 6 0 00-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M10 21h4" /></>,
    shield: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />,
    megaphone: <><path d="M3 11v2a2 2 0 002 2h2l4 4V5L7 9H5a2 2 0 00-2 2z"/><path d="M16 8a5 5 0 010 8M19 5a9 9 0 010 14"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 00.34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0015 19.4a1.7 1.7 0 00-1 .6 1.7 1.7 0 00-.4 1.1V21H9.6v-.1A1.7 1.7 0 008.5 19.4a1.7 1.7 0 00-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 004.6 15a1.7 1.7 0 00-.6-1 1.7 1.7 0 00-1.1-.4H3V9.6h.1A1.7 1.7 0 004.6 8.5a1.7 1.7 0 00-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 009 4.6a1.7 1.7 0 001-.6 1.7 1.7 0 00.4-1.1V3h4v.1A1.7 1.7 0 0015.5 4.6a1.7 1.7 0 001.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0019.4 9c.15.38.37.72.66 1 .29.28.65.4 1.04.4h.1v4h-.1A1.7 1.7 0 0019.4 15z"/></>,
    logout: <><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></>,
    menu: <><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" /></>,
  };
  return <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">{paths[name]}</svg>;
}
