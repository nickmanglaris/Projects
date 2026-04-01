"use client";

import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { ProspectsResponse } from "@/lib/types";
import { TrendingUp, TrendingDown, Minus, RefreshCw, Flame, Loader2 } from "lucide-react";
import { formatDate } from "@/lib/utils";

function RankChange({ change }: { change: number }) {
  if (change > 0) {
    return (
      <span className="inline-flex items-center gap-0.5 text-emerald-600 font-medium text-xs">
        <TrendingUp className="w-3.5 h-3.5" />+{change}
      </span>
    );
  }
  if (change < 0) {
    return (
      <span className="inline-flex items-center gap-0.5 text-red-500 font-medium text-xs">
        <TrendingDown className="w-3.5 h-3.5" />{change}
      </span>
    );
  }
  return <Minus className="w-3.5 h-3.5 text-gray-400 mx-auto" />;
}

export default function ProspectsPage() {
  const [risingOnly, setRisingOnly] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const endpoint = risingOnly ? "/prospects/rising" : "/prospects/top100";
  const { data, isLoading, mutate } = useSWR<ProspectsResponse>(endpoint);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await api.post("/prospects/refresh");
      await mutate();
    } catch (e: any) {
      alert("Refresh failed: " + e.message);
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">MLB Top Prospects</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {data?.last_updated
              ? `Updated ${formatDate(data.last_updated)}`
              : "Live prospect rankings from FanGraphs"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setRisingOnly((v) => !v)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors ${
              risingOnly
                ? "bg-orange-50 border-orange-200 text-orange-700"
                : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
            }`}
          >
            <Flame className="w-4 h-4" />
            Rising Only
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50"
          >
            {refreshing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Refresh
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
            Loading prospects...
          </div>
        ) : !data || data.prospects.length === 0 ? (
          <div className="p-8 text-center space-y-3">
            <p className="text-gray-500 text-sm">
              {risingOnly
                ? "No rising prospects found. Lower the threshold or refresh."
                : "No prospects loaded yet."}
            </p>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {refreshing ? "Fetching..." : "Fetch Prospects from FanGraphs"}
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase w-12">Rank</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Name</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Pos</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Team</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">ETA</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">Grade</th>
                  <th className="px-3 py-2.5 text-center text-xs font-semibold text-gray-500 uppercase">Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.prospects.map((p) => (
                  <tr key={p.id} className={`hover:bg-gray-50 ${p.is_rising ? "bg-orange-50/30" : ""}`}>
                    <td className="px-3 py-2.5 font-mono text-gray-700 font-semibold">
                      #{p.rank_current ?? "—"}
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-gray-900">{p.name}</span>
                        {p.is_rising && (
                          <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-orange-100 text-orange-600 text-xs font-medium rounded-full">
                            <Flame className="w-3 h-3" /> Hot
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-gray-600">{p.position || "—"}</td>
                    <td className="px-3 py-2.5 text-gray-600">{p.team || "—"}</td>
                    <td className="px-3 py-2.5 text-gray-600">{p.eta || "—"}</td>
                    <td className="px-3 py-2.5">
                      {p.scouting_grade ? (
                        <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs font-medium rounded">
                          {p.scouting_grade}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <RankChange change={p.rank_change} />
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
