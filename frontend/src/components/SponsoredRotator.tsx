"use client";

import Image from "next/image";
import { FocusEvent, useEffect, useRef, useState } from "react";

import { advertisingService } from "@/src/services/advertising.service";
import type { PublicAd } from "@/src/types/advertising";

export function SponsoredRotator({ placement, district, destination }: { placement: "HOMEPAGE_BANNER" | "DESTINATION_PROMOTION"; district?: string; destination?: string }) {
  const [items, setItems] = useState<PublicAd[]>([]);
  const [index, setIndex] = useState(0);
  const [seconds, setSeconds] = useState(5);
  const [paused, setPaused] = useState(false);
  const viewed = useRef(new Set<string>());

  useEffect(() => {
    let active = true;
    void advertisingService.publicAds(placement, district, destination).then((data) => {
      if (active) { setItems(data.items); setSeconds(Math.max(1, data.rotation_seconds || 5)); }
    }).catch(() => undefined);
    return () => { active = false; };
  }, [placement, district, destination]);

  useEffect(() => {
    if (items.length < 2 || paused) return;
    const timer = window.setInterval(() => setIndex((value) => (value + 1) % items.length), seconds * 1000);
    return () => window.clearInterval(timer);
  }, [items.length, paused, seconds]);

  const current = items[index];
  useEffect(() => {
    if (!current || viewed.current.has(current.id)) return;
    viewed.current.add(current.id);
    void advertisingService.event(current.id, "impressions", crypto.randomUUID()).catch(() => undefined);
  }, [current]);

  if (!current) return null;
  const move = (direction: number) => setIndex((value) => (value + direction + items.length) % items.length);
  const leaveFocus = (event: FocusEvent<HTMLElement>) => { if (!event.currentTarget.contains(event.relatedTarget)) setPaused(false); };

  return (
    <aside className="container-shell py-7" aria-label="Sponsored stays">
      <div className="relative overflow-hidden rounded-2xl border border-[var(--line)] bg-white shadow-[var(--shadow-sm)]" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocus={() => setPaused(true)} onBlur={leaveFocus}>
        <a href={current.destination_url} target={current.is_external ? "_blank" : undefined} rel={current.is_external ? "noopener noreferrer sponsored" : "sponsored"} onClick={() => { if (!current.is_external) void advertisingService.event(current.id, "clicks", crypto.randomUUID()).catch(() => undefined); }} className="relative block h-44 overflow-hidden bg-slate-900 sm:h-60">
          <Image unoptimized fill priority={placement === "HOMEPAGE_BANNER"} sizes="100vw" src={current.creative_url} alt={current.alt_text} className="object-cover" />
          <span className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/10 to-transparent" />
          <span className="absolute left-4 top-4 rounded-full bg-black/75 px-3 py-1 text-xs font-bold text-white">{current.sponsor_label}</span>
          <span className="absolute bottom-0 left-0 right-0 px-5 pb-5 pt-12 text-lg font-black text-white">{current.headline || current.advertiser_name}</span>
        </a>
        {items.length > 1 && <div className="absolute bottom-4 right-4 flex items-center gap-2" aria-label="Sponsored stay controls">
          <button type="button" onClick={() => move(-1)} className="ad-control" aria-label="Previous sponsored stay">←</button>
          <button type="button" onClick={() => setPaused((value) => !value)} className="ad-control min-w-18 px-3" aria-label={paused ? "Resume sponsored stay rotation" : "Pause sponsored stay rotation"}>{paused ? "Play" : "Pause"}</button>
          <button type="button" onClick={() => move(1)} className="ad-control" aria-label="Next sponsored stay">→</button>
        </div>}
        <p className="sr-only" aria-live="polite">Sponsored item {index + 1} of {items.length}: {current.advertiser_name}</p>
      </div>
    </aside>
  );
}
