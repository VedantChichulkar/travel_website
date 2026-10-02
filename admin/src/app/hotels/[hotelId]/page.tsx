"use client";
/* eslint-disable @next/next/no-img-element -- image hosts are administrator-provided URLs */

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { FormError } from "@/components/FormError";
import { StatusBadge } from "@/components/StatusBadge";
import { amenityService } from "@/services/amenity.service";
import { ApiError } from "@/services/api";
import { hotelService } from "@/services/hotel.service";
import { policyService } from "@/services/policy.service";
import { BOOKING_GATEWAY_STATUSES, HOTEL_STATUSES, type Amenity, type BookingGatewayStatus, type HotelDetail, type HotelPolicyInput, type HotelStatus } from "@/types/hotel";
import { controlService } from "@/services/control.service";

type Tab = "overview" | "amenities" | "policy" | "rooms" | "inventory" | "images";
const tabs: Array<{ id: Tab; label: string }> = [
  { id: "overview", label: "Overview" }, { id: "amenities", label: "Amenities" },
  { id: "policy", label: "Policy" }, { id: "rooms", label: "Rooms" },
  { id: "inventory", label: "Inventory" }, { id: "images", label: "Images" },
];

export default function HotelDetailPage() {
  const { hotelId: hotelIdParam } = useParams<{ hotelId: string }>(); const hotelId = Number(hotelIdParam); const router = useRouter();
  const [hotel, setHotel] = useState<HotelDetail | null>(null); const [amenities, setAmenities] = useState<Amenity[]>([]);
  const [tab, setTab] = useState<Tab>("overview"); const [loading, setLoading] = useState(true); const [error, setError] = useState("");

  const load = useCallback(async () => {
    await Promise.resolve();
    setLoading(true); setError("");
    try { const [detail, allAmenities] = await Promise.all([hotelService.get(hotelId), amenityService.list()]); setHotel(detail); setAmenities(allAmenities); }
    catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) return router.replace("/login");
      setError(caught instanceof ApiError ? caught.message : "Unable to load hotel.");
    } finally { setLoading(false); }
  }, [hotelId, router]);
  // Loading remote API state is the synchronization performed by this effect.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void load(); }, [load]);

  async function changeStatus(status: HotelStatus) {
    if (status === hotel?.status) return;
    if (["SUSPENDED", "INACTIVE"].includes(status) && !window.confirm(`${status === "SUSPENDED" ? "Suspend" : "Deactivate"} this hotel? This changes customer-facing availability.`)) return;
    const reason = window.prompt(`Reason for changing this hotel to ${status}`); if (!reason || reason.trim().length < 5) return;
    try { await controlService.updateHotel(hotelId, status, reason); await load(); } catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to change status."); }
  }

  if (loading) return <div className="panel mx-auto max-w-7xl text-slate-500">Loading hotel…</div>;
  if (!hotel) return <div className="mx-auto max-w-7xl"><FormError message={error || "Hotel not found."} /><Link href="/hotels" className="link mt-4 inline-block">Back to hotels</Link></div>;

  return (
    <div className="mx-auto max-w-7xl">
      <Link href="/hotels" className="link">← Back to hotels</Link>
      <div className="my-6 flex flex-wrap items-start justify-between gap-5"><div><div className="mb-2 flex items-center gap-3"><p className="eyebrow">{hotel.property_type}</p><StatusBadge status={hotel.status} /></div><h1 className="page-title">{hotel.name}</h1><p className="page-subtitle">{hotel.city}, {hotel.state} · {hotel.star_rating} stars</p></div><div className="flex flex-wrap items-center gap-2"><Link href={`/hotels/${hotel.id}/edit`} className="btn-secondary">Edit hotel</Link><select aria-label="Hotel status" value={hotel.status} onChange={(e) => void changeStatus(e.target.value as HotelStatus)} className="input w-auto">{HOTEL_STATUSES.map((status) => <option key={status}>{status}</option>)}</select></div></div>
      <FormError message={error} />
      <div className="mb-6 flex gap-1 overflow-x-auto border-b border-slate-200">{tabs.map((item) => <button key={item.id} onClick={() => setTab(item.id)} className={`whitespace-nowrap border-b-2 px-4 py-3 text-sm font-semibold ${tab === item.id ? "border-indigo-600 text-indigo-700" : "border-transparent text-slate-500 hover:text-slate-900"}`}>{item.label}</button>)}</div>
      {tab === "overview" && <Overview hotel={hotel} />}
      {tab === "amenities" && <AmenitiesPanel hotel={hotel} all={amenities} reload={load} onAllChange={setAmenities} />}
      {tab === "policy" && <PolicyPanel hotel={hotel} reload={load} />}
      {tab === "rooms" && <RoomsPanel hotel={hotel} reload={load} />}
      {tab === "inventory" && <InventoryPanel hotel={hotel} />}
      {tab === "images" && <ImagesPanel hotel={hotel} reload={load} />}
    </div>
  );
}

function Overview({ hotel }: { hotel: HotelDetail }) {
  return <div className="grid gap-6 lg:grid-cols-3"><section className="panel lg:col-span-2"><h2 className="section-title">Property information</h2><p className="mt-4 whitespace-pre-wrap text-slate-600">{hotel.description || "No description provided."}</p><dl className="mt-6 grid gap-5 sm:grid-cols-2"><Detail label="Property type" value={hotel.property_type} /><Detail label="Star rating" value={`${hotel.star_rating} / 5`} /><Detail label="Featured" value={hotel.is_featured ? "Yes" : "No"} /><Detail label="Slug" value={hotel.slug} /><Detail label="Check-in" value={hotel.check_in_time.slice(0, 5)} /><Detail label="Check-out" value={hotel.check_out_time.slice(0, 5)} /></dl></section><aside className="space-y-6"><section className="panel"><h2 className="section-title">Address</h2><p className="mt-4 text-slate-600">{hotel.address_line1}{hotel.address_line2 && <><br />{hotel.address_line2}</>}<br />{hotel.city}, {hotel.state} {hotel.postal_code}<br />{hotel.country}</p></section><GatewayGovernance hotelId={hotel.id} /></aside></div>;
}

function GatewayGovernance({ hotelId }: { hotelId: number }) {
  const [state, setState] = useState<Awaited<ReturnType<typeof hotelService.getGateway>> | null>(null); const [error, setError] = useState("");
  const load = useCallback(async () => { try { setState(await hotelService.getGateway(hotelId)); } catch (cause) { setError(cause instanceof Error ? cause.message : "Gateway state unavailable."); } }, [hotelId]);
  useEffect(() => { queueMicrotask(() => void load()); }, [load]);
  async function override(next: BookingGatewayStatus) { const reason = window.prompt(`Reason for overriding booking gateway to ${next}`); if (!reason || reason.trim().length < 5) return; try { await hotelService.overrideGateway(hotelId, next, reason); await load(); } catch (cause) { setError(cause instanceof Error ? cause.message : "Override failed."); } }
  async function clearOverride() { if (!window.confirm("Clear the Maharashtra Tourist Places override and return control to the partner-requested mode?")) return; const reason = window.prompt("Reason for clearing this override"); if (!reason || reason.trim().length < 5) return; try { await hotelService.clearGatewayOverride(hotelId, reason); await load(); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not clear override."); } }
  return <section className="panel"><h2 className="section-title">Booking gateway</h2>{error && <p className="mt-2 text-xs text-red-700">{error}</p>}{!state ? <p className="mt-3 text-sm text-slate-400">Loading gateway state…</p> : <><dl className="mt-4 space-y-2 text-sm"><Detail label="Partner requested" value={state.partner_requested_status} /><Detail label="Effective" value={state.effective_status} /><Detail label="Override" value={state.override_status ?? "None"} /><Detail label="Inventory" value={state.inventory_is_fresh ? "Fresh" : "Stale"} /></dl>{state.override_reason && <p className="mt-3 rounded-lg bg-amber-50 p-3 text-xs text-amber-800">{state.override_reason}</p>}<select aria-label="Override booking gateway" value={state.override_status ?? state.effective_status} onChange={(event) => void override(event.target.value as BookingGatewayStatus)} className="input mt-4 text-sm">{BOOKING_GATEWAY_STATUSES.map((value) => <option key={value}>{value}</option>)}</select>{state.override_status && <button type="button" className="btn-secondary mt-3 w-full" onClick={() => void clearOverride()}>Clear override</button>}</>}</section>;
}

function AmenitiesPanel({ hotel, all, reload, onAllChange }: { hotel: HotelDetail; all: Amenity[]; reload: () => Promise<void>; onAllChange: (items: Amenity[]) => void }) {
  const [selected, setSelected] = useState<number[]>(hotel.amenities.map((item) => item.id)); const [saving, setSaving] = useState(false); const [error, setError] = useState("");
  async function assign() { setSaving(true); setError(""); try { await amenityService.assign(hotel.id, selected); await reload(); } catch (e) { setError(e instanceof ApiError ? e.message : "Unable to assign amenities."); } finally { setSaving(false); } }
  async function create(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const formElement = event.currentTarget; const form = new FormData(formElement); const name = String(form.get("name")).trim(); const slug = String(form.get("slug")).trim().toLowerCase(); setError(""); try { const created = await amenityService.create({ name, slug, icon: String(form.get("icon")).trim() || null, category: String(form.get("category")).trim() || null, is_active: true }); onAllChange([...all, created]); setSelected((ids) => [...ids, created.id]); formElement.reset(); } catch (e) { setError(e instanceof ApiError ? e.message : "Unable to create amenity."); } }
  return <div className="grid gap-6 lg:grid-cols-[2fr_1fr]"><section className="panel"><h2 className="section-title">Assign amenities</h2><p className="mt-1 text-sm text-slate-500">Select the exact set that belongs to this hotel.</p><FormError message={error} /><div className="mt-5 grid gap-3 sm:grid-cols-2">{all.map((item) => <label key={item.id} className="flex items-center gap-3 rounded-lg border border-slate-200 p-3"><input type="checkbox" checked={selected.includes(item.id)} onChange={() => setSelected((ids) => ids.includes(item.id) ? ids.filter((id) => id !== item.id) : [...ids, item.id])} /><span><span className="block font-semibold">{item.name}</span><span className="text-xs text-slate-500">{item.category || "Uncategorized"}</span></span></label>)}</div><button onClick={() => void assign()} disabled={saving} className="btn-primary mt-5">{saving ? "Saving…" : "Save assignments"}</button></section><section className="panel"><h2 className="section-title">Create amenity</h2><form onSubmit={create} className="mt-5 space-y-4"><SmallField label="Name" name="name" required /><SmallField label="Slug" name="slug" required /><SmallField label="Icon" name="icon" /><SmallField label="Category" name="category" /><button className="btn-secondary w-full">Create amenity</button></form></section></div>;
}

const emptyPolicy: HotelPolicyInput = { cancellation_policy: null, children_policy: null, pet_policy: null, smoking_policy: null, extra_bed_policy: null, additional_rules: null };
function PolicyPanel({ hotel, reload }: { hotel: HotelDetail; reload: () => Promise<void> }) {
  const [saving, setSaving] = useState(false); const [error, setError] = useState(""); const policy = hotel.policy ?? emptyPolicy;
  async function save(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = new FormData(event.currentTarget); const nullable = (name: string) => String(form.get(name)).trim() || null; const data: HotelPolicyInput = { cancellation_policy: nullable("cancellation_policy"), children_policy: nullable("children_policy"), pet_policy: nullable("pet_policy"), smoking_policy: nullable("smoking_policy"), extra_bed_policy: nullable("extra_bed_policy"), additional_rules: nullable("additional_rules") }; setSaving(true); setError(""); try { if (hotel.policy) await policyService.update(hotel.id, data); else await policyService.create(hotel.id, data); await reload(); } catch (e) { setError(e instanceof ApiError ? e.message : "Unable to save policy."); } finally { setSaving(false); } }
  return <section className="panel"><div><h2 className="section-title">Hotel policy</h2><p className="mt-1 text-sm text-slate-500">{hotel.policy ? "Update the current guest policy." : "No policy exists yet. Add one below."}</p></div><FormError message={error} /><form onSubmit={save} className="mt-5 grid gap-5 md:grid-cols-2">{([ ["cancellation_policy", "Cancellation policy"], ["children_policy", "Children policy"], ["pet_policy", "Pet policy"], ["smoking_policy", "Smoking policy"], ["extra_bed_policy", "Extra bed policy"], ["additional_rules", "Additional rules"] ] as const).map(([name, label]) => <label key={name}><span className="mb-1.5 block text-sm font-semibold">{label}</span><textarea name={name} defaultValue={policy[name] ?? ""} rows={4} className="input" /></label>)}<div className="md:col-span-2"><button disabled={saving} className="btn-primary">{saving ? "Saving…" : hotel.policy ? "Update policy" : "Create policy"}</button></div></form></section>;
}

function RoomsPanel({ hotel, reload }: { hotel: HotelDetail; reload: () => Promise<void> }) {
  const [reviewingId, setReviewingId] = useState<number | null>(null);
  const [reviewAction, setReviewAction] = useState<"APPROVED" | "NEEDS_CHANGES" | "BOOKABLE">("APPROVED");
  const [reviewNotes, setReviewNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submitReview(e: FormEvent) {
    e.preventDefault();
    if (!reviewingId) return;
    setSaving(true);
    setError("");
    try {
      await hotelService.reviewRoom(reviewingId, reviewAction, reviewNotes || null);
      setReviewingId(null);
      setReviewNotes("");
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to review room type.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="section-title">Room types</h2>
          <p className="mt-1 text-sm text-slate-500">Manage capacity, pricing, and validation lifecycle.</p>
        </div>
        <Link href={`/hotels/${hotel.id}/rooms/new`} className="btn-primary">Add Room Type</Link>
      </div>
      <FormError message={error} />
      {hotel.room_types.length === 0 ? (
        <p className="empty-state">No room types have been added.</p>
      ) : (
        <div className="mt-5 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b text-xs uppercase text-slate-500">
              <tr>
                {["Room", "Base price", "Total", "Guests", "Bed", "Status", "Review Notes", "Actions"].map((h) => (
                  <th key={h} className="px-3 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {hotel.room_types.map((room) => (
                <tr key={room.id}>
                  <td className="px-3 py-4 font-semibold">{room.name}</td>
                  <td className="px-3 py-4">{room.currency} {Number(room.base_price).toFixed(2)}</td>
                  <td className="px-3 py-4">{room.total_rooms}</td>
                  <td className="px-3 py-4">{room.max_guests}</td>
                  <td className="px-3 py-4">{room.bed_count} × {room.bed_type}</td>
                  <td className="px-3 py-4">
                    <span className="inline-flex items-center rounded-md px-2 py-1 text-xs font-bold ring-1 ring-inset ring-slate-300">
                      {room.status ?? (room.is_active ? "ACTIVE" : "INACTIVE")}
                    </span>
                  </td>
                  <td className="px-3 py-4 text-xs text-slate-500 max-w-xs truncate">
                    {room.review_notes || "-"}
                  </td>
                  <td className="px-3 py-4">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => {
                          setReviewingId(room.id);
                          setReviewAction(room.status === "APPROVED" ? "BOOKABLE" : "APPROVED");
                          setReviewNotes(room.review_notes || "");
                        }}
                        className="text-xs font-bold text-indigo-600 hover:text-indigo-900"
                      >
                        Review
                      </button>
                      <Link className="link" href={`/hotels/${hotel.id}/rooms/${room.id}/edit`}>Edit</Link>
                      <Link className="link" href={`/hotels/${hotel.id}/rooms/${room.id}/inventory`}>Inventory</Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {reviewingId && (
        <div className="mt-6 rounded-xl border border-indigo-200 bg-indigo-50/50 p-5">
          <h3 className="font-bold text-sm text-slate-800">Review Room Type #{reviewingId}</h3>
          <form onSubmit={submitReview} className="mt-3 space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <label className="text-xs font-semibold text-slate-700">Action:</label>
              <select
                value={reviewAction}
                onChange={(e) => setReviewAction(e.target.value as "APPROVED" | "NEEDS_CHANGES" | "BOOKABLE")}
                className="input w-auto text-xs py-1.5"
              >
                <option value="APPROVED">Approve (APPROVED)</option>
                <option value="NEEDS_CHANGES">Request Changes (NEEDS_CHANGES)</option>
                <option value="BOOKABLE">Set Bookable (BOOKABLE)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Feedback / Review Notes:</label>
              <textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Notes for hotel partner..."
                rows={2}
                className="input text-xs"
              />
            </div>
            <div className="flex gap-2">
              <button type="submit" disabled={saving} className="btn-primary text-xs py-1.5 px-3">
                {saving ? "Saving..." : "Save Review Decision"}
              </button>
              <button
                type="button"
                onClick={() => setReviewingId(null)}
                className="btn-secondary text-xs py-1.5 px-3"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
}

function InventoryPanel({ hotel }: { hotel: HotelDetail }) { return <section className="panel"><h2 className="section-title">Inventory by room</h2><p className="mt-1 text-sm text-slate-500">Inventory is managed per room type and date range.</p>{hotel.room_types.length === 0 ? <p className="empty-state">Add a room type before managing inventory.</p> : <div className="mt-5 grid gap-3 sm:grid-cols-2">{hotel.room_types.map((room) => <Link key={room.id} href={`/hotels/${hotel.id}/rooms/${room.id}/inventory`} className="rounded-xl border border-slate-200 p-4 hover:border-indigo-300 hover:bg-indigo-50"><span className="block font-bold">{room.name}</span><span className="mt-1 block text-sm text-slate-500">Manage dated availability and pricing →</span></Link>)}</div>}</section>; }

function ImagesPanel({ hotel, reload }: { hotel: HotelDetail; reload: () => Promise<void> }) {
  const [error, setError] = useState("");
  async function add(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const formElement = event.currentTarget; const form = new FormData(formElement); try { await hotelService.addImage(hotel.id, { image_url: String(form.get("image_url")), alt_text: String(form.get("alt_text")).trim() || null, is_cover: form.get("is_cover") === "on", display_order: Number(form.get("display_order")) }); formElement.reset(); await reload(); } catch (e) { setError(e instanceof ApiError ? e.message : "Unable to add image."); } }
  async function remove(id: number) { if (!window.confirm("Remove this image entry?")) return; try { await hotelService.removeImage(hotel.id, id); await reload(); } catch (e) { setError(e instanceof ApiError ? e.message : "Unable to remove image."); } }
  return <div className="grid gap-6 lg:grid-cols-[2fr_1fr]"><section className="panel"><h2 className="section-title">Hotel images</h2><FormError message={error} />{hotel.images.length === 0 ? <p className="empty-state">No image URLs added.</p> : <div className="mt-5 grid gap-4 sm:grid-cols-2">{hotel.images.map((image) => <article key={image.id} className="overflow-hidden rounded-xl border"><div className="aspect-video bg-slate-100"><img src={image.image_url} alt={image.alt_text || hotel.name} className="h-full w-full object-cover" /></div><div className="flex items-center justify-between p-3"><span className="text-sm">{image.is_cover ? "Cover image" : image.alt_text || "Hotel image"}</span><button className="text-sm font-semibold text-red-700" onClick={() => void remove(image.id)}>Remove</button></div></article>)}</div>}</section><section className="panel"><h2 className="section-title">Add image URL</h2><form onSubmit={add} className="mt-5 space-y-4"><SmallField label="Image URL" name="image_url" type="url" required /><SmallField label="Alt text" name="alt_text" /><SmallField label="Display order" name="display_order" type="number" min={0} defaultValue={0} /><label className="flex gap-2 text-sm font-semibold"><input name="is_cover" type="checkbox" /> Set as cover</label><button className="btn-primary w-full">Add image</button></form></section></div>;
}

function Detail({ label, value }: { label: string; value: string }) { return <div><dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt><dd className="mt-1 font-semibold">{value}</dd></div>; }
function SmallField({ label, ...props }: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) { return <label><span className="mb-1.5 block text-sm font-semibold">{label}</span><input {...props} className="input" /></label>; }
