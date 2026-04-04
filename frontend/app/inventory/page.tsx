"use client";

import { useState } from "react";
import useSWR from "swr";
import { InventoryResponse } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";
import { ExternalLink, RefreshCw, Loader2, Package, Clock, AlertTriangle } from "lucide-react";

function Daysbadge({ days, threshold }: { days: number; threshold: number }) {
  const pct = days / threshold;
  if (pct >= 1) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-900/50 text-red-300">
        <AlertTriangle className="w-3 h-3" /> {days}d
      </span>
    );
  }
  if (pct >= 0.7) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-900/50 text-yellow-300">
        <Clock className="w-3 h-3" /> {days}d
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-700 text-slate-400">
      {days}d
    </span>
  );
}

export default function InventoryPage() {
  const [threshold, setThreshold] = useState(30);
  const [inputVal, setInputVal] = useState("30");

  const { data, isLoading, mutate } = useSWR<InventoryResponse>(
    `/inventory/listings?flag_after_days=${threshold}`
  );

  function applyThreshold() {
    const n = parseInt(inputVal);
    if (!isNaN(n) && n > 0) setThreshold(n);
  }

  const listings = data?.listings ?? [];
  const stale = listings.filter(l => l.days_listed >= threshold);
  const approaching = listings.filter(l => l.days_listed >= threshold * 0.7 && l.days_listed < threshold);

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Inventory</h1>
          <p className="text-sm text-slate-500 mt-0.5">Active eBay listings — live from your account</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Threshold input */}
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5">
            <span className="text-xs text-slate-400 whitespace-nowrap">Flag after</span>
            <input
              type="number"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              onBlur={applyThreshold}
              onKeyDown={(e) => e.key === "Enter" && applyThreshold()}
              className="w-12 text-xs bg-transparent text-slate-200 text-center focus:outline-none"
              min="1"
            />
            <span className="text-xs text-slate-400">days</span>
          </div>
          <button
            onClick={() => mutate()}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800"
          >
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>
      </div>

      {/* Summary cards */}
      {data && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-slate-900 rounded-xl border border-slate-700 p-4">
            <p className="text-xs text-slate-400 mb-1">Total Listings</p>
            <p className="text-2xl font-bold text-slate-100">{data.total_listings}</p>
          </div>
          <div className="bg-slate-900 rounded-xl border border-slate-700 p-4">
            <p className="text-xs text-slate-400 mb-1">Total Listed Value</p>
            <p className="text-2xl font-bold text-slate-100">{formatCurrency(data.total_value)}</p>
          </div>
          <div className="bg-slate-900 rounded-xl border border-slate-700 p-4">
            <p className="text-xs text-slate-400 mb-1">Approaching Threshold</p>
            <p className="text-2xl font-bold text-yellow-300">{approaching.length}</p>
            <p className="text-xs text-slate-500 mt-0.5">&ge;{Math.round(threshold * 0.7)}d listed</p>
          </div>
          <div className="bg-slate-900 rounded-xl border border-slate-700 p-4">
            <p className="text-xs text-slate-400 mb-1">Stale Listings</p>
            <p className="text-2xl font-bold text-red-400">{data.stale_count}</p>
            <p className="text-xs text-slate-500 mt-0.5">&ge;{threshold}d listed</p>
          </div>
        </div>
      )}

      {/* Stale alert */}
      {data && stale.length > 0 && (
        <div className="flex items-start gap-3 px-4 py-3 bg-red-900/20 border border-red-700/40 rounded-lg text-red-300 text-sm">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            <strong>{stale.length} listing{stale.length > 1 ? "s" : ""}</strong> {stale.length > 1 ? "have" : "has"} been active for {threshold}+ days. Consider relisting at a lower price or pulling from eBay.
          </span>
        </div>
      )}

      {/* Listings table */}
      <div className="bg-slate-900 rounded-xl border border-slate-700">
        {isLoading ? (
          <div className="p-8 text-center text-slate-500">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
            Loading listings from eBay...
          </div>
        ) : listings.length === 0 ? (
          <div className="p-8 text-center">
            <Package className="w-8 h-8 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-500 text-sm">No active listings found.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-800 border-b border-slate-700">
                  <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-400 uppercase">Card</th>
                  <th className="px-3 py-2.5 text-right text-xs font-semibold text-slate-400 uppercase">Price</th>
                  <th className="px-3 py-2.5 text-center text-xs font-semibold text-slate-400 uppercase">Days Listed</th>
                  <th className="px-3 py-2.5 text-center text-xs font-semibold text-slate-400 uppercase">Watchers</th>
                  <th className="px-3 py-2.5 text-center text-xs font-semibold text-slate-400 uppercase">Qty</th>
                  <th className="px-3 py-2.5 text-center text-xs font-semibold text-slate-400 uppercase">Listed</th>
                  <th className="px-3 py-2.5 text-center text-xs font-semibold text-slate-400 uppercase"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {listings
                  .sort((a, b) => b.days_listed - a.days_listed)
                  .map((listing) => {
                    const isStale = listing.days_listed >= threshold;
                    return (
                      <tr
                        key={listing.item_id}
                        className={`hover:bg-slate-800/50 ${isStale ? "bg-red-900/5" : ""}`}
                      >
                        <td className="px-3 py-2.5">
                          <div className="flex items-center gap-3">
                            {listing.image_url ? (
                              <img
                                src={listing.image_url}
                                alt={listing.title}
                                className="w-10 h-10 object-contain rounded border border-slate-700 shrink-0"
                              />
                            ) : (
                              <div className="w-10 h-10 rounded border border-slate-700 bg-slate-800 shrink-0 flex items-center justify-center">
                                <Package className="w-4 h-4 text-slate-600" />
                              </div>
                            )}
                            <span className="font-medium text-slate-100 max-w-xs truncate">{listing.title}</span>
                          </div>
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono font-semibold text-slate-100">
                          {formatCurrency(listing.price)}
                        </td>
                        <td className="px-3 py-2.5 text-center">
                          <Daysbadge days={listing.days_listed} threshold={threshold} />
                        </td>
                        <td className="px-3 py-2.5 text-center text-slate-400">
                          {listing.watch_count > 0 ? (
                            <span className="text-orange-400 font-medium">{listing.watch_count}</span>
                          ) : "—"}
                        </td>
                        <td className="px-3 py-2.5 text-center text-slate-400">{listing.quantity}</td>
                        <td className="px-3 py-2.5 text-center text-xs text-slate-500">
                          {listing.listed_date ?? "—"}
                        </td>
                        <td className="px-3 py-2.5 text-center">
                          {listing.listing_url && (
                            <a
                              href={listing.listing_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-1.5 text-slate-500 hover:text-orange-400 rounded inline-flex"
                              title="View on eBay"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </a>
                          )}
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
