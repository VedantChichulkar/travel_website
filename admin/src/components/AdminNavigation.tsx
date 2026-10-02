"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { useAdminAuth } from "@/context/AdminAuthContext";

const groups=[
  {label:"Overview",items:[{href:"/dashboard",label:"Dashboard"}]},
  {label:"Hospitality",items:[{href:"/hotels",label:"Hotels"},{href:"/verifications",label:"Verification"},{href:"/rooms",label:"Room approvals"},{href:"/bookings",label:"Bookings"}]},
  {label:"Discovery",items:[{href:"/discovery/destinations",label:"Destinations"},{href:"/discovery/places",label:"Places"},{href:"/discovery/media",label:"Public media"}]},
  {label:"Operations",items:[{href:"/safaris",label:"Safaris"},{href:"/financial-operations",label:"Financial operations"},{href:"/settlements",label:"Settlements & payouts"},{href:"/advertising",label:"Advertising"},{href:"/conversations",label:"Conversations"}]},
  {label:"Governance",items:[{href:"/users",label:"Users"},{href:"/reviews",label:"Review moderation"},{href:"/notifications",label:"Delivery monitoring"},{href:"/audit",label:"Audit logs"}]},
] as const;

export function AdminNavigation(){
  const router=useRouter(),pathname=usePathname(),{admin,logout}=useAdminAuth(),[open,setOpen]=useState(false);
  function signOut(){logout();router.replace("/login");}
  const content=<div className="flex h-full flex-col"><div className="border-b border-slate-800 px-5 py-5"><Link href="/dashboard" onClick={()=>setOpen(false)} className="flex items-center gap-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-blue-600 text-sm font-black">M</span><span><strong className="block text-xs leading-tight">Maharashtra Tourist Places<br />Control Center</strong><small className="text-slate-400">Governance workspace</small></span></Link></div><nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Admin navigation">{groups.map(group=><section key={group.label} className="mb-5"><h2 className="px-3 text-[10px] font-black uppercase tracking-[.16em] text-slate-500">{group.label}</h2><div className="mt-2 space-y-1">{group.items.map(item=>{const active=pathname===item.href||pathname.startsWith(`${item.href}/`)||(item.href==="/bookings"&&pathname==="/operations")||(item.href==="/safaris"&&pathname.startsWith("/safari-operations"));return <Link key={item.href} href={item.href} onClick={()=>setOpen(false)} className={`block rounded-lg px-3 py-2.5 text-sm font-semibold ${active?"bg-blue-600 text-white":"text-slate-300 hover:bg-slate-800 hover:text-white"}`}>{item.label}</Link>})}</div></section>)}</nav><div className="border-t border-slate-800 p-3"><p className="truncate px-3 py-2 text-xs text-slate-400">{admin?.full_name??"Administrator"}</p><button onClick={signOut} className="w-full rounded-lg px-3 py-2 text-left text-sm font-semibold text-slate-300 hover:bg-red-950 hover:text-red-200">Log out</button></div></div>;
  return <><header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-slate-800 bg-slate-950 px-4 text-white md:hidden"><button aria-label="Open admin navigation" aria-expanded={open} onClick={()=>setOpen(true)} className="rounded-lg p-2 hover:bg-slate-800">☰</button><strong className="max-w-56 text-center text-xs leading-tight">Maharashtra Tourist Places Control Center</strong><span className="h-9 w-9"/></header><aside className="fixed inset-y-0 left-0 z-30 hidden w-64 bg-slate-950 text-white md:block">{content}</aside>{open&&<><button aria-label="Close admin navigation" onClick={()=>setOpen(false)} className="fixed inset-0 z-40 bg-slate-950/60 md:hidden"/><aside className="fixed inset-y-0 left-0 z-50 w-72 bg-slate-950 text-white shadow-2xl md:hidden">{content}<button aria-label="Close admin navigation" onClick={()=>setOpen(false)} className="absolute right-3 top-3 rounded-lg p-2 text-slate-300 hover:bg-slate-800">×</button></aside></>}</>;
}
