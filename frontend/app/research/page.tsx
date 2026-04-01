"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "@/lib/api";
import { ResearchResponse, ResearchResult } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";
import { Search, ExternalLink, Plus, Loader2, AlertCircle } from "lucide-react";

const schema = z.object({
  player_name: z.string().min(2, "Player name is required"),
  year: z.string().optional(),
  variation: z.string().optional(),
  min_price: z.string().optional(),
  max_price: z.string().optional(),
  max_results: z.string(),
});

type FormData = z.infer<typeof schema>;

export default function ResearchPage() {
  const [result, setResult] = useState<ResearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [addedCards, setAddedCards] = useState<Set<number>>(new Set());

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  async function onSubmit(data: FormData) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.post<ResearchResponse>("/research/search", {
        player_name: data.player_name,
        year: data.year ? parseInt(data.year) : undefined,
        variation: data.variation || undefined,
        min_price: data.min_price ? parseFloat(data.min_price) : undefined,
        max_price: data.max_price ? parseFloat(data.max_price) : undefined,
        max_results: parseInt(data.max_results),
      });
      setResult(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function addToWatchlist(r: ResearchResult, idx: number) {
    try {
      await api.post("/tracker/watchlist", {
        card_name: r.title,
        player_name: r.title.split(" ").slice(-2).join(" "),
        grade: "PSA 10",
      });
      setAddedCards((prev) => new Set([...prev, idx]));
    } catch (e: any) {
      alert("Failed to add: " + e.message);
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Card Research</h1>
        <p className="text-sm text-gray-500 mt-0.5">Search eBay completed listings for PSA 10 cards</p>
      </div>

      {/* Search form */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Player Name <span className="text-red-500">*</span>
              </label>
              <input
                {...register("player_name")}
                placeholder="e.g. Wander Franco"
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {errors.player_name && (
                <p className="text-xs text-red-500 mt-1">{errors.player_name.message}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Year</label>
              <input
                {...register("year")}
                type="number"
                placeholder="e.g. 2021"
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Variation</label>
              <input
                {...register("variation")}
                placeholder="e.g. Bowman Chrome"
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Min Price ($)</label>
              <input
                {...register("min_price")}
                type="number"
                step="0.01"
                placeholder="e.g. 20"
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Max Price ($)</label>
              <input
                {...register("max_price")}
                type="number"
                step="0.01"
                placeholder="e.g. 200"
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Max Results</label>
              <select
                {...register("max_results")}
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            {loading ? "Searching eBay..." : "Search PSA 10 Listings"}
          </button>
        </form>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <div>
            <p className="text-sm font-medium">Search failed</p>
            <p className="text-xs text-red-500 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-gray-700">
                {result.total_found} results for "{result.query}"
              </h2>
              {result.avg_price && (
                <p className="text-xs text-gray-500 mt-0.5">
                  Avg price: {formatCurrency(result.avg_price)}
                  {result.price_range && (
                    <> · Range: {formatCurrency(result.price_range.min)} – {formatCurrency(result.price_range.max)}</>
                  )}
                </p>
              )}
            </div>
          </div>

          {result.results.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-8">
              No PSA 10 completed listings found. Try broadening your search.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Card</th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase">Price</th>
                    <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Sold</th>
                    <th className="px-3 py-2.5 text-center text-xs font-semibold text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {result.results.map((r, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-3">
                          {r.image_url && (
                            <img
                              src={r.image_url}
                              alt={r.title}
                              className="w-10 h-10 object-contain rounded border border-gray-100"
                            />
                          )}
                          <span className="font-medium text-gray-900 max-w-xs truncate">{r.title}</span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-right font-mono font-semibold text-gray-900">
                        {formatCurrency(r.price)}
                      </td>
                      <td className="px-3 py-2.5 text-gray-500 text-xs">{r.sale_date || "—"}</td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center justify-center gap-2">
                          {r.listing_url && (
                            <a
                              href={r.listing_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-1.5 text-gray-400 hover:text-blue-600 rounded"
                              title="View on eBay"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          )}
                          <button
                            onClick={() => addToWatchlist(r, i)}
                            disabled={addedCards.has(i)}
                            className={`flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-lg transition-colors ${
                              addedCards.has(i)
                                ? "bg-emerald-50 text-emerald-600"
                                : "bg-blue-50 text-blue-600 hover:bg-blue-100"
                            }`}
                            title="Add to watchlist"
                          >
                            <Plus className="w-3 h-3" />
                            {addedCards.has(i) ? "Added" : "Watch"}
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
      )}
    </div>
  );
}
