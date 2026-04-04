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
      <span className="inline-flex items-center gap-0.5 text-emerald-400 font-medium text-xs">
        <TrendingUp className="w-3.5 h-3.5" />+{change}
      </span>
    );
  }
  if (change < 0) {
    return (
      <span className="inline-flex items-center gap-0.5 text-red-400 font-medium text-xs">
        <TrendingDown className="w-3.5 h-3.5" />{change}
      </span>
    );
  }
  return <Minus className="w-3.5 h-3.5 text-slate-600 mx-auto" />;
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
          <h1 className="text-xl font-bold text-slate-100">MLB Top Prospects</h1>
          <p className="text-sm text-slate-500 mt-0.5">
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
                ? "bg-orange-500/15 border-orange-500/30 text-orange-400"
                : "bg-slate-900 border-slate-700 text-slate-400 hover:bg-slate-800"
            }`}
          >
            <Flame className="w-4 h-4" />
            Rising Only
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-700 bg-slate-900 text-slate-400 hover:bg-slate-800 disabled:opacity-50"
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

      <div className="bg-slate-900 rounded-xl border border-slate-700">
        {isLoading ? (
          <div className="p-8 text-center text-slate-500">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
            Loading prospects...
          </div>
        ) : !data || data.prospects.length === 0 ? (
          <div className="p-8 text-center space-y-3">
            <p className="text-slate-500 text-sm">
              {risingOnly
                ? "No rising prospects found. Lower the threshold or refresh."
                : "No prospects loaded yet."}
            </p>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="px-4 py-2 bg-orange-500 text-white text-sm font-medium rounded-lg hover:bg-orange-600 disabled:opacity-50"
            >
              {refreshing ? "Fetching..." : "Fetch Prospects from FanGraphs"}
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-800 border-b border-slate-700">
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase w-12">Rank</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase">Name</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase">Pos</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase">Team</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase">ETA</th>
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase">Grade</th>
                  <th className="px-3 py-2.5 text-center text-xs font-semibold text-slate-400 uppercase">Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {data.prospects.map((p) => (
                  <tr key={p.id} className={`hover:bg-slate-800/50 ${p.is_rising ? "bg-orange-500/5" : ""}`}>
                    <td className="px-3 py-2.5 font-mono text-slate-300 font-semibold">
                      #{p.rank_current ?? "—"}
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-100">{p.name}</span>
                        {p.is_rising && (
                          <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-orange-500/15 text-orange-400 text-xs font-medium rounded-full">
                            <Flame className="w-3 h-3" /> Hot
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-slate-400">{p.position || "—"}</td>
                    <td className="px-3 py-2.5 text-slate-400">{p.team || "—"}</td>
                    <td className="px-3 py-2.5 text-slate-400">{p.eta || "—"}</td>
                    <td className="px-3 py-2.5">
                      {p.scouting_grade ? (
                        <span className="px-2 py-0.5 bg-orange-500/10 text-orange-400 text-xs font-medium rounded">
                          {p.scouting_grade}
                        </span>
                      ) : (
                        <span className="text-slate-600">—</span>
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
