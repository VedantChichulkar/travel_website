"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";

import { AuthShell } from "@/src/components/AuthShell";
import { useAuth } from "@/src/context/AuthContext";
import { isCustomerRole, portalError, portalForRole, signedInPortalMessage } from "@/src/lib/portal-routing";
import { authPathWithNext, safeCustomerNextPath } from "@/src/lib/safe-next";
import { validateEmail } from "@/src/lib/validation";
import { ApiError, type PortalErrorDetail } from "@/src/services/api";

export default function LoginPage() {
  return <Suspense fallback={null}><LoginForm /></Suspense>;
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = safeCustomerNextPath(searchParams.get("next"));
  const { loading, login, user } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [wrongPortal, setWrongPortal] = useState<PortalErrorDetail | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (loading || !user) return;
    if (isCustomerRole(user.role)) {
      router.replace(nextPath);
      return;
    }
  }, [loading, nextPath, router, user]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const emailError = validateEmail(email);
    if (emailError) return setError(emailError);
    if (!password) return setError("Enter your password.");
    setSubmitting(true);
    setError("");
    setWrongPortal(null);
    try {
      await login({ email: email.trim().toLowerCase(), password, portal: "CUSTOMER" });
      router.replace(nextPath);
    } catch (caught) {
      setWrongPortal(portalError(caught));
      setError(caught instanceof ApiError ? caught.message : "Login failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const signedInMismatch = !loading && user && !isCustomerRole(user.role) ? user : null;
  const portalLink = wrongPortal ? portalForRole(wrongPortal.account_role) : signedInMismatch ? portalForRole(signedInMismatch.role) : null;
  const displayedError = error || (signedInMismatch ? signedInPortalMessage(signedInMismatch) : "");

  return (
    <AuthShell eyebrow="Customer access" title="Continue your journey" description="Sign in to view your travel profile, bookings, and saved details.">
      <form onSubmit={handleSubmit} className="mt-8 space-y-5" noValidate>
        <Field label="Email address" id="email"><input id="email" name="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" className="field-input" placeholder="you@example.com" /></Field>
        <Field label="Password" id="password"><div className="relative"><input id="password" name="password" type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" className="field-input pr-24" /><button type="button" onClick={() => setShowPassword((current) => !current)} className="absolute right-1 top-1/2 inline-flex min-h-11 -translate-y-1/2 items-center px-3 text-xs font-black text-[var(--brand)]" aria-label={`${showPassword ? "Hide" : "Show"} password`} aria-pressed={showPassword}>{showPassword ? "Hide" : "Show"}</button></div></Field>
        <Link href="/forgot-password" className="text-right text-sm font-bold text-[var(--brand)] hover:underline">Forgot password?</Link>
        {displayedError && <div role="alert" className="rounded-xl border border-red-100 bg-red-50 p-3 text-sm font-semibold text-[var(--danger)]"><p>{displayedError}</p>{portalLink && <Link href={portalLink.href} className="mt-2 inline-flex font-black underline">Go to {portalLink.label} →</Link>}</div>}
        <button type="submit" disabled={submitting || loading} className="primary-button w-full">{submitting ? "Signing in…" : loading ? "Checking session…" : "Sign in to customer portal"}</button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500">New to Maharashtra Tourist Places? <Link href={authPathWithNext("/register", nextPath)} className="font-black text-[var(--brand)] hover:underline">Create an account</Link></p>
      <p className="mt-3 text-center text-xs text-slate-400">Manage a property? <Link href="/partner/login" className="font-bold hover:underline">Maharashtra Tourist Places Partner login</Link></p>
    </AuthShell>
  );
}

function Field({ label, id, children }: { label: string; id: string; children: React.ReactNode }) {
  return <div><label htmlFor={id} className="field-label">{label}</label>{children}</div>;
}
