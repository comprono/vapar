"use client";

import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

interface ChartWidgetProps {
    data: any[]; // { timestamp: string, value: number }
}

export default function ChartWidget({ data = [] }: ChartWidgetProps) {
    const safeData = data || [];
    const latestValue = safeData.length > 0 ? safeData[safeData.length - 1].value : 0;
    const startValue = safeData.length > 0 ? safeData[0].value : 0;
    const change = latestValue - startValue;
    const changePct = startValue !== 0 ? (change / startValue) * 100 : 0;

    return (
        <div className="bg-[#0f172a] border border-slate-800 rounded-2xl p-6 relative overflow-hidden h-[400px]">
            {/* Header Overlays */}
            <div className="flex justify-between items-start mb-4 relative z-10">
                <div>
                    <h3 className="text-slate-400 text-sm">Total Portfolio Value</h3>
                    <div className="text-3xl font-bold text-white mt-1">
                        ${latestValue.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </div>
                </div>
                <div className={`flex items-center gap-2 px-3 py-1 rounded-lg border ${change >= 0
                    ? "bg-green-500/10 border-green-500/20 text-green-400"
                    : "bg-red-500/10 border-red-500/20 text-red-400"
                    }`}>
                    <span className="font-bold text-sm">
                        {change >= 0 ? "+" : ""}{changePct.toFixed(2)}%
                    </span>
                </div>
            </div>

            {/* Recharts Area Chart */}
            <div className="h-64 w-full mt-4">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={safeData}>
                        <defs>
                            <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <XAxis
                            dataKey="timestamp"
                            stroke="#475569"
                            tick={{ fontSize: 10 }}
                            tickLine={false}
                            axisLine={false}
                        />
                        <YAxis
                            stroke="#475569"
                            tick={{ fontSize: 10 }}
                            tickLine={false}
                            axisLine={false}
                            domain={['auto', 'auto']}
                            tickFormatter={(val) => `$${val}`}
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                            itemStyle={{ color: '#0ea5e9' }}
                            formatter={(value: number) => [`$${value.toFixed(2)}`, "Value"]}
                        />
                        <Area
                            type="monotone"
                            dataKey="value"
                            stroke="#0ea5e9"
                            strokeWidth={2}
                            fillOpacity={1}
                            fill="url(#colorValue)"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            {/* Timeframe Selectors */}
            <div className="flex justify-between mt-4 border-t border-slate-800 pt-4">
                <div className="flex gap-4">
                    <TimeBtn label="LIVE" active />
                    <TimeBtn label="1H" />
                    <TimeBtn label="1D" />
                </div>
                <div className="text-xs text-slate-500">
                    Auto-updating via Engine
                </div>
            </div>
        </div>
    );
}

function TimeBtn({ label, active }: { label: string, active?: boolean }) {
    return (
        <button className={`text-xs font-medium px-2 py-1 rounded transition-colors ${active ? "bg-slate-700 text-white" : "text-slate-500 hover:text-slate-300"
            }`}>
            {label}
        </button>
    );
}
