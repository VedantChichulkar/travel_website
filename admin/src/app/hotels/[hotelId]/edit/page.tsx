"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FormError } from "@/components/FormError";
import { HotelForm } from "@/components/HotelForm";
import { ApiError } from "@/services/api";
import { hotelService } from "@/services/hotel.service";
import type { Hotel } from "@/types/hotel";

export default function EditHotelPage() {
  const { hotelId: hotelIdParam } = useParams<{ hotelId: string }>(); const router = useRouter(); const hotelId = Number(hotelIdParam);
  const [hotel, setHotel] = useState<Hotel | null>(null); const [error, setError] = useState("");
  useEffect(() => { void hotelService.get(hotelId).then(setHotel).catch((e: unknown) => setError(e instanceof ApiError ? e.message : "Unable to load hotel.")); }, [hotelId]);
  return <div className="mx-auto max-w-5xl"><Link href={`/hotels/${hotelId}`} className="link">← Back to hotel</Link><div className="my-6"><p className="eyebrow">Property details</p><h1 className="page-title">Edit hotel</h1></div><FormError message={error} />{hotel ? <div className="panel mt-5"><HotelForm initial={hotel} submitLabel="Save changes" onSubmit={async (data) => { await hotelService.update(hotelId, data); router.push(`/hotels/${hotelId}`); }} /></div> : !error && <div className="panel mt-5 text-slate-500">Loading hotel…</div>}</div>;
}
