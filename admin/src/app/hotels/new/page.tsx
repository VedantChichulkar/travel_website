"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { HotelForm } from "@/components/HotelForm";
import { hotelService } from "@/services/hotel.service";

export default function NewHotelPage() {
  const router = useRouter();
  return <div className="mx-auto max-w-5xl"><Link href="/hotels" className="link">← Back to hotels</Link><div className="my-6"><p className="eyebrow">New property</p><h1 className="page-title">Add hotel</h1><p className="page-subtitle">New properties begin in DRAFT. Activate them after rooms and inventory are ready.</p></div><div className="panel"><HotelForm submitLabel="Create hotel" onSubmit={async (data) => { const hotel = await hotelService.create(data); router.push(`/hotels/${hotel.id}`); }} /></div></div>;
}
