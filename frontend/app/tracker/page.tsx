"use client";

import { useState } from "react";
import useSWR from "swr";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "@/lib/api";
import { WatchlistEntry, PriceHistoryOut, GradingSubmission } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import { Plus, Trash2, RefreshCw, Loader2, TrendingUp, TrendingDown, Pencil, X } from "lucide-react";

// ── Status badge ────────────────────────────────────────────────────────────
const STATUS_COLORS: Record<string, string> = {
  submitted: "bg-gray-100 text-gray-600",
  received:  "bg-blue-100 text-blue-700",
  grading:   "bg-yellow-100 text-yellow-700",
  graded:    "bg-green-100 text-green-700",
  shipped:   "bg-purple-100 text-purple-700",
  returned:  "bg-emerald-100 text-emerald-700",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_COLORS[status] ?? "bg-gray-100 text-gray-600"}`}>
      {status}
    </span>
  );
}

// ── Sparkline ───────────────────────────────────────────────────────────────
function Sparkline({ data }: { data: PriceHistoryOut[] }) {
  if (data.length < 2) return <span className="text-xs text-gray-300">—</span>;
  return (
    <ResponsiveContainer width={100} height={32}>
      <LineChart data={data} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
        <Line type="monotone" dataKey="avg_sale_price" stroke="#3b82f6" strokeWidth={1.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function Price({ value }: { value?: number }) {
  if (!value) return <span className="text-gray-300">—</span>;
  return <span className="font-mono">{formatCurrency(value)}</span>;
}

// ── Schemas ─────────────────────────────────────────────────────────────────
const watchlistSchema = z.object({
  card_name: z.string().min(2),
  player_name: z.string().optional(),
  year: z.string().optional(),
  variation: z.string().optional(),
  grade: z.string(),
});

const gradingSchema = z.object({
  player_name: z.string().min(1),
  year: z.string().optional(),
  card_set: z.string().min(1),
  variation: z.string().optional(),
  card_number: z.string().optional(),
  psa_order_number: z.string().optional(),
  submitted_date: z.string().optional(),
  estimated_return: z.string().optional(),
  purchase_price: z.string().optional(),
  grading_fee: z.string().optional(),
  notes: z.string().optional(),
});

type WatchlistForm = z.infer<typeof watchlistSchema>;
type GradingForm = z.infer<typeof gradingSchema>;

const STATUSES = ["submitted", "received", "grading", "graded", "shipped", "returned"];

// ── Page ────────────────────────────────────────────────────────────────────
export default function TrackerPage() {
  // Watchlist state
  const [showWlForm, setShowWlForm] = useState(false);
  const [addingWl, setAddingWl] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  // Grading state
  const [showGrForm, setShowGrForm] = useState(false);
  const [addingGr, setAddingGr] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const { data: watchlist, isLoading: wlLoading, mutate: mutateWl } =
    useSWR<WatchlistEntry[]>("/tracker/watchlist", { refreshInterval: 60000 });

  const { data: grading, isLoading: grLoading, mutate: mutateGr } =
    useSWR<GradingSubmission[]>("/tracker/grading");

  const wlForm = useForm<WatchlistForm>({
    resolver: zodResolver(watchlistSchema),
    defaultValues: { grade: "PSA 10" },
  });

  const grForm = useForm<GradingForm>({ resolver: zodResolver(gradingSchema) });

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

  // ── Grading handlers ────────────────────────────────────────────────────
  async function onAddGrading(data: GradingForm) {
    setAddingGr(true);
    try {
      await api.post("/tracker/grading", {
        player_name: data.player_name,
        year: data.year ? parseInt(data.year) : undefined,
        card_set: data.card_set,
        variation: data.variation || undefined,
        card_number: data.card_number || undefined,
        psa_order_number: data.psa_order_number || undefined,
        submitted_date: data.submitted_date || undefined,
        estimated_return: data.estimated_return || undefined,
        purchase_price: data.purchase_price ? parseFloat(data.purchase_price) : undefined,
        grading_fee: data.grading_fee ? parseFloat(data.grading_fee) : undefined,
        notes: data.notes || undefined,
      });
      await mutateGr();
      grForm.reset();
      setShowGrForm(false);
    } catch (e: unknown) {
      alert("Failed to add: " + (e instanceof Error ? e.message : "error"));
    } finally {
      setAddingGr(false);
    }
  }

  async function patchGrading(id: number, patch: Record<string, unknown>) {
    await api.patch(`/tracker/grading/${id}`, patch);
    await mutateGr();
  }

  async function deleteGrading(id: number) {
    if (!confirm("Delete this submission?")) return;
    await api.delete(`/tracker/grading/${id}`);
    await mutateGr();
  }

  // ── Field label helper ──────────────────────────────────────────────────
  const lbl = (text: string, required = false) => (
    <label className="block text-xs font-medium text-gray-700 mb-1">
      {text}{required && <span className="text-red-500 ml-0.5">*</span>}
    </label>
  );
  const inp = "w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500";

  return (
    <div className="p-6 space-y-10 max-w-6xl mx-auto">

      {/* ═══════════════ WATCHLIST ═══════════════════════════════════════ */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Price Tracker</h1>
            <p className="text-sm text-gray-500 mt-0.5">Daily prices via 130point — PSA 10 / 9 / 8</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={handleRefreshAll} disabled={refreshing}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50">
              {refreshing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              Refresh Prices
            </button>
            <button onClick={() => setShowWlForm(v => !v)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700">
              <Plus className="w-4 h-4" /> Add Card
            </button>
          </div>
        </div>

        {showWlForm && (
          <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-4">Add Card to Watchlist</h2>
            <form onSubmit={wlForm.handleSubmit(onAddWatchlist)} className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="col-span-2 sm:col-span-3">
                {lbl("Card Name", true)}
                <input {...wlForm.register("card_name")} placeholder="e.g. 2021 Bowman Chrome Wander Franco" className={inp} />
              </div>
              <div>{lbl("Player Name")}<input {...wlForm.register("player_name")} placeholder="Wander Franco" className={inp} /></div>
              <div>{lbl("Year")}<input {...wlForm.register("year")} type="number" placeholder="2021" className={inp} /></div>
              <div>{lbl("Card Set / Variation")}<input {...wlForm.register("variation")} placeholder="Bowman Chrome" className={inp} /></div>
              <div className="col-span-2 sm:col-span-3 flex justify-end gap-2">
                <button type="button" onClick={() => setShowWlForm(false)} className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">Cancel</button>
                <button type="submit" disabled={addingWl} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50">
                  {addingWl && <Loader2 className="w-4 h-4 animate-spin" />} Add to Watchlist
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="bg-white rounded-xl border border-gray-200">
          {wlLoading ? (
            <div className="p-8 text-center text-gray-400"><Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />Loading...</div>
          ) : !watchlist?.length ? (
            <div className="p-8 text-center">
              <p className="text-gray-500 text-sm mb-3">No cards on your watchlist yet.</p>
              <button onClick={() => setShowWlForm(true)} className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">Add your first card</button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Card</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase">Raw Avg</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-green-600 uppercase">PSA 10</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-blue-600 uppercase">PSA 9</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase">PSA 8</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase">Change</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase">List At</th>
                    <th className="px-3 py-2.5 text-center text-xs font-semibold text-gray-500 uppercase">Trend</th>
                    <th className="px-3 py-2.5 text-center text-xs font-semibold text-gray-500 uppercase"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {watchlist.map((entry) => (
                    <>
                      <tr key={entry.card.id} className="hover:bg-gray-50 cursor-pointer"
                        onClick={() => setExpandedId(expandedId === entry.card.id ? null : entry.card.id)}>
                        <td className="px-3 py-2.5">
                          <div className="font-medium text-gray-900">{entry.card.card_name}</div>
                          {entry.card.player_name && <div className="text-xs text-gray-400">{entry.card.player_name}</div>}
                        </td>
                        <td className="px-3 py-2.5 text-right"><Price value={entry.latest_price} /></td>
                        <td className="px-3 py-2.5 text-right font-semibold text-green-700"><Price value={entry.latest_psa10} /></td>
                        <td className="px-3 py-2.5 text-right text-blue-700"><Price value={entry.latest_psa9} /></td>
                        <td className="px-3 py-2.5 text-right text-gray-600"><Price value={entry.latest_psa8} /></td>
                        <td className="px-3 py-2.5 text-right">
                          {entry.price_change_pct != null ? (
                            <span className={`flex items-center justify-end gap-0.5 font-medium ${entry.price_change_pct >= 0 ? "text-emerald-600" : "text-red-500"}`}>
                              {entry.price_change_pct >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                              {entry.price_change_pct >= 0 ? "+" : ""}{entry.price_change_pct}%
                            </span>
                          ) : <span className="text-gray-300">—</span>}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono text-blue-600">
                          {entry.suggested_list_price ? formatCurrency(entry.suggested_list_price) : "—"}
                        </td>
                        <td className="px-3 py-2.5 flex justify-center"><Sparkline data={entry.price_history} /></td>
                        <td className="px-3 py-2.5 text-center">
                          <button onClick={(e) => { e.stopPropagation(); removeCard(entry.card.id); }}
                            className="p-1 text-gray-400 hover:text-red-500 rounded" title="Remove">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                      {expandedId === entry.card.id && entry.price_history.length > 0 && (
                        <tr key={`${entry.card.id}-chart`}>
                          <td colSpan={9} className="px-4 pb-4 pt-2 bg-gray-50/60">
                            <p className="text-xs font-medium text-gray-500 mb-2">12-week price history</p>
                            <ResponsiveContainer width="100%" height={160}>
                              <LineChart data={entry.price_history} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                <XAxis dataKey="snapshot_date" tick={{ fontSize: 10 }} />
                                <YAxis tickFormatter={(v) => `$${v}`} tick={{ fontSize: 10 }} />
                                <Tooltip formatter={(v) => formatCurrency(v as number)} />
                                <Line type="monotone" dataKey="avg_sale_price" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} name="Raw Avg" />
                                <Line type="monotone" dataKey="psa10_price" stroke="#16a34a" strokeWidth={2} dot={{ r: 3 }} name="PSA 10" />
                                <Line type="monotone" dataKey="psa9_price" stroke="#2563eb" strokeWidth={1.5} strokeDasharray="4 2" dot={false} name="PSA 9" />
                                <Line type="monotone" dataKey="psa8_price" stroke="#9ca3af" strokeWidth={1.5} strokeDasharray="4 2" dot={false} name="PSA 8" />
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

      {/* ═══════════════ CARDS AT PSA ════════════════════════════════════ */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Cards at PSA</h2>
            <p className="text-sm text-gray-500 mt-0.5">Track cards sent out for grading</p>
          </div>
          <button onClick={() => { setShowGrForm(v => !v); grForm.reset(); }}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700">
            <Plus className="w-4 h-4" /> Add Submission
          </button>
        </div>

        {showGrForm && (
          <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-4">New Grading Submission</h3>
            <form onSubmit={grForm.handleSubmit(onAddGrading)} className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div>{lbl("Player Name", true)}<input {...grForm.register("player_name")} placeholder="Shohei Ohtani" className={inp} /></div>
              <div>{lbl("Year")}<input {...grForm.register("year")} type="number" placeholder="2018" className={inp} /></div>
              <div>{lbl("Card Set", true)}<input {...grForm.register("card_set")} placeholder="Bowman Chrome" className={inp} /></div>
              <div>{lbl("Variation / Parallel")}<input {...grForm.register("variation")} placeholder="Refractor" className={inp} /></div>
              <div>{lbl("Card #")}<input {...grForm.register("card_number")} placeholder="BCP-1" className={inp} /></div>
              <div>{lbl("PSA Order #")}<input {...grForm.register("psa_order_number")} placeholder="PSA submission ID" className={inp} /></div>
              <div>{lbl("Submitted Date")}<input {...grForm.register("submitted_date")} type="date" className={inp} /></div>
              <div>{lbl("Est. Return Date")}<input {...grForm.register("estimated_return")} type="date" className={inp} /></div>
              <div>{lbl("Purchase Price")}<input {...grForm.register("purchase_price")} type="number" step="0.01" placeholder="0.00" className={inp} /></div>
              <div>{lbl("Grading Fee")}<input {...grForm.register("grading_fee")} type="number" step="0.01" placeholder="0.00" className={inp} /></div>
              <div className="col-span-2">{lbl("Notes")}<input {...grForm.register("notes")} placeholder="Optional notes" className={inp} /></div>
              <div className="col-span-2 sm:col-span-3 flex justify-end gap-2">
                <button type="button" onClick={() => setShowGrForm(false)} className="px-4 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50">Cancel</button>
                <button type="submit" disabled={addingGr} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50">
                  {addingGr && <Loader2 className="w-4 h-4 animate-spin" />} Add Submission
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="bg-white rounded-xl border border-gray-200">
          {grLoading ? (
            <div className="p-8 text-center text-gray-400"><Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />Loading...</div>
          ) : !grading?.length ? (
            <div className="p-8 text-center">
              <p className="text-gray-500 text-sm mb-3">No cards currently at PSA.</p>
              <button onClick={() => setShowGrForm(true)} className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">Add first submission</button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Card</th>
                    <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                    <th className="px-3 py-2.5 text-center text-xs font-semibold text-gray-500 uppercase">Grade</th>
                    <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Submitted</th>
                    <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Est. Return</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase">Cost</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase">Fee</th>
                    <th className="px-3 py-2.5 text-center text-xs font-semibold text-gray-500 uppercase"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {grading.map((sub) => (
                    <tr key={sub.id} className="hover:bg-gray-50">
                      <td className="px-3 py-2.5">
                        <div className="font-medium text-gray-900">{sub.player_name}</div>
                        <div className="text-xs text-gray-400">
                          {[sub.year, sub.card_set, sub.variation].filter(Boolean).join(" · ")}
                          {sub.card_number && <span className="ml-1 text-gray-300">#{sub.card_number}</span>}
                        </div>
                        {sub.psa_order_number && <div className="text-xs text-gray-400">Order: {sub.psa_order_number}</div>}
                      </td>
                      <td className="px-3 py-2.5">
                        {editingId === sub.id ? (
                          <select defaultValue={sub.status}
                            onChange={(e) => patchGrading(sub.id, { status: e.target.value })}
                            className="text-xs border border-gray-200 rounded px-1.5 py-1">
                            {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                          </select>
                        ) : (
                          <StatusBadge status={sub.status} />
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        {editingId === sub.id ? (
                          <input type="number" min="1" max="10"
                            defaultValue={sub.grade_received ?? ""}
                            placeholder="1-10"
                            className="w-14 text-xs border border-gray-200 rounded px-1 py-1 text-center"
                            onBlur={(e) => {
                              const g = e.target.value;
                              if (g) patchGrading(sub.id, { grade_received: parseInt(g), status: "returned" });
                            }} />
                        ) : (
                          sub.grade_received
                            ? <span className="font-bold text-green-700">PSA {sub.grade_received}</span>
                            : <span className="text-gray-300">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-xs text-gray-600">{sub.submitted_date ?? "—"}</td>
                      <td className="px-3 py-2.5 text-xs text-gray-600">{sub.estimated_return ?? "—"}</td>
                      <td className="px-3 py-2.5 text-right font-mono text-xs"><Price value={sub.purchase_price} /></td>
                      <td className="px-3 py-2.5 text-right font-mono text-xs"><Price value={sub.grading_fee} /></td>
                      <td className="px-3 py-2.5 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <button onClick={() => setEditingId(editingId === sub.id ? null : sub.id)}
                            className="p-1 text-gray-400 hover:text-blue-500 rounded" title="Edit">
                            {editingId === sub.id ? <X className="w-4 h-4" /> : <Pencil className="w-4 h-4" />}
                          </button>
                          <button onClick={() => deleteGrading(sub.id)}
                            className="p-1 text-gray-400 hover:text-red-500 rounded" title="Delete">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
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
