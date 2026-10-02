"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";

import { AuthShell } from "@/src/components/AuthShell";
import { authService } from "@/src/services/auth.service";

export default function ResetPasswordPage() {
  return <Suspense fallback={<AuthShell eyebrow="Account recovery" title="Choose a new password" description="Loading your secure reset link…"><p className="mt-8 text-sm text-slate-500">Preparing the reset form…</p></AuthShell>}><ResetPasswordForm /></Suspense>;
}

function ResetPasswordForm() {
  const token = useSearchParams().get("token") ?? ""; const [password, setPassword] = useState(""); const [message, setMessage] = useState(""); const [submitting, setSubmitting] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); setSubmitting(true); setMessage(""); try { const result = await authService.resetPassword(token, password); setMessage(result.message); } catch { setMessage("This reset link is invalid, expired, or already used."); } finally { setSubmitting(false); } }
  return <AuthShell eyebrow="Account recovery" title="Choose a new password" description="Reset links are short-lived and can be used only once."><form onSubmit={submit} className="mt-8 grid gap-4"><label className="field-label" htmlFor="password">New password</label><input className="field-input" id="password" type="password" autoComplete="new-password" minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} />{message && <p role="status" className="rounded-xl bg-slate-50 p-3 text-sm font-semibold text-slate-700">{message}</p>}<button className="primary-button" disabled={submitting || !token}>{submitting ? "Updating…" : "Update password"}</button><Link href="/login" className="text-center text-sm font-bold text-[var(--brand)] hover:underline">Back to sign in</Link></form></AuthShell>;
}
