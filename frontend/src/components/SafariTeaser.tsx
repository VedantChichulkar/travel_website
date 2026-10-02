"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { safariService } from "@/src/services/safari.service";
import type { Safari } from "@/src/types/safari";

export function SafariTeaser() {
  const [items, setItems] = useState<Safari[] | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => { let active = true; void safariService.list().then((data) => { if (active) setItems(data.slice(0, 3)); }).catch(() => { if (active) setFailed(true); }); return () => { active = false; }; }, []);

  if (!items && !failed) return <div className="grid gap-5 lg:grid-cols-3">{[1, 2, 3].map((item) => <div key={item} className="skeleton h-64 rounded-[1.4rem]" />)}</div>;
  if (failed || !items?.length) return <div className="rounded-2xl border border-[var(--line)] bg-white p-8 text-center text-slate-500">Safari listings are not available right now.</div>;

  return <div className="grid gap-5 lg:grid-cols-3">{items.map((safari, index) => (
    <article key={safari.slug} className="safari-card rounded-2xl border border-[var(--line)] p-6 text-[var(--ink)] shadow-[var(--shadow-sm)]">
      <p className="text-xs font-black uppercase tracking-[.16em] text-[var(--accent)]">Safari {String(index + 1).padStart(2, "0")}</p>
      <h3 className="mt-5 text-2xl font-black tracking-tight text-[var(--brand)]">{safari.name}</h3>
      <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-600">{safari.short_description}</p>
      <div className="mt-6 flex flex-wrap gap-2">{safari.shifts.slice(0, 2).map((shift) => <span key={shift} className="rounded-full border border-[var(--line)] bg-[var(--surface-muted)] px-3 py-1 text-xs font-bold text-slate-600">{shift}</span>)}</div>
      <Link href={`/safaris/${safari.slug}`} className="mt-7 inline-flex text-sm font-black text-[var(--accent)] hover:text-[var(--accent-strong)]">View safari <span aria-hidden className="ml-1">→</span></Link>
    </article>
  ))}</div>;
}
