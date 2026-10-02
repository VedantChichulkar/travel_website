"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { FilterSidebar, type HotelFilterValues, MobileFilterDrawer, SortControl } from "@/src/components/HotelFilters";
import { HotelCard } from "@/src/components/HotelCard";
import { HotelSearchForm } from "@/src/components/HotelSearchForm";
import { StatePanel } from "@/src/components/StatePanel";
import { hotelSearchQuery, validateHotelSearch } from "@/src/lib/hotel-search";
import { hotelService } from "@/src/services/hotel.service";
import type { Amenity, HotelSearchParams, HotelSearchResponse, HotelSort } from "@/src/types/hotel";

function withoutFilters(search: HotelSearchParams): HotelSearchParams {
  return { ...search, minPrice: undefined, maxPrice: undefined, starRating: undefined, propertyType: undefined, amenities: [], sort: "recommended" };
}

function filterCount(search: HotelSearchParams): number {
  return Number(search.minPrice !== undefined || search.maxPrice !== undefined) + Number(search.starRating !== undefined) + Number(Boolean(search.propertyType)) + search.amenities.length;
}

export function HotelResults({ search }: { search: HotelSearchParams }) {
  const router = useRouter();
  const validation = validateHotelSearch(search);
  const [result, setResult] = useState<HotelSearchResponse | null>(null);
  const [error, setError] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    if (validation) return;
    let active = true;
    void hotelService.searchHotels(search).then((data) => { if (active) setResult(data); }).catch(() => { if (active) setError(true); });
    return () => { active = false; };
  }, [search, validation, retryKey]);

  const amenityOptions = useMemo(() => {
    const items = new Map<string, Amenity>();
    result?.items.forEach((hotel) => hotel.amenities.forEach((amenity) => items.set(amenity.slug, amenity)));
    search.amenities.forEach((slug, index) => { if (!items.has(slug)) items.set(slug, { id: -(index + 1), slug, name: slug.replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()), icon: null, category: null }); });
    return [...items.values()].sort((a, b) => a.name.localeCompare(b.name));
  }, [result, search.amenities]);

  function navigate(next: HotelSearchParams) {
    router.push(`/hotels?${hotelSearchQuery(next)}`);
  }

  function applyFilters(values: HotelFilterValues) {
    navigate({ ...search, ...values });
  }

  function clearFilters() {
    navigate(withoutFilters(search));
  }

  function changeSort(sort: HotelSort) {
    navigate({ ...search, sort });
  }

  function retry() {
    setError(false);
    setResult(null);
    setRetryKey((current) => current + 1);
  }

  const filterProps = { search, amenities: amenityOptions, onApply: applyFilters, onClear: clearFilters };
  const destinationLabel = search.city || search.destination?.split("/").at(-1)?.replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()) || "Maharashtra";
  const hasDates = Boolean(search.checkIn && search.checkOut);

  return (
    <div>
      <section className="border-b border-slate-200 bg-white">
        <div className="container-shell py-8 sm:py-10">
          <p className="eyebrow">Maharashtra stays</p>
          <h1 className="page-title mt-3">Hotels in {destinationLabel}</h1>
          <p className="mt-4 text-sm font-semibold text-slate-500">{hasDates ? `${search.checkIn} to ${search.checkOut} · ${search.adults + search.children} guests · ${search.rooms} room${search.rooms === 1 ? "" : "s"}` : "Add travel dates to see live availability and dated prices."}</p>
          <div className="mt-7"><HotelSearchForm initial={search} compact /></div>
        </div>
      </section>

      <main className="container-shell py-8 sm:py-12">
        {validation ? <StatePanel title="Check your search" message={validation} /> : error ? <ErrorState onRetry={retry} /> : !result ? <ResultsSkeleton /> : <>
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <p aria-live="polite" className="text-lg font-black text-[var(--brand-strong)]">{result.total} stay{result.total === 1 ? "" : "s"} found</p>
            <div className="flex flex-1 items-center justify-end gap-2"><MobileFilterDrawer {...filterProps} activeCount={filterCount(search)} /><SortControl value={search.sort} onChange={changeSort} /></div>
          </div>
          <div className="grid items-start gap-7 lg:grid-cols-[270px_minmax(0,1fr)]">
            <FilterSidebar {...filterProps} />
            <section aria-label="Hotel search results" className="min-w-0">{result.items.length === 0 ? <EmptyState hasFilters={filterCount(search) > 0} onClear={clearFilters} /> : <div className="space-y-5">{result.items.map((hotel) => <HotelCard key={hotel.id} hotel={hotel} search={search} />)}</div>}</section>
          </div>
        </>}
      </main>
    </div>
  );
}

function EmptyState({ hasFilters, onClear }: { hasFilters: boolean; onClear: () => void }) {
  return <div className="surface-card px-6 py-12 text-center sm:px-10 sm:py-16"><span aria-hidden className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[var(--accent-soft)] text-xl text-[var(--accent-strong)]">⌕</span><h2 className="mt-5 text-2xl font-black tracking-tight text-[var(--brand-strong)]">No stays match this search</h2><p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-slate-500">Try changing your dates or destination{hasFilters ? ", or clear the active filters" : ""}.</p>{hasFilters && <button type="button" onClick={onClear} className="secondary-button mt-7">Clear filters</button>}</div>;
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return <div className="surface-card px-6 py-12 text-center sm:px-10 sm:py-16"><span aria-hidden className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-red-50 text-xl font-black text-[var(--danger)]">!</span><h2 className="mt-5 text-2xl font-black tracking-tight text-[var(--brand-strong)]">We couldn’t load these stays</h2><p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-slate-500">The hotel catalogue is temporarily unavailable. Your search is still here, so you can try again.</p><button type="button" onClick={onRetry} className="primary-button mt-7">Try again</button></div>;
}

function ResultsSkeleton() {
  return <div><div className="mb-6 flex items-center justify-between"><div className="skeleton h-6 w-32 rounded" /><div className="skeleton h-11 w-48 rounded-xl" /></div><div className="grid gap-7 lg:grid-cols-[270px_minmax(0,1fr)]"><div className="skeleton hidden h-[610px] rounded-2xl lg:block" /><div className="space-y-5">{[1, 2, 3].map((item) => <div key={item} className="grid overflow-hidden rounded-2xl border border-slate-200 bg-white md:grid-cols-[220px_1fr]"><div className="skeleton min-h-60" /><div className="p-6"><div className="skeleton h-3 w-24 rounded" /><div className="skeleton mt-4 h-8 w-2/3 rounded" /><div className="skeleton mt-3 h-4 w-1/3 rounded" /><div className="skeleton mt-8 h-9 w-full rounded" /></div></div>)}</div></div></div>;
}
