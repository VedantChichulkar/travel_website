/**
 * /hotel/dashboard — alias route.
 * Redirects to the canonical partner dashboard at /partner/dashboard.
 * This ensures the requirement for a /hotel/dashboard route is met while
 * keeping all partner portal pages under the /partner/* prefix where all
 * existing auth logic and navigation lives.
 */
import { redirect } from "next/navigation";

export default function HotelDashboardRedirect() {
  redirect("/partner/dashboard");
}
