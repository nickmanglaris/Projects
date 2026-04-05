"use client";

import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { TransactionListResponse } from "@/lib/types";
import { TransactionTable } from "@/components/dashboard/TransactionTable";
import { StatementUploader } from "@/components/dashboard/StatementUploader";

export default function TransactionsPage() {
  const [txType, setTxType] = useState<string>("");
  const [page, setPage] = useState(1);
  const [showUploader, setShowUploader] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const [manualForm, setManualForm] = useState({
    card_name: "", amount: "", transaction_date: "", transaction_type: "purchase", notes: "",
  });
  const [manualSaving, setManualSaving] = useState(false);
  const [manualResult, setManualResult] = useState<string | null>(null);

  const { data: transactions, isLoading: txLoading, mutate: mutateTx } =
    useSWR<TransactionListResponse>(
      `/dashboard/transactions?page=${page}&limit=20${txType ? `&tx_type=${txType}` : ""}`
    );

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
      mutateTx();
    } catch {
      setManualResult("Failed to save — check backend.");
    } finally {
      setManualSaving(false);
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Transactions</h1>
          <p className="text-sm text-slate-500 mt-0.5">All purchases, sales, and imported transactions</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={txType}
            onChange={(e) => { setTxType(e.target.value); setPage(1); }}
            className="text-xs bg-slate-800 border border-slate-700 text-slate-300 rounded-lg px-2 py-1.5 focus:outline-none"
          >
            <option value="">All Types</option>
            <option value="purchase">Purchases</option>
            <option value="sale">Sales</option>
          </select>
        </div>
      </div>

      {/* Transaction table */}
      <div className="bg-slate-900 rounded-xl border border-slate-700 p-5">
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
