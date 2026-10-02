"use client";

import { FormEvent, useState } from "react";

import { FormError } from "@/components/FormError";
import { ApiError } from "@/services/api";
import { PROPERTY_TYPES, type HotelCreate, type HotelInput } from "@/types/hotel";

const defaults: HotelInput = {
  name: "", slug: "", description: null, property_type: "HOTEL", star_rating: 0,
  address_line1: "", address_line2: null, city: "", state: "", country: "India",
  postal_code: "", latitude: null, longitude: null, contact_email: null, contact_phone: null,
  check_in_time: "14:00", check_out_time: "11:00", is_featured: false,
};

export function HotelForm({ initial, submitLabel, onSubmit }: {
  initial?: HotelInput;
  submitLabel: string;
  onSubmit: (data: HotelCreate) => Promise<void>;
}) {
  const values = initial ?? defaults;
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const numberOrNull = (key: string) => form.get(key) === "" ? null : Number(form.get(key));
    const textOrNull = (key: string) => String(form.get(key) ?? "").trim() || null;
    const data: HotelCreate = {
      name: String(form.get("name")).trim(), slug: String(form.get("slug")).trim().toLowerCase(),
      description: textOrNull("description"), property_type: String(form.get("property_type")) as HotelCreate["property_type"],
      star_rating: Number(form.get("star_rating")), address_line1: String(form.get("address_line1")).trim(),
      address_line2: textOrNull("address_line2"), city: String(form.get("city")).trim(), state: String(form.get("state")).trim(),
      country: String(form.get("country")).trim(), postal_code: String(form.get("postal_code")).trim(),
      latitude: numberOrNull("latitude"), longitude: numberOrNull("longitude"), contact_email: textOrNull("contact_email"),
      contact_phone: textOrNull("contact_phone"), check_in_time: String(form.get("check_in_time")),
      check_out_time: String(form.get("check_out_time")), is_featured: form.get("is_featured") === "on",
    };
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(data.slug)) return setError("Slug must use lowercase letters, numbers, and single hyphens only.");
    if (data.contact_phone && !/^\+[1-9]\d{7,14}$/.test(data.contact_phone)) return setError("Phone must use E.164 format, for example +919876543210.");
    setError(""); setSubmitting(true);
    try { await onSubmit(data); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to save the hotel. Please try again."); }
    finally { setSubmitting(false); }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8" noValidate>
      <FormError message={error} />
      <FormSection title="Property">
        <Field label="Name" name="name" defaultValue={values.name} required minLength={2} />
        <Field label="Slug" name="slug" defaultValue={values.slug} required minLength={2} hint="lowercase-with-hyphens" />
        <label className="sm:col-span-2"><Label>Description</Label><textarea name="description" defaultValue={values.description ?? ""} rows={4} className="input" maxLength={10000} /></label>
        <label><Label>Property type</Label><select name="property_type" defaultValue={values.property_type} className="input">{PROPERTY_TYPES.map((value) => <option key={value}>{value}</option>)}</select></label>
        <Field label="Star rating" name="star_rating" type="number" defaultValue={values.star_rating} min={0} max={5} step={0.1} required />
      </FormSection>
      <FormSection title="Address">
        <Field label="Address line 1" name="address_line1" defaultValue={values.address_line1} required minLength={2} />
        <Field label="Address line 2" name="address_line2" defaultValue={values.address_line2 ?? ""} />
        <Field label="City" name="city" defaultValue={values.city} required minLength={2} />
        <Field label="State" name="state" defaultValue={values.state} required minLength={2} />
        <Field label="Country" name="country" defaultValue={values.country} required minLength={2} />
        <Field label="Postal code" name="postal_code" defaultValue={values.postal_code} required minLength={2} />
        <Field label="Latitude" name="latitude" type="number" defaultValue={values.latitude ?? ""} min={-90} max={90} step="any" />
        <Field label="Longitude" name="longitude" type="number" defaultValue={values.longitude ?? ""} min={-180} max={180} step="any" />
      </FormSection>
      <FormSection title="Contact and operations">
        <Field label="Contact email" name="contact_email" type="email" defaultValue={values.contact_email ?? ""} />
        <Field label="Contact phone" name="contact_phone" type="tel" defaultValue={values.contact_phone ?? ""} hint="E.164, e.g. +919876543210" />
        <Field label="Check-in time" name="check_in_time" type="time" defaultValue={values.check_in_time.slice(0, 5)} required />
        <Field label="Check-out time" name="check_out_time" type="time" defaultValue={values.check_out_time.slice(0, 5)} required />
        <label className="flex items-center gap-3 pt-7"><input name="is_featured" type="checkbox" defaultChecked={values.is_featured} className="h-4 w-4" /><span className="text-sm font-semibold">Featured hotel</span></label>
      </FormSection>
      <div className="flex justify-end"><button type="submit" disabled={submitting} className="btn-primary">{submitting ? "Saving…" : submitLabel}</button></div>
    </form>
  );
}

function FormSection({ title, children }: { title: string; children: React.ReactNode }) {
  return <fieldset><legend className="mb-4 text-lg font-bold">{title}</legend><div className="grid gap-5 sm:grid-cols-2">{children}</div></fieldset>;
}

function Label({ children }: { children: React.ReactNode }) { return <span className="mb-1.5 block text-sm font-semibold text-slate-700">{children}</span>; }

function Field({ label, hint, ...props }: { label: string; hint?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return <label><Label>{label}</Label><input {...props} className="input" />{hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}</label>;
}
