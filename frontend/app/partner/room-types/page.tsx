"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { authService } from "@/src/services/auth.service";
import { partnerService } from "@/src/services/partner.service";
import { tokenStorage } from "@/src/services/token-storage";
import type {
  AmenityData,
  MealAddOnOption,
  PartnerOverview,
  PartnerRoomType,
  PartnerRoomTypeInput,
  RoomTypeStatus,
} from "@/src/types/partner";

// ─── Status Visual Config ──────────────────────────────────────────────────────

const STATUS_CONFIGS: Record<
  RoomTypeStatus,
  { label: string; color: string; dot: string; pulse?: boolean }
> = {
  DRAFT: {
    label: "Draft",
    color: "bg-slate-100 text-slate-700 border-slate-200",
    dot: "bg-slate-400",
  },
  PENDING: {
    label: "Pending Validation",
    color: "bg-amber-100 text-amber-800 border-amber-200",
    dot: "bg-amber-500",
    pulse: true,
  },
  APPROVED: {
    label: "Approved",
    color: "bg-emerald-100 text-emerald-800 border-emerald-200",
    dot: "bg-emerald-500",
  },
  NEEDS_CHANGES: {
    label: "Needs Changes",
    color: "bg-rose-100 text-rose-800 border-rose-200",
    dot: "bg-rose-500",
  },
  BOOKABLE: {
    label: "Bookable (Live)",
    color: "bg-blue-100 text-blue-800 border-blue-200",
    dot: "bg-blue-500",
  },
};

function StatusBadge({ status }: { status: RoomTypeStatus }) {
  const cfg = STATUS_CONFIGS[status] ?? {
    label: status,
    color: "bg-slate-100 text-slate-700 border-slate-200",
    dot: "bg-slate-400",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-bold ${cfg.color}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${cfg.dot}${
          cfg.pulse ? " animate-pulse" : ""
        }`}
      />
      {cfg.label}
    </span>
  );
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function IconGrid() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  );
}

function IconBuilding() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z" />
      <path d="M6 12H4a2 2 0 0 0-2 2v8h20v-8a2 2 0 0 0-2-2h-2" />
      <path d="M10 6h4M10 10h4M10 14h4M10 18h4" />
    </svg>
  );
}

function IconShield() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

function IconBed() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M2 4v16M2 8h18a2 2 0 0 1 2 2v10M2 17h20M6 8v9" />
    </svg>
  );
}

function IconPlus() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function IconCheck() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function IconAlertTriangle() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function IconMenu() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  );
}

function IconX() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function IconTrash() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-2 14H7L5 6m5 0V4a2 2 0 0 1 2-2h0a2 2 0 0 1 2 2v2" />
    </svg>
  );
}

function IconPhoto() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <circle cx="8.5" cy="8.5" r="1.5" />
      <path d="M21 15l-5-5L5 21" />
    </svg>
  );
}

// ─── Sidebar Component ────────────────────────────────────────────────────────

function Sidebar({
  hotelName,
  initials,
  userName,
  onLogout,
  mobileOpen,
  onMobileClose,
}: {
  hotelName: string;
  initials: string;
  userName: string;
  onLogout: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}) {
  const navItems = [
    { href: "/partner/dashboard", label: "Dashboard", icon: <IconGrid />, id: "nav-dashboard" },
    { href: "/partner/hotel-profile", label: "Hotel Profile", icon: <IconBuilding />, id: "nav-hotel-profile" },
    { href: "/partner/room-types", label: "Room Types", icon: <IconBed />, id: "nav-room-types" },
    { href: "/partner/inventory", label: "Inventory", icon: <IconGrid />, id: "nav-inventory" },
    { href: "/partner/booking-gateway", label: "Booking Gateway", icon: <IconShield />, id: "nav-booking-gateway" },
    { href: "/partner/operations", label: "Hotel Operations", icon: <IconGrid />, id: "nav-operations" },
    { href: "/partner/settlements", label: "Settlements", icon: "₹", id: "nav-settlements" },
    { href: "/partner/reviews", label: "Guest Reviews", icon: "★", id: "nav-reviews" },
    { href: "/partner/verification", label: "Verification", icon: <IconShield />, id: "nav-verification" },
  ];

  const content = (
    <div className="flex flex-col h-full">
      <div className="px-5 py-5 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-lg bg-[#172554] text-white text-xs font-black">
            V
          </div>
          <div className="min-w-0">
            <p className="text-xs font-black tracking-tight text-[#172554]">Maharashtra Tourist Places Portal</p>
            <p className="text-xs text-slate-400 truncate">{hotelName || "Hotel Partner"}</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 py-4 px-3 space-y-0.5">
        {navItems.map((item) => {
          const active = item.href === "/partner/room-types";
          return (
            <Link
              key={item.href}
              id={item.id}
              href={item.href}
              onClick={onMobileClose}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-bold transition-all duration-150 ${
                active
                  ? "bg-[#172554] text-white shadow-sm"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <span className={active ? "text-white" : "text-slate-400"}>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-3 pb-5 border-t border-slate-100 pt-4 space-y-1">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-full bg-[#ed6a3a] text-white text-xs font-black">
            {initials}
          </div>
          <span className="text-sm font-semibold text-slate-700 truncate">{userName}</span>
        </div>
        <button
          id="btn-sidebar-logout"
          onClick={onLogout}
          className="flex w-full items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-bold text-slate-500 hover:bg-red-50 hover:text-red-700 transition-colors"
        >
          Logout
        </button>
      </div>
    </div>
  );

  return (
    <>
      <aside className="hidden md:flex w-60 flex-col flex-shrink-0 bg-white border-r border-slate-100">
        {content}
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" onClick={onMobileClose} />
          <div className="relative z-10 w-72 bg-white h-full shadow-2xl flex flex-col">
            <div className="absolute top-4 right-4">
              <button
                onClick={onMobileClose}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700"
              >
                <IconX />
              </button>
            </div>
            {content}
          </div>
        </div>
      )}
    </>
  );
}

// ─── Main Room Types Page Component ───────────────────────────────────────────

export default function RoomTypesPage() {
  const router = useRouter();
  const [overview, setOverview] = useState<PartnerOverview | null>(null);
  const [rooms, setRooms] = useState<PartnerRoomType[]>([]);
  const [facilities, setFacilities] = useState<AmenityData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Status Filter
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  // Create / Edit Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRoom, setEditingRoom] = useState<PartnerRoomType | null>(null);
  const [modalSaving, setModalSaving] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // Form Fields
  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formBedType, setFormBedType] = useState("King Bed");
  const [formBedCount, setFormBedCount] = useState(1);
  const [formMaxAdults, setFormMaxAdults] = useState(2);
  const [formMaxChildren, setFormMaxChildren] = useState(1);
  const [formMaxGuests, setFormMaxGuests] = useState(3);
  const [formRoomSize, setFormRoomSize] = useState<number | "">(35);
  const [formBasePrice, setFormBasePrice] = useState<number | "">(4500);
  const [formCurrency, setFormCurrency] = useState("INR");
  const [formTotalRooms, setFormTotalRooms] = useState(5);
  const [formExtraBedRules, setFormExtraBedRules] = useState("");
  const [formAmenities, setFormAmenities] = useState<number[]>([]);
  const [formMealOptions, setFormMealOptions] = useState<MealAddOnOption[]>([]);

  // Images Modal State
  const [galleryModalRoom, setGalleryModalRoom] = useState<PartnerRoomType | null>(null);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageAlt, setImageAlt] = useState("");
  const [imageUrlInput, setImageUrlInput] = useState("");

  // ─── Authentication & Initial Data Load ─────────────────────────────────────

  const loadData = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const tokens = tokenStorage.getTokens();
      if (!tokens) {
        router.replace("/partner/login");
        return;
      }
      const user = await authService.getCurrentUser();
      if (!user || user.role !== "HOTEL_PARTNER") {
        router.replace("/partner/login");
        return;
      }
      const [ov, roomList, facList] = await Promise.all([
        partnerService.getOverview(),
        partnerService.getRoomTypes(),
        partnerService.getFacilities().catch(() => [] as AmenityData[]),
      ]);
      if (!ov.has_hotel) {
        router.replace("/partner/onboarding");
        return;
      }
      setOverview(ov);
      setRooms(roomList);
      setFacilities(facList);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load room types.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    queueMicrotask(() => void loadData());
  }, [loadData]);

  const handleLogout = () => {
    authService.logout();
    router.replace("/partner/login");
  };

  // ─── Open Modal in Create or Edit Mode ──────────────────────────────────────

  const openCreateModal = () => {
    setEditingRoom(null);
    setFormName("");
    setFormDescription("");
    setFormBedType("King Bed");
    setFormBedCount(1);
    setFormMaxAdults(2);
    setFormMaxChildren(1);
    setFormMaxGuests(3);
    setFormRoomSize(35);
    setFormBasePrice(4500);
    setFormCurrency("INR");
    setFormTotalRooms(5);
    setFormExtraBedRules("");
    setFormAmenities([]);
    setFormMealOptions([
      { name: "Buffet Breakfast", price: 450, currency: "INR" },
    ]);
    setModalError(null);
    setModalOpen(true);
  };

  const openEditModal = (room: PartnerRoomType) => {
    setEditingRoom(room);
    setFormName(room.name);
    setFormDescription(room.description || "");
    setFormBedType(room.bed_type);
    setFormBedCount(room.bed_count);
    setFormMaxAdults(room.max_adults);
    setFormMaxChildren(room.max_children);
    setFormMaxGuests(room.max_guests);
    setFormRoomSize(room.room_size_sqm ?? "");
    setFormBasePrice(room.base_price);
    setFormCurrency(room.currency || "INR");
    setFormTotalRooms(room.total_rooms);
    setFormExtraBedRules(room.extra_bed_rules || "");
    setFormAmenities(room.amenities.map((a) => a.id));
    setFormMealOptions(room.meal_add_on_options || []);
    setModalError(null);
    setModalOpen(true);
  };

  // ─── Save Room Type (Create or Update) ───────────────────────────────────────

  const handleSaveRoom = async (e: FormEvent) => {
    e.preventDefault();
    setModalError(null);

    // Client-side validations
    if (!formName.trim()) {
      setModalError("Please specify a room type name.");
      return;
    }
    if (formMaxAdults < 1) {
      setModalError("Maximum adults must be at least 1.");
      return;
    }
    if (formMaxGuests > formMaxAdults + formMaxChildren) {
      setModalError(
        `Total guests (${formMaxGuests}) cannot exceed adults (${formMaxAdults}) + children (${formMaxChildren}).`
      );
      return;
    }
    if (formBasePrice === "" || Number(formBasePrice) < 0) {
      setModalError("Please enter a valid base price.");
      return;
    }

    const payload: PartnerRoomTypeInput = {
      name: formName.trim(),
      description: formDescription.trim() || null,
      bed_type: formBedType,
      bed_count: Number(formBedCount),
      max_adults: Number(formMaxAdults),
      max_children: Number(formMaxChildren),
      max_guests: Number(formMaxGuests),
      room_size_sqm: formRoomSize === "" ? null : Number(formRoomSize),
      base_price: Number(formBasePrice),
      currency: formCurrency,
      total_rooms: Number(formTotalRooms),
      extra_bed_rules: formExtraBedRules.trim() || null,
      meal_add_on_options: formMealOptions.filter((m) => m.name.trim()),
      amenity_ids: formAmenities,
    };

    setModalSaving(true);
    try {
      if (editingRoom) {
        await partnerService.updateRoomType(editingRoom.id, payload);
        setNotice(`Room type "${formName}" updated.`);
      } else {
        await partnerService.createRoomType(payload);
        setNotice(`Room type "${formName}" created as Draft.`);
      }
      setModalOpen(false);
      await loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save room type.";
      setModalError(msg);
    } finally {
      setModalSaving(false);
    }
  };

  // ─── Submit for Maharashtra Tourist Places Validation ──────────────────────────────────────────

  const handleSubmitForReview = async (room: PartnerRoomType) => {
    setError(null);
    setNotice(null);

    if (!room.description || !room.description.trim()) {
      setError(`Cannot submit "${room.name}": Please add a description first.`);
      return;
    }
    if (!room.images || room.images.length === 0) {
      setError(`Cannot submit "${room.name}": Please add at least one room photo first.`);
      return;
    }

    try {
      await partnerService.submitRoomType(room.id);
      setNotice(`"${room.name}" submitted for Maharashtra Tourist Places validation.`);
      await loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Submission failed.");
    }
  };

  // ─── Delete Room ────────────────────────────────────────────────────────────

  const handleDeleteRoom = async (room: PartnerRoomType) => {
    if (!window.confirm(`Are you sure you want to delete "${room.name}"?`)) return;
    try {
      await partnerService.deleteRoomType(room.id);
      setNotice(`"${room.name}" was deleted.`);
      await loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unable to delete room type.");
    }
  };

  // ─── Gallery & Image Actions ────────────────────────────────────────────────

  const openGalleryModal = (room: PartnerRoomType) => {
    setGalleryModalRoom(room);
    setImageFile(null);
    setImageAlt("");
    setImageUrlInput("");
  };

  const handleUploadImage = async (e: FormEvent) => {
    e.preventDefault();
    if (!galleryModalRoom) return;

    setUploadingImage(true);
    setError(null);
    try {
      if (imageFile) {
        await partnerService.uploadRoomImage(galleryModalRoom.id, imageFile, imageAlt || undefined);
      } else if (imageUrlInput.trim()) {
        await partnerService.addRoomImage(galleryModalRoom.id, {
          image_url: imageUrlInput.trim(),
          alt_text: imageAlt.trim() || undefined,
        });
      } else {
        setError("Please select an image file or enter a valid URL.");
        setUploadingImage(false);
        return;
      }
      setImageFile(null);
      setImageAlt("");
      setImageUrlInput("");
      const updatedRooms = await partnerService.getRoomTypes();
      setRooms(updatedRooms);
      const updatedCurrent = updatedRooms.find((r) => r.id === galleryModalRoom.id);
      if (updatedCurrent) setGalleryModalRoom(updatedCurrent);
      setNotice("Photo added to room type.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Image upload failed.");
    } finally {
      setUploadingImage(false);
    }
  };

  const handleSetCover = async (imageId: number) => {
    if (!galleryModalRoom) return;
    try {
      await partnerService.setRoomCoverImage(galleryModalRoom.id, imageId);
      const updatedRooms = await partnerService.getRoomTypes();
      setRooms(updatedRooms);
      const updatedCurrent = updatedRooms.find((r) => r.id === galleryModalRoom.id);
      if (updatedCurrent) setGalleryModalRoom(updatedCurrent);
      setNotice("Cover photo updated.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to set cover photo.");
    }
  };

  const handleDeleteImage = async (imageId: number) => {
    if (!galleryModalRoom) return;
    if (!window.confirm("Remove this image?")) return;
    try {
      await partnerService.deleteRoomImage(galleryModalRoom.id, imageId);
      const updatedRooms = await partnerService.getRoomTypes();
      setRooms(updatedRooms);
      const updatedCurrent = updatedRooms.find((r) => r.id === galleryModalRoom.id);
      if (updatedCurrent) setGalleryModalRoom(updatedCurrent);
      setNotice("Photo removed.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete photo.");
    }
  };

  // ─── Filtered Rooms & Stats ─────────────────────────────────────────────────

  const filteredRooms = useMemo(() => {
    if (statusFilter === "ALL") return rooms;
    return rooms.filter((r) => r.status === statusFilter);
  }, [rooms, statusFilter]);

  const stats = useMemo(() => {
    return {
      total: rooms.length,
      bookable: rooms.filter((r) => r.status === "BOOKABLE").length,
      approved: rooms.filter((r) => r.status === "APPROVED").length,
      pending: rooms.filter((r) => r.status === "PENDING").length,
      needsChanges: rooms.filter((r) => r.status === "NEEDS_CHANGES").length,
      draft: rooms.filter((r) => r.status === "DRAFT").length,
    };
  }, [rooms]);

  const hotel = overview?.hotel;
  const initials = hotel?.name ? hotel.name.slice(0, 2).toUpperCase() : "VP";

  return (
    <div className="flex min-h-screen bg-[#f8fafc]">
      <Sidebar
        hotelName={hotel?.name || "My Hotel"}
        initials={initials}
        userName={hotel?.contact_email || "Partner Account"}
        onLogout={handleLogout}
        mobileOpen={mobileMenuOpen}
        onMobileClose={() => setMobileMenuOpen(false)}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Navbar */}
        <header className="sticky top-0 z-20 bg-white border-b border-slate-100 px-4 sm:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-2 rounded-xl text-slate-500 hover:bg-slate-100"
            >
              <IconMenu />
            </button>
            <div>
              <div className="flex items-center gap-2 text-xs font-bold text-slate-400">
                <Link href="/partner/dashboard" className="hover:text-slate-600">
                  Dashboard
                </Link>
                <span>/</span>
                <span className="text-slate-700">Room Types</span>
              </div>
              <h1 className="text-xl font-black tracking-tight text-[#0b163d]">
                Room Type Management
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link href="/partner/inventory" className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-bold text-[#172554] hover:bg-slate-50">Inventory</Link>
            <button
              id="btn-create-room"
              onClick={openCreateModal}
              className="flex items-center gap-2 rounded-xl bg-[#172554] px-4 py-2.5 text-sm font-bold text-white shadow-sm hover:bg-[#1e3a8a] transition-all"
            >
              <IconPlus />
              <span>Add Room Type</span>
            </button>
          </div>
        </header>

        {/* Content Body */}
        <main className="flex-1 p-4 sm:p-8 max-w-7xl mx-auto w-full space-y-6">
          {/* Notifications */}
          {error && (
            <div
              role="alert"
              className="flex items-center gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm font-bold text-rose-800"
            >
              <IconAlertTriangle />
              <div className="flex-1">{error}</div>
              <button
                onClick={() => setError(null)}
                className="text-xs font-black text-rose-600 hover:text-rose-900"
              >
                Dismiss
              </button>
            </div>
          )}

          {notice && (
            <div className="flex items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-bold text-emerald-800">
              <IconCheck />
              <div className="flex-1">{notice}</div>
              <button
                onClick={() => setNotice(null)}
                className="text-xs font-black text-emerald-600 hover:text-emerald-900"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Stats Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm">
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Total Rooms</p>
              <p className="mt-1 text-3xl font-black text-[#0b163d]">{stats.total}</p>
              <p className="mt-1 text-xs text-slate-500">Categories defined</p>
            </div>

            <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm">
              <p className="text-xs font-bold uppercase tracking-wider text-emerald-600">Approved / Live</p>
              <p className="mt-1 text-3xl font-black text-emerald-700">
                {stats.approved + stats.bookable}
              </p>
              <p className="mt-1 text-xs text-slate-500">{stats.bookable} bookable</p>
            </div>

            <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm">
              <p className="text-xs font-bold uppercase tracking-wider text-amber-600">Pending Review</p>
              <p className="mt-1 text-3xl font-black text-amber-700">{stats.pending}</p>
              <p className="mt-1 text-xs text-slate-500">Awaiting Maharashtra Tourist Places approval</p>
            </div>

            <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm">
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Drafts & Action</p>
              <p className="mt-1 text-3xl font-black text-slate-700">
                {stats.draft + stats.needsChanges}
              </p>
              <p className="mt-1 text-xs text-rose-500">
                {stats.needsChanges > 0 ? `${stats.needsChanges} need changes` : "Ready to configure"}
              </p>
            </div>
          </div>

          {/* Filter Chips */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {[
              { id: "ALL", label: `All (${rooms.length})` },
              { id: "DRAFT", label: `Draft (${stats.draft})` },
              { id: "PENDING", label: `Pending Review (${stats.pending})` },
              { id: "NEEDS_CHANGES", label: `Needs Changes (${stats.needsChanges})` },
              { id: "APPROVED", label: `Approved (${stats.approved})` },
              { id: "BOOKABLE", label: `Bookable (${stats.bookable})` },
            ].map((chip) => (
              <button
                key={chip.id}
                onClick={() => setStatusFilter(chip.id)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap ${
                  statusFilter === chip.id
                    ? "bg-[#172554] text-white shadow-sm"
                    : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
                }`}
              >
                {chip.label}
              </button>
            ))}
          </div>

          {/* Room Types Listing */}
          {loading ? (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="h-64 rounded-2xl bg-white border border-slate-100 p-6 animate-pulse space-y-4">
                <div className="h-6 bg-slate-100 rounded w-1/3" />
                <div className="h-4 bg-slate-100 rounded w-2/3" />
                <div className="h-24 bg-slate-100 rounded-xl" />
              </div>
              <div className="h-64 rounded-2xl bg-white border border-slate-100 p-6 animate-pulse space-y-4">
                <div className="h-6 bg-slate-100 rounded w-1/3" />
                <div className="h-4 bg-slate-100 rounded w-2/3" />
                <div className="h-24 bg-slate-100 rounded-xl" />
              </div>
            </div>
          ) : filteredRooms.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-12 text-center shadow-sm">
              <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-blue-50 text-[#172554]">
                <IconBed />
              </div>
              <h3 className="mt-4 text-lg font-black text-[#0b163d]">
                {statusFilter === "ALL"
                  ? "No room types created yet"
                  : `No room types match the filter "${statusFilter}"`}
              </h3>
              <p className="mt-1 text-sm text-slate-500 max-w-md mx-auto">
                Room types define your accommodations, bed configurations, maximum guest capacity,
                pricing, and amenities for guest bookings.
              </p>
              <button
                onClick={openCreateModal}
                className="mt-5 inline-flex items-center gap-2 rounded-xl bg-[#172554] px-5 py-2.5 text-sm font-bold text-white shadow-sm hover:bg-[#1e3a8a]"
              >
                <IconPlus />
                <span>Create First Room Type</span>
              </button>
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2">
              {filteredRooms.map((room) => {
                const coverImage =
                  room.images?.find((img) => img.is_cover) || room.images?.[0];
                return (
                  <article
                    key={room.id}
                    id={`room-card-${room.id}`}
                    className="flex flex-col justify-between rounded-3xl border border-slate-200/90 bg-white shadow-sm overflow-hidden transition-all hover:shadow-md"
                  >
                    <div>
                      {/* Image / Banner Header */}
                      <div className="relative aspect-[16/9] w-full bg-slate-100 overflow-hidden">
                        {coverImage ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={coverImage.image_url}
                            alt={coverImage.alt_text || room.name}
                            className="h-full w-full object-cover"
                          />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center bg-slate-100 text-slate-400 flex-col gap-2">
                            <IconPhoto />
                            <span className="text-xs font-semibold">No photos uploaded yet</span>
                          </div>
                        )}

                        <div className="absolute top-3 left-3">
                          <StatusBadge status={room.status} />
                        </div>

                        <div className="absolute top-3 right-3 flex items-center gap-1.5 rounded-xl bg-black/60 backdrop-blur-md px-2.5 py-1 text-xs font-bold text-white">
                          <IconPhoto />
                          <span>{room.images?.length || 0}</span>
                        </div>
                      </div>

                      {/* Card Content */}
                      <div className="p-6 space-y-4">
                        {/* Title & Price */}
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <h2 className="text-lg font-black text-[#0b163d] leading-snug">
                              {room.name}
                            </h2>
                            <p className="text-xs font-bold text-slate-500 mt-0.5">
                              {room.bed_count} × {room.bed_type}
                              {room.room_size_sqm ? ` · ${room.room_size_sqm} m²` : ""}
                              {` · ${room.total_rooms} units`}
                            </p>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <p className="text-lg font-black text-[#172554]">
                              ₹{Number(room.base_price).toLocaleString("en-IN")}
                            </p>
                            <p className="text-[10px] font-bold text-slate-400">per night</p>
                          </div>
                        </div>

                        {/* Description */}
                        <p className="text-xs text-slate-600 line-clamp-2">
                          {room.description || "No description provided."}
                        </p>

                        {/* Occupancy details */}
                        <div className="flex flex-wrap gap-2 text-xs font-bold text-slate-600">
                          <span className="rounded-lg bg-slate-100 px-2.5 py-1">
                            👤 Max {room.max_adults} Adults
                          </span>
                          {room.max_children > 0 && (
                            <span className="rounded-lg bg-slate-100 px-2.5 py-1">
                              👶 Max {room.max_children} Children
                            </span>
                          )}
                          <span className="rounded-lg bg-slate-100 px-2.5 py-1">
                            👥 Max {room.max_guests} Guests
                          </span>
                          <span className="rounded-lg bg-indigo-50 text-indigo-700 px-2.5 py-1">
                            v{room.version}
                          </span>
                        </div>

                        {/* Amenities Chips */}
                        {room.amenities?.length > 0 && (
                          <div className="flex flex-wrap gap-1.5">
                            {room.amenities.slice(0, 4).map((a) => (
                              <span
                                key={a.id}
                                className="rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-semibold text-slate-600"
                              >
                                {a.name}
                              </span>
                            ))}
                            {room.amenities.length > 4 && (
                              <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-semibold text-slate-400">
                                +{room.amenities.length - 4} more
                              </span>
                            )}
                          </div>
                        )}

                        {/* Meal / Add-on Options */}
                        {room.meal_add_on_options?.length > 0 && (
                          <div className="border-t border-slate-100 pt-3">
                            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                              Meal / Add-On Options
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                              {room.meal_add_on_options.map((option, idx) => (
                                <span
                                  key={idx}
                                  className="rounded-lg bg-amber-50 border border-amber-200/80 px-2 py-1 text-xs font-semibold text-amber-900"
                                >
                                  {option.name} (+₹{Number(option.price).toLocaleString("en-IN")})
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Extra Bed Rules */}
                        {room.extra_bed_rules && (
                          <p className="text-[11px] text-slate-500 italic">
                            <span className="font-bold">Extra-bed policy:</span> {room.extra_bed_rules}
                          </p>
                        )}

                        {/* Needs Changes Alert */}
                        {room.status === "NEEDS_CHANGES" && (
                          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-3.5 space-y-1">
                            <div className="flex items-center gap-2 text-xs font-black text-rose-800">
                              <IconAlertTriangle />
                              <span>Maharashtra Tourist Places Reviewer Feedback:</span>
                            </div>
                            <p className="text-xs text-rose-700">
                              {room.review_notes || "Please review room details and photos."}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Card Actions Footer */}
                    <div className="border-t border-slate-100 bg-slate-50/70 p-4 flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => openGalleryModal(room)}
                          className="text-xs font-bold text-[#172554] hover:text-[#1e3a8a] bg-white border border-slate-200 px-3 py-1.5 rounded-lg shadow-2xs hover:bg-slate-50 transition"
                        >
                          Photos ({room.images?.length || 0})
                        </button>
                        <button
                          onClick={() => openEditModal(room)}
                          className="text-xs font-bold text-slate-700 hover:text-slate-900 bg-white border border-slate-200 px-3 py-1.5 rounded-lg shadow-2xs hover:bg-slate-50 transition"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteRoom(room)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition"
                          title="Delete room type"
                        >
                          <IconTrash />
                        </button>
                      </div>

                      {(room.status === "DRAFT" || room.status === "NEEDS_CHANGES") && (
                        <button
                          id={`btn-submit-${room.id}`}
                          onClick={() => handleSubmitForReview(room)}
                          className="inline-flex items-center gap-1.5 rounded-xl bg-[#172554] px-3.5 py-1.5 text-xs font-bold text-white shadow-xs hover:bg-[#1e3a8a] transition"
                        >
                          <span>Submit for Review</span>
                          <span>→</span>
                        </button>
                      )}

                      {room.status === "PENDING" && (
                        <span className="text-xs font-bold text-amber-700 flex items-center gap-1.5">
                          <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
                          Under Review
                        </span>
                      )}

                      {(room.status === "APPROVED" || room.status === "BOOKABLE") && (
                        <span className="text-xs font-bold text-emerald-700 flex items-center gap-1">
                          <IconCheck />
                          Validated by Maharashtra Tourist Places
                        </span>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </main>
      </div>

      {/* ─── CREATE / EDIT MODAL ──────────────────────────────────────────────── */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs overflow-y-auto">
          <div className="relative w-full max-w-2xl bg-white rounded-3xl shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-black text-[#0b163d]">
                  {editingRoom ? `Edit "${editingRoom.name}"` : "Create New Room Type"}
                </h3>
                <p className="text-xs text-slate-400">
                  {editingRoom
                    ? "Updating an approved room will return it to Draft for re-validation."
                    : "Fill in the room attributes for Maharashtra Tourist Places guest discovery and booking."}
                </p>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700"
              >
                <IconX />
              </button>
            </div>

            {/* Modal Form Body */}
            <form onSubmit={handleSaveRoom} className="flex-1 overflow-y-auto p-6 space-y-6">
              {modalError && (
                <div className="rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-xs font-bold text-rose-800">
                  {modalError}
                </div>
              )}

              {/* Basic Information */}
              <div className="space-y-4">
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-400">
                  1. Basic Details
                </h4>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Room Type Name *
                  </label>
                  <input
                    required
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder="e.g. Deluxe Ocean View Suite"
                    className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm font-semibold text-slate-800 focus:border-[#172554] focus:ring-1 focus:ring-[#172554] outline-hidden"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Description (Required for validation)
                  </label>
                  <textarea
                    rows={3}
                    value={formDescription}
                    onChange={(e) => setFormDescription(e.target.value)}
                    placeholder="Describe room view, interior style, highlights..."
                    className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm font-medium text-slate-800 focus:border-[#172554] focus:ring-1 focus:ring-[#172554] outline-hidden"
                  />
                </div>
              </div>

              {/* Bedding & Capacity */}
              <div className="space-y-4">
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-400">
                  2. Bed Configuration & Occupancy
                </h4>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      Bed Type *
                    </label>
                    <select
                      value={formBedType}
                      onChange={(e) => setFormBedType(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm font-semibold text-slate-800 focus:border-[#172554] outline-hidden"
                    >
                      <option>King Bed</option>
                      <option>Queen Bed</option>
                      <option>Twin Beds</option>
                      <option>Double Bed</option>
                      <option>Single Bed</option>
                      <option>Bunk Bed</option>
                      <option>Sofa Bed</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      Bed Count *
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={formBedCount}
                      onChange={(e) => setFormBedCount(Math.max(1, Number(e.target.value)))}
                      className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm font-semibold text-slate-800 focus:border-[#172554] outline-hidden"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      Max Adults *
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={formMaxAdults}
                      onChange={(e) => {
                        const val = Math.max(1, Number(e.target.value));
                        setFormMaxAdults(val);
                        if (formMaxGuests > val + formMaxChildren) {
                          setFormMaxGuests(val + formMaxChildren);
                        }
                      }}
                      className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-800"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      Max Children
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={20}
                      value={formMaxChildren}
                      onChange={(e) => {
                        const val = Math.max(0, Number(e.target.value));
                        setFormMaxChildren(val);
                        if (formMaxGuests > formMaxAdults + val) {
                          setFormMaxGuests(formMaxAdults + val);
                        }
                      }}
                      className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-800"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      Total Capacity *
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={formMaxAdults + formMaxChildren}
                      value={formMaxGuests}
                      onChange={(e) => setFormMaxGuests(Math.max(1, Number(e.target.value)))}
                      className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-800"
                    />
                  </div>
                </div>
              </div>

              {/* Pricing & Units */}
              <div className="space-y-4">
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-400">
                  3. Pricing & Units
                </h4>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      Base Price (₹) *
                    </label>
                    <input
                      type="number"
                      min={0}
                      step={10}
                      value={formBasePrice}
                      onChange={(e) =>
                        setFormBasePrice(e.target.value === "" ? "" : Number(e.target.value))
                      }
                      className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm font-semibold text-slate-800"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Currency</label>
                    <input
                      disabled
                      value={formCurrency}
                      className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm font-semibold text-slate-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      Total Units *
                    </label>
                    <input
                      type="number"
                      min={1}
                      value={formTotalRooms}
                      onChange={(e) => setFormTotalRooms(Math.max(1, Number(e.target.value)))}
                      className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm font-semibold text-slate-800"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Room Size (m²)
                  </label>
                  <input
                    type="number"
                    min={5}
                    value={formRoomSize}
                    onChange={(e) =>
                      setFormRoomSize(e.target.value === "" ? "" : Number(e.target.value))
                    }
                    placeholder="e.g. 35"
                    className="w-full rounded-xl border border-slate-200 px-3.5 py-2 text-sm font-semibold text-slate-800"
                  />
                </div>
              </div>

              {/* Extra Bed & Meal Options */}
              <div className="space-y-4">
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-400">
                  4. Extra-Bed Rules & Meal Add-Ons
                </h4>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Extra-Bed Policy
                  </label>
                  <input
                    value={formExtraBedRules}
                    onChange={(e) => setFormExtraBedRules(e.target.value)}
                    placeholder="e.g. 1 rollaway bed available on request at ₹800/night"
                    className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm font-semibold text-slate-800"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs font-bold text-slate-700">Meal / Add-On Options</label>
                    <button
                      type="button"
                      onClick={() =>
                        setFormMealOptions((prev) => [
                          ...prev,
                          { name: "", price: 0, currency: "INR" },
                        ])
                      }
                      className="text-xs font-bold text-[#172554] hover:underline"
                    >
                      + Add Option
                    </button>
                  </div>

                  <div className="space-y-2">
                    {formMealOptions.map((opt, idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <input
                          placeholder="Option Name (e.g. Buffet Breakfast)"
                          value={opt.name}
                          onChange={(e) => {
                            const updated = [...formMealOptions];
                            updated[idx].name = e.target.value;
                            setFormMealOptions(updated);
                          }}
                          className="flex-1 rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-800"
                        />
                        <div className="flex items-center gap-1 w-32">
                          <span className="text-xs font-bold text-slate-400">₹</span>
                          <input
                            type="number"
                            min={0}
                            placeholder="Price"
                            value={opt.price}
                            onChange={(e) => {
                              const updated = [...formMealOptions];
                              updated[idx].price = Number(e.target.value);
                              setFormMealOptions(updated);
                            }}
                            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-800"
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() =>
                            setFormMealOptions((prev) => prev.filter((_, i) => i !== idx))
                          }
                          className="p-2 text-slate-400 hover:text-rose-600"
                        >
                          <IconTrash />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Room Amenities */}
              <div className="space-y-3">
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-400">
                  5. Room Amenities
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {facilities.map((fac) => {
                    const checked = formAmenities.includes(fac.id);
                    return (
                      <label
                        key={fac.id}
                        className={`flex items-center gap-2 p-2.5 rounded-xl border text-xs font-semibold cursor-pointer transition ${
                          checked
                            ? "border-[#172554] bg-blue-50 text-[#172554]"
                            : "border-slate-200 text-slate-700 hover:bg-slate-50"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() =>
                            setFormAmenities((prev) =>
                              checked ? prev.filter((id) => id !== fac.id) : [...prev, fac.id]
                            )
                          }
                          className="rounded text-[#172554]"
                        />
                        <span className="truncate">{fac.name}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Modal Actions */}
              <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={modalSaving}
                  className="rounded-xl bg-[#172554] px-5 py-2.5 text-sm font-bold text-white shadow-sm hover:bg-[#1e3a8a] disabled:opacity-50"
                >
                  {modalSaving ? "Saving..." : editingRoom ? "Save Changes" : "Create Room Type"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ─── GALLERY & IMAGE MANAGEMENT MODAL ─────────────────────────────────── */}
      {galleryModalRoom && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs overflow-y-auto">
          <div className="relative w-full max-w-2xl bg-white rounded-3xl shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col">
            <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-black text-[#0b163d]">
                  Photos for &quot;{galleryModalRoom.name}&quot;
                </h3>
                <p className="text-xs text-slate-400">
                  Upload photos for this room type. At least one photo is required for Maharashtra Tourist Places validation.
                </p>
              </div>
              <button
                onClick={() => setGalleryModalRoom(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700"
              >
                <IconX />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6">
              {/* Upload Form */}
              <form onSubmit={handleUploadImage} className="space-y-4 rounded-2xl bg-slate-50 p-4 border border-slate-200/80">
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-500">
                  Add Room Photo
                </h4>

                <div className="grid sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-600 mb-1">
                      Upload from computer
                    </label>
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      onChange={(e) => setImageFile(e.target.files?.[0] || null)}
                      className="w-full text-xs font-semibold text-slate-600 file:mr-3 file:py-2 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-[#172554] file:text-white hover:file:bg-[#1e3a8a]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-600 mb-1">
                      Or image URL
                    </label>
                    <input
                      type="url"
                      value={imageUrlInput}
                      onChange={(e) => setImageUrlInput(e.target.value)}
                      placeholder="https://..."
                      className="w-full rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <input
                    value={imageAlt}
                    onChange={(e) => setImageAlt(e.target.value)}
                    placeholder="Photo description (e.g. Balcony view)"
                    className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800"
                  />
                  <button
                    type="submit"
                    disabled={uploadingImage}
                    className="rounded-xl bg-[#172554] px-4 py-1.5 text-xs font-bold text-white shadow-xs hover:bg-[#1e3a8a] disabled:opacity-50"
                  >
                    {uploadingImage ? "Uploading..." : "Add Photo"}
                  </button>
                </div>
              </form>

              {/* Photo Gallery Grid */}
              <div className="space-y-3">
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-400">
                  Current Photos ({galleryModalRoom.images?.length || 0})
                </h4>

                {galleryModalRoom.images?.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No photos added yet.</p>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {galleryModalRoom.images.map((img) => (
                      <div
                        key={img.id}
                        className="relative rounded-xl border border-slate-200 bg-slate-100 overflow-hidden group aspect-[4/3]"
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={img.image_url}
                          alt={img.alt_text || "Room"}
                          className="h-full w-full object-cover"
                        />
                        {img.is_cover && (
                          <span className="absolute top-2 left-2 rounded-md bg-emerald-600 px-2 py-0.5 text-[10px] font-black text-white shadow-xs">
                            COVER
                          </span>
                        )}
                        <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2 p-2">
                          {!img.is_cover && (
                            <button
                              type="button"
                              onClick={() => handleSetCover(img.id)}
                              className="rounded-lg bg-white px-2 py-1 text-[11px] font-bold text-slate-800 shadow-xs hover:bg-slate-50"
                            >
                              Set Cover
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => handleDeleteImage(img.id)}
                            className="rounded-lg bg-rose-600 px-2 py-1 text-[11px] font-bold text-white shadow-xs hover:bg-rose-700"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="px-6 py-4 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setGalleryModalRoom(null)}
                className="rounded-xl bg-slate-100 px-4 py-2 text-xs font-bold text-slate-700 hover:bg-slate-200"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
