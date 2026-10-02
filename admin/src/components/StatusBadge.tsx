import { AdminStatus } from "@/components/AdminStatus";
export function StatusBadge({ status }: { status: string }) { return <AdminStatus value={status} />; }
