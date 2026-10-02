import type { Metadata } from "next";
import { SafariAccount } from "@/src/components/safari/SafariAccount";

export const metadata: Metadata = { title: "Your Safari Requests", robots: { index: false, follow: false } };

export default function AccountSafarisPage() { return <SafariAccount />; }
