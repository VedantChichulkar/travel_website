"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/src/context/AuthContext";
import { isCustomerRole } from "@/src/lib/portal-routing";
import { bookingService, type CustomerBooking } from "@/src/services/booking.service";
import { safariService } from "@/src/services/safari.service";
import { supportService } from "@/src/services/support.service";
import type { SafariRequest } from "@/src/types/safari";
import { ENQUIRY_TYPES, type ContactConfig, type EnquiryType, type SupportEnquiryReceipt } from "@/src/types/support";

const LABELS: Record<EnquiryType, string> = {
  BOOKING_HELP: "Booking Help",
  SAFARI_HELP: "Safari Help",
  CANCELLATION_REFUND: "Cancellation / Refund",
  HOTEL_PARTNER: "Hotel Partner Enquiry",
  GENERAL: "General Enquiry",
};

const DESCRIPTIONS: Record<EnquiryType, string> = {
  BOOKING_HELP: "Questions about an existing Maharashtra Tourist Places hotel booking.",
  SAFARI_HELP: "Help with a managed Safari availability or booking request.",
  CANCELLATION_REFUND: "Support for a cancellation or refund already connected to a booking.",
  HOTEL_PARTNER: "For properties and hospitality businesses considering Maharashtra Tourist Places.",
  GENERAL: "Anything that does not fit the other support paths.",
};

function isEnquiryType(value: string | null): value is EnquiryType {
  return ENQUIRY_TYPES.includes(value as EnquiryType);
}

export function ContactPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedType = searchParams.get("type");
  const requestedReference = searchParams.get("reference");
  const { user, loading: authLoading } = useAuth();
  const [type, setType] = useState<EnquiryType>(() => isEnquiryType(requestedType) ? requestedType : "GENERAL");
  const [name, setName] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [mobile, setMobile] = useState<string | null>(null);
  const [reference, setReference] = useState(() => requestedReference?.slice(0, 64).toUpperCase() ?? "");
  const [propertyName, setPropertyName] = useState("");
  const [location, setLocation] = useState("");
  const [message, setMessage] = useState("");
  const [bookings, setBookings] = useState<CustomerBooking[]>([]);
  const [safaris, setSafaris] = useState<SafariRequest[]>([]);
  const [config, setConfig] = useState<ContactConfig | null>(null);
  const [referenceError, setReferenceError] = useState("");
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState<SupportEnquiryReceipt | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const idempotencyKey = useRef(crypto.randomUUID().replaceAll("-", ""));
  const resolvedName = name ?? user?.full_name ?? "";
  const resolvedEmail = email ?? user?.email ?? "";
  const resolvedMobile = mobile ?? user?.phone ?? "";

  useEffect(() => { void supportService.config().then(setConfig).catch(() => setConfig({ email: null, whatsapp_url: null })); }, []);
  useEffect(() => {
    if (!user || !isCustomerRole(user.role)) return;
    let active = true;
    void Promise.allSettled([bookingService.listMine(), safariService.mine()]).then(([bookingResult, safariResult]) => {
      if (!active) return;
      if (bookingResult.status === "fulfilled") setBookings(bookingResult.value.items);
      if (safariResult.status === "fulfilled") setSafaris(safariResult.value);
      if (bookingResult.status === "rejected" || safariResult.status === "rejected") setReferenceError("Some account references could not be loaded. You can enter the customer-facing reference manually.");
    });
    return () => { active = false; };
  }, [user]);

  const relevantReferences = useMemo(() => {
    if (type === "SAFARI_HELP") return safaris.map((item) => ({ value: item.request_reference, label: `${item.request_reference} · ${item.safari.name}` }));
    if (type === "BOOKING_HELP" || type === "CANCELLATION_REFUND") return bookings.map((item) => ({ value: item.booking_reference, label: `${item.booking_reference} · ${item.hotel.name}` }));
    return [];
  }, [bookings, safaris, type]);

  function changeType(next: EnquiryType) {
    setType(next); setReference(""); setError(""); setReceipt(null);
    router.replace(`/contact?type=${next}`, { scroll: false });
  }

  function validate(): string {
    if (resolvedName.trim().length < 2) return "Enter your name.";
    if (!/^\S+@\S+\.\S+$/.test(resolvedEmail.trim())) return "Enter a valid email address.";
    if (!/^\+?[1-9]\d{7,14}$/.test(resolvedMobile.trim())) return "Enter a valid mobile number, including country code where possible.";
    if (["BOOKING_HELP", "SAFARI_HELP", "CANCELLATION_REFUND"].includes(type) && reference.trim().length < 3) return "Enter or select the customer-facing reference.";
    if (type === "HOTEL_PARTNER" && propertyName.trim().length < 2) return "Enter the property or business name.";
    if (message.trim().length < 10) return "Please add a little more detail so the support team can understand the enquiry.";
    return "";
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const invalid = validate();
    if (invalid) { setError(invalid); return; }
    setSubmitting(true); setError("");
    try {
      const result = await supportService.submit({
        idempotency_key: idempotencyKey.current, enquiry_type: type,
        name: resolvedName.trim().replace(/\s+/g, " "), email: resolvedEmail.trim().toLowerCase(), mobile: resolvedMobile.trim(), message: message.trim(),
        customer_reference: reference.trim() || undefined, property_name: propertyName.trim() || undefined, location: location.trim() || undefined,
      });
      setReceipt(result);
    } catch {
      setError("The enquiry could not be submitted. Your details remain in the form so you can try again.");
    } finally { setSubmitting(false); }
  }

  function reset() {
    setReceipt(null); setMessage(""); setReference(""); setPropertyName(""); setLocation(""); setError("");
    idempotencyKey.current = crypto.randomUUID().replaceAll("-", "");
  }

  const whatsappMessage = type === "BOOKING_HELP" || type === "CANCELLATION_REFUND"
    ? "Hi Maharashtra Tourist Places, I need help with my booking."
    : type === "SAFARI_HELP" ? "Hi Maharashtra Tourist Places, I need help with a Safari request." : type === "HOTEL_PARTNER" ? "Hi Maharashtra Tourist Places, I have a hotel partner enquiry." : "Hi Maharashtra Tourist Places, I have an enquiry.";
  const whatsappHref = config?.whatsapp_url ? `${config.whatsapp_url}?text=${encodeURIComponent(whatsappMessage)}` : null;

  return <>
    <header className="border-b border-[var(--line)] bg-white"><div className="container-shell grid gap-8 py-12 lg:grid-cols-[1fr_.72fr] lg:items-center lg:py-16"><div><p className="eyebrow">Contact Maharashtra Tourist Places</p><h1 className="page-title mt-3">The right help, without a maze.</h1><p className="body-lead mt-5 max-w-2xl">Choose what you need help with, include the safe customer-facing reference when relevant, and keep payment credentials or traveller documents out of the message.</p></div><div className="rounded-2xl border border-[var(--line)] bg-[var(--surface-muted)] p-6"><h2 className="text-lg font-black text-[var(--brand)]">Contact methods</h2><div className="mt-4 grid gap-3">{whatsappHref && <a href={whatsappHref} target="_blank" rel="noopener noreferrer" className="primary-button w-full">Chat on WhatsApp <span aria-hidden>↗</span></a>}{config?.email && <a href={`mailto:${config.email}`} className="secondary-button w-full">Email {config.email}</a>}<a href="#enquiry-form" className="secondary-button w-full">Use the enquiry form</a>{config && !config.email && !config.whatsapp_url && <p className="text-sm leading-6 text-slate-500">The website enquiry form is the configured contact method right now.</p>}</div></div></div></header>

    <main className="container-shell py-12 sm:py-16">
      <section aria-labelledby="support-path-heading"><p className="eyebrow">Start here</p><h2 id="support-path-heading" className="section-title mt-3">What can we help with?</h2><div className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{ENQUIRY_TYPES.map((item) => <button type="button" key={item} aria-pressed={type === item} onClick={() => changeType(item)} className={`rounded-2xl border p-5 text-left transition ${type === item ? "border-[var(--accent)] bg-[var(--accent-soft)]" : "border-[var(--line)] bg-white hover:border-slate-300"}`}><strong className="block text-[var(--brand)]">{LABELS[item]}</strong><span className="mt-2 block text-xs leading-5 text-slate-500">{DESCRIPTIONS[item]}</span></button>)}</div></section>

      <div className="mt-12 grid items-start gap-8 lg:grid-cols-[1.35fr_.65fr]">
        <section id="enquiry-form" className="content-card scroll-mt-28" aria-labelledby="form-heading">
          {receipt ? <div role="status"><span aria-hidden className="grid h-12 w-12 place-items-center rounded-2xl bg-emerald-50 text-xl font-black text-[var(--success)]">✓</span><p className="eyebrow mt-5">Enquiry received</p><h2 id="form-heading" className="mt-2 text-2xl font-black text-[var(--brand)]">Reference {receipt.reference}</h2><p className="mt-3 leading-7 text-slate-600">{receipt.next_step}</p><p className="mt-3 text-sm text-slate-500">No response time is promised on this page. Support will use the contact information submitted with this enquiry.</p><button type="button" onClick={reset} className="secondary-button mt-6">Send another enquiry</button></div> : <>
            <p className="eyebrow">Website enquiry</p><h2 id="form-heading" className="mt-2 text-2xl font-black text-[var(--brand)]">{LABELS[type]}</h2><p className="mt-2 text-sm leading-6 text-slate-500">{DESCRIPTIONS[type]}</p>
            <form onSubmit={(event) => void submit(event)} className="mt-7 grid gap-5" noValidate>
              <div className="grid gap-5 sm:grid-cols-2"><Field label="Name" htmlFor="contact-name"><input id="contact-name" value={resolvedName} onChange={(event) => setName(event.target.value)} className="field-input" autoComplete="name" maxLength={100} required /></Field><Field label="Email" htmlFor="contact-email"><input id="contact-email" type="email" value={resolvedEmail} onChange={(event) => setEmail(event.target.value)} className="field-input" autoComplete="email" required /></Field><Field label="Mobile" htmlFor="contact-mobile"><input id="contact-mobile" type="tel" value={resolvedMobile} onChange={(event) => setMobile(event.target.value)} className="field-input" autoComplete="tel" placeholder="+919876543210" required /></Field><Field label="Enquiry type" htmlFor="contact-type"><select id="contact-type" value={type} onChange={(event) => changeType(event.target.value as EnquiryType)} className="field-input">{ENQUIRY_TYPES.map((item) => <option key={item} value={item}>{LABELS[item]}</option>)}</select></Field></div>
              {(type === "BOOKING_HELP" || type === "SAFARI_HELP" || type === "CANCELLATION_REFUND") && <Field label={type === "SAFARI_HELP" ? "Safari request reference" : "Booking reference"} htmlFor="contact-reference">{relevantReferences.length ? <select id="contact-reference" value={reference} onChange={(event) => setReference(event.target.value)} className="field-input" required><option value="">Choose one of your references</option>{relevantReferences.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select> : <input id="contact-reference" value={reference} onChange={(event) => setReference(event.target.value.toUpperCase())} className="field-input" placeholder={authLoading ? "Loading your account…" : "Customer-facing reference"} required />}{referenceError && <span className="mt-2 block text-xs text-amber-700">{referenceError}</span>}</Field>}
              {type === "HOTEL_PARTNER" && <div className="grid gap-5 sm:grid-cols-2"><Field label="Property / business name" htmlFor="property-name"><input id="property-name" value={propertyName} onChange={(event) => setPropertyName(event.target.value)} className="field-input" required /></Field><Field label="District / city" htmlFor="property-location"><input id="property-location" value={location} onChange={(event) => setLocation(event.target.value)} className="field-input" /></Field></div>}
              <Field label="Message" htmlFor="contact-message"><textarea id="contact-message" value={message} onChange={(event) => setMessage(event.target.value)} className="field-input min-h-36 resize-y" maxLength={5000} required /><span className="mt-2 block text-right text-xs text-slate-400">{message.length} / 5000</span></Field>
              <p className="text-xs leading-5 text-slate-500">Do not send card details, passwords, identity documents, or sensitive traveller information through this form.</p>
              {error && <p role="alert" className="rounded-xl border border-red-100 bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</p>}
              <button className="primary-button w-full" disabled={submitting}>{submitting ? "Sending enquiry…" : "Send enquiry"}</button>
            </form>
          </>}
        </section>

        <aside className="space-y-5 lg:sticky lg:top-24"><div className="content-card"><p className="eyebrow">Before you send</p><ul className="mt-4 space-y-3 text-sm leading-6 text-slate-600"><li>Use a Maharashtra Tourist Places booking or Safari request reference—not an internal database ID.</li><li>Cancellation and refund outcomes remain governed by the existing booking and reconciliation workflow.</li><li>Safari enquiries do not create availability or guarantee an official booking.</li></ul></div>{type === "HOTEL_PARTNER" && <div className="content-card"><h2 className="text-lg font-black text-[var(--brand)]">Ready to join?</h2><p className="mt-2 text-sm leading-6 text-slate-600">Use the existing partner registration and verification flow when you are ready to create a property account.</p><Link href="/partner/register" className="secondary-button mt-5 w-full">Become a Maharashtra Tourist Places Partner</Link></div>}</aside>
      </div>
    </main>
  </>;
}

function Field({ label, htmlFor, children }: { label: string; htmlFor: string; children: React.ReactNode }) {
  return <label htmlFor={htmlFor}><span className="field-label">{label}</span>{children}</label>;
}
