import type { Metadata } from "next";
import { SafariCatalog } from "@/src/components/safari/SafariCatalog";

export const metadata: Metadata = {
  title: "Jungle Safaris",
  description: "Explore supported jungle safaris and send a managed availability request through Maharashtra Tourist Places.",
  alternates: { canonical: "/safaris" },
  openGraph: { images: [{ url: "/images/safaris/tiger-forest-hero.webp", alt: "A tiger walking through a forest habitat" }] },
};

export default function SafarisPage() {
  return <SafariCatalog />;
}
