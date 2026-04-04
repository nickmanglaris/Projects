"use client";

import { Transaction } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";

interface Props {
  transactions: Transaction[];
  total: number;
  page: number;
  onPageChange: (p: number) => void;
}

const LIMIT = 20;

export function TransactionTable({ transactions, total, page, onPageChange }: Props) {
  const totalPages = Math.ceil(total / LIMIT);

  return (
    <div>
      <div className="overflow-x-auto rounded-lg border border-slate-700">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-800 text-left">
              <th className="px-3 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wide">Date</th>
              <th className="px-3 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wide">Card</th>
              <th className="px-3 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wide">Type</th>
              <th className="px-3 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wide text-right">Amount</th>
              <th className="px-3 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wide text-right">Fees</th>
              <th className="px-3 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wide text-right">Net</th>
              <th className="px-3 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wide">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {transactions.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-slate-500">
                  No transactions found.
                </td>
              </tr>
            ) : (
              transactions.map((tx) => (
                <tr key={tx.id} className="hover:bg-slate-800/50">
                  <td className="px-3 py-2.5 text-slate-400 whitespace-nowrap">
                    {formatDate(tx.transaction_date)}
                  </td>
                  <td className="px-3 py-2.5 max-w-xs truncate">
                    <span className="font-medium text-slate-100">{tx.card_name}</span>
                  </td>
                  <td className="px-3 py-2.5">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        tx.transaction_type === "sale"
                          ? "bg-emerald-900/50 text-emerald-300"
                          : "bg-blue-900/50 text-blue-300"
                      }`}
                    >
                      {tx.transaction_type}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-right font-mono text-slate-200">
                    {formatCurrency(tx.amount)}
                  </td>
                  <td className="px-3 py-2.5 text-right font-mono text-slate-500">
                    {tx.ebay_fees > 0 ? formatCurrency(tx.ebay_fees) : "—"}
                  </td>
                  <td
                    className={`px-3 py-2.5 text-right font-mono font-medium ${
                      (tx.net_amount ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"
                    }`}
                  >
                    {formatCurrency(tx.net_amount)}
                  </td>
                  <td className="px-3 py-2.5">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs ${
                        tx.reconciled
                          ? "bg-slate-700 text-slate-400"
                          : "bg-amber-900/50 text-amber-300"
                      }`}
                    >
                      {tx.reconciled ? "reconciled" : "pending"}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-3 text-sm text-slate-400">
          <span>{total} total transactions</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page === 1}
              className="px-3 py-1 rounded border border-slate-700 disabled:opacity-40 hover:bg-slate-800"
            >
              Prev
            </button>
            <span>
              {page} / {totalPages}
            </span>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="px-3 py-1 rounded border border-slate-700 disabled:opacity-40 hover:bg-slate-800"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
