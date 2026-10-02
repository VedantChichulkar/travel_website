"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { AuthShell } from "@/src/components/AuthShell";
import { authService } from "@/src/services/auth.service";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault(); setSubmitting(true);
    try { const result = await authService.forgotPassword(email.trim().toLowerCase()); setMessage(result.message); }
    catch { setMessage("If an account exists, password reset instructions have been sent."); }
    finally { setSubmitting(false); }
  }

  return <AuthShell eyebrow="Account recovery" title="Reset your password" description="Enter your account email. The response is intentionally the same for every address."><form onSubmit={submit} className="mt-8 grid gap-4"><label className="field-label" htmlFor="email">Email address</label><input className="field-input" id="email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />{message && <p role="status" className="rounded-xl bg-slate-50 p-3 text-sm font-semibold text-slate-700">{message}</p>}<button className="primary-button" disabled={submitting}>{submitting ? "Sending…" : "Send reset instructions"}</button><Link href="/login" className="text-center text-sm font-bold text-[var(--brand)] hover:underline">Back to sign in</Link></form></AuthShell>;
}
