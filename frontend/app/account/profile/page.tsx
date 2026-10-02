import type { Metadata } from "next";
import { ProfileOverview } from "@/src/components/account/ProfileOverview";
export const metadata: Metadata = { title: "Profile" };
export default function AccountProfilePage() { return <ProfileOverview />; }
