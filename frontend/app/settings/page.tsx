"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { CheckCircle, XCircle, ExternalLink, AlertTriangle } from "lucide-react";

interface EbayStatus {
  connected: boolean;
  mock_mode?: boolean;
  expires_at?: string | null;
}

const BANK_FORMATS = [
  {
    name: "Chase",
    value: "chase",
    columns: "Transaction Date, Post Date, Description, Category, Type, Amount, Memo",
  },
  {
    name: "PayPal",
    value: "paypal",
    columns: "Date, Time, TimeZone, Name, Type, Status, Currency, Gross, Fee, Net, ...",
  },
  {
    name: "Bank of America",
    value: "bofa",
    columns: "Date, Description, Amount, Running Bal.",
  },
  {
    name: "Generic CSV",
    value: "generic",
    columns: "Auto-detected. Must have at least 3 columns: Date, Description, Amount.",
  },
];

export default function SettingsPage() {
  const [disconnecting, setDisconnecting] = useState(false);

  const { data: ebayStatus, isLoading, mutate } = useSWR<EbayStatus>("/ebay/auth/status");

  async function connectEbay() {
    try {
      const res = await api.get<{ auth_url: string }>("/ebay/auth/url");
      window.open(res.auth_url, "_blank", "width=600,height=700");
    } catch (e: any) {
      alert("Cannot start OAuth: " + e.message);
    }
  }

  async function disconnectEbay() {
    if (!confirm("Disconnect your eBay account?")) return;
    setDisconnecting(true);
    try {
      await api.post("/ebay/auth/disconnect");
      await mutate();
    } catch (e: any) {
      alert("Failed: " + e.message);
    } finally {
      setDisconnecting(false);
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-0.5">Configure your eBay connection and data preferences</p>
      </div>

      {/* eBay OAuth */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">eBay Account Connection</h2>

        {isLoading ? (
          <div className="h-10 bg-gray-100 rounded animate-pulse" />
        ) : ebayStatus?.mock_mode ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-amber-700">
              <AlertTriangle className="w-4 h-4" />
              <span className="text-sm font-medium">Running in Demo Mode</span>
            </div>
            <p className="text-sm text-gray-500">
              eBay credentials are not configured. The dashboard is using simulated data.
            </p>
            <div className="bg-gray-50 rounded-lg p-4 text-sm space-y-2">
              <p className="font-medium text-gray-700">To connect your eBay account:</p>
              <ol className="list-decimal list-inside space-y-1 text-gray-600">
                <li>Register at <strong>developer.ebay.com</strong> (free)</li>
                <li>Create an application and get your Client ID and Secret</li>
                <li>
                  Copy <code className="bg-gray-200 px-1 rounded text-xs">backend/.env.example</code> to{" "}
                  <code className="bg-gray-200 px-1 rounded text-xs">backend/.env</code>
                </li>
                <li>Fill in <code className="bg-gray-200 px-1 rounded text-xs">EBAY_CLIENT_ID</code> and{" "}
                  <code className="bg-gray-200 px-1 rounded text-xs">EBAY_CLIENT_SECRET</code>
                </li>
                <li>Restart the backend server</li>
                <li>Click "Connect eBay Account" below</li>
              </ol>
            </div>
            <button
              onClick={connectEbay}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
            >
              <ExternalLink className="w-4 h-4" />
              Connect eBay Account
            </button>
          </div>
        ) : ebayStatus?.connected ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-emerald-600">
              <CheckCircle className="w-4 h-4" />
              <span className="text-sm font-medium">eBay account connected</span>
            </div>
            {ebayStatus.expires_at && (
              <p className="text-xs text-gray-500">Token expires: {ebayStatus.expires_at}</p>
            )}
            <button
              onClick={disconnectEbay}
              disabled={disconnecting}
              className="px-4 py-2 border border-red-200 text-red-600 text-sm font-medium rounded-lg hover:bg-red-50 disabled:opacity-50"
            >
              {disconnecting ? "Disconnecting..." : "Disconnect eBay Account"}
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-gray-500">
              <XCircle className="w-4 h-4" />
              <span className="text-sm">Not connected</span>
            </div>
            <button
              onClick={connectEbay}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
            >
              <ExternalLink className="w-4 h-4" />
              Connect eBay Account
            </button>
          </div>
        )}
      </div>

      {/* Bank statement formats */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Bank Statement Formats</h2>
        <p className="text-sm text-gray-500">
          When uploading a statement on the Dashboard page, select the matching bank for best results.
        </p>
        <div className="space-y-3">
          {BANK_FORMATS.map((b) => (
            <div key={b.value} className="p-3 bg-gray-50 rounded-lg">
              <div className="text-sm font-medium text-gray-800 mb-1">{b.name}</div>
              <code className="text-xs text-gray-500">{b.columns}</code>
            </div>
          ))}
        </div>
      </div>

      {/* About */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-2">
        <h2 className="text-sm font-semibold text-gray-700">About</h2>
        <div className="text-sm text-gray-500 space-y-1">
          <p>Sports Card Dashboard v1.0</p>
          <p>Backend API: <code className="bg-gray-100 px-1 rounded text-xs">http://localhost:8000</code></p>
          <p>API Docs: <a href="http://localhost:8000/docs" target="_blank" rel="noopener" className="text-blue-600 hover:underline">localhost:8000/docs</a></p>
        </div>
      </div>
    </div>
  );
}
