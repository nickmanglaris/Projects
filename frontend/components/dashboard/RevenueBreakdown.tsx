"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { DashboardSummary } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

interface Props {
  summary: DashboardSummary;
}

export function RevenueBreakdown({ summary }: Props) {
  const data = [
    { name: "Revenue", value: summary.revenue_total, color: "#f97316" },
    { name: "Costs", value: summary.cost_total, color: "#475569" },
    {
      name: "Net Profit",
      value: Math.abs(summary.profit_total),
      color: summary.profit_total >= 0 ? "#4ade80" : "#f87171",
    },
  ].filter((d) => d.value > 0);

  return (
    <div>
      <h2 className="text-sm font-semibold text-slate-300 mb-1">Revenue Breakdown</h2>
      <p className="text-xs text-slate-500 mb-3">Revenue vs costs vs profit</p>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={80}
            paddingAngle={3}
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => formatCurrency(value as number)}
            contentStyle={{
              backgroundColor: "#1e293b",
              border: "1px solid #334155",
              borderRadius: "8px",
              color: "#f1f5f9",
              fontSize: "12px",
            }}
          />
          <Legend
            iconType="circle"
            iconSize={8}
            formatter={(value) => <span style={{ color: "#94a3b8", fontSize: "11px" }}>{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
