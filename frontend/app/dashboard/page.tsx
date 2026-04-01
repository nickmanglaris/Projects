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

  const { data: summary, isLoading: summaryLoading, mutate: mutateSummary } = useSWR<DashboardSummary>(
    `/dashboard/summary?period=${period}`
  );

  const { data: trajectory, isLoading: trajectoryLoading } = useSWR<TrajectoryResponse>(
    `/dashboard/trajectory?period=${period}`
  );

  const { data: transactions, isLoading: txLoading } = useSWR<TransactionListResponse>(
    `/dashboard/transactions?page=${page}&limit=20${txType ? `&tx_type=${txType}` : ""}`
  );

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Business Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">P&L overview and transaction history</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Period selector */}
          <div className="flex bg-white border border-gray-200 rounded-lg overflow-hidden">
            {PERIODS.map((p) => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                  period === p.value
                    ? "bg-blue-600 text-white"
                    : "text-gray-600 hover:bg-gray-50"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <button
            onClick={() => mutateSummary()}
            className="p-1.5 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Mock data banner */}
      {summary?.is_mock && (
        <div className="flex items-center gap-2 px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-sm">
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
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-5 h-28 animate-pulse bg-gray-100" />
          ))}
        </div>
      ) : summary ? (
        <PLSummaryCards summary={summary} />
      ) : null}

      {/* Trajectory chart */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Revenue & Profit Trajectory</h2>
        {trajectoryLoading ? (
          <div className="h-64 animate-pulse bg-gray-100 rounded-lg" />
        ) : (
          <TrajectoryChart data={trajectory?.data ?? []} />
        )}
      </div>

      {/* Transactions */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-700">Transactions</h2>
          <div className="flex items-center gap-2">
            <select
              value={txType}
              onChange={(e) => { setTxType(e.target.value); setPage(1); }}
              className="text-xs border border-gray-200 rounded-lg px-2 py-1 focus:outline-none"
            >
              <option value="">All Types</option>
              <option value="purchase">Purchases</option>
              <option value="sale">Sales</option>
            </select>
          </div>
        </div>
        {txLoading ? (
          <div className="h-40 animate-pulse bg-gray-100 rounded-lg" />
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
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-700">Import Bank Statement</h2>
          <button
            onClick={() => setShowUploader((v) => !v)}
            className="text-xs text-blue-600 hover:underline"
          >
            {showUploader ? "Hide" : "Show"}
          </button>
        </div>
        {showUploader && <StatementUploader />}
      </div>
    </div>
  );
}
