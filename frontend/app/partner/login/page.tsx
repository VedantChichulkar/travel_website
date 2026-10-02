"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";

import { useAuth } from "@/src/context/AuthContext";
import { partnerEntryRoute, portalError, portalForRole, signedInPortalMessage } from "@/src/lib/portal-routing";
import { ApiError, type PortalErrorDetail } from "@/src/services/api";
import { partnerService } from "@/src/services/partner.service";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { loading, login, user } = useAuth();
  const justRegistered = searchParams.get("registered") === "1";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [wrongPortal, setWrongPortal] = useState<PortalErrorDetail | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (loading || !user) return;
    if (user.role === "HOTEL_PARTNER") {
      void partnerService.getOverview().then((overview) => router.replace(partnerEntryRoute(overview))).catch(() => setError("We could not determine your partner onboarding status. Please try again."));
      return;
    }
  }, [loading, router, user]);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setWrongPortal(null);
    if (!email || !password) {
      setError("Email and password are required.");
      return;
    }
    setSubmitting(true);
    try {
      await login({ email: email.trim().toLowerCase(), password, portal: "HOTEL_PARTNER" });
      const overview = await partnerService.getOverview();
      router.replace(partnerEntryRoute(overview));
    } catch (err) {
      setWrongPortal(portalError(err));
      setError(err instanceof ApiError ? err.message : "Login failed. Please check your credentials.");
    } finally {
      setSubmitting(false);
    }
  }

  const signedInMismatch = !loading && user && user.role !== "HOTEL_PARTNER" ? user : null;
  const portalLink = wrongPortal ? portalForRole(wrongPortal.account_role) : signedInMismatch ? portalForRole(signedInMismatch.role) : null;
  const displayedError = error || (signedInMismatch ? signedInPortalMessage(signedInMismatch) : "");

  return (
    <section className="min-h-screen flex items-center justify-center py-10 px-4">
      <div className="w-full max-w-5xl overflow-hidden rounded-3xl shadow-2xl grid lg:grid-cols-2">
        {/* Left */}
        <aside className="hidden lg:flex flex-col justify-between bg-[#172554] text-white p-12 relative overflow-hidden">
          <div className="absolute inset-0 opacity-40" style={{ backgroundImage: "radial-gradient(circle at 80% 20%, #5364a1 0, transparent 40%), radial-gradient(circle at 20% 80%, #ed6a3a 0, transparent 30%)" }} />
          <div className="relative">
            <div className="flex items-center gap-3 mb-16">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-white text-base font-black text-[#172554]">M</span>
              <span className="text-lg font-black tracking-tight">Maharashtra Tourist Places Partner</span>
            </div>
            <p className="text-xs font-black tracking-[.18em] text-[#ffac8d] mb-4">HOTEL PARTNER PORTAL</p>
            <h2 className="text-4xl font-black leading-tight tracking-tight mb-6">Welcome back, partner</h2>
            <p className="text-sm text-slate-300 leading-6">Manage your property, track verifications, and access your hotel portal dashboard.</p>
          </div>
          <p className="relative text-xs text-slate-400">
            New to Maharashtra Tourist Places?{" "}
            <Link href="/partner/register" className="text-white font-bold hover:underline">Register as partner</Link>
          </p>
        </aside>

        {/* Right */}
        <div className="bg-white p-8 sm:p-10 flex flex-col justify-center">
          {justRegistered && (
            <div className="mb-6 rounded-xl bg-emerald-50 border border-emerald-200 p-4 text-sm font-semibold text-emerald-700">
              ✓ Account created successfully! Please sign in to continue.
            </div>
          )}
          <div className="mb-8">
            <p className="text-xs font-black tracking-[.16em] text-[#d95025] uppercase mb-2">Hotel Partner Portal</p>
            <h1 className="text-3xl font-black tracking-tight text-[#0b163d]">Sign in</h1>
            <p className="mt-2 text-sm text-slate-500">Access your hotel partner dashboard and onboarding.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            <div>
              <label htmlFor="email" className="field-label">Email address</label>
              <input id="email" name="email" type="email" autoComplete="email" value={email}
                onChange={(e) => setEmail(e.target.value)} className="field-input" placeholder="you@hotel.com" />
            </div>
            <div>
              <label htmlFor="password" className="field-label">Password</label>
              <div className="relative">
                <input id="password" name="password" type={showPassword ? "text" : "password"} autoComplete="current-password"
                  value={password} onChange={(e) => setPassword(e.target.value)} className="field-input pr-16" />
                <button type="button" onClick={() => setShowPassword((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-black text-[#172554]">
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            {displayedError && (
              <div role="alert" className="rounded-xl bg-red-50 border border-red-200 p-3 text-sm font-semibold text-red-700">
                <p>{displayedError}</p>
                {portalLink && <Link href={portalLink.href} className="mt-2 inline-flex font-black underline">Go to {portalLink.label} →</Link>}
              </div>
            )}

            <button type="submit" disabled={submitting || loading} className="primary-button w-full justify-center">
              {submitting ? "Signing in…" : loading ? "Checking session…" : "Sign in to partner portal"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            No account yet?{" "}
            <Link href="/partner/register" className="font-black text-[#172554] hover:underline">Register as hotel partner</Link>
          </p>
          <p className="mt-3 text-center text-xs text-slate-400">
            Looking to book a stay?{" "}
            <Link href="/login" className="hover:underline">Customer login</Link>
          </p>
        </div>
      </div>
    </section>
  );
}

export default function PartnerLoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
