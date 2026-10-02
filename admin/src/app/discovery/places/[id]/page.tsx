"use client";
import { useParams } from "next/navigation";
import { PlaceEditor } from "@/components/PlaceEditor";
export default function PlacePage() { const params = useParams<{id: string}>(); return <PlaceEditor id={Number(params.id)} />; }
