"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { useAdminAuth } from "@/context/AdminAuthContext";
import { AdminAccessError } from "@/services/auth.service";
import { ApiError } from "@/services/api";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CUSTOMER_PORTAL_URL = process.env.NEXT_PUBLIC_CUSTOMER_PORTAL_URL;

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated, loading, login } = useAdminAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [portalLink, setPortalLink] = useState<{ href: string; label: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && isAuthenticated) router.replace("/dashboard");
  }, [isAuthenticated, loading, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!EMAIL_PATTERN.test(email.trim())) {
      setError("Enter a valid email address.");
      return;
    }
    if (!password) {
      setError("Enter your password.");
      return;
    }

    setError("");
    setPortalLink(null);
    setSubmitting(true);
    try {
      await login({ email: email.trim().toLowerCase(), password });
      router.replace("/dashboard");
    } catch (caught) {
      if (caught instanceof AdminAccessError) {
        setError(caught.message);
        if (caught.portal?.account_role === "HOTEL_PARTNER") {
          if (CUSTOMER_PORTAL_URL) setPortalLink({ href: `${CUSTOMER_PORTAL_URL}/partner/login`, label: "Hotel Partner login" });
        } else if (caught.portal?.account_role === "CUSTOMER") {
          if (CUSTOMER_PORTAL_URL) setPortalLink({ href: `${CUSTOMER_PORTAL_URL}/login`, label: "Customer login" });
        }
      }
      else if (caught instanceof ApiError) setError(caught.message);
      else setError("Admin login failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="mb-8">
          <div className="mb-7 flex items-center gap-3 text-slate-950">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-indigo-700 text-sm font-black text-white">M</span>
            <strong className="text-sm leading-tight">Maharashtra Tourist Places<br />Control Center</strong>
          </div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-indigo-700">Restricted access</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">Admin sign in</h1>
          <p className="mt-2 text-slate-600">Use an authorized administrator account.</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm font-semibold text-slate-800">Email</label>
            <input id="email" name="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} className="input" />
          </div>
          <div>
            <label htmlFor="password" className="mb-1.5 block text-sm font-semibold text-slate-800">Password</label>
            <div className="relative">
              <input id="password" name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} className="input pr-16" />
              <button type="button" onClick={() => setShowPassword((current) => !current)} className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-indigo-700" aria-label={`${showPassword ? "Hide" : "Show"} password`}>{showPassword ? "Hide" : "Show"}</button>
            </div>
          </div>
          {error && <div role="alert" className="rounded-lg border border-red-100 bg-red-50 p-3 text-sm text-red-700"><p>{error}</p>{portalLink && <Link href={portalLink.href} className="mt-2 inline-flex font-bold underline">Go to {portalLink.label} →</Link>}</div>}
          <button type="submit" disabled={submitting} className="w-full rounded-lg bg-indigo-700 px-4 py-3 font-semibold text-white hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-60">
            {submitting ? "Verifying access…" : "Sign in as administrator"}
          </button>
        </form>
      </section>
    </main>
  );
}
