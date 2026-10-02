import type { Metadata } from "next";

import { Footer } from "@/src/components/Footer";
import { Navigation } from "@/src/components/Navigation";
import { AuthProvider } from "@/src/context/AuthContext";

import "./globals.css";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? (
  process.env.NODE_ENV === "development" ? "http://localhost:3000" : undefined
);
if (!siteUrl) throw new Error("NEXT_PUBLIC_SITE_URL is not configured");

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "Maharashtra Tourist Places — Maharashtra, thoughtfully explored", template: "%s | Maharashtra Tourist Places" },
  description: "Discover Maharashtra destinations, active stays, and supported safari experiences with Maharashtra Tourist Places.",
  openGraph: {
    title: "Maharashtra Tourist Places — Maharashtra, thoughtfully explored",
    description: "Discover Maharashtra destinations, active stays, and supported safari experiences with Maharashtra Tourist Places.",
    images: [{ url: "/og.png", width: 1536, height: 1024, alt: "Maharashtra Tourist Places — Maharashtra, thoughtfully explored" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Maharashtra Tourist Places — Maharashtra, thoughtfully explored",
    description: "Discover Maharashtra destinations, active stays, and supported safari experiences with Maharashtra Tourist Places.",
    images: ["/og.png"],
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased" data-scroll-behavior="smooth">
      <body className="min-h-full">
        <AuthProvider>
          <div className="flex min-h-screen flex-col">
            <Navigation />
            <main className="flex flex-1 flex-col">{children}</main>
            <Footer />
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
