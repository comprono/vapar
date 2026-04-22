import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface Opportunity {
    symbol: string;
    direction: "BUY" | "SELL" | "NEUTRAL";
    confidence: number;
    expected_return: number;
    risk_score: number;
}

interface MarketTableProps {
    data: Opportunity[];
    title: string;
}

export default function MarketTable({ data, title }: MarketTableProps) {
    if (!data || data.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-64 text-[#9aa0a6] bg-[#303134]">
                <p>No active signals. Waiting for market data...</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-[#303134]">
            <div className="px-6 py-4 border-b border-[#5f6368]/30 flex justify-between items-center">
                <h3 className="font-medium text-[#e8eaed] text-sm">{title}</h3>
                <span className="text-[11px] text-[#9aa0a6]">Real-time Updates</span>
            </div>

            <div className="overflow-auto flex-1">
                <table className="w-full text-left text-sm border-collapse">
                    <thead className="text-[#9aa0a6] text-xs font-medium border-b border-[#5f6368]/30">
                        <tr>
                            <th className="px-6 py-3 font-normal">Asset</th>
                            <th className="px-6 py-3 font-normal">Signal</th>
                            <th className="px-6 py-3 font-normal text-right">Confidence</th>
                            <th className="px-6 py-3 font-normal text-right">Exp. Return</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-[#5f6368]/20">
                        {data.map((opp, idx) => (
                            <tr key={idx} className="hover:bg-[#3c4043] transition-colors group">
                                <td className="px-6 py-3 font-medium text-[#e8eaed] group-hover:text-white">
                                    {opp.symbol}
                                </td>
                                <td className="px-6 py-3">
                                    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${opp.direction === "BUY" ? "text-[#81c995]" :
                                            opp.direction === "SELL" ? "text-[#f28b82]" :
                                                "text-[#9aa0a6]"
                                        }`}>
                                        {opp.direction === "BUY" && <TrendingUp size={14} />}
                                        {opp.direction === "SELL" && <TrendingDown size={14} />}
                                        {opp.direction}
                                    </span>
                                </td>
                                <td className="px-6 py-3 text-right text-[#e8eaed]">
                                    {/* Google-style progress bar within cell */}
                                    <div className="flex items-center justify-end gap-3">
                                        <div className="w-16 h-1 bg-[#5f6368]/30 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-[#8ab4f8]"
                                                style={{ width: `${opp.confidence * 100}%` }}
                                            />
                                        </div>
                                        <span className="w-8">{(opp.confidence * 100).toFixed(0)}%</span>
                                    </div>
                                </td>
                                <td className={`px-6 py-3 text-right font-medium ${opp.expected_return > 0 ? 'text-[#81c995]' : 'text-[#f28b82]'}`}>
                                    {opp.expected_return > 0 ? "+" : ""}{(opp.expected_return * 100).toFixed(2)}%
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
