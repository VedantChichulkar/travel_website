"use client";
/* eslint-disable @next/next/no-img-element -- public-media URLs are runtime values and already server-optimized */

import { FormEvent, useState } from "react";

import { FormError } from "@/components/FormError";
import { ApiError } from "@/services/api";
import { discoveryService } from "@/services/discovery.service";
import type { AdminDestination, AdminPlace, DiscoveryFAQ } from "@/types/discovery";

type Entity = AdminDestination | AdminPlace;

export function FAQEditor({ value, onChange }: { value: DiscoveryFAQ[]; onChange: (value: DiscoveryFAQ[]) => void }) {
  function patch(index: number, change: Partial<DiscoveryFAQ>) { onChange(value.map((item, itemIndex) => itemIndex === index ? {...item, ...change} : item)); }
  function move(index: number, direction: -1 | 1) { const target = index + direction; if (target < 0 || target >= value.length) return; const next = [...value]; [next[index], next[target]] = [next[target], next[index]]; onChange(next.map((item, itemIndex) => ({...item, display_order: itemIndex}))); }
  return <section className="panel space-y-4"><div className="flex items-center justify-between gap-3"><div><p className="eyebrow">FAQs</p><h2 className="mt-1 text-lg font-black">Questions and answers</h2><p className="mt-1 text-sm text-slate-500">Only active FAQs appear publicly, in this order.</p></div><button type="button" className="btn-secondary" onClick={() => onChange([...value, {question: "", answer: "", display_order: value.length, is_active: true}])}>Add FAQ</button></div>
    {value.length === 0 ? <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">No FAQs added. This section is optional.</p> : value.map((faq, index) => <div key={faq.id ?? `new-${index}`} className="space-y-3 rounded-xl border border-slate-200 p-4"><div className="flex justify-between gap-3"><strong className="text-sm">FAQ {index + 1}</strong><div className="flex gap-2"><button type="button" aria-label="Move FAQ up" onClick={() => move(index, -1)} disabled={index === 0}>↑</button><button type="button" aria-label="Move FAQ down" onClick={() => move(index, 1)} disabled={index === value.length - 1}>↓</button><button type="button" className="text-xs font-bold text-red-700" onClick={() => onChange(value.filter((_, itemIndex) => itemIndex !== index))}>Remove</button></div></div><label className="block text-sm font-bold">Question<input value={faq.question} onChange={(event) => patch(index, {question: event.target.value})} className="input mt-2" maxLength={500} /></label><label className="block text-sm font-bold">Answer<textarea value={faq.answer} onChange={(event) => patch(index, {answer: event.target.value})} className="input mt-2" rows={4} /></label><label className="flex items-center gap-2 text-sm font-bold"><input type="checkbox" checked={faq.is_active} onChange={(event) => patch(index, {is_active: event.target.checked})} />Active publicly</label></div>)}
  </section>;
}

export function DiscoveryPreview({ entity }: { entity: Entity }) {
  const place = "interests" in entity;
  return <section className="panel overflow-hidden p-0" aria-labelledby="preview-heading">
    {entity.image_url ? <img src={entity.image_url} alt={entity.image_alt ?? ""} className="h-56 w-full object-cover" /> : <div className="grid h-56 place-items-center bg-gradient-to-br from-blue-950 to-emerald-800 text-sm font-bold text-white">Category fallback will be used</div>}
    <div className="p-5"><p className="eyebrow">Secure admin preview</p><h2 id="preview-heading" className="mt-1 text-2xl font-black">{entity.name}</h2>
      <p className="mt-2 text-sm text-slate-600">{place ? entity.short_description : entity.description || "No description yet."}</p>
      {place && <div className="mt-3 flex flex-wrap gap-2">{entity.interests.map((value) => <span key={value.id} className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-800">{value.name}</span>)}</div>}
      <p className="mt-4 text-xs text-slate-500">/{entity.public_path.replace(/^\//, "")} · {entity.status}</p>
    </div>
  </section>;
}

export function LifecycleActions({ kind, entity, onChange }: { kind: "destinations" | "places"; entity: Entity; onChange: (entity: Entity) => void }) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  async function act(action: "publish" | "unpublish") {
    const warning = action === "unpublish" ? "This removes the page from all public discovery routes and may hide linked content." : "This makes the page visible across public discovery routes.";
    if (!window.confirm(`${warning}\n\nContinue?`)) return;
    const reason = window.prompt(`Reason for ${action}ing ${entity.name}`); if (!reason || reason.trim().length < 5) return;
    setBusy(true); setError("");
    try {
      const result = action === "publish" ? await discoveryService.publish<Entity>(kind, entity.id, entity.version, reason) : await discoveryService.unpublish<Entity>(kind, entity.id, entity.version, reason);
      onChange(result.entity);
      if (Object.values(result.affected).some(Boolean)) window.alert(`Impact recorded: ${Object.entries(result.affected).map(([key, value]) => `${key.replaceAll("_", " ")}: ${value}`).join(", ")}`);
    } catch (caught) { setError(caught instanceof ApiError ? caught.message : `Unable to ${action}.`); } finally { setBusy(false); }
  }
  return <div><div className="flex flex-wrap gap-2">{entity.status !== "PUBLISHED" ? <button disabled={busy} onClick={() => void act("publish")} className="btn-primary">Publish</button> : <button disabled={busy} onClick={() => void act("unpublish")} className="rounded-lg bg-red-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">Unpublish</button>}</div><div className="mt-3"><FormError message={error} /></div></div>;
}

export function DiscoveryMediaUpload({ entityType, entityId, onUploaded }: { entityType: "DESTINATION" | "PLACE"; entityId: number; onUploaded: () => Promise<void> | void }) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const element = event.currentTarget; const body = new FormData(element); setBusy(true); setError("");
    try { await discoveryService.uploadMedia(entityType, entityId, body); element.reset(); await onUploaded(); }
    catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to upload public media."); }
    finally { setBusy(false); }
  }
  return <form onSubmit={submit} className="panel space-y-4"><div><p className="eyebrow">Public media</p><h2 className="mt-1 text-lg font-black">Upload hero or gallery image</h2><p className="mt-1 text-sm text-slate-500">JPEG, PNG, or WebP · 8 MB · minimum 640 × 360. Files are verified, metadata-stripped, resized, and stored separately from private documents.</p></div>
    <label className="block text-sm font-bold">Image<input required name="file" type="file" accept="image/jpeg,image/png,image/webp" className="input mt-2" /></label>
    <label className="block text-sm font-bold">Accessible alt text<input required minLength={5} maxLength={300} name="alt_text" className="input mt-2" /></label>
    <div className="grid gap-4 sm:grid-cols-2"><label className="text-sm font-bold">Specificity<select name="specificity" className="input mt-2"><option value="SPECIFIC">Specific subject</option><option value="EDITORIAL">Editorial / regional</option><option value="FALLBACK">Category fallback</option></select></label><label className="text-sm font-bold">Rights verified on<input required name="rights_verified_at" type="date" max={new Date().toISOString().slice(0,10)} className="input mt-2" /></label></div>
    <div className="grid gap-4 sm:grid-cols-2"><label className="text-sm font-bold">Placement<select name="role" className="input mt-2"><option value="HERO">Hero / primary</option><option value="GALLERY">Gallery</option></select></label><label className="text-sm font-bold">Display order<input name="display_order" type="number" min={0} defaultValue={0} className="input mt-2" /></label></div>
    <div className="grid gap-4 sm:grid-cols-2"><label className="text-sm font-bold">Creator / owner<input required name="creator_owner" className="input mt-2" /></label><label className="text-sm font-bold">Source name<input required name="source_name" className="input mt-2" /></label></div>
    <label className="block text-sm font-bold">Source URL<input name="source_url" type="url" className="input mt-2" placeholder="https://…" /></label>
    <label className="block text-sm font-bold">Usage basis<input required minLength={3} name="usage_basis" className="input mt-2" placeholder="Owned, commissioned, licensed…" /></label>
    <label className="block text-sm font-bold">Attribution text<input name="attribution_text" className="input mt-2" /></label>
    <label className="flex items-start gap-3 text-sm"><input name="subject_match_confirmed" value="true" type="checkbox" className="mt-1" /><span>I confirm that a “Specific subject” image depicts this exact destination or place.</span></label>
    <FormError message={error} /><button disabled={busy} className="btn-primary">{busy ? "Processing…" : "Upload verified media"}</button>
  </form>;
}

export function DiscoveryMediaManager({ entityType, entity, onChange }: { entityType: "DESTINATION" | "PLACE"; entity: Entity; onChange: (entity: Entity) => void }) {
  const [busy, setBusy] = useState<number | null>(null); const [error, setError] = useState("");
  async function update(mediaId: number, role: "HERO" | "GALLERY", displayOrder: number, altText: string) { setBusy(mediaId); setError(""); try { onChange(await discoveryService.updateMedia<Entity>(entityType, entity.id, mediaId, {expected_version: entity.version, role, display_order: displayOrder, alt_text: altText})); } catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to update media."); } finally { setBusy(null); } }
  async function retire(mediaId: number) { if (!window.confirm("Retire this image? It will stop appearing publicly but its rights record will remain.")) return; setBusy(mediaId); setError(""); try { onChange(await discoveryService.retireMedia<Entity>(entityType, entity.id, mediaId, entity.version)); } catch (caught) { setError(caught instanceof ApiError ? caught.message : "Unable to retire media."); } finally { setBusy(null); } }
  if (!entity.media.length) return null;
  return <section className="panel space-y-4"><div><p className="eyebrow">Media gallery</p><h2 className="mt-1 text-lg font-black">Current images</h2></div><FormError message={error} /><div className="grid gap-4 sm:grid-cols-2">{entity.media.map((media) => <MediaRow key={media.id} media={media} busy={busy === media.id} onSave={update} onRetire={retire} />)}</div></section>;
}

function MediaRow({ media, busy, onSave, onRetire }: { media: Entity["media"][number]; busy: boolean; onSave: (id: number, role: "HERO" | "GALLERY", order: number, alt: string) => Promise<void>; onRetire: (id: number) => Promise<void> }) {
  const [role, setRole] = useState(media.role); const [order, setOrder] = useState(media.display_order); const [alt, setAlt] = useState(media.alt_text);
  return <article className="overflow-hidden rounded-xl border border-slate-200"><img src={media.public_url} alt="" className="h-40 w-full object-cover" /><div className="space-y-3 p-4"><label className="block text-xs font-bold">Alt text<input className="input mt-1" value={alt} onChange={(event) => setAlt(event.target.value)} /></label><div className="grid grid-cols-2 gap-2"><label className="text-xs font-bold">Role<select className="input mt-1" value={role} onChange={(event) => setRole(event.target.value as "HERO" | "GALLERY")}><option>HERO</option><option>GALLERY</option></select></label><label className="text-xs font-bold">Order<input className="input mt-1" type="number" min={0} value={order} onChange={(event) => setOrder(Number(event.target.value))} /></label></div><p className="text-xs text-slate-500">{media.creator_owner} · {media.source_name} · rights checked {media.rights_verified_at}</p><div className="flex gap-2"><button type="button" disabled={busy || alt.trim().length < 5} className="btn-primary" onClick={() => void onSave(media.id, role, order, alt)}>Save</button><button type="button" disabled={busy} className="text-xs font-bold text-red-700" onClick={() => void onRetire(media.id)}>Retire</button></div></div></article>;
}
