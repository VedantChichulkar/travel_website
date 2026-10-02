"use client";

import Image from "next/image";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { SafariArtwork } from "@/src/components/safari/SafariArtwork";
import { SafariCard } from "@/src/components/safari/SafariCard";
import { SAFARI_IMAGES } from "@/src/lib/safari-images";
import { safariService } from "@/src/services/safari.service";
import type { Safari } from "@/src/types/safari";

const trust = ["Managed Safari Assistance", "Secure Booking Process", "Customer Support", "Responsible Travel"];
const process = ["Choose Safari", "Request Availability", "Maharashtra Tourist Places Checks Availability", "Traveller Details", "Payment", "Official Booking Processing", "Confirmation & Permit"];
const landscapeStories = [
  { label: "Big cats", detail: "Tiger and leopard habitat across layered forest.", image: SAFARI_IMAGES.leopard, alt: "Leopard in a rocky forest habitat" },
  { label: "Deer & gaur", detail: "Wildlife shaped by grassland, woodland and water.", image: SAFARI_IMAGES.deer, alt: "Chital deer in a forest clearing" },
  { label: "Birdlife", detail: "Wetlands and forest canopy reward patient observation.", image: SAFARI_IMAGES.birdlife, alt: "Peacock beside a forest wetland" },
  { label: "Living landscapes", detail: "Rock, water, bamboo and changing seasonal light.", image: SAFARI_IMAGES.wildlifeStory, alt: "Layered forest and rocky woodland" },
];

function today() {
  const value = new Date();
  return new Date(value.getTime() - value.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

function Skeleton() {
  return <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3" aria-label="Loading supported Safaris">{[1, 2, 3].map((item) => <div key={item} className="h-[29rem] animate-pulse rounded-[1.5rem] bg-white/80" />)}</div>;
}

export function SafariCatalog() {
  const router = useRouter();
  const [items, setItems] = useState<Safari[]>([]);
  const [selected, setSelected] = useState("");
  const [date, setDate] = useState("");
  const [visitors, setVisitors] = useState(2);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true); setError("");
    try { const result = await safariService.list(); setItems(result); setSelected((current) => current || result[0]?.slug || ""); }
    catch { setError("The Safari catalogue is temporarily unavailable. Please try again."); }
    finally { setLoading(false); }
  }
  useEffect(() => { queueMicrotask(() => { void load(); }); }, []);

  function explore(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) { document.querySelector("#wildlife-destinations")?.scrollIntoView({ behavior: "smooth" }); return; }
    const params = new URLSearchParams();
    if (date) params.set("date", date);
    params.set("visitors", String(visitors));
    router.push(`/safaris/${selected}?${params.toString()}#availability-request`);
  }

  return <main className="overflow-hidden bg-[#f7f5ef] text-[#173326]">
    <header className="relative isolate bg-[#10251c] text-white sm:min-h-[50rem]">
      <SafariArtwork variant="hero" priority className="w-full" alt="A tiger walking through a forest habitat at dawn" />
      <div className="absolute inset-0 bg-gradient-to-r from-[#07140e]/95 via-[#07140e]/65 to-transparent" aria-hidden="true" />
      <div className="absolute inset-0 bg-gradient-to-t from-[#07140e] via-transparent to-black/20" aria-hidden="true" />
      <div className="container-shell relative flex min-h-[38rem] flex-col justify-end pb-10 pt-24 sm:min-h-[50rem] sm:pb-44 sm:pt-28 lg:justify-center lg:pb-32">
        <p className="text-xs font-black uppercase tracking-[.26em] text-[#e6b675]">Wildlife Safaris in Maharashtra</p>
        <h1 className="mt-5 max-w-3xl font-serif text-6xl font-semibold leading-[.92] tracking-[-.045em] sm:text-7xl lg:text-8xl">Into the Wild</h1>
        <p className="mt-6 max-w-2xl text-base leading-7 text-white/80 sm:text-lg">Explore Maharashtra&apos;s forests, tiger reserves and extraordinary wildlife through Maharashtra Tourist Places&apos; managed Safari experience.</p>
        <a href="#wildlife-destinations" className="mt-8 inline-flex min-h-12 w-fit items-center rounded-full bg-[#d9783f] px-6 text-sm font-black text-white transition hover:bg-[#ed8c51] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white">Explore Safaris <span aria-hidden className="ml-2">↓</span></a>
      </div>
      <form onSubmit={explore} className="container-shell relative z-10 pb-6 sm:absolute sm:inset-x-0 sm:bottom-0 sm:translate-y-1/2 sm:pb-0" aria-label="Explore supported Safaris">
        <div className="grid grid-cols-2 gap-3 rounded-[1.5rem] border border-white/50 bg-white p-4 text-[#173326] shadow-[0_24px_80px_rgba(0,0,0,.25)] sm:p-5 lg:grid-cols-[1.5fr_1fr_.7fr_auto] lg:items-end">
          <label className="col-span-2 text-[11px] font-black uppercase tracking-[.14em] text-[#58705f] sm:col-span-1">Safari / Tiger Reserve<select value={selected} onChange={(event) => setSelected(event.target.value)} className="mt-2 block min-h-12 w-full rounded-xl border border-[#dce5dd] bg-[#f8faf8] px-4 text-sm font-bold outline-none focus:border-[#2e6a49] focus:ring-2 focus:ring-[#2e6a49]/20"><option value="">View all Safaris</option>{items.map((item) => <option key={item.id} value={item.slug}>{item.name}</option>)}</select></label>
          <label className="text-[11px] font-black uppercase tracking-[.14em] text-[#58705f]">Preferred date<input type="date" min={today()} value={date} onChange={(event) => setDate(event.target.value)} className="mt-2 block min-h-12 w-full rounded-xl border border-[#dce5dd] bg-[#f8faf8] px-4 text-sm font-bold outline-none focus:border-[#2e6a49] focus:ring-2 focus:ring-[#2e6a49]/20" /></label>
          <label className="text-[11px] font-black uppercase tracking-[.14em] text-[#58705f]">Visitors<input type="number" min={1} max={20} value={visitors} onChange={(event) => setVisitors(Number(event.target.value))} className="mt-2 block min-h-12 w-full rounded-xl border border-[#dce5dd] bg-[#f8faf8] px-4 text-sm font-bold outline-none focus:border-[#2e6a49] focus:ring-2 focus:ring-[#2e6a49]/20" /></label>
          <button className="col-span-2 min-h-12 rounded-xl bg-[#1f5b3a] px-7 text-sm font-black text-white transition hover:bg-[#173f2b] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1f5b3a] sm:col-span-1">{selected ? "Check Availability" : "Explore Safaris"}</button>
        </div>
      </form>
    </header>

    <section className="border-b border-[#dce5dd] bg-white sm:pt-28" aria-label="Safari service principles"><div className="container-shell grid grid-cols-2 divide-x divide-y divide-[#e5ebe6] border-x border-t border-[#e5ebe6] md:grid-cols-4 md:divide-y-0">{trust.map((item) => <div key={item} className="flex min-h-24 items-center justify-center px-4 text-center text-xs font-black uppercase tracking-[.12em] text-[#46604f]">{item}</div>)}</div></section>

    <section id="wildlife-destinations" className="container-shell scroll-mt-24 py-20 sm:py-28" aria-labelledby="wildlife-heading"><div className="max-w-3xl"><p className="text-xs font-black uppercase tracking-[.2em] text-[#a8532b]">Choose your Safari</p><h2 id="wildlife-heading" className="mt-4 font-serif text-4xl font-semibold tracking-tight sm:text-5xl">Explore Maharashtra&apos;s Wildlife Destinations</h2><p className="mt-5 max-w-2xl leading-7 text-slate-600">Browse the active Safari catalogue. Dates and permits are checked only after you send a request.</p></div><div className="mt-10">{loading ? <Skeleton /> : error ? <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center"><p className="font-bold text-red-800">We could not load supported Safaris.</p><p className="mt-2 text-sm text-red-700">{error}</p><button type="button" onClick={() => void load()} className="secondary-button mt-5">Try again</button></div> : items.length ? <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">{items.map((item) => <SafariCard key={item.id} safari={item} />)}</div> : <div className="rounded-[1.5rem] border border-[#dce5dd] bg-white p-10 text-center"><p className="text-xl font-black">No Safari destinations are available for requests right now.</p><p className="mt-3 text-sm text-slate-500">Published options will appear here when Maharashtra Tourist Places operations enables them.</p></div>}</div></section>

    <section className="bg-[#f1ede3] py-20 sm:py-28" aria-labelledby="biodiversity-heading">
      <div className="container-shell grid gap-12 lg:grid-cols-[.78fr_1.22fr] lg:items-center lg:gap-16">
        <div className="max-w-xl">
          <p className="text-xs font-black uppercase tracking-[.22em] text-[#a8532b]">The wider forest</p>
          <h2 id="biodiversity-heading" className="mt-5 font-serif text-5xl font-semibold leading-[.98] tracking-[-.035em] sm:text-6xl">More Than Just Tigers</h2>
          <p className="mt-6 text-base leading-8 text-slate-600 sm:text-lg">Maharashtra&apos;s wild places are layered with deer, gaur, birdlife, wetlands and quiet woodland. A thoughtful Safari notices the whole habitat—not only a single species.</p>
          <p className="mt-8 border-l-2 border-[#c87943] pl-5 text-sm leading-7 text-slate-500">Editorial photography represents the wider wildlife experience and never guarantees a sighting.</p>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:h-[38rem] lg:grid-cols-[1.25fr_.75fr] lg:grid-rows-2">
          <figure className="group relative col-span-2 min-h-80 overflow-hidden rounded-[1.5rem] bg-[#dce5dd] lg:col-span-1 lg:row-span-2 lg:min-h-0">
            <Image src={SAFARI_IMAGES.hero} alt="Tiger in a representative forest habitat" fill sizes="(max-width: 1024px) 100vw, 44vw" className="object-cover object-[82%_center] transition duration-700 group-hover:scale-[1.025] motion-reduce:transition-none" />
            <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-transparent to-transparent" aria-hidden="true" />
            <figcaption className="absolute bottom-5 left-5 text-xs font-black uppercase tracking-[.16em] text-white">Tiger</figcaption>
          </figure>
          <figure className="group relative aspect-[4/3] overflow-hidden rounded-[1.25rem] bg-[#dce5dd] lg:aspect-auto">
            <Image src={SAFARI_IMAGES.deer} alt="Chital deer in a representative forest clearing" fill sizes="(max-width: 1024px) 50vw, 24vw" className="object-cover transition duration-700 group-hover:scale-[1.035] motion-reduce:transition-none" />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" aria-hidden="true" />
            <figcaption className="absolute bottom-4 left-4 text-xs font-black uppercase tracking-[.14em] text-white">Deer</figcaption>
          </figure>
          <figure className="group relative aspect-[4/3] overflow-hidden rounded-[1.25rem] bg-[#dce5dd] lg:aspect-auto">
            <Image src={SAFARI_IMAGES.leopard} alt="Leopard in a representative rocky forest habitat" fill sizes="(max-width: 1024px) 50vw, 24vw" className="object-cover transition duration-700 group-hover:scale-[1.035] motion-reduce:transition-none" />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" aria-hidden="true" />
            <figcaption className="absolute bottom-4 left-4 text-xs font-black uppercase tracking-[.14em] text-white">Leopard</figcaption>
          </figure>
        </div>
      </div>
    </section>

    <section className="relative isolate min-h-[30rem] overflow-hidden bg-[#263d2e] text-white sm:min-h-[34rem]" aria-labelledby="journey-heading">
      <Image src={SAFARI_IMAGES.safariJourney} alt="Safari vehicle entering a forest and grassland landscape" fill sizes="100vw" className="object-cover object-[63%_center] sm:object-center" />
      <div className="absolute inset-0 bg-gradient-to-r from-[#07140e]/76 via-[#07140e]/25 to-transparent" aria-hidden="true" />
      <div className="container-shell relative flex min-h-[30rem] items-end py-14 sm:min-h-[34rem] sm:items-center sm:py-20">
        <div className="max-w-lg"><p className="text-xs font-black uppercase tracking-[.22em] text-[#f0ba73]">The journey</p><h2 id="journey-heading" className="mt-4 font-serif text-4xl font-semibold leading-tight sm:text-5xl">Into Maharashtra&apos;s Wild</h2><p className="mt-4 max-w-md text-sm leading-7 text-white/75">The experience begins before the first sighting—with changing light, quiet tracks and the forest opening ahead.</p></div>
      </div>
    </section>

    <section className="container-shell py-20 sm:py-28" aria-labelledby="process-heading"><div className="text-center"><p className="text-xs font-black uppercase tracking-[.2em] text-[#a8532b]">Clear from the start</p><h2 id="process-heading" className="mt-4 font-serif text-4xl font-semibold sm:text-5xl">Plan Your Safari</h2><p className="mx-auto mt-5 max-w-2xl leading-7 text-slate-600">Safari availability is manually checked. Payment never means automatic confirmation.</p></div><ol className="relative mt-12 grid gap-4 md:grid-cols-7">{process.map((step, index) => <li key={step} className="relative flex gap-4 rounded-2xl border border-[#dce5dd] bg-white p-5 md:block md:border-0 md:bg-transparent md:p-0 md:text-center"><span className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#1f5b3a] text-sm font-black text-white md:mx-auto">{index + 1}</span><p className="pt-2 text-sm font-bold leading-5 text-[#31483a] md:mt-3 md:pt-0">{step}</p>{index < process.length - 1 && <span className="absolute left-1/2 top-5 hidden h-px w-full bg-[#b9c9bd] md:block" aria-hidden="true" />}</li>)}</ol></section>

    <section className="border-y border-[#dce5dd] bg-white py-20 sm:py-28" aria-labelledby="wildlife-strip-heading">
      <div className="container-shell">
        <div className="grid gap-10 lg:grid-cols-[1.15fr_.85fr] lg:items-center lg:gap-16">
          <div className="relative aspect-[16/11] overflow-hidden rounded-[1.5rem] bg-[#dce5dd] sm:aspect-[16/9] lg:aspect-[4/3]">
            <Image src={SAFARI_IMAGES.biodiversity} alt="Chital deer beside a misty forest wetland" fill sizes="(max-width: 1024px) 100vw, 56vw" className="object-cover object-[68%_center]" />
          </div>
          <div className="max-w-xl"><p className="text-xs font-black uppercase tracking-[.22em] text-[#a8532b]">Wild Maharashtra</p><h2 id="wildlife-strip-heading" className="mt-4 font-serif text-4xl font-semibold leading-tight sm:text-5xl">Life across the landscape</h2><p className="mt-6 text-base leading-8 text-slate-600">Look beyond a single sighting. Forest texture, water, movement and changing light are all part of the experience.</p></div>
        </div>
        <div className="mt-12 grid gap-x-5 gap-y-9 sm:grid-cols-2 lg:grid-cols-4">{landscapeStories.map((item) => <article key={item.label} className="group"><div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-[#dce5dd]"><Image src={item.image} alt={item.alt} fill sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw" className="object-cover transition duration-700 group-hover:scale-[1.035] motion-reduce:transition-none" /></div><h3 className="mt-5 font-serif text-2xl font-semibold text-[#173326]">{item.label}</h3><p className="mt-2 text-sm leading-6 text-slate-500">{item.detail}</p></article>)}</div>
      </div>
    </section>

    <section className="relative isolate overflow-hidden bg-[#07140e] py-24 text-white sm:py-32" aria-labelledby="responsible-heading"><Image src={SAFARI_IMAGES.leopard} alt="" fill sizes="100vw" className="object-cover opacity-20" /><div className="absolute inset-0 bg-gradient-to-r from-[#07140e] via-[#07140e]/90 to-[#07140e]/60" /><div className="container-shell relative"><p className="text-xs font-black uppercase tracking-[.2em] text-[#e6b675]">Leave only footprints</p><h2 id="responsible-heading" className="mt-4 font-serif text-5xl font-semibold sm:text-6xl">Travel Responsibly</h2><div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{["Respect Wildlife", "Follow Park Rules", "Keep the Forest Clean", "Support Conservation"].map((item, index) => <div key={item} className="rounded-2xl border border-white/15 bg-white/5 p-6 backdrop-blur-sm"><span className="text-sm font-black text-[#e6b675]">0{index + 1}</span><h3 className="mt-4 text-lg font-black">{item}</h3></div>)}</div><Link href="#wildlife-destinations" className="mt-10 inline-flex min-h-12 items-center rounded-full bg-white px-6 text-sm font-black text-[#173326] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white">Choose a Safari <span aria-hidden className="ml-2">↑</span></Link></div></section>
  </main>;
}
