"use client";
import { useParams } from "next/navigation";
import { DestinationEditor } from "@/components/DestinationEditor";
export default function DestinationPage() { const params = useParams<{id: string}>(); return <DestinationEditor id={Number(params.id)} />; }
