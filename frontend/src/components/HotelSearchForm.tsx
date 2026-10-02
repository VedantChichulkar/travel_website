"use client";

import { useRouter } from "next/navigation";
import { FormEvent, KeyboardEvent, useEffect, useId, useState } from "react";

import { hotelSearchQuery, validateHotelSearch } from "@/src/lib/hotel-search";
import { destinationService } from "@/src/services/destination.service";
import type { DestinationSearchResult } from "@/src/types/destination";
import type { HotelSearchParams } from "@/src/types/hotel";

const emptySearch: HotelSearchParams = { city: "", checkIn: "", checkOut: "", adults: 2, children: 0, rooms: 1, amenities: [], sort: "recommended" };

function initialDestinationLabel(initial: HotelSearchParams): string {
  if (initial.city) return initial.city;
  const slug = initial.destination?.split("/").at(-1);
  return slug ? slug.replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()) : "";
}

export function HotelSearchForm({ initial = emptySearch, compact = false, hero = false }: { initial?: HotelSearchParams; compact?: boolean; hero?: boolean }) {
  const router = useRouter();
  const listId = useId();
  const [error, setError] = useState("");
  const [query, setQuery] = useState(() => initialDestinationLabel(initial));
  const [destination, setDestination] = useState(initial.destination ?? "");
  const [items, setItems] = useState<DestinationSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchFailed, setSearchFailed] = useState(false);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  useEffect(() => {
    if (destination || query.trim().length < 2) {
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setSearching(true);
      setSearchFailed(false);
      void destinationService.search(query.trim(), 8, true).then((result) => {
        if (!controller.signal.aborted) {
          setItems(result.items);
          setOpen(true);
          setActiveIndex(-1);
        }
      }).catch(() => {
        if (!controller.signal.aborted) setSearchFailed(true);
      }).finally(() => {
        if (!controller.signal.aborted) setSearching(false);
      });
    }, 250);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [destination, query]);

  function choose(item: DestinationSearchResult) {
    const canonical = item.kind === "DISTRICT"
      ? item.slug
      : item.kind === "PLACE"
        ? item.destination_slug
          ? `${item.district_slug}/${item.destination_slug}`
          : item.district_slug ?? ""
        : `${item.district_slug}/${item.slug}`;
    setQuery(item.name);
    setDestination(canonical);
    setOpen(false);
    setError("");
  }

  function onDestinationKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!open || items.length === 0) return;
    if (event.key === "ArrowDown") { event.preventDefault(); setActiveIndex((value) => Math.min(value + 1, items.length - 1)); }
    if (event.key === "ArrowUp") { event.preventDefault(); setActiveIndex((value) => Math.max(value - 1, 0)); }
    if (event.key === "Escape") setOpen(false);
    if (event.key === "Enter" && activeIndex >= 0) { event.preventDefault(); choose(items[activeIndex]); }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const search: HotelSearchParams = {
      city: query.trim(), destination: destination || undefined,
      checkIn: String(form.get("checkIn") ?? ""), checkOut: String(form.get("checkOut") ?? ""),
      adults: Number(form.get("adults")), children: Number(form.get("children")), rooms: Number(form.get("rooms")),
      amenities: [], sort: "recommended",
    };
    const validation = validateHotelSearch(search);
    if (validation) return setError(validation);
    setError("");
    router.push(`/hotels?${hotelSearchQuery(search)}`);
  }

  const shell = hero
    ? "rounded-2xl border border-white/30 bg-white/97 p-4 text-slate-900 shadow-[var(--shadow-lg)] backdrop-blur sm:p-5"
    : compact
      ? "rounded-2xl border border-[var(--line)] bg-white p-4 shadow-[var(--shadow-sm)]"
      : "rounded-2xl border border-[var(--line)] bg-white p-4 shadow-[var(--shadow-sm)] sm:p-5";

  return (
    <form id={compact ? undefined : "search"} onSubmit={submit} className={shell} noValidate>
      <div className="grid items-end gap-3 md:grid-cols-2 xl:grid-cols-[1.45fr_1fr_1fr_1.15fr_.7fr_auto]">
        <div className="relative">
          <label htmlFor={`${listId}-input`} className="field-label">Destination</label>
          <input
            id={`${listId}-input`} name="city" aria-label="Destination" role="combobox" aria-autocomplete="list"
            aria-expanded={open} aria-controls={listId} aria-activedescendant={activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined}
            className="field-input" value={query} placeholder="District, city or place"
            onChange={(event) => { setQuery(event.target.value); setDestination(""); setItems([]); setSearching(event.target.value.trim().length >= 2); setOpen(true); }}
            onFocus={() => { if (items.length) setOpen(true); }} onKeyDown={onDestinationKeyDown} autoComplete="off" required
          />
          <input type="hidden" name="destination" value={destination} />
          {open && query.trim().length >= 2 && !destination && (
            <div id={listId} role="listbox" className="absolute left-0 right-0 top-full z-50 mt-2 max-h-72 overflow-auto rounded-xl border border-[var(--line)] bg-white p-1.5 shadow-[var(--shadow-lg)]">
              {searching && <p className="px-3 py-3 text-sm text-slate-500">Searching destinations…</p>}
              {!searching && searchFailed && <p className="px-3 py-3 text-sm text-red-700">Destination search is temporarily unavailable.</p>}
              {!searching && !searchFailed && items.length === 0 && <p className="px-3 py-3 text-sm text-slate-500">No matching destination found.</p>}
              {items.map((item, itemIndex) => (
                <button key={`${item.kind}-${item.path}`} id={`${listId}-${itemIndex}`} role="option" aria-selected={activeIndex === itemIndex} type="button"
                  onMouseDown={(event) => event.preventDefault()} onClick={() => choose(item)}
                  className={`flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm ${activeIndex === itemIndex ? "bg-[var(--accent-soft)]" : "hover:bg-[var(--surface-muted)]"}`}>
                  <span><strong className="block text-[var(--brand)]">{item.name}</strong>{item.district_name && <span className="text-xs text-slate-500">{item.district_name} district</span>}</span>
                  <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">{item.kind === "DISTRICT" ? "District" : item.kind === "DESTINATION" ? "Destination" : "Place"}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <Field label="Check-in"><input name="checkIn" aria-label="Check-in" type="date" className="field-input" defaultValue={initial.checkIn} required /></Field>
        <Field label="Check-out"><input name="checkOut" aria-label="Check-out" type="date" className="field-input" defaultValue={initial.checkOut} required /></Field>
        <div>
          <span className="field-label">Guests</span>
          <div className="grid grid-cols-2 gap-2">
            <label className="min-w-0"><span className="mb-1 block text-[10px] font-semibold leading-none text-slate-500">Adults</span><input name="adults" aria-label="Adults" type="number" min={1} max={20} className="field-input" defaultValue={initial.adults} /></label>
            <label className="min-w-0"><span className="mb-1 block text-[10px] font-semibold leading-none text-slate-500">Children</span><input name="children" aria-label="Children" type="number" min={0} max={20} className="field-input" defaultValue={initial.children} /></label>
          </div>
        </div>
        <Field label="Rooms"><input name="rooms" aria-label="Rooms" type="number" min={1} max={10} className="field-input" defaultValue={initial.rooms} /></Field>
        <button className="primary-button min-h-[3.15rem] px-6" type="submit">Search stays <span aria-hidden>→</span></button>
      </div>
      {error && <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm font-semibold text-[var(--danger)]">{error}</p>}
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label><span className="field-label">{label}</span>{children}</label>;
}
