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
        <label className="text-sm font-medium text-gray-700">Bank / Format</label>
        <select
          value={bankName}
          onChange={(e) => setBankName(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
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
            isDragActive ? "border-blue-400 bg-blue-50" : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"
          }`}
        >
          <input {...getInputProps()} />
          <UploadCloud className="w-8 h-8 mx-auto mb-3 text-gray-400" />
          <p className="text-sm font-medium text-gray-700">
            {isDragActive ? "Drop your statement here" : "Drop a CSV or PDF statement, or click to browse"}
          </p>
          <p className="text-xs text-gray-400 mt-1">Supports Chase, PayPal, Bank of America, and generic CSV/PDF</p>
        </div>
      )}

      {/* Uploading */}
      {status === "uploading" && (
        <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-xl text-blue-700">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm font-medium">Parsing statement...</span>
        </div>
      )}

      {/* Preview */}
      {(status === "preview" || status === "reconciling") && uploadResult && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-emerald-700">
              <CheckCircle className="w-4 h-4" />
              <span className="text-sm font-medium">{uploadResult.message}</span>
            </div>
            <button onClick={reset} className="text-xs text-gray-400 hover:text-gray-600">Clear</button>
          </div>

          <div className="rounded-lg border border-gray-200 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-3 py-2 text-left text-gray-500 font-semibold">Date</th>
                  <th className="px-3 py-2 text-left text-gray-500 font-semibold">Description</th>
                  <th className="px-3 py-2 text-right text-gray-500 font-semibold">Amount</th>
                  <th className="px-3 py-2 text-left text-gray-500 font-semibold">Category</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {uploadResult.preview.map((line) => (
                  <tr key={line.id} className="hover:bg-gray-50">
                    <td className="px-3 py-1.5 text-gray-600 whitespace-nowrap">{formatDate(line.line_date)}</td>
                    <td className="px-3 py-1.5 max-w-xs truncate text-gray-700">{line.description}</td>
                    <td className="px-3 py-1.5 text-right font-mono">{formatCurrency(line.amount)}</td>
                    <td className="px-3 py-1.5">
                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                        line.category.startsWith("ebay")
                          ? "bg-blue-50 text-blue-700"
                          : line.category === "shipping"
                          ? "bg-amber-50 text-amber-700"
                          : "bg-gray-100 text-gray-500"
                      }`}>
                        {line.category}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {uploadResult.lines_found > uploadResult.preview.length && (
              <p className="text-xs text-center text-gray-400 py-2">
                Showing first 20 of {uploadResult.lines_found} lines
              </p>
            )}
          </div>

          <button
            onClick={handleReconcile}
            disabled={status === "reconciling"}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {status === "reconciling" && <Loader2 className="w-4 h-4 animate-spin" />}
            {status === "reconciling" ? "Reconciling..." : "Match to eBay Transactions"}
          </button>
        </div>
      )}

      {/* Done */}
      {status === "done" && reconcileResult && (
        <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200">
          <div className="flex items-center gap-2 text-emerald-700 mb-2">
            <CheckCircle className="w-4 h-4" />
            <span className="text-sm font-semibold">Reconciliation complete</span>
          </div>
          <p className="text-sm text-emerald-600">
            {reconcileResult.matched} matched · {reconcileResult.unmatched} unmatched
          </p>
          <button onClick={reset} className="mt-3 text-xs text-emerald-600 hover:text-emerald-800 underline">
            Upload another statement
          </button>
        </div>
      )}

      {/* Error */}
      {status === "error" && error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 rounded-xl text-red-700">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <div>
            <p className="text-sm font-medium">Upload failed</p>
            <p className="text-xs mt-0.5 text-red-500">{error}</p>
          </div>
          <button onClick={reset} className="ml-auto text-xs underline">Try again</button>
        </div>
      )}
    </div>
  );
}
