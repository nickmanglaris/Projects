"use client";

import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { DashboardSummary, TrajectoryResponse, TransactionListResponse } from "@/lib/types";
import { PLSummaryCards } from "@/components/dashboard/PLSummaryCards";
import { TrajectoryChart } from "@/components/dashboard/TrajectoryChart";
import { TransactionTable } from "@/components/dashboard/TransactionTable";
import { StatementUploader } from "@/components/dashboard/StatementUploader";
import { AlertTriangle, RefreshCw } from "lucide-react";

const PERIODS = [
  { value: "30d", label: "30 Days" },
  { value: "90d", label: "90 Days" },
  { value: "6m", label: "6 Months" },
  { value: "12m", label: "12 Months" },
  { value: "all", label: "All Time" },
];

export default function DashboardPage() {
  const [period, setPeriod] = useState("12m");
  const [txType, setTxType] = useState<string>("");
  const [page, setPage] = useState(1);
  const [showUploader, setShowUploader] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [manualForm, setManualForm] = useState({
    card_name: "", amount: "", transaction_date: "", transaction_type: "purchase", notes: "",
  });
  const [manualSaving, setManualSaving] = useState(false);
  const [manualResult, setManualResult] = useState<string | null>(null);

  async function handleManualSave() {
    if (!manualForm.card_name || !manualForm.amount || !manualForm.transaction_date) return;
    setManualSaving(true);
    setManualResult(null);
    try {
      await api.post("/dashboard/transactions", {
        card_name: manualForm.card_name,
        amount: parseFloat(manualForm.amount),
        transaction_date: manualForm.transaction_date,
        transaction_type: manualForm.transaction_type,
        notes: manualForm.notes,
        ebay_fees: 0, shipping_cost: 0,
      });
      setManualResult("Transaction added.");
      setManualForm({ card_name: "", amount: "", transaction_date: "", transaction_type: "purchase", notes: "" });
      mutateSummary();
      mutateTx();
    } catch {
      setManualResult("Failed to save — check backend.");
    } finally {
      setManualSaving(false);
    }
  }

  const { data: summary, isLoading: summaryLoading, mutate: mutateSummary } = useSWR<DashboardSummary>(
    `/dashboard/summary?period=${period}`
  );

  const { data: trajectory, isLoading: trajectoryLoading } = useSWR<TrajectoryResponse>(
    `/dashboard/trajectory?period=${period}`
  );

  const { data: transactions, isLoading: txLoading, mutate: mutateTx } = useSWR<TransactionListResponse>(
    `/dashboard/transactions?page=${page}&limit=20${txType ? `&tx_type=${txType}` : ""}`
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
      mutateTx();
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
          <p className="text-sm text-slate-500 mt-0.5">P&L overview and transaction history</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Period selector */}
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

      {/* Trajectory chart */}
      <div className="bg-slate-900 rounded-xl border border-slate-700 p-5">
        <h2 className="text-sm font-semibold text-slate-300 mb-4">Revenue & Profit Trajectory</h2>
        {trajectoryLoading ? (
          <div className="h-64 animate-pulse bg-slate-800 rounded-lg" />
        ) : (
          <TrajectoryChart data={trajectory?.data ?? []} />
        )}
      </div>

      {/* Transactions */}
      <div className="bg-slate-900 rounded-xl border border-slate-700 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-300">Transactions</h2>
          <div className="flex items-center gap-2">
            <select
              value={txType}
              onChange={(e) => { setTxType(e.target.value); setPage(1); }}
              className="text-xs bg-slate-800 border border-slate-700 text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
            >
              <option value="">All Types</option>
              <option value="purchase">Purchases</option>
              <option value="sale">Sales</option>
            </select>
          </div>
        </div>
        {txLoading ? (
          <div className="h-40 animate-pulse bg-slate-800 rounded-lg" />
        ) : (
          <TransactionTable
            transactions={transactions?.items ?? []}
            total={transactions?.total ?? 0}
            page={page}
            onPageChange={setPage}
          />
        )}
      </div>

      {/* Statement upload */}
      <div className="bg-slate-900 rounded-xl border border-slate-700 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-300">Import Bank Statement</h2>
          <button onClick={() => setShowUploader((v) => !v)} className="text-xs text-orange-400 hover:underline">
            {showUploader ? "Hide" : "Show"}
          </button>
        </div>
        {showUploader && <StatementUploader />}
      </div>

      {/* Manual transaction */}
      <div className="bg-slate-900 rounded-xl border border-slate-700 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-300">Add Manual Transaction</h2>
          <button onClick={() => setShowManual((v) => !v)} className="text-xs text-orange-400 hover:underline">
            {showManual ? "Hide" : "Show"}
          </button>
        </div>
        {showManual && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Description / Card Name</label>
                <input
                  value={manualForm.card_name}
                  onChange={(e) => setManualForm((f) => ({ ...f, card_name: e.target.value }))}
                  placeholder="e.g. Initial inventory purchase"
                  className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Amount ($)</label>
                <input
                  type="number" step="0.01" min="0"
                  value={manualForm.amount}
                  onChange={(e) => setManualForm((f) => ({ ...f, amount: e.target.value }))}
                  placeholder="0.00"
                  className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Date</label>
                <input
                  type="date"
                  value={manualForm.transaction_date}
                  onChange={(e) => setManualForm((f) => ({ ...f, transaction_date: e.target.value }))}
                  className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Type</label>
                <select
                  value={manualForm.transaction_type}
                  onChange={(e) => setManualForm((f) => ({ ...f, transaction_type: e.target.value }))}
                  className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
                >
                  <option value="purchase">Purchase (Cost)</option>
                  <option value="sale">Sale (Revenue)</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Notes (optional)</label>
              <input
                value={manualForm.notes}
                onChange={(e) => setManualForm((f) => ({ ...f, notes: e.target.value }))}
                placeholder="e.g. Startup cost — initial card inventory"
                className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-orange-500"
              />
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handleManualSave}
                disabled={manualSaving || !manualForm.card_name || !manualForm.amount || !manualForm.transaction_date}
                className="px-4 py-2 bg-orange-500 text-white text-sm font-medium rounded-lg hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {manualSaving ? "Saving…" : "Add Transaction"}
              </button>
              {manualResult && <span className="text-xs text-emerald-400">{manualResult}</span>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
