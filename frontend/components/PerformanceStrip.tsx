interface PerformanceStripProps {
    metrics: {
        total_pnl: number;
        total_return_pct: number;
        sharpe_ratio: number;
        max_drawdown_pct: number;
        win_rate_pct: number;
        profit_factor: number;
        total_trades: number;
        winning_trades: number;
        losing_trades: number;
    };
}

import {
    Activity,
    TrendingUp,
    ShieldCheck,
    Zap,
    BarChart,
    PieChart,
    Award
} from "lucide-react";

interface PerformanceStripProps {
    metrics: {
        total_pnl: number;
        total_return_pct: number;
        sharpe_ratio: number;
        max_drawdown_pct: number;
        win_rate_pct: number;
        profit_factor: number;
        total_trades: number;
        winning_trades: number;
        losing_trades: number;
    };
}

export default function PerformanceStrip({ metrics }: PerformanceStripProps) {
    const isProfit = metrics.total_pnl >= 0;
    const quality = calculateQualityScore(metrics);

    const cards = [
        {
            label: "Absolute P&L",
            value: `$${metrics.total_pnl.toLocaleString()}`,
            sub: `${metrics.total_return_pct > 0 ? '+' : ''}${metrics.total_return_pct.toFixed(2)}%`,
            icon: <TrendingUp className={isProfit ? "text-green-400" : "text-red-400"} size={16} />,
            color: isProfit ? "text-green-400" : "text-red-400"
        },
        {
            label: "Sharpe Ratio",
            value: metrics.sharpe_ratio.toFixed(2),
            sub: metrics.sharpe_ratio > 1.5 ? "Institutional" : "Market Avg",
            icon: <ShieldCheck className="text-cyan-400" size={16} />,
            color: "text-cyan-400"
        },
        {
            label: "Edge (Win Rate)",
            value: `${metrics.win_rate_pct.toFixed(1)}%`,
            sub: `${metrics.winning_trades}W / ${metrics.losing_trades}L`,
            icon: <Zap className="text-amber-400" size={16} />,
            color: "text-white"
        },
        {
            label: "Risk (Drawdown)",
            value: `${metrics.max_drawdown_pct.toFixed(2)}%`,
            sub: "Trailing Peak",
            icon: <Activity className="text-red-400" size={16} />,
            color: "text-red-400"
        },
        {
            label: "Profit Factor",
            value: metrics.profit_factor.toFixed(2),
            sub: metrics.profit_factor > 2 ? "High Alpha" : "Normal",
            icon: <PieChart className="text-purple-400" size={16} />,
            color: "text-purple-400"
        },
        {
            label: "Execution",
            value: metrics.total_trades,
            sub: "Total Cycles",
            icon: <BarChart className="text-slate-400" size={16} />,
            color: "text-white"
        },
        {
            label: "Strategy Grade",
            value: `${quality}/10`,
            sub: getGradeLabel(quality),
            icon: <Award className="text-cyan-500" size={16} />,
            color: "text-cyan-500"
        }
    ];

    return (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-8">
            {cards.map((card, idx) => (
                <div key={idx} className="relative overflow-hidden bg-[#0f172a]/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-4 transition-all hover:border-slate-700 hover:translate-y-[-2px] group">
                    <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-br from-white/5 to-transparent rounded-full -mr-8 -mt-8" />
                    <div className="flex items-center justify-between mb-3">
                        <div className="text-[10px] text-slate-500 uppercase font-black tracking-widest">{card.label}</div>
                        <div className="bg-slate-900/50 p-1.5 rounded-lg border border-slate-800 group-hover:border-slate-600 transition-colors">
                            {card.icon}
                        </div>
                    </div>
                    <div className={`text-xl font-bold font-mono tracking-tight ${card.color}`}>
                        {card.value}
                    </div>
                    <div className="text-[10px] text-slate-500 font-bold mt-1 uppercase">
                        {card.sub}
                    </div>
                </div>
            ))}
        </div>
    );
}

function getGradeLabel(score: number): string {
    if (score >= 8) return "Legendary";
    if (score >= 6) return "Elite";
    if (score >= 4) return "Stable";
    return "Refine Needed";
}

function calculateQualityScore(metrics: any): number {
    let score = 0;
    if (metrics.sharpe_ratio > 2) score += 3;
    else if (metrics.sharpe_ratio > 1) score += 2;
    // ... rest same as before
    return Math.min(score + 1, 10);
    return Math.min(score, 10);
}
