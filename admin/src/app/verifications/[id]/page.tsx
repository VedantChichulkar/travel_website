"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AdminShell } from "@/components/AdminShell";
import {
  VerificationDetail,
  VerificationStatus,
  verificationService,
} from "@/services/verification.service";

const STATUS_CONFIG: Record<VerificationStatus, { label: string; color: string; dot: string }> = {
  PENDING: { label: "Pending Review", color: "bg-amber-100 text-amber-800 border-amber-300", dot: "bg-amber-500" },
  APPROVED: { label: "Approved", color: "bg-emerald-100 text-emerald-800 border-emerald-300", dot: "bg-emerald-500" },
  REJECTED: { label: "Rejected", color: "bg-red-100 text-red-800 border-red-300", dot: "bg-red-500" },
  ADDITIONAL_INFO_REQUIRED: { label: "Info Required", color: "bg-orange-100 text-orange-800 border-orange-300", dot: "bg-orange-500" },
  NEEDS_CHANGES: { label: "Needs Changes", color: "bg-orange-100 text-orange-800 border-orange-300", dot: "bg-orange-500" },
};

function StatusBadge({ status }: { status: string }) {
  const cfg =
    STATUS_CONFIG[status as VerificationStatus] ?? {
      label: status,
      color: "bg-slate-100 text-slate-700 border-slate-200",
      dot: "bg-slate-400",
    };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold ${cfg.color}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

function InfoRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div>
      <dt className="text-xs font-black tracking-widest text-slate-400 uppercase mb-0.5">{label}</dt>
      <dd className="text-sm font-semibold text-slate-800 break-all">{value ?? "—"}</dd>
    </div>
  );
}

function RejectModal({
  onConfirm,
  onCancel,
}: {
  onConfirm: (reason: string, notes: string) => void;
  onCancel: () => void;
}) {
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
        <h3 className="text-lg font-bold text-slate-900 mb-2">Reject Verification</h3>
        <p className="text-sm text-slate-500 mb-4">
          The hotel partner will see the rejection reason. Please be clear and specific.
        </p>
        <div className="mb-3">
          <label className="block text-xs font-black tracking-widest text-slate-400 uppercase mb-1">
            Rejection Reason <span className="text-red-500">*</span>
          </label>
          <textarea
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full border border-slate-200 rounded-xl p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-red-300"
            placeholder="e.g. Trade licence has expired. Please upload a valid certificate."
          />
        </div>
        <div className="mb-4">
          <label className="block text-xs font-black tracking-widest text-slate-400 uppercase mb-1">
            Admin Notes (internal)
          </label>
          <textarea
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full border border-slate-200 rounded-xl p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-slate-300"
            placeholder="Internal notes not visible to partner…"
          />
        </div>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            onClick={() => reason.trim() && onConfirm(reason.trim(), notes.trim())}
            disabled={!reason.trim()}
            className="flex-1 rounded-xl bg-red-600 px-4 py-2 text-sm font-bold text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Reject Verification
          </button>
        </div>
      </div>
    </div>
  );
}

function ApproveModal({ onConfirm, onCancel }: { onConfirm: (notes: string) => void; onCancel: () => void }) {
  const [notes, setNotes] = useState("");
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
        <h3 className="text-lg font-bold text-slate-900 mb-2">Approve Hotel Verification</h3>
        <p className="text-sm text-slate-500 mb-4">
          Approving will activate this property on Maharashtra Tourist Places. This decision can be revised by a subsequent action.
        </p>
        <div className="mb-4">
          <label className="block text-xs font-black tracking-widest text-slate-400 uppercase mb-1">
            Admin Notes (optional)
          </label>
          <textarea
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full border border-slate-200 rounded-xl p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-emerald-300"
            placeholder="Any notes to record about this approval…"
          />
        </div>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(notes)}
            className="flex-1 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-700"
          >
            Approve & Activate
          </button>
        </div>
      </div>
    </div>
  );
}

function RequestInfoModal({ onConfirm, onCancel }: { onConfirm: (notes: string) => void; onCancel: () => void }) {
  const [notes, setNotes] = useState("");
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
        <h3 className="text-lg font-bold text-slate-900 mb-2">Request Changes</h3>
        <p className="text-sm text-slate-500 mb-4">
          The partner will see your reason and can correct and re-submit without paying again.
        </p>
        <div className="mb-4">
          <label className="block text-xs font-black tracking-widest text-slate-400 uppercase mb-1">
            Notes for Partner <span className="text-red-500">*</span>
          </label>
          <textarea
            rows={4}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full border border-slate-200 rounded-xl p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-orange-300"
            placeholder="e.g. Please upload a clearer copy of the electricity bill for address verification."
          />
        </div>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 rounded-xl border border-slate-200 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            onClick={() => notes.trim() && onConfirm(notes.trim())}
            disabled={!notes.trim()}
            className="flex-1 rounded-xl bg-orange-500 px-4 py-2 text-sm font-bold text-white hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Request Changes
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main ──────────────────────────────────────────────────────────────────────
export default function VerificationDetailPage() {
  return (
    <AdminShell>
      <DetailContent />
    </AdminShell>
  );
}

function DetailContent() {
  const params = useParams();
  const router = useRouter();
  const verificationId = Number(params.id);

  const [detail, setDetail] = useState<VerificationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [actioning, setActioning] = useState(false);
  const [modal, setModal] = useState<"approve" | "reject" | "request-info" | null>(null);

  useEffect(() => {
    if (!verificationId) return;
    verificationService
      .getDetail(verificationId)
      .then(setDetail)
      .catch(() => setError("Failed to load verification details."))
      .finally(() => setLoading(false));
  }, [verificationId]);

  async function doApprove(notes: string) {
    setModal(null);
    setActioning(true);
    setActionError("");
    try {
      await verificationService.approve(verificationId, notes || undefined);
      router.push("/verifications");
    } catch {
      setActionError("Failed to approve. Please try again.");
    } finally {
      setActioning(false);
    }
  }

  async function doReject(reason: string, notes: string) {
    setModal(null);
    setActioning(true);
    setActionError("");
    try {
      await verificationService.reject(verificationId, reason, notes || undefined);
      router.push("/verifications");
    } catch {
      setActionError("Failed to reject. Please try again.");
    } finally {
      setActioning(false);
    }
  }

  async function doRequestInfo(notes: string) {
    setModal(null);
    setActioning(true);
    setActionError("");
    try {
      await verificationService.requestChanges(verificationId, notes);
      router.push("/verifications");
    } catch {
      setActionError("Failed to send request. Please try again.");
    } finally {
      setActioning(false);
    }
  }

  if (loading)
    return <div className="p-12 text-center text-slate-400 text-sm">Loading verification details…</div>;

  if (error || !detail)
    return (
      <div className="p-12 text-center">
        <p className="text-red-600 font-semibold mb-4">{error || "Verification not found."}</p>
        <Link href="/verifications" className="text-indigo-600 font-bold hover:underline text-sm">
          ← Back to verifications
        </Link>
      </div>
    );

  const { verification: ver, hotel, partner } = detail;
  const isActionable = ver.verification_status === "PENDING" || ver.verification_status === "ADDITIONAL_INFO_REQUIRED" || ver.verification_status === "NEEDS_CHANGES";

  return (
    <div className="mx-auto max-w-5xl">
      {/* Modals */}
      {modal === "approve" && <ApproveModal onConfirm={doApprove} onCancel={() => setModal(null)} />}
      {modal === "reject" && <RejectModal onConfirm={doReject} onCancel={() => setModal(null)} />}
      {modal === "request-info" && <RequestInfoModal onConfirm={doRequestInfo} onCancel={() => setModal(null)} />}

      {/* Breadcrumb */}
      <div className="mb-6 flex items-center gap-2 text-sm text-slate-500">
        <Link href="/verifications" className="hover:text-indigo-600 font-medium">
          Verifications
        </Link>
        <span>›</span>
        <span className="text-slate-900 font-semibold">{hotel.name}</span>
      </div>

      {/* Header card */}
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm p-6 sm:p-8 mb-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <StatusBadge status={ver.verification_status} />
              {ver.reviewed_at && (
                <span className="text-xs text-slate-400">
                  Reviewed{" "}
                  {new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(
                    new Date(ver.reviewed_at)
                  )}
                </span>
              )}
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">{hotel.name}</h1>
            <p className="text-sm text-slate-500 mt-1">
              {hotel.address_line1}, {hotel.city}, {hotel.state} · {hotel.property_type}
            </p>
          </div>

          {/* Action buttons */}
          {isActionable && (
            <div className="flex flex-wrap gap-2">
              <button
                id="btn-approve"
                onClick={() => setModal("approve")}
                disabled={actioning}
                className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors"
              >
                ✓ Approve
              </button>
              <button
                id="btn-reject"
                onClick={() => setModal("reject")}
                disabled={actioning}
                className="rounded-xl bg-red-600 px-4 py-2 text-sm font-bold text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                ✗ Reject
              </button>
              <button
                id="btn-request-info"
                onClick={() => setModal("request-info")}
                disabled={actioning}
                className="rounded-xl border border-orange-400 bg-orange-50 px-4 py-2 text-sm font-bold text-orange-700 hover:bg-orange-100 disabled:opacity-50 transition-colors"
              >
                ? Request Changes
              </button>
            </div>
          )}

          {ver.verification_status === "APPROVED" && (
            <span className="rounded-xl bg-emerald-100 border border-emerald-200 px-4 py-2 text-sm font-bold text-emerald-700">
              ✓ Approved
            </span>
          )}
          {ver.verification_status === "REJECTED" && (
            <span className="rounded-xl bg-red-100 border border-red-200 px-4 py-2 text-sm font-bold text-red-700">
              Rejected
            </span>
          )}
        </div>

        {actionError && (
          <p
            role="alert"
            className="mt-4 rounded-xl bg-red-50 border border-red-200 p-3 text-sm font-semibold text-red-700"
          >
            {actionError}
          </p>
        )}
        {ver.rejection_reason && (
          <div className="mt-4 rounded-xl bg-red-50 border border-red-200 p-4">
            <p className="text-xs font-black tracking-widest text-red-600 uppercase mb-1">Rejection Reason</p>
            <p className="text-sm text-red-800">{ver.rejection_reason}</p>
          </div>
        )}
        {ver.admin_notes && (
          <div className="mt-4 rounded-xl bg-slate-50 border border-slate-200 p-4">
            <p className="text-xs font-black tracking-widest text-slate-500 uppercase mb-1">Admin Notes</p>
            <p className="text-sm text-slate-700">{ver.admin_notes}</p>
          </div>
        )}
      </div>

      {/* Three-column detail grid */}
      {ver.fee && <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-black uppercase tracking-widest text-slate-400">Verification Fee & Refund</h2>
        <dl className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <InfoRow label="Fee" value={`${ver.fee.currency} ${ver.fee.amount}`} />
          <InfoRow label="Payment" value={ver.fee.payment_status.replaceAll("_", " ")} />
          <InfoRow label="Payment Reference" value={ver.fee.payment_reference ?? ver.fee.provider_order_id} />
          <InfoRow label="Refund" value={ver.fee.refund_status?.replaceAll("_", " ") ?? "Not applicable"} />
          {ver.fee.refund_reference && <InfoRow label="Refund Reference" value={ver.fee.refund_reference} />}
          {ver.fee.refund_failure_reason && <InfoRow label="Reconciliation" value={ver.fee.refund_failure_reason} />}
        </dl>
        <p className="mt-4 text-xs text-slate-500">Payment and application status are independent. Approval remains an Admin decision.</p>
      </div>}

      {/* Three-column detail grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Partner account */}
        <div className="rounded-2xl border border-slate-200 bg-white shadow-sm p-6">
          <h2 className="text-sm font-black tracking-widest text-slate-400 uppercase mb-4">Partner Account</h2>
          <dl className="space-y-4">
            <InfoRow label="Name" value={partner?.full_name as string | null} />
            <InfoRow label="Email" value={partner?.email as string | null} />
            <InfoRow label="Phone" value={partner?.phone as string | null} />
            {partner?.created_at && (
              <InfoRow
                label="Registered"
                value={new Intl.DateTimeFormat("en-IN", { dateStyle: "medium" }).format(
                  new Date(partner.created_at as string)
                )}
              />
            )}
          </dl>
        </div>

        {/* Business details */}
        <div className="rounded-2xl border border-slate-200 bg-white shadow-sm p-6">
          <h2 className="text-sm font-black tracking-widest text-slate-400 uppercase mb-4">Business Details</h2>
          <dl className="space-y-4">
            <InfoRow label="Business Name" value={ver.business_name} />
            <InfoRow label="Business Type" value={ver.business_type?.replace(/_/g, " ")} />
            <InfoRow label="GSTIN" value={ver.gstin} />
            <InfoRow label="PAN" value={ver.pan} />
            <InfoRow label="Document Type" value={ver.document_proof_type?.replace(/_/g, " ")} />
            {ver.document_available && (
              <div>
                <dt className="text-xs font-black tracking-widest text-slate-400 uppercase mb-0.5">
                  Document Link
                </dt>
                <dd>
                  <button
                    type="button"
                    onClick={() => void verificationService.downloadDocument(verificationId)}
                    className="text-indigo-600 hover:underline text-sm font-semibold break-all"
                  >
                    View Document →
                  </button>
                </dd>
              </div>
            )}
          </dl>
        </div>

        {/* Bank details */}
        <div className="rounded-2xl border border-slate-200 bg-white shadow-sm p-6">
          <h2 className="text-sm font-black tracking-widest text-slate-400 uppercase mb-4">Bank Account</h2>
          <dl className="space-y-4">
            <InfoRow label="Bank Name" value={ver.bank_name} />
            <InfoRow
              label="Account Number"
              value={
                ver.bank_account_number
                  ? `••••••${ver.bank_account_number.slice(-4)}`
                  : null
              }
            />
            <InfoRow label="IFSC Code" value={ver.bank_ifsc} />
            <InfoRow label="Beneficiary" value={ver.bank_beneficiary_name} />
          </dl>
        </div>
      </div>

      {/* Hotel property details */}
      <div className="mt-6 rounded-2xl border border-slate-200 bg-white shadow-sm p-6 sm:p-8">
        <h2 className="text-sm font-black tracking-widest text-slate-400 uppercase mb-4">Property Information</h2>
        <dl className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <InfoRow label="Hotel Status" value={hotel.status} />
          <InfoRow label="Booking Gateway" value={hotel.booking_gateway_status} />
          <InfoRow label="Check-in" value={hotel.check_in_time} />
          <InfoRow label="Check-out" value={hotel.check_out_time} />
          <InfoRow label="Address" value={hotel.address_line1} />
          <InfoRow label="City" value={hotel.city} />
          <InfoRow label="District" value={hotel.district} />
          <InfoRow label="Pincode" value={hotel.postal_code} />
          {hotel.contact_email && <InfoRow label="Contact Email" value={hotel.contact_email} />}
          {hotel.contact_phone && <InfoRow label="Contact Phone" value={hotel.contact_phone} />}
          {ver.submitted_at && (
            <InfoRow
              label="Submitted On"
              value={new Intl.DateTimeFormat("en-IN", {
                dateStyle: "long",
                timeStyle: "short",
              }).format(new Date(ver.submitted_at))}
            />
          )}
        </dl>
      </div>
    </div>
  );
}
