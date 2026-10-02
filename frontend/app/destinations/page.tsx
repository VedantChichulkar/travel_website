import type { Metadata } from "next";

import { DestinationsExplorer } from "@/src/components/destinations/DestinationsExplorer";

export const metadata: Metadata = {
  title: "Explore Maharashtra Destinations",
  description: "Browse Maharashtra districts and destination records using Maharashtra Tourist Places’ active destination directory.",
  alternates: { canonical: "/destinations" },
};

export default function DestinationsPage() {
  return <DestinationsExplorer />;
}
