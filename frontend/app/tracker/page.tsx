"use client";

import { useState } from "react";
import useSWR from "swr";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "@/lib/api";
import { WatchlistEntry, PriceHistoryOut } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import { Plus, Trash2, RefreshCw, Loader2, TrendingUp, TrendingDown } from "lucide-react";

// ── Status badge ────────────────────────────────────────────────────────────
const STATUS_COLORS: Record<string, string> = {
  submitted: "bg-slate-700 text-slate-300",
  received:  "bg-blue-900/50 text-blue-300",
  grading:   "bg-yellow-900/50 text-yellow-300",
  graded:    "bg-green-900/50 text-green-300",
  shipped:   "bg-purple-900/50 text-purple-300",
  returned:  "bg-emerald-900/50 text-emerald-300",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_COLORS[status] ?? "bg-slate-700 text-slate-300"}`}>
      {status}
    </span>
  );
}

// ── Sparkline ───────────────────────────────────────────────────────────────
function Sparkline({ data }: { data: PriceHistoryOut[] }) {
  if (data.length < 2) return <span className="text-xs text-slate-600">—</span>;
  return (
    <ResponsiveContainer width={100} height={32}>
      <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
        <Line type="monotone" dataKey="avg_sale_price" stroke="#f97316" strokeWidth={1.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function Price({ value }: { value?: number }) {
  if (!value) return <span className="text-slate-600">—</span>;
  return <span className="font-mono text-slate-200">{formatCurrency(value)}</span>;
}

// ── Schemas ─────────────────────────────────────────────────────────────────
const watchlistSchema = z.object({
  card_name: z.string().min(2),
  player_name: z.string().optional(),
  year: z.string().optional(),
  variation: z.string().optional(),
  grade: z.string(),
});

type WatchlistForm = z.infer<typeof watchlistSchema>;

// ── Page ────────────────────────────────────────────────────────────────────
export default function TrackerPage() {
  const [showWlForm, setShowWlForm] = useState(false);
  const [addingWl, setAddingWl] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const { data: watchlist, isLoading: wlLoading, mutate: mutateWl } =
    useSWR<WatchlistEntry[]>("/tracker/watchlist", { refreshInterval: 60000 });

  const wlForm = useForm<WatchlistForm>({
    resolver: zodResolver(watchlistSchema),
    defaultValues: { grade: "PSA 10" },
  });

  // ── Watchlist handlers ──────────────────────────────────────────────────
  async function onAddWatchlist(data: WatchlistForm) {
    setAddingWl(true);
    try {
      await api.post("/tracker/watchlist", {
        card_name: data.card_name,
        player_name: data.player_name || undefined,
        year: data.year ? parseInt(data.year) : undefined,
        variation: data.variation || undefined,
        grade: data.grade,
      });
      await mutateWl();
      wlForm.reset({ grade: "PSA 10" });
      setShowWlForm(false);
    } catch (e: unknown) {
      alert("Failed to add: " + (e instanceof Error ? e.message : "error"));
    } finally {
      setAddingWl(false);
    }
  }

  async function removeCard(id: number) {
    if (!confirm("Remove from watchlist?")) return;
    await api.delete(`/tracker/watchlist/${id}`);
    await mutateWl();
  }

  async function handleRefreshAll() {
    setRefreshing(true);
    try {
      const r = await api.post<{ updated: number; failed: number }>("/tracker/snapshot");
      await mutateWl();
      alert(`Snapshot complete: ${r.updated} updated, ${r.failed} failed.`);
    } catch (e: unknown) {
      alert("Snapshot failed: " + (e instanceof Error ? e.message : "error"));
    } finally {
      setRefreshing(false);
    }
  }

  // ── Field helpers ───────────────────────────────────────────────────────
  const lbl = (text: string, required = false) => (
    <label className="block text-xs font-medium text-slate-400 mb-1">
      {text}{required && <span className="text-red-400 ml-0.5">*</span>}
    </label>
  );
  const inp = "w-full text-sm bg-slate-800 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-500 placeholder:text-slate-600";

  return (
    <div className="p-6 space-y-10 max-w-6xl mx-auto">

      {/* ═══════════════ WATCHLIST ═══════════════════════════════════════ */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-bold text-slate-100">Price Tracker</h1>
            <p className="text-sm text-slate-500 mt-0.5">Daily prices via eBay sold — PSA 10 / 9 / 8</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={handleRefreshAll} disabled={refreshing}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800 disabled:opacity-50">
              {refreshing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              Refresh Prices
            </button>
            <button onClick={() => setShowWlForm(v => !v)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-orange-500 text-white hover:bg-orange-600">
              <Plus className="w-4 h-4" /> Add Card
            </button>
          </div>
        </div>

        {showWlForm && (
          <div className="bg-slate-900 rounded-xl border border-slate-700 p-5 mb-4">
            <h2 className="text-sm font-semibold text-slate-300 mb-4">Add Card to Watchlist</h2>
            <form onSubmit={wlForm.handleSubmit(onAddWatchlist)} className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="col-span-2 sm:col-span-3">
                {lbl("Card Name", true)}
                <input {...wlForm.register("card_name")} placeholder="e.g. 2021 Bowman Chrome Wander Franco" className={inp} />
              </div>
              <div>{lbl("Player Name")}<input {...wlForm.register("player_name")} placeholder="Wander Franco" className={inp} /></div>
              <div>{lbl("Year")}<input {...wlForm.register("year")} type="number" placeholder="2021" className={inp} /></div>
              <div>{lbl("Card Set / Variation")}<input {...wlForm.register("variation")} placeholder="Bowman Chrome" className={inp} /></div>
              <div className="col-span-2 sm:col-span-3 flex justify-end gap-2">
                <button type="button" onClick={() => setShowWlForm(false)} className="px-4 py-2 text-sm border border-slate-700 rounded-lg text-slate-300 hover:bg-slate-800">Cancel</button>
                <button type="submit" disabled={addingWl} className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white text-sm font-medium rounded-lg hover:bg-orange-600 disabled:opacity-50">
                  {addingWl && <Loader2 className="w-4 h-4 animate-spin" />} Add to Watchlist
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="bg-slate-900 rounded-xl border border-slate-700">
          {wlLoading ? (
            <div className="p-8 text-center text-slate-500"><Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />Loading...</div>
          ) : !watchlist?.length ? (
            <div className="p-8 text-center">
              <p className="text-slate-500 text-sm mb-3">No cards on your watchlist yet.</p>
              <button onClick={() => setShowWlForm(true)} className="px-4 py-2 bg-orange-500 text-white text-sm font-medium rounded-lg hover:bg-orange-600">Add your first card</button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-800 border-b border-slate-700">
                    <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase">Card</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-slate-400 uppercase">Raw Avg</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-green-400 uppercase">PSA 10</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-blue-400 uppercase">PSA 9</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-slate-400 uppercase">PSA 8</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-slate-400 uppercase">Change</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-slate-400 uppercase">List At</th>
                    <th className="px-3 py-2.5 text-center text-xs font-semibold text-slate-400 uppercase">Trend</th>
                    <th className="px-3 py-2.5 text-center text-xs font-semibold text-slate-400 uppercase"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50">
                  {watchlist.map((entry) => (
                    <>
                      <tr key={entry.card.id} className="hover:bg-slate-800/50 cursor-pointer"
                        onClick={() => setExpandedId(expandedId === entry.card.id ? null : entry.card.id)}>
                        <td className="px-3 py-2.5">
                          <div className="font-medium text-slate-100">{entry.card.card_name}</div>
                          {entry.card.player_name && <div className="text-xs text-slate-500">{entry.card.player_name}</div>}
                        </td>
                        <td className="px-3 py-2.5 text-right"><Price value={entry.latest_price} /></td>
                        <td className="px-3 py-2.5 text-right font-semibold text-green-400"><Price value={entry.latest_psa10} /></td>
                        <td className="px-3 py-2.5 text-right text-blue-400"><Price value={entry.latest_psa9} /></td>
                        <td className="px-3 py-2.5 text-right text-slate-400"><Price value={entry.latest_psa8} /></td>
                        <td className="px-3 py-2.5 text-right">
                          {entry.price_change_pct != null ? (
                            <span className={`flex items-center justify-end gap-0.5 font-medium ${entry.price_change_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                              {entry.price_change_pct >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                              {entry.price_change_pct >= 0 ? "+" : ""}{entry.price_change_pct}%
                            </span>
                          ) : <span className="text-slate-600">—</span>}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono text-orange-400">
                          {entry.suggested_list_price ? formatCurrency(entry.suggested_list_price) : "—"}
                        </td>
                        <td className="px-3 py-2.5 flex justify-center"><Sparkline data={entry.price_history} /></td>
                        <td className="px-3 py-2.5 text-center">
                          <button onClick={(e) => { e.stopPropagation(); removeCard(entry.card.id); }}
                            className="p-1 text-slate-500 hover:text-red-400 rounded" title="Remove">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                      {expandedId === entry.card.id && entry.price_history.length > 0 && (
                        <tr key={`${entry.card.id}-chart`}>
                          <td colSpan={9} className="px-4 pb-4 pt-2 bg-slate-800/40">
                            <p className="text-xs font-medium text-slate-500 mb-2">12-week price history</p>
                            <ResponsiveContainer width="100%" height={160}>
                              <LineChart data={entry.price_history} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                <XAxis dataKey="snapshot_date" tick={{ fontSize: 10, fill: "#94a3b8" }} />
                                <YAxis tickFormatter={(v) => `$${v}`} tick={{ fontSize: 10, fill: "#94a3b8" }} />
                                <Tooltip
                                  formatter={(v) => formatCurrency(v as number)}
                                  contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "8px", color: "#f1f5f9" }}
                                />
                                <Line type="monotone" dataKey="avg_sale_price" stroke="#f97316" strokeWidth={2} dot={{ r: 3 }} name="Raw Avg" />
                                <Line type="monotone" dataKey="psa10_price" stroke="#4ade80" strokeWidth={2} dot={{ r: 3 }} name="PSA 10" />
                                <Line type="monotone" dataKey="psa9_price" stroke="#60a5fa" strokeWidth={1.5} strokeDasharray="4 2" dot={false} name="PSA 9" />
                                <Line type="monotone" dataKey="psa8_price" stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="4 2" dot={false} name="PSA 8" />
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
          )}
        </div>
      </section>

    </div>
  );
}
