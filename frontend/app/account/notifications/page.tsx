import type { Metadata } from "next";
import { NotificationCenter } from "@/src/components/account/NotificationCenter";
export const metadata: Metadata = { title: "Notifications" };
export default function AccountNotificationsPage() { return <NotificationCenter />; }
