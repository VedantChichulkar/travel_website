import type { Metadata } from "next";

import { AdminAuthProvider } from "@/context/AdminAuthContext";

import "./globals.css";

export const metadata: Metadata = {
  title: "Maharashtra Tourist Places Control Center",
  description: "Maharashtra Tourist Places platform operations and governance",
  robots: { index: false, follow: false, nocache: true },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-slate-100 text-slate-950">
        <AdminAuthProvider>{children}</AdminAuthProvider>
      </body>
    </html>
  );
}
