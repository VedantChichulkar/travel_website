import type { HotelSearchParams, HotelSort, PropertyType } from "@/src/types/hotel";
import { HOTEL_SORTS, PROPERTY_TYPES } from "@/src/types/hotel";
import { MAHARASHTRA_DESTINATION_NAMES } from "@/src/data/maharashtra-destinations";

type RawSearch = Record<string, string | string[] | undefined>;

function first(value: string | string[] | undefined): string { return Array.isArray(value) ? value[0] ?? "" : value ?? ""; }
function positiveInt(value: string, fallback: number, allowZero = false): number { const parsed = Number(value); const minimum = allowZero ? 0 : 1; return Number.isInteger(parsed) && parsed >= minimum ? parsed : fallback; }
function optionalNumber(value: string): number | undefined { if (!value) return undefined; const parsed = Number(value); return Number.isFinite(parsed) && parsed >= 0 ? parsed : undefined; }

export function parseHotelSearch(raw: RawSearch): HotelSearchParams {
  const property = first(raw.propertyType);
  const sort = first(raw.sort);
  const amenities = raw.amenities;
  return {
    city: first(raw.city).trim(), destination: first(raw.destination).trim() || undefined, checkIn: first(raw.checkIn), checkOut: first(raw.checkOut),
    adults: positiveInt(first(raw.adults), 2), children: positiveInt(first(raw.children), 0, true), rooms: positiveInt(first(raw.rooms), 1),
    minPrice: optionalNumber(first(raw.minPrice)), maxPrice: optionalNumber(first(raw.maxPrice)), starRating: optionalNumber(first(raw.starRating)),
    propertyType: PROPERTY_TYPES.includes(property as PropertyType) ? property as PropertyType : undefined,
    amenities: Array.isArray(amenities) ? amenities : amenities ? [amenities] : [],
    sort: HOTEL_SORTS.includes(sort as HotelSort) ? sort as HotelSort : "recommended",
  };
}

export function validateHotelSearch(params: HotelSearchParams): string {
  if (!params.city && !params.destination) return "Choose a Maharashtra destination or enter a city.";
  if (!params.destination && !MAHARASHTRA_DESTINATION_NAMES.some((city) => city.toLocaleLowerCase("en-IN") === params.city.toLocaleLowerCase("en-IN"))) return "Choose a destination from the suggestions.";
  if (Boolean(params.checkIn) !== Boolean(params.checkOut)) return "Select both check-in and check-out dates.";
  if (params.checkIn && params.checkOut && params.checkOut <= params.checkIn) return "Check-out must be after check-in.";
  if (params.adults < 1 || params.rooms < 1 || params.children < 0) return "Guest and room counts are invalid.";
  if (params.minPrice !== undefined && params.maxPrice !== undefined && params.minPrice > params.maxPrice) return "Minimum price cannot exceed maximum price.";
  return "";
}

export function validateStaySelection(params: HotelSearchParams): string {
  if (!params.checkIn || !params.checkOut) return "Select both check-in and check-out dates to view live room availability.";
  if (params.checkOut <= params.checkIn) return "Check-out must be after check-in.";
  if (params.adults < 1 || params.rooms < 1 || params.children < 0) return "Guest and room counts are invalid.";
  return "";
}

export function hotelSearchQuery(params: HotelSearchParams): string {
  const query = new URLSearchParams({ city: params.city, checkIn: params.checkIn, checkOut: params.checkOut, adults: String(params.adults), children: String(params.children), rooms: String(params.rooms) });
  if (params.destination) query.set("destination", params.destination);
  if (params.minPrice !== undefined) query.set("minPrice", String(params.minPrice));
  if (params.maxPrice !== undefined) query.set("maxPrice", String(params.maxPrice));
  if (params.starRating !== undefined) query.set("starRating", String(params.starRating));
  if (params.propertyType) query.set("propertyType", params.propertyType);
  params.amenities.forEach((amenity) => query.append("amenities", amenity));
  if (params.sort !== "recommended") query.set("sort", params.sort);
  return query.toString();
}

export function formatMoney(value: string | number, currency = "INR"): string {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: 0 }).format(Number(value));
}
