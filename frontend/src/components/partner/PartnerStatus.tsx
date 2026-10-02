import { partnerStatus } from "@/src/lib/partner-status";
export function PartnerStatus({ value }: { value: string | null | undefined }) { const display = partnerStatus(value); return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-black ${display.className}`}>{display.label}</span>; }
