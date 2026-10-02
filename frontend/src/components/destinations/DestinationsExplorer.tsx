"use client";

import { useRouter } from "next/navigation";
import { KeyboardEvent, useEffect, useId, useMemo, useState } from "react";

import { DistrictCard } from "@/src/components/destinations/DistrictCard";
import { InterestCard } from "@/src/components/discovery/InterestCard";
import { destinationService } from "@/src/services/destination.service";
import { placeService } from "@/src/services/place.service";
import type { DestinationSearchResult, PublicDistrict } from "@/src/types/destination";
import type { PublicInterest } from "@/src/types/place";

export function DestinationsExplorer() {
  const router = useRouter();
  const listId = useId();
  const [districts, setDistricts] = useState<PublicDistrict[] | null>(null);
  const [interests, setInterests] = useState<PublicInterest[] | null>(null);
  const [interestsFailed, setInterestsFailed] = useState(false);
  const [query, setQuery] = useState("");
  const [division, setDivision] = useState("");
  const [suggestions, setSuggestions] = useState<DestinationSearchResult[]>([]);
  const [matchedSlugs, setMatchedSlugs] = useState<Set<string> | null>(null);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [searching, setSearching] = useState(false);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let active = true;
    void destinationService.listDistricts().then((response) => { if (active) setDistricts(response.items); }).catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    void placeService.listInterests().then((response) => { if (active) setInterests(response.items); }).catch(() => { if (active) setInterestsFailed(true); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (query.trim().length < 2) return;
    let active = true;
    const timer = window.setTimeout(() => {
      setSearching(true);
      void destinationService.search(query.trim(), 25, true, true).then((response) => {
        if (!active) return;
        setSuggestions(response.items);
        setMatchedSlugs(new Set(response.items.map((item) => item.kind === "DISTRICT" ? item.slug : item.district_slug).filter((slug): slug is string => Boolean(slug))));
        setActiveIndex(-1);
        setOpen(true);
      }).catch(() => {
        if (active) setSuggestions([]);
      }).finally(() => { if (active) setSearching(false); });
    }, 250);
    return () => { active = false; window.clearTimeout(timer); };
  }, [query]);

  const divisions = useMemo(() => [...new Set((districts ?? []).map((district) => district.division))].sort(), [districts]);
  const visible = useMemo(() => {
    const term = query.trim().toLocaleLowerCase("en-IN");
    return (districts ?? []).filter((district) => {
      const divisionMatch = !division || district.division === division;
      if (!term) return divisionMatch;
      if (term.length < 2 || !matchedSlugs) return divisionMatch && `${district.name} ${district.division}`.toLocaleLowerCase("en-IN").includes(term);
      return divisionMatch && matchedSlugs.has(district.slug);
    });
  }, [districts, division, matchedSlugs, query]);

  function clear() {
    setQuery(""); setDivision(""); setSuggestions([]); setMatchedSlugs(null); setOpen(false); setSearching(false);
  }

  function choose(item: DestinationSearchResult) {
    setOpen(false);
    router.push(item.path);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!open || suggestions.length === 0) return;
    if (event.key === "ArrowDown") { event.preventDefault(); setActiveIndex((value) => Math.min(value + 1, suggestions.length - 1)); }
    if (event.key === "ArrowUp") { event.preventDefault(); setActiveIndex((value) => Math.max(value - 1, 0)); }
    if (event.key === "Escape") setOpen(false);
    if (event.key === "Enter" && activeIndex >= 0) { event.preventDefault(); choose(suggestions[activeIndex]); }
  }

  if (failed) return <section className="container-shell py-16"><State title="We couldn’t load Maharashtra’s districts" detail="The destination service is temporarily unavailable. Please try again later." /></section>;

  return (
    <>
      <section className="border-b border-[var(--line)] bg-white">
        <div className="container-shell py-14 sm:py-18">
          <p className="eyebrow">Maharashtra destinations</p>
          <h1 className="page-title mt-3">Explore Maharashtra</h1>
          <p className="body-lead mt-5 max-w-2xl">Browse active districts and places using Maharashtra Tourist Places’ destination directory.</p>
          <div className="mt-8 grid gap-3 rounded-2xl border border-[var(--line)] bg-[var(--surface-muted)] p-4 md:grid-cols-[minmax(0,1fr)_minmax(13rem,.4fr)_auto]">
            <div className="relative">
              <label htmlFor={`${listId}-search`} className="field-label">Search Maharashtra</label>
              <input id={`${listId}-search`} type="search" role="combobox" aria-expanded={open} aria-controls={listId} aria-autocomplete="list" aria-activedescendant={activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined} value={query} onChange={(event) => { const value = event.target.value; setQuery(value); setMatchedSlugs(null); setSuggestions([]); setSearching(value.trim().length >= 2); setOpen(value.trim().length >= 2); }} onFocus={() => { if (suggestions.length) setOpen(true); }} onKeyDown={onKeyDown} className="field-input" placeholder="Try Nagpur, Pune or Chandrapur" />
              {open && query.trim().length >= 2 && <div id={listId} role="listbox" className="absolute left-0 right-0 top-full z-40 mt-2 max-h-72 overflow-y-auto rounded-xl border border-[var(--line)] bg-white p-1.5 shadow-[var(--shadow-lg)]">
                {searching && <p className="px-3 py-3 text-sm text-slate-500">Searching destinations…</p>}
                {!searching && suggestions.length === 0 && <p className="px-3 py-3 text-sm text-slate-500">No matching district, place or story found.</p>}
                {suggestions.map((item, index) => <button key={`${item.kind}-${item.path}`} id={`${listId}-${index}`} type="button" role="option" aria-selected={activeIndex === index} onMouseDown={(event) => event.preventDefault()} onClick={() => choose(item)} className={`flex w-full items-center justify-between gap-4 rounded-lg px-3 py-2.5 text-left ${activeIndex === index ? "bg-[var(--accent-soft)]" : "hover:bg-[var(--surface-muted)]"}`}><span><strong className="block text-sm text-[var(--brand)]">{item.name}</strong>{item.district_name && <span className="text-xs text-slate-500">{item.district_name} district</span>}</span><span className="text-[10px] font-black uppercase tracking-wider text-slate-400">{item.kind === "DISTRICT" ? "District" : item.kind === "DESTINATION" ? "Destination" : item.kind === "PLACE" ? "Place" : "Story"}</span></button>)}
              </div>}
            </div>
            <label><span className="field-label">Division</span><select value={division} onChange={(event) => setDivision(event.target.value)} className="field-input"><option value="">All divisions</option>{divisions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
            <button type="button" onClick={clear} disabled={!query && !division} className="secondary-button self-end">Clear filters</button>
          </div>
        </div>
      </section>
      <main>
        <section id="explore-by-interest" className="scroll-mt-20 border-b border-[#e5dfd4] bg-[#faf8f3] py-16 sm:py-24" aria-labelledby="interest-heading">
          <div className="container-shell">
            <div className="max-w-3xl"><p className="eyebrow">Explore Maharashtra by interest</p><h2 id="interest-heading" className="section-title mt-3 text-balance">Follow what draws you here.</h2><p className="body-lead mt-4">From ancient caves and hill forts to sacred places, wildlife and the Konkan coast—discover Maharashtra through what interests you.</p></div>
            {interestsFailed ? <div className="mt-9"><State title="Interest discovery is temporarily unavailable" detail="The complete district directory remains available below while the interest service reconnects." /></div> : !interests ? <InterestSkeleton /> : interests.length > 0 ? <div className="mt-10 grid auto-rows-fr gap-4 md:grid-cols-2 xl:grid-cols-12">{interests.map((interest, index) => <div key={interest.slug} className={index === 0 ? "xl:col-span-7 xl:row-span-2" : index === 1 || index === 2 ? "xl:col-span-5" : "xl:col-span-4"}><InterestCard interest={interest} featured={index === 0} preload={index === 0} /></div>)}</div> : <div className="mt-9"><State title="No interests are available yet" detail="Browse Maharashtra through its 36 districts while interest-led discovery is being prepared." /></div>}
          </div>
        </section>

        <section id="district-directory" className="scroll-mt-20 bg-[var(--canvas)] py-12 sm:py-18" aria-labelledby="district-directory-title">
          <div className="container-shell">
            <div className="mb-8 max-w-2xl"><p className="eyebrow">Explore by location</p><h2 id="district-directory-title" className="section-title mt-3">All Maharashtra districts</h2><p className="body-lead mt-4">Start with a district, then continue into its destinations, published places, stays and Safari discovery.</p></div>
            {!districts ? <DistrictSkeleton /> : <>
              <div className="mb-7 flex flex-wrap items-center justify-between gap-3"><p aria-live="polite" className="font-bold text-[var(--brand)]">{visible.length} district{visible.length === 1 ? "" : "s"}</p><p className="text-sm text-slate-500">{districts.length} active districts in the directory</p></div>
              {visible.length ? <div className="grid auto-rows-fr gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{visible.map((district) => <DistrictCard key={district.slug} district={district} />)}</div> : <State title="No districts match these filters" detail="Clear the search or choose another division to see more districts." action={<button type="button" onClick={clear} className="primary-button mt-6">Clear filters</button>} />}
            </>}
          </div>
        </section>
      </main>
    </>
  );
}

function DistrictSkeleton() {
  return <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" aria-label="Loading districts">{Array.from({ length: 8 }, (_, index) => <div key={index} className="skeleton h-80 rounded-2xl" />)}</div>;
}

function InterestSkeleton() {
  return <div className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="Loading interests">{Array.from({ length: 6 }, (_, index) => <div key={index} className="skeleton h-80 rounded-[1.35rem]" />)}</div>;
}

function State({ title, detail, action }: { title: string; detail: string; action?: React.ReactNode }) {
  return <div className="surface-card px-6 py-12 text-center"><h2 className="text-xl font-black text-[var(--brand)]">{title}</h2><p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-500">{detail}</p>{action}</div>;
}
