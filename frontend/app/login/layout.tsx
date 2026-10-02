import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Customer login",
  description: "Sign in to manage your Maharashtra Tourist Places bookings, Safari requests, messages, and profile.",
  robots: { index: false, follow: false },
};

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return children;
}
