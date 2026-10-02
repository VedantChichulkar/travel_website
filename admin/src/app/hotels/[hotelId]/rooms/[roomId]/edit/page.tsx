"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FormError } from "@/components/FormError";
import { RoomForm } from "@/components/RoomForm";
import { ApiError } from "@/services/api";
import { roomService } from "@/services/room.service";
import type { RoomType } from "@/types/hotel";

export default function EditRoomPage() { const { hotelId, roomId } = useParams<{ hotelId: string; roomId: string }>(); const router = useRouter(); const [room, setRoom] = useState<RoomType | null>(null); const [error, setError] = useState(""); useEffect(() => { void roomService.get(Number(roomId)).then((value) => { if (value.hotel_id !== Number(hotelId)) throw new Error("Room does not belong to this hotel."); setRoom(value); }).catch((e: unknown) => setError(e instanceof ApiError || e instanceof Error ? e.message : "Unable to load room.")); }, [hotelId, roomId]); return <div className="mx-auto max-w-4xl"><Link href={`/hotels/${hotelId}`} className="link">← Back to hotel</Link><div className="my-6"><p className="eyebrow">Rooms</p><h1 className="page-title">Edit room type</h1></div><FormError message={error} />{room ? <div className="panel mt-5"><RoomForm initial={room} submitLabel="Save room" onSubmit={async (data) => { const { is_active, ...updates } = data; await roomService.update(Number(roomId), updates); if (is_active !== room.is_active) await roomService.updateStatus(Number(roomId), is_active); router.push(`/hotels/${hotelId}`); }} /></div> : !error && <div className="panel text-slate-500">Loading room…</div>}</div>; }
