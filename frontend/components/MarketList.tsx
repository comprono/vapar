import { TrendingUp, TrendingDown } from "lucide-react";

interface MarketItem {
    name: string;
    symbol: string;
    price: number;
    change: number;
    marketCap: string;
}

export default function MarketList({ items }: { items: any[] }) {
    // Mock data if empty
    const displayItems = items.length > 0 ? items : [
        { name: "Bitcoin", symbol: "BTC", price: 32254.56, change: 3.25, marketCap: "$958B" },
        { name: "USDC Coin", symbol: "USDC", price: 1.00, change: 0.01, marketCap: "$48B" },
        { name: "Ethereum", symbol: "ETH", price: 2125.38, change: -1.25, marketCap: "$258B" },
        { name: "Tesla Inc", symbol: "TSLA", price: 245.67, change: 5.12, marketCap: "$780B" }
    ];

    return (
        <div className="bg-[#0f172a] border border-slate-800 rounded-2xl p-6 shadow-sm">
            <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-bold text-white">Market Intelligence</h3>
                <button className="text-xs text-cyan-400 hover:text-cyan-300 font-medium">View All</button>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-left">
                    <thead>
                        <tr className="text-slate-500 text-xs uppercase tracking-wider border-b border-slate-800/50">
                            <th className="pb-4 pl-2 font-medium">Name</th>
                            <th className="pb-4 font-medium">Price</th>
                            <th className="pb-4 font-medium">24h %</th>
                            <th className="pb-4 font-medium text-right pr-2">Market Cap</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/30">
                        {displayItems.map((item, i) => (
                            <tr key={i} className="group hover:bg-slate-800/30 transition-colors">
                                <td className="py-4 pl-2">
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-[10px] font-bold text-white group-hover:bg-cyan-500 group-hover:text-[#0f172a] transition-colors">
                                            {item.symbol[0]}
                                        </div>
                                        <div>
                                            <div className="font-bold text-white text-sm">{item.name}</div>
                                        </div>
                                    </div>
                                </td>
                                <td className="py-4 font-mono text-slate-300 text-sm">
                                    ${item.price.toLocaleString()}
                                </td>
                                <td className="py-4">
                                    <span className={`flex items-center gap-1 text-xs font-bold ${item.change >= 0 ? "text-green-400" : "text-red-400"
                                        }`}>
                                        {item.change >= 0 ? "+" : ""}{item.change}%
                                    </span>
                                </td>
                                <td className="py-4 text-right pr-2 font-mono text-slate-400 text-sm">
                                    {item.marketCap}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
