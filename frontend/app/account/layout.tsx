import type { Metadata } from "next";
import { AccountShell } from "@/src/components/account/AccountShell";

export const metadata: Metadata = { title: { default: "Your Account", template: "%s | Maharashtra Tourist Places" }, robots: { index: false, follow: false, nocache: true } };

export default function AccountLayout({ children }: { children: React.ReactNode }) { return <AccountShell>{children}</AccountShell>; }
