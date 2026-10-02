"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { RoomForm } from "@/components/RoomForm";
import { roomService } from "@/services/room.service";

export default function NewRoomPage() { const { hotelId: hotelIdParam } = useParams<{ hotelId: string }>(); const hotelId = Number(hotelIdParam); const router = useRouter(); return <div className="mx-auto max-w-4xl"><Link href={`/hotels/${hotelId}`} className="link">← Back to hotel</Link><div className="my-6"><p className="eyebrow">Rooms</p><h1 className="page-title">Add room type</h1></div><div className="panel"><RoomForm submitLabel="Create room type" onSubmit={async (data) => { await roomService.create(hotelId, data); router.push(`/hotels/${hotelId}`); }} /></div></div>; }
