import { TrendingUp, TrendingDown, Target, Info } from "lucide-react";

interface BacktestSummaryProps {
    symbolResults: Record<string, any>;
    symbols: string[];
}

export default function BacktestSummary({ symbolResults, symbols }: BacktestSummaryProps) {
    return (
        <div className="bg-[#0f172a]/50 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 mb-8">
            <div className="flex items-center gap-2 mb-6">
                <Target size={20} className="text-cyan-400" />
                <h3 className="text-lg font-bold text-white">Asset Performance Breakdown</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {symbols.map(symbol => {
                    const res = symbolResults[symbol];
                    if (!res) return null;

                    const isProfit = res.total_pnl >= 0;

                    return (
                        <div key={symbol} className="bg-[#0b1221] border border-slate-800/50 rounded-xl p-4 hover:border-cyan-500/30 transition-all group">
                            <div className="flex justify-between items-start mb-3">
                                <div className="flex flex-col">
                                    <div className="text-sm font-bold text-white tracking-tight">{symbol}</div>
                                    <div className="text-[9px] text-cyan-400 font-black uppercase tracking-widest mt-0.5">Alpha Intelligence</div>
                                </div>
                                <div className={`flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-md ${isProfit ? 'text-green-400 bg-green-500/10' : 'text-red-400 bg-red-500/10'}`}>
                                    {isProfit ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                                    {res.total_return_pct.toFixed(2)}%
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-x-4 gap-y-3 mt-4">
                                <div>
                                    <div className="text-[10px] text-slate-500 uppercase font-black tracking-widest mb-1">Net P&L</div>
                                    <div className={`text-sm font-mono font-bold ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
                                        {isProfit ? '+' : ''}${res.total_pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </div>
                                </div>
                                <div>
                                    <div className="text-[10px] text-slate-500 uppercase font-black tracking-widest mb-1">Success Rate</div>
                                    <div className="text-sm text-white font-mono font-bold">{res.win_rate_pct.toFixed(1)}%</div>
                                </div>
                                <div>
                                    <div className="text-[10px] text-slate-500 uppercase font-black tracking-widest mb-1">Sharpe Ratio</div>
                                    <div className="text-sm text-white font-mono font-bold">{res.sharpe_ratio.toFixed(2)}</div>
                                </div>
                                <div>
                                    <div className="text-[10px] text-slate-500 uppercase font-black tracking-widest mb-1">Trade Count</div>
                                    <div className="text-sm text-slate-300 font-mono text-[11px]">{res.total_trades} Executions</div>
                                </div>
                            </div>

                            <div className="mt-5 space-y-1.5">
                                <div className="flex justify-between text-[9px] uppercase font-black tracking-tighter text-slate-600">
                                    <span>Momentum Strength</span>
                                    <span>{Math.min(Math.abs(res.total_return_pct) * 2.5, 100).toFixed(0)}%</span>
                                </div>
                                <div className="h-1.5 bg-slate-900 rounded-full overflow-hidden border border-slate-800/50">
                                    <div
                                        className={`h-full transition-all duration-1000 ${isProfit ? 'bg-gradient-to-r from-cyan-600 to-cyan-400' : 'bg-gradient-to-r from-red-600 to-red-400'}`}
                                        style={{ width: `${Math.min(Math.abs(res.total_return_pct) * 2.5, 100)}%` }}
                                    />
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
