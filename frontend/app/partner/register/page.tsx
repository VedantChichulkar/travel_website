"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ApiError } from "@/src/services/api";
import { authService } from "@/src/services/auth.service";

const initialValues = {
  full_name: "",
  email: "",
  phone: "",
  password: "",
  confirmPassword: "",
};

export default function PartnerRegisterPage() {
  const router = useRouter();
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  function update(field: keyof typeof values, value: string) {
    setValues((c) => ({ ...c, [field]: value }));
    setErrors((c) => ({ ...c, [field]: "" }));
  }

  function validate() {
    const e: Record<string, string> = {};
    if (values.full_name.trim().length < 2) e.full_name = "Full name is required (min 2 characters)";
    if (!values.email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) e.email = "Valid email address is required";
    if (!values.phone.match(/^\+[1-9]\d{7,14}$/)) e.phone = "Phone must use E.164 format, e.g. +919876543210";
    if (values.password.length < 8) e.password = "Password must be at least 8 characters";
    else if (!/[A-Z]/.test(values.password)) e.password = "Password must contain an uppercase letter";
    else if (!/[a-z]/.test(values.password)) e.password = "Password must contain a lowercase letter";
    else if (!/\d/.test(values.password)) e.password = "Password must contain a number";
    if (values.password !== values.confirmPassword) e.confirmPassword = "Passwords do not match";
    return e;
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const validationErrors = validate();
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
        role: "HOTEL_PARTNER",
      });
      router.push("/partner/login?registered=1");
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "Registration failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="min-h-screen flex items-center justify-center py-10 px-4">
      <div className="w-full max-w-5xl overflow-hidden rounded-3xl shadow-2xl grid lg:grid-cols-2">
        {/* Left panel */}
        <aside className="hidden lg:flex flex-col justify-between bg-[#172554] text-white p-12 relative overflow-hidden">
          <div className="absolute inset-0 opacity-40" style={{ backgroundImage: "radial-gradient(circle at 80% 20%, #5364a1 0, transparent 40%), radial-gradient(circle at 20% 80%, #ed6a3a 0, transparent 30%)" }} />
          <div className="relative">
            <div className="flex items-center gap-3 mb-16">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-white text-base font-black text-[#172554]">M</span>
              <span className="text-lg font-black tracking-tight">Maharashtra Tourist Places Partner</span>
            </div>
            <p className="text-xs font-black tracking-[.18em] text-[#ffac8d] mb-4">HOTEL PARTNER PROGRAMME</p>
            <h2 className="text-4xl font-black leading-tight tracking-tight mb-6">Grow your property with Maharashtra Tourist Places</h2>
            <ul className="space-y-3 text-sm text-slate-300">
              {["Access Maharashtra's travel audience", "Real-time booking management", "Transparent settlement reports", "Dedicated verification support"].map((item) => (
                <li key={item} className="flex items-center gap-2.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#ed6a3a] flex-shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <p className="relative text-xs text-slate-400">
            Already a partner?{" "}
            <Link href="/partner/login" className="text-white font-bold hover:underline">Sign in here</Link>
          </p>
        </aside>

        {/* Right panel */}
        <div className="bg-white p-8 sm:p-10">
          <div className="mb-8">
            <p className="text-xs font-black tracking-[.16em] text-[#d95025] uppercase mb-2">Join Maharashtra Tourist Places Partner Network</p>
            <h1 className="text-3xl font-black tracking-tight text-[#0b163d]">Create partner account</h1>
            <p className="mt-2 text-sm text-slate-500">Register your hotel business to start listing on Maharashtra Tourist Places.</p>
          </div>

          <form onSubmit={handleSubmit} className="grid gap-5 sm:grid-cols-2" noValidate>
            <Field label="Full name" id="full_name" error={errors.full_name} wide>
              <input id="full_name" name="full_name" autoComplete="name" value={values.full_name}
                onChange={(e) => update("full_name", e.target.value)} className="field-input" />
            </Field>
            <Field label="Business email" id="email" error={errors.email}>
              <input id="email" name="email" type="email" autoComplete="email" value={values.email}
                onChange={(e) => update("email", e.target.value)} className="field-input" />
            </Field>
            <Field label="Phone" id="phone" error={errors.phone} hint="E.164 format: +919876543210">
              <input id="phone" name="phone" type="tel" autoComplete="tel" placeholder="+919876543210"
                value={values.phone} onChange={(e) => update("phone", e.target.value)} className="field-input" />
            </Field>
            <Field label="Password" id="password" error={errors.password} hint="8+ chars, uppercase, lowercase, number">
              <div className="relative">
                <input id="password" name="password" type={showPassword ? "text" : "password"} autoComplete="new-password"
                  value={values.password} onChange={(e) => update("password", e.target.value)} className="field-input pr-16" />
                <button type="button" onClick={() => setShowPassword((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-black text-[#172554]">
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </Field>
            <Field label="Confirm password" id="confirmPassword" error={errors.confirmPassword}>
              <input id="confirmPassword" name="confirmPassword" type={showPassword ? "text" : "password"} autoComplete="new-password"
                value={values.confirmPassword} onChange={(e) => update("confirmPassword", e.target.value)} className="field-input" />
            </Field>

            {formError && (
              <p role="alert" className="sm:col-span-2 rounded-xl bg-red-50 border border-red-200 p-3 text-sm font-semibold text-red-700">
                {formError}
              </p>
            )}

            <button type="submit" disabled={submitting}
              className="primary-button sm:col-span-2 justify-center">
              {submitting ? "Creating account…" : "Create hotel partner account"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            Already registered?{" "}
            <Link href="/partner/login" className="font-black text-[#172554] hover:underline">Sign in</Link>
          </p>
          <p className="mt-3 text-center text-xs text-slate-400">
            Looking to book a stay?{" "}
            <Link href="/register" className="hover:underline">Customer registration</Link>
          </p>
        </div>
      </div>
    </section>
  );
}

function Field({ label, id, error, hint, wide = false, children }: {
  label: string; id: string; error?: string; hint?: string; wide?: boolean; children: React.ReactNode;
}) {
  return (
    <div className={wide ? "sm:col-span-2" : ""}>
      <label htmlFor={id} className="field-label">{label}</label>
      {children}
      {error ? (
        <p role="alert" className="mt-1.5 text-xs font-semibold text-red-600">{error}</p>
      ) : hint ? (
        <p className="mt-1.5 text-xs text-slate-400">{hint}</p>
      ) : null}
    </div>
  );
}
