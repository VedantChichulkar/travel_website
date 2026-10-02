"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { AuthShell } from "@/src/components/AuthShell";
import { authService } from "@/src/services/auth.service";

export default function VerifyEmailPage() {
  return <Suspense fallback={<AuthShell eyebrow="Email verification" title="Verify your email" description="Checking your secure verification link…"><p className="mt-8 text-sm text-slate-500">Preparing verification…</p></AuthShell>}><VerifyEmail /></Suspense>;
}

function VerifyEmail() {
  const token = useSearchParams().get("token");
  const [message, setMessage] = useState("Verifying your email…");
  useEffect(() => { if (!token) { queueMicrotask(() => setMessage("This verification link is invalid.")); return; } void authService.verifyEmail(token).then(() => setMessage("Email verified. You can now sign in.")).catch(() => setMessage("This verification link is invalid, expired, or already used.")); }, [token]);
  return <AuthShell eyebrow="Email verification" title="Verify your email" description="Verification links are short-lived and single-use."><p role="status" className="mt-8 rounded-xl bg-slate-50 p-4 text-sm font-semibold text-slate-700">{message}</p><Link href="/login" className="primary-button mt-5 inline-flex">Continue to sign in</Link></AuthShell>;
}
