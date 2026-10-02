"use client";

import Image from "next/image";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { SafariArtwork } from "@/src/components/safari/SafariArtwork";
import { useAuth } from "@/src/context/AuthContext";
import { isCustomerRole } from "@/src/lib/portal-routing";
import { authPathWithNext } from "@/src/lib/safe-next";
import { SAFARI_IMAGES } from "@/src/lib/safari-images";
import { safariStatusClasses, safariStatusDisplay } from "@/src/lib/safari-status";
import { safariService } from "@/src/services/safari.service";
import { ApiError } from "@/src/services/api";
import type { Safari, SafariRequest } from "@/src/types/safari";

function todayInputValue() {
  const value = new Date(); const offset = value.getTimezoneOffset() * 60_000;
  return new Date(value.getTime() - offset).toISOString().slice(0, 10);
}

const steps = ["Choose Safari", "Request Availability", "Maharashtra Tourist Places Checks Availability", "Complete Traveller Details", "Payment", "Official Booking Processing", "Confirmation & Permit"];

function requestErrorMessage(cause: unknown) {
  if (cause instanceof ApiError && cause.status === 401) return "Your session has expired. Sign in again to check availability.";
  if (cause instanceof ApiError && cause.status === 409) return "That preference is no longer available. Review the options and try another date or selection.";
  if (cause instanceof ApiError && (cause.status === 400 || cause.status === 422)) return "Review the highlighted preferences and try again.";
  return "We could not send this availability check right now. Your selections remain in the form so you can try again.";
}

export function SafariDetailView({ safari }: { safari: Safari }) {
  const searchParams = useSearchParams();
  const { loading: authLoading, user } = useAuth();
  const requestedDate = searchParams.get("date") || "";
  const requestedVisitors = Number(searchParams.get("visitors"));
  const [date, setDate] = useState(requestedDate >= todayInputValue() ? requestedDate : "");
  const [shift, setShift] = useState("");
  const [visitors, setVisitors] = useState(Number.isInteger(requestedVisitors) && requestedVisitors >= 1 && requestedVisitors <= 20 ? requestedVisitors : 1);
  const [alternate, setAlternate] = useState("");
  const [bookingCategory, setBookingCategory] = useState("");
  const [vehicleOption, setVehicleOption] = useState("");
  const [created, setCreated] = useState<SafariRequest>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [mobileCtaVisible, setMobileCtaVisible] = useState(true);
  const customer = user && isCustomerRole(user.role);
  const location = safari.destination_name || safari.district_name;
  const hotelHref = safari.hotel_destination_filter ? `/hotels?destination=${encodeURIComponent(safari.hotel_destination_filter)}` : undefined;
  const information = [
    { title: "Booking categories", values: safari.booking_categories.map(optionLabel) },
    { title: "Safari shifts", values: safari.shifts },
    { title: "Vehicle options", values: safari.vehicle_options.map(optionLabel) },
    { title: "Zones", values: safari.zones },
    { title: "Gates", values: safari.gates },
  ].filter((group) => group.values.length > 0);
  const returnParams = new URLSearchParams();
  if (date) returnParams.set("date", date);
  returnParams.set("visitors", String(visitors));
  const returnTo = `/safaris/${safari.slug}?${returnParams.toString()}#availability-request`;

  useEffect(() => {
    const targets = [document.querySelector("#availability-request"), document.querySelector("#responsible-detail-section")].filter((target): target is Element => Boolean(target));
    const visibility = new Map<Element, boolean>();
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => visibility.set(entry.target, entry.isIntersecting));
      setMobileCtaVisible(![...visibility.values()].some(Boolean));
    }, { threshold: 0.08 });
    targets.forEach((target) => observer.observe(target));
    return () => observer.disconnect();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setBusy(true);
    try { setCreated(await safariService.request(safari.slug, { preferred_date: date, preferred_shift: shift || undefined, preferred_booking_category: bookingCategory || undefined, preferred_vehicle_option: vehicleOption || undefined, visitor_count: visitors, alternate_preference: alternate.trim() || undefined })); }
    catch (cause) { setError(requestErrorMessage(cause)); }
    finally { setBusy(false); }
  }

  return <main className="overflow-hidden bg-[#f7f5ef] pb-20 text-[#173326] lg:pb-0">
    <header className="relative isolate min-h-[42rem] bg-[#10251c] text-white sm:min-h-[46rem]">
      <SafariArtwork safari={safari} variant="hero" priority className="w-full" alt={`${safari.name} — representative Maharashtra wildlife and forest landscape`} />
      <div className="absolute inset-0 bg-gradient-to-r from-[#07140e]/95 via-[#07140e]/60 to-black/10" aria-hidden="true" />
      <div className="absolute inset-0 bg-gradient-to-t from-[#07140e]/90 via-transparent to-black/35" aria-hidden="true" />
      <div className="container-shell relative flex min-h-[42rem] flex-col justify-between pb-14 pt-8 sm:min-h-[46rem] sm:pb-20">
        <Link href="/safaris" className="w-fit rounded-full border border-white/25 bg-black/20 px-4 py-2 text-sm font-black text-white backdrop-blur-sm outline-offset-4 hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-white">← All Safaris</Link>
        <div className="max-w-3xl">{location && <p className="text-xs font-black uppercase tracking-[.22em] text-[#e6b675]">{location}{safari.destination_name && safari.district_name ? ` · ${safari.district_name}` : ""}</p>}<h1 className="mt-4 font-serif text-5xl font-semibold leading-[.96] tracking-[-.04em] sm:text-7xl">{safari.name}</h1><p className="mt-6 max-w-2xl text-base leading-8 text-white/80 sm:text-lg">{safari.short_description}</p><div className="mt-8 flex flex-wrap gap-3"><a href="#availability-request" className="inline-flex min-h-12 items-center rounded-full bg-[#d9783f] px-6 text-sm font-black text-white hover:bg-[#ed8c51] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white">Check Availability</a>{safari.destination_path && <Link href={safari.destination_path} className="inline-flex min-h-12 items-center rounded-full border border-white/30 bg-white/10 px-6 text-sm font-black text-white backdrop-blur-sm hover:bg-white/20">Explore Destination</Link>}</div><p className="mt-4 text-xs leading-5 text-white/60">A request starts a manual availability check. It does not reserve a permit or guarantee a sighting.</p></div>
      </div>
    </header>

    <section className="border-b border-[#dce5dd] bg-white" aria-label="Safari booking principles"><div className="container-shell grid grid-cols-2 divide-x divide-y divide-[#e5ebe6] md:grid-cols-4 md:divide-y-0">{["Managed availability", "Configured options", "Secure traveller details", "Permit in your account"].map((item) => <div key={item} className="flex min-h-20 items-center justify-center px-4 text-center text-[11px] font-black uppercase tracking-[.12em] text-[#4b6553]">{item}</div>)}</div></section>

    <div className="container-shell grid gap-12 py-20 lg:grid-cols-[1fr_.72fr] lg:items-start lg:py-28">
      <div className="space-y-20">
        <section aria-labelledby="overview-heading"><p className="text-xs font-black uppercase tracking-[.18em] text-[#a8532b]">Overview</p><h2 id="overview-heading" className="mt-4 font-serif text-4xl font-semibold sm:text-5xl">A considered way into the forest</h2><p className="mt-6 max-w-3xl text-base leading-8 text-slate-600">{safari.short_description}</p>{safari.last_verified_at && <p className="mt-5 text-xs font-bold uppercase tracking-[.12em] text-slate-400">Configuration last verified {new Date(safari.last_verified_at).toLocaleDateString()}</p>}</section>

        {information.length > 0 && <section aria-labelledby="safari-information"><p className="text-xs font-black uppercase tracking-[.18em] text-[#a8532b]">Safari information</p><h2 id="safari-information" className="mt-4 font-serif text-4xl font-semibold sm:text-5xl">Your configured options</h2><p className="mt-5 max-w-2xl leading-7 text-slate-600">Only options currently configured for this Safari are shown. Final details are confirmed through the managed workflow.</p><div className="mt-8 grid gap-4 sm:grid-cols-2">{information.map((group) => <InfoList key={group.title} title={group.title} values={group.values} />)}</div></section>}

        <section className="group relative min-h-[28rem] overflow-hidden rounded-[2rem] text-white" aria-labelledby="landscape-heading"><Image src={SAFARI_IMAGES.deer} alt="Spotted deer in a representative forest clearing" fill sizes="(max-width: 1024px) 100vw, 65vw" className="object-cover transition duration-700 group-hover:scale-[1.02] motion-reduce:transition-none" /><div className="absolute inset-0 bg-gradient-to-t from-[#07140e]/95 via-[#07140e]/25 to-transparent" /><div className="absolute inset-x-0 bottom-0 p-7 sm:p-10"><p className="text-xs font-black uppercase tracking-[.18em] text-[#e6b675]">Wildlife & landscape</p><h2 id="landscape-heading" className="mt-3 font-serif text-4xl font-semibold">Notice the whole habitat</h2><p className="mt-4 max-w-xl text-sm leading-7 text-white/75">Forests are living systems. Look for changing light, birdlife, deer, tracks, water and woodland—not only a single species.</p></div></section>

        {safari.operational_notices.length > 0 && <section aria-labelledby="operational-notices"><p className="text-xs font-black uppercase tracking-[.18em] text-[#a8532b]">Important information</p><h2 id="operational-notices" className="mt-4 font-serif text-4xl font-semibold sm:text-5xl">Before Your Safari</h2><div className="mt-8 space-y-4">{safari.operational_notices.map((notice) => <article key={notice.id} className={`rounded-2xl border p-6 ${notice.severity === "RESTRICTION" ? "border-red-200 bg-red-50" : notice.severity === "WARNING" ? "border-amber-200 bg-amber-50" : "border-[#bfd4c4] bg-[#eef5ef]"}`}><div className="flex flex-wrap items-center justify-between gap-3"><h3 className="text-lg font-black text-[#173326]">{notice.title}</h3><span className="text-[10px] font-black uppercase tracking-[.14em] text-slate-500">{notice.severity}</span></div><p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">{notice.body}</p>{notice.last_verified_at && <p className="mt-4 text-xs text-slate-500">Last verified {new Date(notice.last_verified_at).toLocaleDateString()}</p>}</article>)}</div></section>}

        <section aria-labelledby="managed-process"><p className="text-xs font-black uppercase tracking-[.18em] text-[#a8532b]">How Maharashtra Tourist Places works</p><h2 id="managed-process" className="mt-4 font-serif text-4xl font-semibold sm:text-5xl">From preference to permit</h2><p className="mt-5 max-w-2xl leading-7 text-slate-600">Availability and official processing stay separate from payment and confirmation.</p><ol className="mt-8 space-y-3">{steps.map((step, index) => <li key={step} className="flex items-center gap-4 rounded-2xl border border-[#dce5dd] bg-white p-5"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#1f5b3a] text-sm font-black text-white">{index + 1}</span><p className="text-sm font-bold text-[#31483a]">{step}</p></li>)}</ol></section>

        {(safari.traveller_requirements.fields?.length || safari.traveller_requirements.documents?.length) ? <section aria-labelledby="requirements"><p className="text-xs font-black uppercase tracking-[.18em] text-[#a8532b]">After availability</p><h2 id="requirements" className="mt-4 font-serif text-4xl font-semibold">Traveller requirements</h2><p className="mt-4 max-w-3xl text-sm leading-7 text-slate-600">These details are requested only after availability is confirmed. Documents use Maharashtra Tourist Places&apos; authenticated private upload flow.</p><ul className="mt-6 flex flex-wrap gap-2">{safari.traveller_requirements.fields?.map((field) => <li key={field.key} className="rounded-full border border-[#dce5dd] bg-white px-4 py-2 text-sm font-semibold">{field.label || field.key.replaceAll("_", " ")}{field.required ? " · required" : " · optional"}</li>)}{safari.traveller_requirements.documents?.map((doc) => <li key={doc.type} className="rounded-full border border-[#dce5dd] bg-white px-4 py-2 text-sm font-semibold">{doc.label || doc.type.replaceAll("_", " ")}{doc.required ? " · required" : " · optional"}</li>)}</ul></section> : null}

        {hotelHref && <section className="rounded-[2rem] border border-[#dce5dd] bg-white p-7 sm:flex sm:items-center sm:justify-between sm:gap-8 sm:p-10"><div><p className="text-xs font-black uppercase tracking-[.18em] text-[#a8532b]">Continue planning</p><h2 className="mt-3 font-serif text-3xl font-semibold">Find Stays Near Your Safari Destination</h2><p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">Search active Maharashtra Tourist Places stays using this Safari&apos;s canonical destination relationship. Proximity to a specific gate is not implied.</p></div><Link href={hotelHref} className="mt-6 inline-flex min-h-12 shrink-0 items-center rounded-full bg-[#1f5b3a] px-6 text-sm font-black text-white sm:mt-0">Find stays <span aria-hidden className="ml-2">→</span></Link></section>}
      </div>

      <aside id="availability-request" className="scroll-mt-24 rounded-[1.5rem] border border-[#dce5dd] bg-white p-6 shadow-[0_22px_65px_rgba(22,51,38,.12)] sm:p-8 lg:sticky lg:top-24">
        <p className="text-xs font-black uppercase tracking-[.18em] text-[#a8532b]">Check availability</p><h2 className="mt-3 font-serif text-3xl font-semibold">Tell us your preference</h2><p className="mt-3 text-sm leading-7 text-slate-600">Maharashtra Tourist Places checks external availability before traveller details, pricing, or payment.</p>
        {created ? <RequestReceipt request={created} /> : authLoading ? <p className="mt-6 animate-pulse rounded-xl bg-slate-100 p-4 text-sm text-slate-500">Checking your account…</p> : !customer ? <div className="mt-6 rounded-xl border border-[#c8d9cb] bg-[#eef5ef] p-5"><p className="font-bold text-[#173326]">Sign in with a customer account to continue.</p><p className="mt-2 text-sm leading-6 text-[#46604f]">Your Safari, date, and party size will stay with you. Traveller documents and payment are not requested at this stage.</p><div className="mt-4 flex flex-wrap gap-3"><Link href={authPathWithNext("/login", returnTo)} className="inline-flex min-h-11 items-center rounded-full bg-[#1f5b3a] px-5 text-sm font-black text-white">Sign in to continue</Link><Link href={authPathWithNext("/register", returnTo)} className="inline-flex min-h-11 items-center rounded-full border border-[#9fbaa5] px-5 text-sm font-black text-[#1f5b3a]">Create account</Link></div></div> : <form onSubmit={submit} className="mt-7 space-y-5"><FieldLabel text="Preferred date"><input id="safari-date" type="date" required min={todayInputValue()} value={date} onChange={(event) => setDate(event.target.value)} className="field-input mt-2" /></FieldLabel>{safari.shifts.length > 0 && <FieldLabel text="Preferred shift"><select id="safari-shift" required value={shift} onChange={(event) => setShift(event.target.value)} className="field-input mt-2"><option value="">Choose a configured shift</option>{safari.shifts.map((value) => <option key={value} value={value}>{value}</option>)}</select></FieldLabel>}{safari.booking_categories.length > 0 && <FieldLabel text="Booking category"><select id="booking-category" required value={bookingCategory} onChange={(event) => setBookingCategory(event.target.value)} className="field-input mt-2"><option value="">Choose a configured category</option>{safari.booking_categories.map((value) => <option key={String(value.code)} value={String(value.code)}>{optionLabel(value)}</option>)}</select></FieldLabel>}{safari.vehicle_options.length > 0 && <FieldLabel text="Vehicle option"><select id="vehicle-option" required value={vehicleOption} onChange={(event) => setVehicleOption(event.target.value)} className="field-input mt-2"><option value="">Choose a configured vehicle</option>{safari.vehicle_options.map((value) => <option key={String(value.code)} value={String(value.code)}>{optionLabel(value)}</option>)}</select></FieldLabel>}<FieldLabel text="Number of visitors"><input id="safari-visitors" type="number" required min={1} max={20} inputMode="numeric" value={visitors} onChange={(event) => setVisitors(Number(event.target.value))} className="field-input mt-2" /></FieldLabel><label className="field-label block" htmlFor="safari-alternate">Alternate preference <span className="font-normal text-slate-400">(optional)</span><textarea id="safari-alternate" maxLength={500} rows={3} value={alternate} onChange={(event) => setAlternate(event.target.value)} className="field-input mt-2 resize-y" placeholder="For example, another configured shift or nearby date" /></label>{error && <p role="alert" className="rounded-xl border border-red-100 bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</p>}<button disabled={busy} className="min-h-12 w-full rounded-xl bg-[#d9783f] px-5 text-sm font-black text-white transition hover:bg-[#bd622f] disabled:opacity-60">{busy ? "Checking availability…" : "Check Availability"}</button><p className="text-xs leading-5 text-slate-500">No identity documents or payment are collected with this initial request.</p></form>}
      </aside>
    </div>

    <section id="responsible-detail-section" className="relative isolate overflow-hidden bg-[#07140e] py-24 text-white" aria-labelledby="responsible-detail"><Image src={SAFARI_IMAGES.leopard} alt="" fill sizes="100vw" className="object-cover opacity-20" /><div className="absolute inset-0 bg-[#07140e]/75" /><div className="container-shell relative"><p className="text-xs font-black uppercase tracking-[.18em] text-[#e6b675]">Travel responsibly</p><h2 id="responsible-detail" className="mt-4 font-serif text-5xl font-semibold">The forest comes first.</h2><div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{["Respect wildlife", "Follow park rules", "Keep the forest clean", "Support conservation"].map((item) => <div key={item} className="rounded-2xl border border-white/15 bg-white/5 p-5 text-sm font-black backdrop-blur-sm">{item}</div>)}</div></div></section>

    {!created && mobileCtaVisible && <a href="#availability-request" className="fixed inset-x-4 bottom-[max(1rem,env(safe-area-inset-bottom))] z-40 flex min-h-12 items-center justify-center rounded-full bg-[#d9783f] px-6 text-sm font-black text-white shadow-2xl outline-offset-2 focus-visible:outline-2 focus-visible:outline-[#173326] lg:hidden">Check Availability</a>}
  </main>;
}

function InfoList({ title, values }: { title: string; values: string[] }) { return <div className="rounded-2xl border border-[#dce5dd] bg-white p-6"><h3 className="text-lg font-black text-[#173326]">{title}</h3><ul className="mt-4 flex flex-wrap gap-2">{values.map((value) => <li key={value} className="rounded-full bg-[#eef5ef] px-3 py-1.5 text-xs font-bold text-[#46604f]">{value}</li>)}</ul></div>; }
function optionLabel(value: { code?: string; label?: string }) { return value.label || value.code || "Configured option"; }
function FieldLabel({ text, children }: { text: string; children: React.ReactNode }) { return <label className="field-label block" htmlFor={text === "Preferred date" ? "safari-date" : text === "Preferred shift" ? "safari-shift" : text === "Booking category" ? "booking-category" : text === "Vehicle option" ? "vehicle-option" : "safari-visitors"}>{text}{children}</label>; }

function RequestReceipt({ request }: { request: SafariRequest }) {
  const display = safariStatusDisplay(request.status);
  return <div className="mt-6"><div className={`rounded-xl border p-5 ${safariStatusClasses(display.tone)}`}><p className="text-xs font-black uppercase tracking-[.14em]">Request created</p><p className="mt-2 text-xl font-black">{display.label}</p><p className="mt-2 text-sm leading-6">{display.description}</p></div><dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2"><div><dt className="text-slate-500">Reference</dt><dd className="mt-1 font-black text-[#173326]">{request.request_reference}</dd></div><div><dt className="text-slate-500">Safari</dt><dd className="mt-1 font-bold">{request.safari.name}</dd></div><div><dt className="text-slate-500">Preferred date</dt><dd className="mt-1 font-bold">{new Date(`${request.preferred_date}T00:00:00`).toLocaleDateString()}</dd></div><div><dt className="text-slate-500">Response target</dt><dd className="mt-1 font-bold">{new Date(request.target_response_at).toLocaleString()}</dd></div></dl><p className="mt-4 text-xs leading-5 text-slate-500">This is an operational target, not guaranteed availability. We will update your account when the check progresses.</p><Link href={`/account/safaris/${request.request_reference}`} className="mt-5 inline-flex min-h-11 w-full items-center justify-center rounded-full bg-[#1f5b3a] px-5 text-sm font-black text-white">Track this request</Link></div>;
}
