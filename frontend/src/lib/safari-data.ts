import { notFound } from "next/navigation";
import { ApiError } from "@/src/services/api";
import { safariService } from "@/src/services/safari.service";

export async function getSafariOrNotFound(slug: string) {
  try { return await safariService.get(slug); }
  catch (error) { if (error instanceof ApiError && error.status === 404) notFound(); throw error; }
}
