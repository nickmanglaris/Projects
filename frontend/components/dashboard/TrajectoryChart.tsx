"use client";

import { TrajectoryPoint } from "@/lib/types";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { formatCurrency } from "@/lib/utils";

interface Props {
  data: TrajectoryPoint[];
}

function formatMonth(val: string) {
  if (!val) return "";
  const [year, month] = val.split("-");
  const d = new Date(Number(year), Number(month) - 1);
  return d.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}

export function TrajectoryChart({ data }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
        No data available for this period.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 4, right: 16, bottom: 4, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="date" tickFormatter={formatMonth} tick={{ fontSize: 11 }} />
        <YAxis
          yAxisId="left"
          tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
          tick={{ fontSize: 11 }}
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
          tick={{ fontSize: 11 }}
        />
        <Tooltip
          formatter={(value, name) => [formatCurrency(value as number), name as string]}
          labelFormatter={(val) => formatMonth(val as string)}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar
          yAxisId="left"
          dataKey="revenue"
          name="Revenue"
          fill="#3b82f6"
          opacity={0.8}
          radius={[2, 2, 0, 0]}
        />
        <Bar
          yAxisId="left"
          dataKey="cost"
          name="Cost"
          fill="#e5e7eb"
          opacity={0.8}
          radius={[2, 2, 0, 0]}
        />
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="cumulative_profit"
          name="Cumulative Profit"
          stroke="#10b981"
          strokeWidth={2}
          dot={false}
        />
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="profit"
          name="Monthly Profit"
          stroke="#f59e0b"
          strokeWidth={1.5}
          strokeDasharray="4 2"
          dot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
