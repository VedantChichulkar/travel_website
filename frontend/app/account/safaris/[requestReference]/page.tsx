import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { SafariRequestDetail } from "@/src/components/safari/SafariRequestDetail";
export const metadata: Metadata = { title: "Safari Request" };
export default async function SafariRequestPage({ params }: { params: Promise<{ requestReference: string }> }) { const { requestReference } = await params; const value = decodeURIComponent(requestReference); if (!/^SAF-[A-Z0-9-]+$/i.test(value)) notFound(); return <SafariRequestDetail requestReference={value} />; }
