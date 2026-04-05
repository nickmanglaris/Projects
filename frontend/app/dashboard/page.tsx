"use client";

import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { DashboardSummary, TrajectoryResponse, TransactionListResponse } from "@/lib/types";
import { PLSummaryCards } from "@/components/dashboard/PLSummaryCards";
import { TrajectoryChart } from "@/components/dashboard/TrajectoryChart";
import { RevenueBreakdown } from "@/components/dashboard/RevenueBreakdown";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import Link from "next/link";

const PERIODS = [
  { value: "30d", label: "30 Days" },
  { value: "90d", label: "90 Days" },
  { value: "6m", label: "6 Months" },
  { value: "12m", label: "12 Months" },
  { value: "all", label: "All Time" },
];

export default function DashboardPage() {
  const [period, setPeriod] = useState("12m");
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);

  const { data: summary, isLoading: summaryLoading, mutate: mutateSummary } = useSWR<DashboardSummary>(
    `/dashboard/summary?period=${period}`
  );

  const { data: trajectory, isLoading: trajectoryLoading } = useSWR<TrajectoryResponse>(
    `/dashboard/trajectory?period=${period}`
  );

  const { data: recentTx } = useSWR<TransactionListResponse>(
    `/dashboard/transactions?page=1&limit=5`
  );

  async function handleSync() {
    setSyncing(true);
    setSyncResult(null);
    try {
      const [sales, purchases] = await Promise.all([
        api.post<{ synced: number; skipped_duplicates: number }>("/ebay/sync/sales?days=90"),
        api.post<{ synced: number; skipped_duplicates: number }>("/ebay/sync/purchases?days=90"),
      ]);
      setSyncResult(
        `Synced ${sales.synced} sales + ${purchases.synced} purchases (${sales.skipped_duplicates + purchases.skipped_duplicates} already up to date)`
      );
      mutateSummary();
    } catch {
      setSyncResult("Sync failed — check that your backend is running.");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Business Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">P&L overview and recent activity</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex bg-slate-900 border border-slate-700 rounded-lg overflow-hidden">
            {PERIODS.map((p) => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                  period === p.value
                    ? "bg-orange-500 text-white"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-500 text-white text-xs font-medium rounded-lg hover:bg-orange-600 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Syncing…" : "Sync eBay"}
          </button>
        </div>
      </div>

      {/* Sync result message */}
      {syncResult && (
        <div className="px-4 py-2.5 bg-emerald-900/30 border border-emerald-700/50 rounded-lg text-emerald-300 text-sm">
          {syncResult}
        </div>
      )}

      {/* Mock data banner */}
      {summary?.is_mock && (
        <div className="flex items-center gap-2 px-4 py-3 bg-amber-900/30 border border-amber-700/50 rounded-lg text-amber-300 text-sm">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>
            <strong>Demo Data</strong> — eBay account not connected. Go to{" "}
            <a href="/settings" className="underline">Settings</a> to connect your eBay account.
          </span>
        </div>
      )}

      {/* KPI cards */}
      {summaryLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-slate-900 rounded-xl border border-slate-700 p-5 h-28 animate-pulse" />
          ))}
        </div>
      ) : summary ? (
        <PLSummaryCards summary={summary} />
      ) : null}

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Trajectory chart — 60% */}
        <div className="lg:col-span-3 bg-slate-900 rounded-xl border border-slate-700 p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">Revenue & Profit Trajectory</h2>
          {trajectoryLoading ? (
            <div className="h-52 animate-pulse bg-slate-800 rounded-lg" />
          ) : (
            <TrajectoryChart data={trajectory?.data ?? []} />
          )}
        </div>

        {/* Revenue breakdown donut — 40% */}
        <div className="lg:col-span-2 bg-slate-900 rounded-xl border border-slate-700 p-5">
          {summaryLoading ? (
            <div className="h-52 animate-pulse bg-slate-800 rounded-lg" />
          ) : summary ? (
            <RevenueBreakdown summary={summary} />
          ) : null}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-slate-900 rounded-xl border border-slate-700 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-300">Recent Activity</h2>
          <Link href="/transactions" className="text-xs text-orange-400 hover:underline">
            View all →
          </Link>
        </div>
        {!recentTx?.items?.length ? (
          <p className="text-sm text-slate-500">No transactions yet.</p>
        ) : (
          <div className="space-y-2">
            {recentTx.items.map((tx) => (
              <div key={tx.id} className="flex items-center justify-between py-2 border-b border-slate-700/40 last:border-0">
                <div className="flex items-center gap-3">
                  <span className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${tx.transaction_type === "sale" ? "bg-emerald-400" : "bg-orange-400"}`} />
                  <div>
                    <p className="text-sm text-slate-200 leading-tight">{tx.card_name}</p>
                    <p className="text-xs text-slate-500">{tx.transaction_date} · {tx.transaction_type}</p>
                  </div>
                </div>
                <span className={`font-mono text-sm font-medium ${tx.transaction_type === "sale" ? "text-emerald-400" : "text-slate-300"}`}>
                  {tx.transaction_type === "sale" ? "+" : "-"}{formatCurrency(tx.amount)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
