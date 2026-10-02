import type { Metadata } from "next";
import { PaymentHistory } from "@/src/components/account/PaymentHistory";
export const metadata: Metadata = { title: "Payments & Receipts" };
export default function PaymentsPage() { return <PaymentHistory />; }
