"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const FOOTER_LINKS = [
  { title: "Explore", links: [{ label: "Destinations", href: "/destinations" }, { label: "Hotels", href: "/hotels" }, { label: "Safaris", href: "/safaris" }] },
  { title: "Maharashtra Tourist Places", links: [{ label: "About", href: "/about" }, { label: "Contact", href: "/contact" }, { label: "Customer login", href: "/login" }] },
  { title: "Support", links: [{ label: "Booking Help", href: "/contact?type=BOOKING_HELP" }, { label: "Cancellation / Refund", href: "/contact?type=CANCELLATION_REFUND" }, { label: "Safari Help", href: "/contact?type=SAFARI_HELP" }] },
  { title: "Hotel partners", links: [{ label: "Become a partner", href: "/partner/register" }, { label: "Partner login", href: "/partner/login" }] },
] as const;

export function Footer() {
  const pathname = usePathname();
  if (pathname.startsWith("/partner")) return null;
  return (
    <footer id="contact" className="bg-[var(--brand-strong)] text-white">
      <div className="container-shell grid gap-10 py-14 sm:grid-cols-2 lg:grid-cols-[1.6fr_1fr_1fr_1fr_1fr]">
        <div><Link href="/" className="inline-flex items-center gap-2 text-base font-black uppercase tracking-[.1em]"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-white text-xs text-[var(--brand)]">M</span><span>Maharashtra Tourist Places</span></Link><p className="mt-4 max-w-sm text-sm leading-6 text-slate-300">A Maharashtra-first platform for destination discovery, active stays, and supported safari requests. Maharashtra Tourist Places is independent and is not affiliated with the Government of Maharashtra.</p></div>
        {FOOTER_LINKS.map((group) => <div key={group.title}><h2 className="text-xs font-black uppercase tracking-[.16em] text-[var(--accent-on-dark)]">{group.title}</h2><div className="mt-2 grid text-sm font-semibold text-slate-300">{group.links.map((link) => <Link key={link.label} href={link.href} className="inline-flex min-h-11 w-fit items-center hover:text-white">{link.label}</Link>)}</div></div>)}
        <p className="border-t border-white/10 pt-6 text-xs text-slate-400 sm:col-span-2 lg:col-span-5">© {new Date().getFullYear()} Maharashtra Tourist Places. Made for considered journeys across Maharashtra.</p>
      </div>
    </footer>
  );
}
