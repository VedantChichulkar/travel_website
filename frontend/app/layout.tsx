import type { Metadata } from "next";

import { Navigation } from "@/src/components/Navigation";
import { AuthProvider } from "@/src/context/AuthContext";

import "./globals.css";

export const metadata: Metadata = {
  title: "Travel Booking",
  description: "Customer travel booking portal",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-slate-50 text-slate-950">
        <AuthProvider>
          <div className="flex min-h-screen flex-col">
            <Navigation />
            <main className="flex flex-1 flex-col">{children}</main>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
