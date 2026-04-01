"use client";

import { useState } from "react";
import useSWR from "swr";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "@/lib/api";
import { WatchlistEntry, PriceHistoryOut } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import { Plus, Trash2, RefreshCw, Loader2, TrendingUp, TrendingDown } from "lucide-react";

const schema = z.object({
  card_name: z.string().min(2),
  player_name: z.string().optional(),
  year: z.string().optional(),
  variation: z.string().optional(),
  grade: z.string(),
});

type FormData = z.infer<typeof schema>;

function Sparkline({ data }: { data: PriceHistoryOut[] }) {
  if (data.length < 2) return <span className="text-xs text-gray-400">Not enough data</span>;
  return (
    <ResponsiveContainer width={100} height={32}>
      <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
        <Line
          type="monotone"
          dataKey="avg_sale_price"
          stroke="#3b82f6"
          strokeWidth={1.5}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export default function TrackerPage() {
  const [showForm, setShowForm] = useState(false);
  const [adding, setAdding] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const { data: watchlist, isLoading, mutate } = useSWR<WatchlistEntry[]>(
    "/tracker/watchlist",
    { refreshInterval: 30000 }
  );

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  async function onSubmit(data: FormData) {
    setAdding(true);
    try {
      await api.post("/tracker/watchlist", {
        card_name: data.card_name,
        player_name: data.player_name || undefined,
        year: data.year ? parseInt(data.year) : undefined,
        variation: data.variation || undefined,
        grade: data.grade,
      });
      await mutate();
      reset();
      setShowForm(false);
    } catch (e: any) {
      alert("Failed to add: " + e.message);
    } finally {
      setAdding(false);
    }
  }

  async function removeCard(cardId: number) {
    if (!confirm("Remove from watchlist?")) return;
    try {
      await api.delete(`/tracker/watchlist/${cardId}`);
      await mutate();
    } catch (e: any) {
      alert("Failed to remove: " + e.message);
    }
  }

  async function handleRefreshAll() {
    setRefreshing(true);
    try {
      const result = await api.post<{ updated: number; failed: number }>("/tracker/snapshot");
      await mutate();
      alert(`Snapshot complete: ${result.updated} updated, ${result.failed} failed.`);
    } catch (e: any) {
      alert("Snapshot failed: " + e.message);
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Price Tracker</h1>
          <p className="text-sm text-gray-500 mt-0.5">Monitor weekly eBay prices for your watchlist</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefreshAll}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50"
          >
            {refreshing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Refresh Prices
          </button>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            Add Card
          </button>
        </div>
      </div>

      {/* Add form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Add Card to Watchlist</h2>
          <form onSubmit={handleSubmit(onSubmit)} className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div className="col-span-2 sm:col-span-3">
              <label className="block text-xs font-medium text-gray-700 mb-1">Card Name <span className="text-red-500">*</span></label>
              <input
                {...register("card_name")}
                placeholder="e.g. 2021 Bowman Chrome Wander Franco PSA 10"
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {errors.card_name && <p className="text-xs text-red-500 mt-1">{errors.card_name.message}</p>}
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Player Name</label>
              <input {...register("player_name")} placeholder="e.g. Wander Franco" className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Year</label>
              <input {...register("year")} type="number" placeholder="e.g. 2021" className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Variation</label>
              <input {...register("variation")} placeholder="e.g. Bowman Chrome" className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div className="col-span-2 sm:col-span-3 flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">Cancel</button>
              <button type="submit" disabled={adding} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {adding && <Loader2 className="w-4 h-4 animate-spin" />}
                Add to Watchlist
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Watchlist */}
      <div className="bg-white rounded-xl border border-gray-200">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
            Loading watchlist...
          </div>
        ) : !watchlist || watchlist.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-500 text-sm mb-3">No cards on your watchlist yet.</p>
            <button
              onClick={() => setShowForm(true)}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
            >
              Add your first card
            </button>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Card</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase">Current Avg</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase">Change</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase">List At</th>
                    <th className="px-3 py-2.5 text-center text-xs font-semibold text-gray-500 uppercase">12-wk Trend</th>
                    <th className="px-3 py-2.5 text-center text-xs font-semibold text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {watchlist.map((entry) => (
                    <>
                      <tr
                        key={entry.card.id}
                        className="hover:bg-gray-50 cursor-pointer"
                        onClick={() => setExpandedId(expandedId === entry.card.id ? null : entry.card.id)}
                      >
                        <td className="px-3 py-2.5">
                          <div className="font-medium text-gray-900">{entry.card.card_name}</div>
                          {entry.card.player_name && (
                            <div className="text-xs text-gray-400">{entry.card.player_name}</div>
                          )}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono font-semibold">
                          {entry.latest_price ? formatCurrency(entry.latest_price) : <span className="text-gray-400">No data</span>}
                        </td>
                        <td className="px-3 py-2.5 text-right">
                          {entry.price_change_pct != null ? (
                            <span className={`flex items-center justify-end gap-0.5 font-medium ${entry.price_change_pct >= 0 ? "text-emerald-600" : "text-red-500"}`}>
                              {entry.price_change_pct >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                              {entry.price_change_pct >= 0 ? "+" : ""}{entry.price_change_pct}%
                            </span>
                          ) : <span className="text-gray-400">—</span>}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono text-blue-600">
                          {entry.suggested_list_price ? formatCurrency(entry.suggested_list_price) : "—"}
                        </td>
                        <td className="px-3 py-2.5 flex justify-center">
                          <Sparkline data={entry.price_history} />
                        </td>
                        <td className="px-3 py-2.5 text-center">
                          <button
                            onClick={(e) => { e.stopPropagation(); removeCard(entry.card.id); }}
                            className="p-1 text-gray-400 hover:text-red-500 rounded"
                            title="Remove"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                      {expandedId === entry.card.id && entry.price_history.length > 0 && (
                        <tr key={`${entry.card.id}-chart`}>
                          <td colSpan={6} className="px-4 pb-4 pt-2 bg-gray-50/60">
                            <p className="text-xs font-medium text-gray-500 mb-2">12-week price history</p>
                            <ResponsiveContainer width="100%" height={160}>
                              <LineChart data={entry.price_history} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                <XAxis dataKey="snapshot_date" tick={{ fontSize: 10 }} />
                                <YAxis tickFormatter={(v) => `$${v}`} tick={{ fontSize: 10 }} />
                                <Tooltip formatter={(v) => formatCurrency(v as number)} />
                                <Line type="monotone" dataKey="avg_sale_price" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} name="Avg Price" />
                                <Line type="monotone" dataKey="min_price" stroke="#d1d5db" strokeWidth={1} strokeDasharray="3 2" dot={false} name="Min" />
                                <Line type="monotone" dataKey="max_price" stroke="#d1d5db" strokeWidth={1} strokeDasharray="3 2" dot={false} name="Max" />
                              </LineChart>
                            </ResponsiveContainer>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
