"use client";

import { FormEvent, useEffect, useState } from "react";

import type { Amenity, HotelSearchParams, HotelSort, PropertyType } from "@/src/types/hotel";
import { PROPERTY_TYPES } from "@/src/types/hotel";

export interface HotelFilterValues {
  minPrice?: number;
  maxPrice?: number;
  starRating?: number;
  propertyType?: PropertyType;
  amenities: string[];
}

interface FilterProps {
  search: HotelSearchParams;
  amenities: Amenity[];
  onApply: (values: HotelFilterValues) => void;
  onClear: () => void;
}

export function FilterSidebar(props: FilterProps) {
  return <aside aria-label="Hotel filters" className="sticky top-24 hidden lg:block"><FilterForm {...props} /></aside>;
}

export function MobileFilterDrawer(props: FilterProps & { activeCount: number }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  function apply(values: HotelFilterValues) {
    props.onApply(values);
    setOpen(false);
  }

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className="secondary-button !min-h-11 lg:hidden" aria-haspopup="dialog">
        Filters{props.activeCount > 0 && <span className="grid h-5 min-w-5 place-items-center rounded-full bg-[var(--brand)] px-1 text-[10px] text-white">{props.activeCount}</span>}
      </button>
      {open && <div className="fixed inset-0 z-[80] lg:hidden"><button type="button" aria-label="Close filters" onClick={() => setOpen(false)} className="absolute inset-0 bg-slate-950/45 backdrop-blur-[2px]" /><section role="dialog" aria-modal="true" aria-labelledby="mobile-filter-title" className="absolute inset-y-0 right-0 w-[min(92vw,24rem)] overflow-y-auto bg-[var(--canvas)] p-4 shadow-2xl"><div className="mb-4 flex items-center justify-between"><h2 id="mobile-filter-title" className="text-xl font-black text-[var(--brand-strong)]">Filters</h2><button type="button" onClick={() => setOpen(false)} aria-label="Close filters" className="grid h-11 w-11 place-items-center rounded-xl border border-slate-200 bg-white text-xl text-[var(--brand)]">×</button></div><FilterForm {...props} onApply={apply} compact /></section></div>}
    </>
  );
}

export function SortControl({ value, onChange }: { value: HotelSort; onChange: (sort: HotelSort) => void }) {
  return <label className="flex items-center gap-2"><span className="hidden text-sm font-bold text-slate-500 sm:inline">Sort by</span><select aria-label="Sort stays" value={value} onChange={(event) => onChange(event.target.value as HotelSort)} className="field-input !min-h-11 min-w-44 !py-2"><option value="recommended">Recommended</option><option value="price_asc">Price: Low to High</option><option value="price_desc">Price: High to Low</option><option value="rating">Property classification</option></select></label>;
}

function FilterForm({ search, amenities, onApply, onClear, compact = false }: FilterProps & { compact?: boolean }) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const min = String(form.get("minPrice") ?? "");
    const max = String(form.get("maxPrice") ?? "");
    const rating = String(form.get("starRating") ?? "");
    const property = String(form.get("propertyType") ?? "");
    onApply({ minPrice: min ? Number(min) : undefined, maxPrice: max ? Number(max) : undefined, starRating: rating ? Number(rating) : undefined, propertyType: property ? property as PropertyType : undefined, amenities: form.getAll("amenities").map(String) });
  }

  return (
    <form onSubmit={submit} className={compact ? "rounded-2xl border border-slate-200 bg-white p-5" : "surface-card p-5"}>
      {!compact && <div className="flex items-center justify-between"><h2 className="text-lg font-black text-[var(--brand-strong)]">Filter stays</h2><span className="text-xs font-bold text-slate-400">Live results</span></div>}
      <fieldset className={compact ? "" : "mt-6"}><legend className="field-label">Price per night</legend><div className="grid grid-cols-2 gap-2"><label><span className="mb-1.5 block text-xs font-bold text-slate-500">Minimum</span><input aria-label="Minimum price" name="minPrice" type="number" min={0} defaultValue={search.minPrice ?? ""} placeholder="₹ Min" className="field-input" /></label><label><span className="mb-1.5 block text-xs font-bold text-slate-500">Maximum</span><input aria-label="Maximum price" name="maxPrice" type="number" min={0} defaultValue={search.maxPrice ?? ""} placeholder="₹ Max" className="field-input" /></label></div></fieldset>
      <fieldset className="mt-6"><legend className="field-label">Property classification</legend><div className="grid grid-cols-2 gap-2">{[{ label: "Any", value: "" }, { label: "3+ stars", value: "3" }, { label: "4+ stars", value: "4" }, { label: "5 stars", value: "5" }].map((option) => <label key={option.value || "any"} className="flex cursor-pointer items-center gap-2 rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-bold text-slate-600"><input type="radio" name="starRating" value={option.value} defaultChecked={String(search.starRating ?? "") === option.value} className="accent-[var(--accent)]" />{option.label}</label>)}</div></fieldset>
      <label className="mt-6 block"><span className="field-label">Property type</span><select name="propertyType" defaultValue={search.propertyType ?? ""} className="field-input"><option value="">All property types</option>{PROPERTY_TYPES.map((type) => <option key={type} value={type}>{type[0] + type.slice(1).toLowerCase()}</option>)}</select></label>
      <fieldset className="mt-6"><legend className="field-label">Amenities</legend>{amenities.length > 0 ? <div className="space-y-2.5">{amenities.map((amenity) => <label key={amenity.slug} className="flex cursor-pointer items-center gap-2.5 text-sm text-slate-600"><input name="amenities" value={amenity.slug} type="checkbox" defaultChecked={search.amenities.includes(amenity.slug)} className="h-4 w-4 accent-[var(--accent)]" />{amenity.name}</label>)}</div> : <p className="text-sm leading-6 text-slate-500">Amenity choices will appear when matching stays provide them.</p>}</fieldset>
      <div className="mt-7 grid gap-2"><button type="submit" className="primary-button w-full">Apply filters</button><button type="button" onClick={onClear} className="secondary-button w-full">Clear filters</button></div>
    </form>
  );
}
