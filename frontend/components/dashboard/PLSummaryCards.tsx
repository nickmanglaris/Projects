"use client";

import { DashboardSummary } from "@/lib/types";
import { formatCurrency, formatPct } from "@/lib/utils";
import { TrendingUp, TrendingDown, DollarSign, ShoppingCart, BarChart2, Percent } from "lucide-react";

interface Props {
  summary: DashboardSummary;
}

interface KPICardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  positive?: boolean | null;
  subtitle?: string;
}

function KPICard({ label, value, icon, positive, subtitle }: KPICardProps) {
  return (
    <div className="bg-slate-900 rounded-xl border border-slate-700 p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-400">{label}</span>
        <div className="w-9 h-9 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-400">
          {icon}
        </div>
      </div>
      <div className="flex items-end gap-2">
        <span
          className={`text-2xl font-bold ${
            positive === true
              ? "text-emerald-400"
              : positive === false
              ? "text-red-400"
              : "text-slate-100"
          }`}
        >
          {value}
        </span>
      </div>
      {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
    </div>
  );
}

export function PLSummaryCards({ summary }: Props) {
  const profitPositive = summary.profit_total >= 0;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <KPICard
        label="Total Revenue"
        value={formatCurrency(summary.revenue_total)}
        icon={<DollarSign className="w-4 h-4" />}
        positive={null}
        subtitle={`${summary.transaction_count} transactions`}
      />
      <KPICard
        label="Total Cost"
        value={formatCurrency(summary.cost_total)}
        icon={<ShoppingCart className="w-4 h-4" />}
        positive={null}
        subtitle="Purchases + shipping"
      />
      <KPICard
        label="Net Profit"
        value={formatCurrency(summary.profit_total)}
        icon={profitPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
        positive={profitPositive}
        subtitle={`Avg ${formatCurrency(summary.avg_profit_per_card)}/card`}
      />
      <KPICard
        label="ROI"
        value={formatPct(summary.roi_pct)}
        icon={<Percent className="w-4 h-4" />}
        positive={summary.roi_pct >= 0}
        subtitle={`Period: ${summary.period}`}
      />
    </div>
  );
}
