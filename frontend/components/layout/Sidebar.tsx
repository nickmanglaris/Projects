"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Search,
  TrendingUp,
  LineChart,
  Package,
  Settings,
  Award,
  Receipt,
} from "lucide-react";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/inventory", label: "Inventory", icon: Package },
  { href: "/grading", label: "Cards at Grading", icon: Award },
  { href: "/research", label: "Research", icon: Search },
  { href: "/prospects", label: "Prospects", icon: TrendingUp },
  { href: "/tracker", label: "Price Tracker", icon: LineChart },
  { href: "/transactions", label: "Transactions", icon: Receipt },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 bg-slate-950 border-r border-slate-800 flex flex-col shrink-0">
      {/* Logo */}
      <div className="h-20 flex items-center gap-2.5 px-4 border-b border-slate-800">
        <img
          src="/nicks-naks-logo.png"
          alt="Nicks Naks"
          className="w-12 h-12 rounded-xl object-cover shrink-0"
        />
        <span className="text-base font-bold text-orange-400 tracking-tight leading-tight">
          Nicks Naks
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-2 space-y-0.5">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                active
                  ? "bg-orange-500/15 text-orange-400"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-slate-800">
        <p className="text-xs text-slate-600">Nicks Naks Dashboard v1.0</p>
      </div>
    </aside>
  );
}
