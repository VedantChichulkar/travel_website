"use client";

import { FormEvent, useState } from "react";

import { FormError } from "@/components/FormError";
import { ApiError } from "@/services/api";
import type { RoomTypeInput } from "@/types/hotel";

const defaults: RoomTypeInput = { name: "", description: null, max_adults: 2, max_children: 0, max_guests: 2, bed_type: "KING", bed_count: 1, room_size_sqm: null, base_price: 0, currency: "INR", total_rooms: 0, is_active: true };

export function RoomForm({ initial, submitLabel, onSubmit }: { initial?: RoomTypeInput; submitLabel: string; onSubmit: (data: RoomTypeInput) => Promise<void> }) {
  const values = initial ?? defaults; const [error, setError] = useState(""); const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = new FormData(event.currentTarget); const num = (name: string) => Number(form.get(name)); const size = String(form.get("room_size_sqm")); const data: RoomTypeInput = { name: String(form.get("name")).trim(), description: String(form.get("description")).trim() || null, max_adults: num("max_adults"), max_children: num("max_children"), max_guests: num("max_guests"), bed_type: String(form.get("bed_type")).trim(), bed_count: num("bed_count"), room_size_sqm: size ? Number(size) : null, base_price: num("base_price"), currency: String(form.get("currency")).trim().toUpperCase(), total_rooms: num("total_rooms"), is_active: form.get("is_active") === "on" };
    if (data.max_guests > data.max_adults + data.max_children) return setError("Maximum guests cannot exceed adults plus children.");
    setSaving(true); setError(""); try { await onSubmit(data); } catch (e) { setError(e instanceof ApiError ? e.message : "Unable to save room type."); } finally { setSaving(false); }
  }
  return <form onSubmit={submit} className="space-y-6"><FormError message={error} /><div className="grid gap-5 sm:grid-cols-2"><Field label="Room name" name="name" defaultValue={values.name} required minLength={2} /><Field label="Bed type" name="bed_type" defaultValue={values.bed_type} required minLength={2} /><label className="sm:col-span-2"><Label>Description</Label><textarea name="description" className="input" rows={4} defaultValue={values.description ?? ""} /></label><Field label="Maximum adults" name="max_adults" type="number" defaultValue={values.max_adults} min={1} required /><Field label="Maximum children" name="max_children" type="number" defaultValue={values.max_children} min={0} required /><Field label="Maximum guests" name="max_guests" type="number" defaultValue={values.max_guests} min={1} required /><Field label="Bed count" name="bed_count" type="number" defaultValue={values.bed_count} min={1} required /><Field label="Room size (sqm)" name="room_size_sqm" type="number" defaultValue={values.room_size_sqm ?? ""} min={0.01} step={0.01} /><Field label="Base price" name="base_price" type="number" defaultValue={values.base_price} min={0} step={0.01} required /><Field label="Currency" name="currency" defaultValue={values.currency} minLength={3} maxLength={3} required /><Field label="Total rooms" name="total_rooms" type="number" defaultValue={values.total_rooms} min={0} required /><label className="flex items-center gap-3 pt-7"><input type="checkbox" name="is_active" defaultChecked={values.is_active} /><span className="text-sm font-semibold">Active room type</span></label></div><div className="flex justify-end"><button className="btn-primary" disabled={saving}>{saving ? "Saving…" : submitLabel}</button></div></form>;
}
function Label({ children }: { children: React.ReactNode }) { return <span className="mb-1.5 block text-sm font-semibold text-slate-700">{children}</span>; }
function Field({ label, ...props }: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) { return <label><Label>{label}</Label><input {...props} className="input" /></label>; }
