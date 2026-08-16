"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { validateRegistration, type RegisterErrors } from "@/src/lib/validation";
import { ApiError } from "@/src/services/api";
import { authService } from "@/src/services/auth.service";

const initialValues = { full_name: "", email: "", phone: "", password: "", confirmPassword: "" };

export default function RegisterPage() {
  const router = useRouter();
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState<RegisterErrors>({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationErrors = validateRegistration(values);
    setErrors(validationErrors);
    setFormError("");
    if (Object.keys(validationErrors).length) return;

    setSubmitting(true);
    try {
      await authService.register({
        full_name: values.full_name.trim().replace(/\s+/g, " "),
        email: values.email.trim().toLowerCase(),
        phone: values.phone.trim(),
        password: values.password,
      });
      router.push("/login");
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "Registration failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  function update(field: keyof typeof values, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  }

  return (
    <section className="mx-auto w-full max-w-lg px-4 py-12 sm:px-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h1 className="text-3xl font-bold tracking-tight">Create your account</h1>
        <p className="mt-2 text-slate-600">Register as a customer to access your travel profile.</p>
        <form onSubmit={handleSubmit} className="mt-8 space-y-5" noValidate>
          <Field label="Full name" id="full_name" error={errors.full_name}>
            <input id="full_name" name="full_name" value={values.full_name} onChange={(event) => update("full_name", event.target.value)} autoComplete="name" className="input" />
          </Field>
          <Field label="Email" id="email" error={errors.email}>
            <input id="email" name="email" type="email" value={values.email} onChange={(event) => update("email", event.target.value)} autoComplete="email" className="input" />
          </Field>
          <Field label="Phone" id="phone" error={errors.phone} hint="E.164 format, such as +919876543210">
            <input id="phone" name="phone" type="tel" value={values.phone} onChange={(event) => update("phone", event.target.value)} autoComplete="tel" placeholder="+919876543210" className="input" />
          </Field>
          <Field label="Password" id="password" error={errors.password} hint="8+ characters with uppercase, lowercase, and a number">
            <input id="password" name="password" type="password" value={values.password} onChange={(event) => update("password", event.target.value)} autoComplete="new-password" className="input" />
          </Field>
          <Field label="Confirm password" id="confirmPassword" error={errors.confirmPassword}>
            <input id="confirmPassword" name="confirmPassword" type="password" value={values.confirmPassword} onChange={(event) => update("confirmPassword", event.target.value)} autoComplete="new-password" className="input" />
          </Field>
          {formError && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{formError}</p>}
          <button type="submit" disabled={submitting} className="w-full rounded-lg bg-sky-700 px-4 py-3 font-semibold text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-60">
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-600">Already registered? <Link href="/login" className="font-semibold text-sky-700 hover:underline">Sign in</Link></p>
      </div>
    </section>
  );
}

function Field({ label, id, error, hint, children }: { label: string; id: string; error?: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-semibold text-slate-800">{label}</label>
      {children}
      {error ? <p role="alert" className="mt-1.5 text-sm text-red-600">{error}</p> : hint ? <p className="mt-1.5 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}
