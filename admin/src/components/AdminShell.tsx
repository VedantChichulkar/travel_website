"use client";

import { AdminGuard } from "@/components/AdminGuard";
import { AdminNavigation } from "@/components/AdminNavigation";

export function AdminShell({ children }: { children: React.ReactNode }) {
  return (
    <AdminGuard>
      <div className="min-h-screen">
        <AdminNavigation />
        <main className="px-4 py-8 sm:px-6 md:ml-64 lg:px-10">{children}</main>
      </div>
    </AdminGuard>
  );
}
