interface Trade {
    symbol?: string; // Optional for backward compatibility
    entry_time: string;
    exit_time: string;
    entry_price: number;
    exit_price: number;
    shares: number;
    pnl: number;
    return_pct: number;
    reason?: string;
}

interface TradeTableProps {
    trades: Trade[];
}

export default function TradeTable({ trades }: TradeTableProps) {
    if (trades.length === 0) {
        return (
            <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-8 text-center">
                <p className="text-slate-500">No trades executed in this backtest.</p>
            </div>
        );
    }

    return (
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl overflow-hidden">
            <div className="p-4 border-b border-slate-800">
                <h3 className="text-white font-bold">Trade History</h3>
                <p className="text-xs text-slate-500 mt-1">{trades.length} trades executed</p>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead>
                        <tr className="border-b border-slate-800 bg-[#0b1221]/50">
                            <th className="text-left text-[10px] text-slate-500 font-black uppercase tracking-widest px-4 py-3">#</th>
                            <th className="text-left text-[10px] text-slate-500 font-black uppercase tracking-widest px-4 py-3">Asset</th>
                            <th className="text-left text-[10px] text-slate-500 font-black uppercase tracking-widest px-4 py-3">Entry/Exit</th>
                            <th className="text-right text-[10px] text-slate-500 font-black uppercase tracking-widest px-4 py-3">Units</th>
                            <th className="text-right text-[10px] text-slate-500 font-black uppercase tracking-widest px-4 py-3">Price Delta</th>
                            <th className="text-right text-[10px] text-slate-500 font-black uppercase tracking-widest px-4 py-3">Profit/Loss</th>
                            <th className="text-right text-[10px] text-slate-500 font-black uppercase tracking-widest px-4 py-3">Return</th>
                            <th className="text-left text-[10px] text-slate-500 font-black uppercase tracking-widest px-4 py-4 min-w-[200px]">Alpha Logic (Diagnostic)</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/30">
                        {trades.map((trade, index) => {
                            const isWin = trade.pnl > 0;
                            return (
                                <tr key={index} className="hover:bg-cyan-500/[0.02] transition-colors group">
                                    <td className="px-4 py-4 text-[10px] text-slate-600 font-bold">{index + 1}</td>
                                    <td className="px-4 py-4">
                                        <span className="text-xs font-black text-white group-hover:text-cyan-400 transition-colors uppercase">{trade.symbol || "N/A"}</span>
                                    </td>
                                    <td className="px-4 py-4">
                                        <div className="flex flex-col">
                                            <span className="text-[11px] text-slate-300 font-mono">{new Date(trade.entry_time).toLocaleDateString()}</span>
                                            <span className="text-[9px] text-slate-600 font-mono tracking-tighter">to {new Date(trade.exit_time).toLocaleDateString()}</span>
                                        </div>
                                    </td>
                                    <td className="px-4 py-4 text-xs text-right text-slate-400 font-mono">
                                        {trade.shares < 0.01 ? trade.shares.toFixed(8) : trade.shares.toLocaleString(undefined, { maximumFractionDigits: 4 })}
                                    </td>
                                    <td className="px-4 py-4 text-xs text-right font-mono">
                                        <div className="flex flex-col">
                                            <span className="text-slate-500">${trade.entry_price.toFixed(2)}</span>
                                            <span className="text-white font-bold">${trade.exit_price.toFixed(2)}</span>
                                        </div>
                                    </td>
                                    <td className={`px-4 py-4 text-sm text-right font-black font-mono ${isWin ? 'text-green-400' : 'text-red-400'}`}>
                                        {isWin ? '+' : ''}${Math.abs(trade.pnl).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </td>
                                    <td className="px-4 py-4 text-right">
                                        <span className={`px-2 py-0.5 rounded text-[10px] font-black ${isWin ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-500'}`}>
                                            {isWin ? '+' : ''}{trade.return_pct.toFixed(2)}%
                                        </span>
                                    </td>
                                    <td className="px-4 py-4">
                                        <div className="text-[10px] text-slate-400 leading-relaxed max-w-xs truncate hover:text-clip hover:overflow-visible hover:whitespace-normal transition-all cursor-help border-l border-slate-800 pl-3 italic">
                                            {trade.reason || "Automatic engine execution"}
                                        </div>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
