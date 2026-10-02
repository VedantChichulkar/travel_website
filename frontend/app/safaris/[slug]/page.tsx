import type { Metadata } from "next";

import { SafariDetailView } from "@/src/components/safari/SafariDetailView";
import { getSafariOrNotFound } from "@/src/lib/safari-data";

export async function generateMetadata({ params }: PageProps<"/safaris/[slug]">): Promise<Metadata> {
  const { slug } = await params; const safari = await getSafariOrNotFound(slug);
  const description = safari.short_description.slice(0, 155);
  return { title: safari.name, description, alternates: { canonical: `/safaris/${safari.slug}` }, openGraph: { title: safari.name, description, url: `/safaris/${safari.slug}`, images: [{ url: "/images/safaris/tiger-forest-hero.webp", alt: "Representative Maharashtra wildlife and forest landscape" }] } };
}

export default async function SafariPage({ params }: PageProps<"/safaris/[slug]">) {
  const { slug } = await params;
  return <SafariDetailView safari={await getSafariOrNotFound(slug)} />;
}
