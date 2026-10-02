import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Create a customer account",
  description: "Create a Maharashtra Tourist Places customer account to manage supported travel bookings and requests.",
  robots: { index: false, follow: false },
};

export default function RegisterLayout({ children }: { children: React.ReactNode }) {
  return children;
}
