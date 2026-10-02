import type { Metadata } from "next";

export const metadata: Metadata = { title: { default: "Advertiser workspace", template: "%s | Maharashtra Tourist Places" }, robots: { index: false, follow: false, nocache: true } };
export default function AdvertiserLayout({ children }: { children: React.ReactNode }) { return children; }
