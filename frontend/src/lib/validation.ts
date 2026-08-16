import type { RegisterRequest } from "@/src/types/auth";

export interface RegisterErrors {
  full_name?: string;
  email?: string;
  phone?: string;
  password?: string;
  confirmPassword?: string;
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_PATTERN = /^\+[1-9]\d{7,14}$/;

export function validateEmail(email: string): string | undefined {
  return EMAIL_PATTERN.test(email.trim()) ? undefined : "Enter a valid email address.";
}

export function validateRegistration(
  values: RegisterRequest & { confirmPassword: string },
): RegisterErrors {
  const errors: RegisterErrors = {};
  const name = values.full_name.trim().replace(/\s+/g, " ");
  const passwordBytes = new TextEncoder().encode(values.password).length;

  if (name.length < 2 || name.length > 100) {
    errors.full_name = "Full name must be between 2 and 100 characters.";
  }
  errors.email = validateEmail(values.email);
  if (!PHONE_PATTERN.test(values.phone.trim())) {
    errors.phone = "Use E.164 format, for example +919876543210.";
  }
  if (values.password.length < 8) {
    errors.password = "Password must be at least 8 characters.";
  } else if (values.password.length > 128 || passwordBytes > 72) {
    errors.password = "Password must not exceed 72 UTF-8 bytes.";
  } else if (!/[a-z]/.test(values.password)) {
    errors.password = "Password must include a lowercase letter.";
  } else if (!/[A-Z]/.test(values.password)) {
    errors.password = "Password must include an uppercase letter.";
  } else if (!/\d/.test(values.password)) {
    errors.password = "Password must include a number.";
  }
  if (values.confirmPassword !== values.password) {
    errors.confirmPassword = "Passwords do not match.";
  }

  return Object.fromEntries(Object.entries(errors).filter(([, value]) => value));
}
