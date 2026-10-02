import { AdminShell } from "@/components/AdminShell";

export default function HotelsLayout({ children }: LayoutProps<"/hotels">) {
  return <AdminShell>{children}</AdminShell>;
}
