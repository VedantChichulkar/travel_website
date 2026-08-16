"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/src/context/AuthContext";

export default function ProfilePage() {
  const router = useRouter();
  const { user, refresh } = useAuth();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let active = true;
    void refresh().then((currentUser) => {
      if (!active) return;
      if (!currentUser) router.replace("/login");
      setChecking(false);
    });
    return () => {
      active = false;
    };
  }, [refresh, router]);

  if (checking || !user) {
    return <div className="flex flex-1 items-center justify-center text-slate-600">Loading your profile…</div>;
  }

  const createdAt = new Intl.DateTimeFormat(undefined, { dateStyle: "long", timeStyle: "short" }).format(new Date(user.created_at));

  return (
    <section className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-6">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wider text-sky-700">Customer profile</p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight">{user.full_name}</h1>
          </div>
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">{user.is_active ? "Active" : "Inactive"}</span>
        </div>
        <dl className="mt-6 grid gap-6 sm:grid-cols-2">
          <ProfileItem label="Email" value={user.email} />
          <ProfileItem label="Phone" value={user.phone} />
          <ProfileItem label="Role" value={user.role} />
          <ProfileItem label="Account created" value={createdAt} />
        </dl>
      </div>
    </section>
  );
}

function ProfileItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-sm font-medium text-slate-500">{label}</dt>
      <dd className="mt-1 break-words font-semibold text-slate-900">{value}</dd>
    </div>
  );
}
