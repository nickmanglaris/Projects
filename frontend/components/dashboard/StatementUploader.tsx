"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { UploadCloud, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { uploadStatement } from "@/lib/api";
import { UploadResponse } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";
import { api } from "@/lib/api";

const BANK_OPTIONS = [
  { value: "generic", label: "Generic / Auto-detect" },
  { value: "chase", label: "Chase" },
  { value: "paypal", label: "PayPal" },
  { value: "bofa", label: "Bank of America" },
  { value: "wellsfargo", label: "Wells Fargo" },
];

export function StatementUploader() {
  const [bankName, setBankName] = useState("generic");
  const [status, setStatus] = useState<"idle" | "uploading" | "preview" | "reconciling" | "done" | "error">("idle");
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reconcileResult, setReconcileResult] = useState<{ matched: number; unmatched: number } | null>(null);

  const onDrop = useCallback(async (files: File[]) => {
    const file = files[0];
    if (!file) return;
    setStatus("uploading");
    setError(null);
    try {
      const result = await uploadStatement(file, bankName);
      setUploadResult(result);
      setStatus("preview");
    } catch (e: any) {
      setError(e.message || "Upload failed");
      setStatus("error");
    }
  }, [bankName]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"], "application/pdf": [".pdf"] },
    maxFiles: 1,
    disabled: status === "uploading",
  });

  async function handleReconcile() {
    if (!uploadResult) return;
    setStatus("reconciling");
    try {
      const result = await api.post<{ matched: number; unmatched: number; total: number }>(
        `/statements/${uploadResult.upload_id}/reconcile`
      );
      setReconcileResult(result);
      setStatus("done");
    } catch (e: any) {
      setError(e.message);
      setStatus("error");
    }
  }

  function reset() {
    setStatus("idle");
    setUploadResult(null);
    setError(null);
    setReconcileResult(null);
  }

  return (
    <div className="space-y-4">
      {/* Bank selector */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-slate-300">Bank / Format</label>
        <select
          value={bankName}
          onChange={(e) => setBankName(e.target.value)}
          className="text-sm bg-slate-800 border border-slate-700 text-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-orange-500"
        >
          {BANK_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* Drop zone */}
      {status === "idle" && (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
            isDragActive ? "border-orange-400 bg-orange-500/5" : "border-slate-600 hover:border-slate-500 hover:bg-slate-800/50"
          }`}
        >
          <input {...getInputProps()} />
          <UploadCloud className="w-8 h-8 mx-auto mb-3 text-slate-500" />
          <p className="text-sm font-medium text-slate-300">
            {isDragActive ? "Drop your statement here" : "Drop a CSV or PDF statement, or click to browse"}
          </p>
          <p className="text-xs text-slate-500 mt-1">Supports Chase, PayPal, Bank of America, and generic CSV/PDF</p>
        </div>
      )}

      {/* Uploading */}
      {status === "uploading" && (
        <div className="flex items-center gap-3 p-4 bg-orange-500/10 rounded-xl text-orange-300">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm font-medium">Parsing statement...</span>
        </div>
      )}

      {/* Preview */}
      {(status === "preview" || status === "reconciling") && uploadResult && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle className="w-4 h-4" />
              <span className="text-sm font-medium">{uploadResult.message}</span>
            </div>
            <button onClick={reset} className="text-xs text-slate-500 hover:text-slate-300">Clear</button>
          </div>

          <div className="rounded-lg border border-slate-700 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-800">
                  <th className="px-3 py-2 text-left text-slate-400 font-semibold">Date</th>
                  <th className="px-3 py-2 text-left text-slate-400 font-semibold">Description</th>
                  <th className="px-3 py-2 text-right text-slate-400 font-semibold">Amount</th>
                  <th className="px-3 py-2 text-left text-slate-400 font-semibold">Category</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {uploadResult.preview.map((line) => (
                  <tr key={line.id} className="hover:bg-slate-800/50">
                    <td className="px-3 py-1.5 text-slate-400 whitespace-nowrap">{formatDate(line.line_date)}</td>
                    <td className="px-3 py-1.5 max-w-xs truncate text-slate-300">{line.description}</td>
                    <td className="px-3 py-1.5 text-right font-mono text-slate-200">{formatCurrency(line.amount)}</td>
                    <td className="px-3 py-1.5">
                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                        line.category.startsWith("ebay")
                          ? "bg-orange-500/15 text-orange-300"
                          : line.category === "shipping"
                          ? "bg-amber-900/50 text-amber-300"
                          : "bg-slate-700 text-slate-400"
                      }`}>
                        {line.category}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {uploadResult.lines_found > uploadResult.preview.length && (
              <p className="text-xs text-center text-slate-500 py-2">
                Showing first 20 of {uploadResult.lines_found} lines
              </p>
            )}
          </div>

          <button
            onClick={handleReconcile}
            disabled={status === "reconciling"}
            className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white text-sm font-medium rounded-lg hover:bg-orange-600 disabled:opacity-50"
          >
            {status === "reconciling" && <Loader2 className="w-4 h-4 animate-spin" />}
            {status === "reconciling" ? "Reconciling..." : "Match to eBay Transactions"}
          </button>
        </div>
      )}

      {/* Done */}
      {status === "done" && reconcileResult && (
        <div className="p-4 bg-emerald-900/30 rounded-xl border border-emerald-700/50">
          <div className="flex items-center gap-2 text-emerald-400 mb-2">
            <CheckCircle className="w-4 h-4" />
            <span className="text-sm font-semibold">Reconciliation complete</span>
          </div>
          <p className="text-sm text-emerald-300">
            {reconcileResult.matched} matched · {reconcileResult.unmatched} unmatched
          </p>
          <button onClick={reset} className="mt-3 text-xs text-emerald-400 hover:text-emerald-300 underline">
            Upload another statement
          </button>
        </div>
      )}

      {/* Error */}
      {status === "error" && error && (
        <div className="flex items-center gap-3 p-4 bg-red-900/30 rounded-xl text-red-400 border border-red-700/50">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <div>
            <p className="text-sm font-medium">Upload failed</p>
            <p className="text-xs mt-0.5 text-red-400/70">{error}</p>
          </div>
          <button onClick={reset} className="ml-auto text-xs underline">Try again</button>
        </div>
      )}
    </div>
  );
}
