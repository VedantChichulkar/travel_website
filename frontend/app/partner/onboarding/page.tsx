"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { ApiError } from "@/src/services/api";
import { openPaymentCheckout } from "@/src/lib/payment-checkout";
import { authService } from "@/src/services/auth.service";
import { partnerService } from "@/src/services/partner.service";
import { tokenStorage } from "@/src/services/token-storage";
import type { PartnerOverview, PropertyType, BusinessType, VerificationFeeStatus } from "@/src/types/partner";

const PRIVATE_DOCUMENT_MAX_BYTES = 10 * 1024 * 1024;

// ─── Slugification helper ──────────────────────────────────────────────────────
function toSlug(name: string) {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 180);
}

// ─── Status badge helper ───────────────────────────────────────────────────────
const STATUS_CONFIGS = {
  PENDING: { label: "Under Review", color: "bg-amber-100 text-amber-800 border-amber-300", dot: "bg-amber-500", pulse: true },
  APPROVED: { label: "Approved", color: "bg-emerald-100 text-emerald-800 border-emerald-300", dot: "bg-emerald-500", pulse: false },
  REJECTED: { label: "Rejected", color: "bg-red-100 text-red-800 border-red-300", dot: "bg-red-500", pulse: false },
  ADDITIONAL_INFO_REQUIRED: { label: "Action Required", color: "bg-orange-100 text-orange-800 border-orange-300", dot: "bg-orange-500", pulse: true },
} as const;

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIGS[status as keyof typeof STATUS_CONFIGS] ?? { label: status, color: "bg-slate-100 text-slate-700 border-slate-300", dot: "bg-slate-500", pulse: false };
  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-black ${cfg.color}`}>
      <span className={`h-2 w-2 rounded-full flex-shrink-0 ${cfg.dot}${cfg.pulse ? " animate-pulse" : ""}`} />
      {cfg.label}
    </span>
  );
}

// ─── Section heading ────────────────────────────────────────────────────────────
function SectionTitle({ step, title, subtitle }: { step: number; title: string; subtitle: string }) {
  return (
    <div className="flex items-start gap-4 mb-8">
      <div className="flex-shrink-0 h-10 w-10 rounded-xl bg-[#172554] grid place-items-center text-white font-black text-sm">{step}</div>
      <div>
        <h2 className="text-xl font-black text-[#0b163d] tracking-tight">{title}</h2>
        <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>
      </div>
    </div>
  );
}

function Field({ label, id, error, hint, children, required = false }: {
  label: string; id: string; error?: string; hint?: string; children: React.ReactNode; required?: boolean;
}) {
  return (
    <div>
      <label htmlFor={id} className="field-label">
        {label}{required && <span className="ml-1 text-red-500">*</span>}
      </label>
      {children}
      {error ? (
        <p role="alert" className="mt-1 text-xs font-semibold text-red-600">{error}</p>
      ) : hint ? (
        <p className="mt-1 text-xs text-slate-400">{hint}</p>
      ) : null}
    </div>
  );
}

// ─── Step 1: Hotel Profile Form ─────────────────────────────────────────────────
function HotelProfileForm({ onSuccess }: { onSuccess: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [values, setValues] = useState({
    name: "",
    slug: "",
    description: "",
    property_type: "HOTEL" as PropertyType,
    star_rating: "3.0",
    address_line1: "",
    address_line2: "",
    city: "",
    district: "",
    state: "Maharashtra",
    country: "India",
    postal_code: "",
    contact_email: "",
    contact_phone: "",
    check_in_time: "14:00",
    check_out_time: "11:00",
  });

  function update(field: string, value: string) {
    setValues((v) => {
      const next = { ...v, [field]: value };
      if (field === "name") next.slug = toSlug(value);
      return next;
    });
    setErrors((e) => ({ ...e, [field]: "" }));
  }

  function validate() {
    const e: Record<string, string> = {};
    if (values.name.trim().length < 2) e.name = "Property name is required (min 2 characters)";
    if (!values.slug.match(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)) e.slug = "Slug must be lowercase with hyphens only";
    if (!values.address_line1.trim()) e.address_line1 = "Street address is required";
    if (!values.city.trim()) e.city = "City is required";
    if (!values.postal_code.trim()) e.postal_code = "Pincode is required";
    if (!values.check_in_time) e.check_in_time = "Check-in time is required";
    if (!values.check_out_time) e.check_out_time = "Check-out time is required";
    return e;
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const validation = validate();
    setErrors(validation);
    setFormError("");
    if (Object.keys(validation).length) return;
    setSubmitting(true);
    try {
      await partnerService.createHotel({
        name: values.name.trim(),
        slug: values.slug,
        description: values.description.trim() || undefined,
        property_type: values.property_type,
        star_rating: parseFloat(values.star_rating),
        address_line1: values.address_line1.trim(),
        address_line2: values.address_line2.trim() || undefined,
        city: values.city.trim(),
        district: values.district.trim() || undefined,
        state: values.state.trim(),
        country: values.country.trim(),
        postal_code: values.postal_code.trim(),
        contact_email: values.contact_email.trim() || undefined,
        contact_phone: values.contact_phone.trim() || undefined,
        check_in_time: values.check_in_time,
        check_out_time: values.check_out_time,
      });
      onSuccess();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Failed to save hotel profile. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6" noValidate>
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Property Name" id="name" error={errors.name} required>
          <input id="name" value={values.name} onChange={(e) => update("name", e.target.value)} className="field-input" placeholder="Sahyadri Heritage Resort" />
        </Field>
        <Field label="URL Slug" id="slug" error={errors.slug} hint="Auto-generated from name" required>
          <input id="slug" value={values.slug} onChange={(e) => update("slug", e.target.value)} className="field-input" placeholder="sahyadri-heritage-resort" />
        </Field>
        <div className="sm:col-span-2">
          <Field label="Description" id="description" error={errors.description} hint="Max 10,000 characters">
            <textarea id="description" rows={3} value={values.description} onChange={(e) => update("description", e.target.value)} className="field-input resize-none" placeholder="Describe your property…" />
          </Field>
        </div>
        <Field label="Property Type" id="property_type" error={errors.property_type} required>
          <select id="property_type" value={values.property_type} onChange={(e) => update("property_type", e.target.value)} className="field-input">
            {["HOTEL", "RESORT", "VILLA", "APARTMENT", "HOSTEL", "HOMESTAY"].map((t) => (
              <option key={t} value={t}>{t.charAt(0) + t.slice(1).toLowerCase()}</option>
            ))}
          </select>
        </Field>
        <Field label="Star Rating" id="star_rating" error={errors.star_rating}>
          <select id="star_rating" value={values.star_rating} onChange={(e) => update("star_rating", e.target.value)} className="field-input">
            {["0.0", "1.0", "2.0", "2.5", "3.0", "3.5", "4.0", "4.5", "5.0"].map((r) => (
              <option key={r} value={r}>{r} ★</option>
            ))}
          </select>
        </Field>
        <div className="sm:col-span-2 border-t border-slate-100 pt-4">
          <p className="text-xs font-black tracking-widest text-slate-400 uppercase mb-4">Location</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <Field label="Street Address" id="address_line1" error={errors.address_line1} required>
                <input id="address_line1" value={values.address_line1} onChange={(e) => update("address_line1", e.target.value)} className="field-input" placeholder="Plot No. 45, NH 4 Bypass" />
              </Field>
            </div>
            <Field label="Address Line 2" id="address_line2">
              <input id="address_line2" value={values.address_line2} onChange={(e) => update("address_line2", e.target.value)} className="field-input" placeholder="Near ABC Landmark" />
            </Field>
            <Field label="City" id="city" error={errors.city} required>
              <input id="city" value={values.city} onChange={(e) => update("city", e.target.value)} className="field-input" placeholder="Mahabaleshwar" />
            </Field>
            <Field label="District" id="district">
              <input id="district" value={values.district} onChange={(e) => update("district", e.target.value)} className="field-input" placeholder="Satara" />
            </Field>
            <Field label="State" id="state" error={errors.state} required>
              <input id="state" value={values.state} onChange={(e) => update("state", e.target.value)} className="field-input" />
            </Field>
            <Field label="Pincode" id="postal_code" error={errors.postal_code} required>
              <input id="postal_code" value={values.postal_code} onChange={(e) => update("postal_code", e.target.value)} className="field-input" placeholder="412806" />
            </Field>
          </div>
        </div>
        <div className="sm:col-span-2 border-t border-slate-100 pt-4">
          <p className="text-xs font-black tracking-widest text-slate-400 uppercase mb-4">Contact & Timings</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Contact Email" id="contact_email">
              <input id="contact_email" type="email" value={values.contact_email} onChange={(e) => update("contact_email", e.target.value)} className="field-input" placeholder="reservations@hotel.com" />
            </Field>
            <Field label="Contact Phone" id="contact_phone" hint="E.164 format: +919876543210">
              <input id="contact_phone" type="tel" value={values.contact_phone} onChange={(e) => update("contact_phone", e.target.value)} className="field-input" placeholder="+919876543210" />
            </Field>
            <Field label="Check-in Time" id="check_in_time" error={errors.check_in_time} required>
              <input id="check_in_time" type="time" value={values.check_in_time} onChange={(e) => update("check_in_time", e.target.value)} className="field-input" />
            </Field>
            <Field label="Check-out Time" id="check_out_time" error={errors.check_out_time} required>
              <input id="check_out_time" type="time" value={values.check_out_time} onChange={(e) => update("check_out_time", e.target.value)} className="field-input" />
            </Field>
          </div>
        </div>
      </div>

      {formError && (
        <p role="alert" className="rounded-xl bg-red-50 border border-red-200 p-3 text-sm font-semibold text-red-700">{formError}</p>
      )}
      <button type="submit" disabled={submitting} className="primary-button">
        {submitting ? "Saving hotel profile…" : "Save hotel profile & continue"}
      </button>
    </form>
  );
}

function VerificationFeeStep({ fee, onRefresh }: { fee: VerificationFeeStatus; onRefresh: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function createOrder() {
    setBusy(true); setError("");
    try {
      const order = await partnerService.createVerificationFeePaymentOrder();
      if (order.provider === "RAZORPAY") await openPaymentCheckout(order, "Hotel verification processing fee");
      onRefresh();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Could not create the verification fee payment order.");
    } finally { setBusy(false); }
  }

  return <div className="space-y-5">
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6">
      <p className="text-xs font-black uppercase tracking-widest text-slate-400">Verification processing fee</p>
      <p className="mt-2 text-3xl font-black text-[#0b163d]">{fee.currency} {fee.amount}</p>
      <p className="mt-3 text-sm text-slate-600">{fee.disclaimer}</p>
      <div className="mt-4 flex flex-wrap gap-2 text-xs font-bold">
        <span className="rounded-full bg-white px-3 py-1.5 text-slate-700">Payment: {fee.payment_status.replaceAll("_", " ")}</span>
        {fee.provider_order_id && <span className="rounded-full bg-white px-3 py-1.5 text-slate-500">Order: {fee.provider_order_id}</span>}
      </div>
    </div>
    {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</p>}
    {fee.payment_status === "NOT_STARTED" || fee.payment_status === "FAILED" ?
      <button disabled={busy} onClick={() => void createOrder()} className="primary-button">{busy ? "Creating order…" : "Create secure payment order"}</button> :
      <div className="flex flex-wrap gap-3"><button disabled={busy} onClick={onRefresh} className="secondary-button">Refresh payment status</button>{fee.payment_status === "PENDING" && <button disabled={busy} onClick={() => void createOrder()} className="primary-button">{busy ? "Opening…" : "Open secure checkout"}</button>}</div>}
    {fee.payment_status === "PENDING" && <p className="text-sm text-amber-700">Waiting for a signed provider confirmation. The browser cannot mark this fee paid.</p>}
  </div>;
}

// ─── Verification Form ──────────────────────────────────────────────────
function VerificationForm({ onSuccess }: { onSuccess: () => void }) {
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [values, setValues] = useState({
    business_name: "",
    business_type: "PROPRIETORSHIP" as BusinessType,
    gstin: "",
    pan: "",
    bank_account_number: "",
    bank_ifsc: "",
    bank_name: "",
    bank_beneficiary_name: "",
    document_proof_type: "TRADE_LICENSE",
  });

  function update(field: string, value: string) {
    setValues((v) => ({ ...v, [field]: value }));
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setFormError("");
    if (!values.business_name.trim()) {
      setFormError("Business name is required.");
      return;
    }
    if (documentFile && documentFile.size > PRIVATE_DOCUMENT_MAX_BYTES) {
      setFormError("The private document must be 10 MB or smaller.");
      return;
    }
    setSubmitting(true);
    try {
      const application = {
        business_name: values.business_name.trim(),
        business_type: values.business_type,
        gstin: values.gstin.trim().toUpperCase() || undefined,
        pan: values.pan.trim().toUpperCase() || undefined,
        bank_account_number: values.bank_account_number.trim() || undefined,
        bank_ifsc: values.bank_ifsc.trim().toUpperCase() || undefined,
        bank_name: values.bank_name.trim() || undefined,
        bank_beneficiary_name: values.bank_beneficiary_name.trim() || undefined,
        document_proof_type: values.document_proof_type || undefined,
      };
      await partnerService.submitVerification(application);
      if (documentFile) {
        const uploaded = await partnerService.uploadVerificationDocument(documentFile);
        await partnerService.submitVerification({ ...application, document_reference: uploaded.document_reference });
      }
      onSuccess();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Failed to submit verification. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6" noValidate>
      <div className="grid gap-5 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Field label="Registered Business Name" id="business_name" required>
            <input id="business_name" value={values.business_name} onChange={(e) => update("business_name", e.target.value)} className="field-input" placeholder="Sahyadri Hospitality LLP" />
          </Field>
        </div>
        <Field label="Business Type" id="business_type" required>
          <select id="business_type" value={values.business_type} onChange={(e) => update("business_type", e.target.value)} className="field-input">
            {["PROPRIETORSHIP", "PARTNERSHIP", "PRIVATE_LIMITED", "PUBLIC_LIMITED", "LLP", "OTHER"].map((t) => (
              <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
            ))}
          </select>
        </Field>
        <Field label="GSTIN" id="gstin" hint="e.g. 27ABCDE1234F1Z5 (optional)">
          <input id="gstin" value={values.gstin} onChange={(e) => update("gstin", e.target.value)} className="field-input" placeholder="27ABCDE1234F1Z5" />
        </Field>
        <Field label="PAN" id="pan" hint="e.g. ABCDE1234F (optional)">
          <input id="pan" value={values.pan} onChange={(e) => update("pan", e.target.value)} className="field-input" placeholder="ABCDE1234F" />
        </Field>

        <div className="sm:col-span-2 border-t border-slate-100 pt-4">
          <p className="text-xs font-black tracking-widest text-slate-400 uppercase mb-4">Bank Account Details</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Account Number" id="bank_account_number">
              <input id="bank_account_number" value={values.bank_account_number} onChange={(e) => update("bank_account_number", e.target.value)} className="field-input" placeholder="012345678901234" />
            </Field>
            <Field label="IFSC Code" id="bank_ifsc" hint="e.g. HDFC0001234">
              <input id="bank_ifsc" value={values.bank_ifsc} onChange={(e) => update("bank_ifsc", e.target.value)} className="field-input" placeholder="HDFC0001234" />
            </Field>
            <Field label="Bank Name" id="bank_name">
              <input id="bank_name" value={values.bank_name} onChange={(e) => update("bank_name", e.target.value)} className="field-input" placeholder="HDFC Bank Ltd" />
            </Field>
            <Field label="Account Holder Name" id="bank_beneficiary_name">
              <input id="bank_beneficiary_name" value={values.bank_beneficiary_name} onChange={(e) => update("bank_beneficiary_name", e.target.value)} className="field-input" placeholder="Sahyadri Hospitality LLP" />
            </Field>
          </div>
        </div>

        <div className="sm:col-span-2 border-t border-slate-100 pt-4">
          <p className="text-xs font-black tracking-widest text-slate-400 uppercase mb-4">Document Proof</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Document Type" id="document_proof_type">
              <select id="document_proof_type" value={values.document_proof_type} onChange={(e) => update("document_proof_type", e.target.value)} className="field-input">
                {["TRADE_LICENSE", "GST_CERTIFICATE", "FOOD_LICENSE", "ELECTRICITY_BILL", "OWNERSHIP_PROOF", "OTHER"].map((t) => (
                  <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                ))}
              </select>
            </Field>
            <Field label="Private document" id="document_file" hint="PDF, JPEG, or PNG; maximum 10 MB; stored privately">
              <input id="document_file" type="file" accept="application/pdf,image/jpeg,image/png" onChange={(e) => setDocumentFile(e.target.files?.[0] ?? null)} className="field-input" />
            </Field>
          </div>
        </div>
      </div>

      {formError && (
        <p role="alert" className="rounded-xl bg-red-50 border border-red-200 p-3 text-sm font-semibold text-red-700">{formError}</p>
      )}
      <button type="submit" disabled={submitting} className="primary-button">
        {submitting ? "Submitting verification…" : "Submit for verification"}
      </button>
    </form>
  );
}

// ─── Verification Status Panel ──────────────────────────────────────────────────
function VerificationStatusPanel({ overview, onResubmit }: { overview: PartnerOverview; onResubmit: () => void }) {
  const router = useRouter();
  const ver = overview.verification!;
  const hotel = overview.hotel!;

  if (ver.verification_status === "APPROVED") {
    return (
      <div className="text-center py-8">
        <div className="mx-auto mb-6 h-20 w-20 rounded-full bg-emerald-100 grid place-items-center">
          <span className="text-4xl">✓</span>
        </div>
        <StatusBadge status="APPROVED" />
        <h2 className="mt-4 text-2xl font-black text-[#0b163d] tracking-tight">Congratulations! Your hotel is verified.</h2>
        <p className="mt-3 text-slate-500 max-w-md mx-auto">
          <strong>{hotel.name}</strong> has been approved by Maharashtra Tourist Places and is now active on the platform.
        </p>
        <button onClick={() => router.push("/partner/dashboard")} className="primary-button mt-8">
          Go to Hotel Portal →
        </button>
      </div>
    );
  }

  if (ver.verification_status === "REJECTED") {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4 p-5 rounded-2xl bg-red-50 border border-red-200">
          <span className="text-3xl flex-shrink-0">✗</span>
          <div>
            <div className="flex items-center gap-3 mb-1">
              <StatusBadge status="REJECTED" />
            </div>
            <h2 className="font-black text-red-900">Verification was not approved</h2>
            {ver.rejection_reason && (
              <div className="mt-3 p-3 bg-white rounded-xl border border-red-200">
                <p className="text-xs font-black tracking-widest text-red-600 uppercase mb-1">Reason</p>
                <p className="text-sm text-red-800">{ver.rejection_reason}</p>
              </div>
            )}
          </div>
        </div>
        <p className="text-sm text-slate-600">This is a final rejection. Your full verification fee refund is handled automatically through the original payment path.</p>
        {overview.verification_fee?.refund_status && <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm"><strong>Refund: {overview.verification_fee.refund_status.replaceAll("_", " ")}</strong>{overview.verification_fee.refund_reference && <p className="mt-1 break-all text-xs text-slate-500">Reference: {overview.verification_fee.refund_reference}</p>}{overview.verification_fee.refund_failure_reason && <p className="mt-1 text-amber-700">{overview.verification_fee.refund_failure_reason}</p>}</div>}
      </div>
    );
  }

  if (ver.verification_status === "ADDITIONAL_INFO_REQUIRED" || ver.verification_status === "NEEDS_CHANGES") {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4 p-5 rounded-2xl bg-orange-50 border border-orange-200">
          <span className="text-3xl flex-shrink-0">!</span>
          <div>
            <div className="flex items-center gap-3 mb-1">
              <StatusBadge status="ADDITIONAL_INFO_REQUIRED" />
            </div>
            <h2 className="font-black text-orange-900">Additional information required</h2>
            {ver.admin_notes && (
              <div className="mt-3 p-3 bg-white rounded-xl border border-orange-200">
                <p className="text-xs font-black tracking-widest text-orange-600 uppercase mb-1">Notes from Maharashtra Tourist Places team</p>
                <p className="text-sm text-orange-800">{ver.admin_notes}</p>
              </div>
            )}
          </div>
        </div>
        <p className="text-sm text-slate-600">Please update the required information and re-submit.</p>
        <button onClick={onResubmit} className="primary-button">Update & re-submit verification</button>
      </div>
    );
  }

  // PENDING
  return (
    <div className="text-center py-8">
      <div className="mx-auto mb-6 h-20 w-20 rounded-full bg-amber-100 grid place-items-center">
        <span className="text-3xl animate-pulse">⏳</span>
      </div>
      <StatusBadge status="PENDING" />
      <h2 className="mt-4 text-2xl font-black text-[#0b163d] tracking-tight">Your application is under review</h2>
      <p className="mt-3 text-slate-500 max-w-md mx-auto">
        The Maharashtra Tourist Places team is reviewing your submission for <strong>{hotel.name}</strong>. This usually takes 1–3 business days.
      </p>
      <div className="mt-8 max-w-sm mx-auto space-y-3 text-left">
        <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 flex-shrink-0" />
          <span className="text-sm text-slate-700">Hotel profile created</span>
        </div>
        <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 flex-shrink-0" />
          <span className="text-sm text-slate-700">Verification documents submitted</span>
        </div>
        <div className="flex items-center gap-3 p-3 rounded-xl bg-amber-50 border border-amber-200">
          <span className="h-2.5 w-2.5 rounded-full bg-amber-500 animate-pulse flex-shrink-0" />
          <span className="text-sm text-amber-800 font-semibold">Maharashtra Tourist Places admin review in progress</span>
        </div>
        <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-100 opacity-50">
          <span className="h-2.5 w-2.5 rounded-full bg-slate-300 flex-shrink-0" />
          <span className="text-sm text-slate-400">Portal access unlocked</span>
        </div>
      </div>
    </div>
  );
}

// ─── Main Onboarding Page ───────────────────────────────────────────────────────
export default function PartnerOnboardingPage() {
  const router = useRouter();
  const [overview, setOverview] = useState<PartnerOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [resubmitting, setResubmitting] = useState(false);

  // Determine current UI step
  const step = !overview?.has_hotel ? "create-hotel"
    : !overview.is_onboarding_complete && overview.verification_fee?.payment_status !== "PAID" ? "verification-fee"
    : !overview.is_onboarding_complete ? "submit-verification"
    : resubmitting ? "submit-verification"
    : "status";

  const loadOverview = useCallback(async () => {
    try {
      const tokens = tokenStorage.getTokens();
      if (!tokens) { router.replace("/partner/login"); return; }
      const user = await authService.getCurrentUser();
      if (!user) { router.replace("/partner/login"); return; }
      if (user.role !== "HOTEL_PARTNER") {
        setAuthError("This portal is for hotel partners only.");
        setLoading(false);
        return;
      }
      if (overview?.can_access_portal) {
        // Already approved — redirect to dashboard
        router.replace("/partner/dashboard");
        return;
      }
      const data = await partnerService.getOverview();
      setOverview(data);
      if (data.can_access_portal) router.replace("/partner/dashboard");
    } catch {
      router.replace("/partner/login");
    } finally {
      setLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { queueMicrotask(() => void loadOverview()); }, [loadOverview]);

  if (loading) return <LoadingSkeleton />;
  if (authError) return <UnauthorizedPanel message={authError} />;

  const hotel = overview?.hotel;
  const ver = overview?.verification;

  return (
    <div className="min-h-screen bg-[#f0f4f8]">
      {/* Top bar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-[#172554] text-white text-xs font-black">M</div>
            <span className="font-black text-[#172554] tracking-tight">Maharashtra Tourist Places Partner Onboarding</span>
          </div>
          {hotel && <StatusBadge status={hotel.status} />}
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
        {/* Progress steps */}
        <div className="mb-10 flex items-center gap-0">
          {[
            { num: 1, label: "Hotel Profile", done: !!overview?.has_hotel },
            { num: 2, label: "Fee", done: overview?.verification_fee?.payment_status === "PAID" },
            { num: 3, label: "Application", done: !!overview?.is_onboarding_complete },
            { num: 4, label: "Admin Review", done: ver?.verification_status === "APPROVED" },
            { num: 5, label: "Portal", done: !!overview?.can_access_portal },
          ].map((s, idx) => (
            <div key={s.num} className="flex items-center flex-1 last:flex-none">
              <div className={`flex-shrink-0 flex items-center gap-2`}>
                <div className={`h-8 w-8 rounded-full grid place-items-center text-sm font-black border-2 transition-colors
                  ${s.done ? "bg-emerald-500 border-emerald-500 text-white" : step === `create-hotel` && s.num === 1 ? "bg-[#172554] border-[#172554] text-white" : step === "verification-fee" && s.num === 2 ? "bg-[#172554] border-[#172554] text-white" : step === "submit-verification" && s.num === 3 ? "bg-[#172554] border-[#172554] text-white" : step === "status" && s.num === 4 ? "bg-amber-400 border-amber-400 text-white" : "bg-white border-slate-300 text-slate-400"}`}>
                  {s.done ? "✓" : s.num}
                </div>
                <span className={`text-xs font-bold hidden sm:block ${s.done ? "text-emerald-600" : "text-slate-500"}`}>{s.label}</span>
              </div>
              {idx < 4 && <div className={`flex-1 h-0.5 mx-2 ${s.done ? "bg-emerald-400" : "bg-slate-200"}`} />}
            </div>
          ))}
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 sm:p-10">
          {step === "create-hotel" && (
            <>
              <SectionTitle step={1} title="Create your hotel profile" subtitle="Add your property's basic details, address, and operational timings." />
              <HotelProfileForm onSuccess={() => void loadOverview()} />
            </>
          )}

          {step === "submit-verification" && (
            <>
              {hotel && (
                <div className="mb-8 p-4 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center gap-3">
                  <span className="text-emerald-600 font-black text-lg">✓</span>
                  <div>
                    <p className="text-sm font-black text-emerald-800">{hotel.name}</p>
                    <p className="text-xs text-emerald-600">{hotel.city}, {hotel.state} · {hotel.property_type}</p>
                  </div>
                </div>
              )}
              <SectionTitle step={3} title="Submit verification documents" subtitle="Provide business registration details so Maharashtra Tourist Places can verify your property." />
              <VerificationForm onSuccess={() => { setResubmitting(false); void loadOverview(); }} />
            </>
          )}

          {step === "verification-fee" && overview?.verification_fee && (
            <>
              <SectionTitle step={2} title="Pay the verification fee" subtitle="The server sets the fee. Payment is required to submit an application, but does not guarantee approval." />
              <VerificationFeeStep fee={overview.verification_fee} onRefresh={() => void loadOverview()} />
            </>
          )}

          {step === "status" && overview && (
            <>
              <SectionTitle step={4} title="Verification status" subtitle="Track payment, application, and refund status with the Maharashtra Tourist Places admin team." />
              <VerificationStatusPanel overview={overview} onResubmit={() => setResubmitting(true)} />
            </>
          )}
        </div>

        {/* Hotel details sidebar for reference */}
        {hotel && step !== "create-hotel" && (
          <div className="mt-6 bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
            <p className="text-xs font-black tracking-widest text-slate-400 uppercase mb-4">Your Property</p>
            <div className="grid sm:grid-cols-3 gap-4 text-sm">
              <div><p className="text-slate-400 text-xs uppercase tracking-wide">Name</p><p className="font-bold text-slate-800 mt-0.5">{hotel.name}</p></div>
              <div><p className="text-slate-400 text-xs uppercase tracking-wide">Location</p><p className="font-bold text-slate-800 mt-0.5">{hotel.city}, {hotel.district || hotel.state}</p></div>
              <div><p className="text-slate-400 text-xs uppercase tracking-wide">Status</p><div className="mt-0.5"><StatusBadge status={hotel.status} /></div></div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="min-h-screen bg-[#f0f4f8] p-10">
      <div className="max-w-5xl mx-auto space-y-4">
        <div className="skeleton h-16 rounded-xl" />
        <div className="skeleton h-96 rounded-2xl" />
      </div>
    </div>
  );
}

function UnauthorizedPanel({ message }: { message: string }) {
  return (
    <div className="min-h-screen bg-[#f0f4f8] flex items-center justify-center p-10">
      <div className="bg-white rounded-2xl border border-red-200 shadow-sm p-10 text-center max-w-md">
        <p className="text-4xl mb-4">🔒</p>
        <h2 className="text-xl font-black text-[#0b163d] mb-2">Unauthorized</h2>
        <p className="text-slate-500 text-sm mb-6">{message}</p>
        <Link href="/partner/login" className="primary-button inline-flex">Go to Partner Login</Link>
      </div>
    </div>
  );
}
