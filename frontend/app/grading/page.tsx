"use client";

import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { GradingSubmission, TransactionListResponse } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";
import { Plus, Trash2, Pencil, X, AlertCircle, Loader2 } from "lucide-react";

// ── Helpers ──────────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  submitted: "bg-slate-700 text-slate-300",
  received:  "bg-blue-900/50 text-blue-300",
  grading:   "bg-amber-900/50 text-amber-300",
  graded:    "bg-green-900/50 text-green-300",
  shipped:   "bg-purple-900/50 text-purple-300",
  returned:  "bg-emerald-900/50 text-emerald-300",
};

const STATUSES = ["submitted", "received", "grading", "graded", "shipped", "returned"];

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_COLORS[status] ?? "bg-slate-700 text-slate-300"}`}>
      {status}
    </span>
  );
}

function isComplete(sub: GradingSubmission) {
  return !!(sub.player_name && sub.year && sub.card_set);
}

const VARIATION_KEYWORDS = [
  "Refractor", "Auto", "Autograph", "Gold", "Silver", "Prizm", "Holo",
  "Chrome", "Foil", "Numbered", "RC", "Rookie", "Parallel", "SSP",
  "Short Print", "Orange", "Purple", "Red", "Blue", "Green", "Black",
  "Rainbow", "Atomic", "Mojo", "Superfractor",
];

function parseCardInfo(title: string): {
  year: string; card_set: string; variation: string;
} {
  const yearMatch = title.match(/\b(19|20)\d{2}\b/);
  const year = yearMatch ? yearMatch[0] : "";

  // Card set: up to 4 words after the year
  let card_set = "";
  if (yearMatch && yearMatch.index !== undefined) {
    const afterYear = title.slice(yearMatch.index + year.length).trim();
    const words = afterYear.split(/\s+/).slice(0, 4);
    card_set = words.join(" ");
  }

  // Variation: scan for known keywords
  const foundVariations: string[] = [];
  const titleLower = title.toLowerCase();
  for (const kw of VARIATION_KEYWORDS) {
    if (titleLower.includes(kw.toLowerCase())) {
      foundVariations.push(kw);
    }
  }
  const variation = foundVariations.slice(0, 2).join(" ");

  return { year, card_set, variation };
}

const inp = "w-full text-sm bg-slate-800 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-500 placeholder:text-slate-600";

// ── Page ─────────────────────────────────────────────────────────────────────

export default function GradingPage() {
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const { data: submissions, isLoading, mutate } = useSWR<GradingSubmission[]>("/tracker/grading");
  const { data: purchasesData } = useSWR<TransactionListResponse>(
    "/dashboard/transactions?tx_type=purchase&limit=200"
  );
  const purchases = purchasesData?.items ?? [];

  // Form state
  const [selectedTxId, setSelectedTxId] = useState<string>("");
  const [form, setForm] = useState({
    player_name: "", year: "", card_set: "", variation: "",
    card_number: "", psa_order_number: "", submitted_date: "",
    estimated_return: "", purchase_price: "", grading_fee: "", notes: "",
  });

  function setField(key: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function handlePickPurchase(txId: string) {
    setSelectedTxId(txId);
    if (!txId) return;
    const tx = purchases.find((p) => String(p.id) === txId);
    if (!tx) return;
    const parsed = parseCardInfo(tx.card_name);
    setForm((f) => ({
      ...f,
      player_name: tx.player_name ?? f.player_name,
      year: parsed.year || (tx.year ? String(tx.year) : f.year),
      card_set: parsed.card_set || f.card_set,
      variation: parsed.variation || f.variation,
      purchase_price: tx.amount ? String(tx.amount) : f.purchase_price,
    }));
  }

  function resetForm() {
    setSelectedTxId("");
    setForm({
      player_name: "", year: "", card_set: "", variation: "",
      card_number: "", psa_order_number: "", submitted_date: "",
      estimated_return: "", purchase_price: "", grading_fee: "", notes: "",
    });
  }

  async function handleSave() {
    setSaving(true);
    try {
      await api.post("/tracker/grading", {
        player_name: form.player_name || undefined,
        year: form.year ? parseInt(form.year) : undefined,
        card_set: form.card_set || undefined,
        variation: form.variation || undefined,
        card_number: form.card_number || undefined,
        psa_order_number: form.psa_order_number || undefined,
        submitted_date: form.submitted_date || undefined,
        estimated_return: form.estimated_return || undefined,
        purchase_price: form.purchase_price ? parseFloat(form.purchase_price) : undefined,
        grading_fee: form.grading_fee ? parseFloat(form.grading_fee) : undefined,
        notes: form.notes || undefined,
      });
      await mutate();
      resetForm();
      setShowForm(false);
    } catch {
      alert("Failed to save submission.");
    } finally {
      setSaving(false);
    }
  }

  async function patchSub(id: number, patch: Record<string, unknown>) {
    await api.patch(`/tracker/grading/${id}`, patch);
    await mutate();
  }

  async function deleteSub(id: number) {
    if (!confirm("Delete this submission?")) return;
    await api.delete(`/tracker/grading/${id}`);
    await mutate();
  }

  const incomplete = submissions?.filter((s) => !isComplete(s)) ?? [];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Cards at Grading</h1>
          <p className="text-sm text-slate-500 mt-0.5">Track cards sent to PSA for grading</p>
        </div>
        <button
          onClick={() => { setShowForm((v) => !v); resetForm(); }}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-orange-500 text-white hover:bg-orange-600"
        >
          <Plus className="w-4 h-4" />
          Send to Grading
        </button>
      </div>

      {/* Incomplete warning banner */}
      {incomplete.length > 0 && (
        <div className="flex items-center gap-2 px-4 py-3 bg-red-900/20 border border-red-700/40 rounded-lg text-red-300 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{incomplete.length} submission{incomplete.length > 1 ? "s are" : " is"} missing fields — click the edit icon to complete them.</span>
        </div>
      )}

      {/* Add form */}
      {showForm && (
        <div className="bg-slate-900 rounded-xl border border-slate-700 p-5">
          <h2 className="text-sm font-semibold text-slate-300 mb-4">New Grading Submission</h2>

          {/* eBay picker */}
          <div className="mb-4">
            <label className="block text-xs font-medium text-slate-400 mb-1">
              Select from eBay Purchase <span className="text-slate-600">(optional — auto-fills fields below)</span>
            </label>
            <select
              value={selectedTxId}
              onChange={(e) => handlePickPurchase(e.target.value)}
              className={inp}
            >
              <option value="">— Pick an eBay purchase —</option>
              {purchases.map((tx) => (
                <option key={tx.id} value={String(tx.id)}>
                  {tx.transaction_date} · {formatCurrency(tx.amount)} · {tx.card_name.slice(0, 60)}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Player Name {!form.player_name && <span className="text-red-400">*</span>}
              </label>
              <input value={form.player_name} onChange={(e) => setField("player_name", e.target.value)}
                placeholder="Shohei Ohtani" className={inp} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Year {!form.year && <span className="text-red-400">*</span>}
              </label>
              <input type="number" value={form.year} onChange={(e) => setField("year", e.target.value)}
                placeholder="2018" className={inp} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Card Set {!form.card_set && <span className="text-red-400">*</span>}
              </label>
              <input value={form.card_set} onChange={(e) => setField("card_set", e.target.value)}
                placeholder="Bowman Chrome" className={inp} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Variation / Parallel</label>
              <input value={form.variation} onChange={(e) => setField("variation", e.target.value)}
                placeholder="Refractor" className={inp} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Card #</label>
              <input value={form.card_number} onChange={(e) => setField("card_number", e.target.value)}
                placeholder="BCP-1" className={inp} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">PSA Order #</label>
              <input value={form.psa_order_number} onChange={(e) => setField("psa_order_number", e.target.value)}
                placeholder="PSA submission ID" className={inp} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Submitted Date</label>
              <input type="date" value={form.submitted_date} onChange={(e) => setField("submitted_date", e.target.value)}
                className={inp} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Est. Return Date</label>
              <input type="date" value={form.estimated_return} onChange={(e) => setField("estimated_return", e.target.value)}
                className={inp} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Purchase Price</label>
              <input type="number" step="0.01" value={form.purchase_price} onChange={(e) => setField("purchase_price", e.target.value)}
                placeholder="0.00" className={inp} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Grading Fee</label>
              <input type="number" step="0.01" value={form.grading_fee} onChange={(e) => setField("grading_fee", e.target.value)}
                placeholder="0.00" className={inp} />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-slate-400 mb-1">Notes</label>
              <input value={form.notes} onChange={(e) => setField("notes", e.target.value)}
                placeholder="Optional notes" className={inp} />
            </div>
          </div>

          {!form.player_name || !form.year || !form.card_set ? (
            <p className="text-xs text-red-400 mt-3">
              Fields marked <span className="text-red-400">*</span> are incomplete — the card will be saved with a red flag until filled in.
            </p>
          ) : null}

          <div className="flex justify-end gap-2 mt-4">
            <button onClick={() => { setShowForm(false); resetForm(); }}
              className="px-4 py-2 text-sm border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-800">
              Cancel
            </button>
            <button onClick={handleSave} disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white text-sm font-medium rounded-lg hover:bg-orange-600 disabled:opacity-50">
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              Save Submission
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-slate-900 rounded-xl border border-slate-700">
        {isLoading ? (
          <div className="p-8 text-center text-slate-500">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />Loading...
          </div>
        ) : !submissions?.length ? (
          <div className="p-8 text-center">
            <p className="text-slate-500 text-sm mb-3">No cards currently at grading.</p>
            <button onClick={() => setShowForm(true)}
              className="px-4 py-2 bg-orange-500 text-white text-sm font-medium rounded-lg hover:bg-orange-600">
              Send your first card
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-800 border-b border-slate-700">
                  <th className="px-3 py-2.5 w-6"></th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase">Card</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase">Status</th>
                  <th className="px-3 py-2.5 text-center text-xs font-semibold text-slate-400 uppercase">Grade</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase">Submitted</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase">Est. Return</th>
                  <th className="px-3 py-2.5 text-right text-xs font-semibold text-slate-400 uppercase">Cost</th>
                  <th className="px-3 py-2.5 text-right text-xs font-semibold text-slate-400 uppercase">Fee</th>
                  <th className="px-3 py-2.5 text-center text-xs font-semibold text-slate-400 uppercase"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {submissions.map((sub) => (
                  <tr key={sub.id} className="hover:bg-slate-800/50">
                    {/* Flag */}
                    <td className="px-3 py-2.5 text-center">
                      {!isComplete(sub) && (
                        <AlertCircle className="w-4 h-4 text-red-400" title="Missing player, year, or card set" />
                      )}
                    </td>
                    {/* Card info */}
                    <td className="px-3 py-2.5">
                      <div className="font-medium text-slate-100">{sub.player_name || <span className="text-slate-600 italic">Unknown player</span>}</div>
                      <div className="text-xs text-slate-500">
                        {[sub.year, sub.card_set, sub.variation].filter(Boolean).join(" · ") || <span className="italic">Incomplete info</span>}
                        {sub.card_number && <span className="ml-1 text-slate-600">#{sub.card_number}</span>}
                      </div>
                      {sub.psa_order_number && <div className="text-xs text-slate-600">Order: {sub.psa_order_number}</div>}
                    </td>
                    {/* Status */}
                    <td className="px-3 py-2.5">
                      {editingId === sub.id ? (
                        <select defaultValue={sub.status}
                          onChange={(e) => patchSub(sub.id, { status: e.target.value })}
                          className="text-xs bg-slate-800 border border-slate-700 text-slate-200 rounded px-1.5 py-1">
                          {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                        </select>
                      ) : (
                        <StatusBadge status={sub.status} />
                      )}
                    </td>
                    {/* Grade */}
                    <td className="px-3 py-2.5 text-center">
                      {editingId === sub.id ? (
                        <input type="number" min="1" max="10"
                          defaultValue={sub.grade_received ?? ""}
                          placeholder="1-10"
                          className="w-14 text-xs bg-slate-800 border border-slate-700 text-slate-200 rounded px-1 py-1 text-center"
                          onBlur={(e) => {
                            const g = e.target.value;
                            if (g) patchSub(sub.id, { grade_received: parseInt(g), status: "returned" });
                          }} />
                      ) : sub.grade_received ? (
                        <span className="font-bold text-green-400">PSA {sub.grade_received}</span>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-slate-400">{sub.submitted_date ?? "—"}</td>
                    <td className="px-3 py-2.5 text-xs text-slate-400">{sub.estimated_return ?? "—"}</td>
                    <td className="px-3 py-2.5 text-right font-mono text-xs text-slate-300">
                      {sub.purchase_price ? formatCurrency(sub.purchase_price) : <span className="text-slate-600">—</span>}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-xs text-slate-300">
                      {sub.grading_fee ? formatCurrency(sub.grading_fee) : <span className="text-slate-600">—</span>}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <button onClick={() => setEditingId(editingId === sub.id ? null : sub.id)}
                          className="p-1 text-slate-500 hover:text-orange-400 rounded" title="Edit">
                          {editingId === sub.id ? <X className="w-4 h-4" /> : <Pencil className="w-4 h-4" />}
                        </button>
                        <button onClick={() => deleteSub(sub.id)}
                          className="p-1 text-slate-500 hover:text-red-400 rounded" title="Delete">
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
    </div>
  );
}
