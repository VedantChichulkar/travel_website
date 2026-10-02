import type { Metadata } from "next";
import { Header } from "@/src/components/account/AccountDashboard";
import { MessagingWorkspace } from "@/src/components/MessagingWorkspace";
export const metadata: Metadata = { title: "Messages" };
export default function AccountMessagesPage() { return <div><Header eyebrow="Your account" title="Messages" description="Private customer-owned conversations connected to your hotel bookings. Contact details and internal notes remain hidden." /><MessagingWorkspace customer /></div>; }
