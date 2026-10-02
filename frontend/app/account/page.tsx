import type { Metadata } from "next";
import { AccountDashboard } from "@/src/components/account/AccountDashboard";
export const metadata: Metadata = { title: "Account Overview" };
export default function AccountPage() { return <AccountDashboard />; }
