"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import ChartWidget from "@/components/ChartWidget";
import { Play, RotateCcw, Settings, Trophy, Bitcoin, BarChart3, TrendingUp, AlertTriangle, FlaskConical } from "lucide-react";

export default function BacktestPage() {
    const [isRunning, setIsRunning] = useState(false);
    const [regime, setRegime] = useState("NORMAL");
    const [assetClass, setAssetClass] = useState("CRYPTO");
    const [results, setResults] = useState<any>(null);

    const runSimulation = async () => {
        setIsRunning(true);
        // Mock simulation delay
        await new Promise(r => setTimeout(r, 2000));

        // Mock Results
        setResults({
            pnl: 1250.50,
            return_pct: 12.5,
            max_drawdown: -4.2,
            win_rate: 68,
            trades: 142,
            sharpe: 1.8,
            history: Array.from({ length: 50 }, (_, i) => ({
                timestamp: `Day ${i}`,
                value: 10000 + (Math.random() * 1000) + (i * 50)
            }))
        });
        setIsRunning(false);
    };

    return (
        <div className="min-h-screen bg-[#060b13] flex font-sans text-slate-300">
            <Sidebar />

            <main className="flex-1 md:ml-64 p-8">
                <header className="flex justify-between items-center mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
                            <FlaskConical className="text-purple-500" size={32} /> Simulation Lab
                        </h1>
                        <p className="text-slate-500">Phase 2: Cross-Market Validation & Stress Testing</p>
                    </div>
                    <div className="px-4 py-2 bg-purple-500/10 border border-purple-500/20 rounded-lg text-purple-400 text-xs font-bold uppercase tracking-wider">
                        Offline Environment
                    </div>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                    {/* Configuration Panel */}
                    <div className="space-y-6">
                        <div className="bg-[#0f172a] border border-slate-800 rounded-2xl p-6">
                            <h3 className="text-white font-bold mb-6 flex items-center gap-2">
                                <Settings size={18} /> Simulation Config
                            </h3>

                            <div className="space-y-5">
                                {/* Asset Class */}
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Target Market</label>
                                    <div className="grid grid-cols-3 gap-2">
                                        <button
                                            onClick={() => setAssetClass("EQUITY")}
                                            className={`p-3 rounded-xl border flex flex-col items-center gap-2 transition-all ${assetClass === "EQUITY" ? "bg-blue-600 border-blue-500 text-white" : "border-slate-700 hover:bg-slate-800"}`}
                                        >
                                            <BarChart3 size={20} /> <span className="text-[10px] font-bold">STOCKS</span>
                                        </button>
                                        <button
                                            onClick={() => setAssetClass("CRYPTO")}
                                            className={`p-3 rounded-xl border flex flex-col items-center gap-2 transition-all ${assetClass === "CRYPTO" ? "bg-blue-600 border-blue-500 text-white" : "border-slate-700 hover:bg-slate-800"}`}
                                        >
                                            <Bitcoin size={20} /> <span className="text-[10px] font-bold">CRYPTO</span>
                                        </button>
                                        <button
                                            onClick={() => setAssetClass("SPORTS")}
                                            className={`p-3 rounded-xl border flex flex-col items-center gap-2 transition-all ${assetClass === "SPORTS" ? "bg-blue-600 border-blue-500 text-white" : "border-slate-700 hover:bg-slate-800"}`}
                                        >
                                            <Trophy size={20} /> <span className="text-[10px] font-bold">SPORTS</span>
                                        </button>
                                    </div>
                                </div>

                                {/* Regime Selector */}
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Market Regime (Stress Test)</label>
                                    <select
                                        value={regime}
                                        onChange={(e) => setRegime(e.target.value)}
                                        className="w-full bg-black border border-slate-700 rounded-lg p-3 text-white focus:ring-2 focus:ring-purple-500 outline-none appearance-none"
                                    >
                                        <option value="NORMAL">Normal Market (Random Walk)</option>
                                        <option value="BULL">Strong Bull Run (Trend Follow)</option>
                                        <option value="BEAR">Bear Market (Short/Cash)</option>
                                        <option value="CRASH">Flash Crash (Tail Risk Check)</option>
                                        <option value="HIGH_VOL">High Volatility / Chop</option>
                                    </select>
                                </div>

                                <div className="pt-4">
                                    <button
                                        onClick={runSimulation}
                                        disabled={isRunning}
                                        className="w-full py-4 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 rounded-xl text-white font-bold shadow-lg shadow-purple-500/20 transition-all flex items-center justify-center gap-2 text-lg"
                                    >
                                        {isRunning ? <RotateCcw className="animate-spin" /> : <Play fill="currentColor" />}
                                        {isRunning ? "Simulating..." : "Run Simulation"}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Results Panel */}
                    <div className="lg:col-span-2 space-y-6">
                        <ChartWidget data={results?.history || []} />

                        {results && (
                            <div className="grid grid-cols-4 gap-4">
                                <MetricBox label="Total Return" value={`+${results.return_pct}%`} good />
                                <MetricBox label="Max Drawdown" value={`${results.max_drawdown}%`} bad />
                                <MetricBox label="Win Rate" value={`${results.win_rate}%`} />
                                <MetricBox label="Sharpe Ratio" value={results.sharpe} />
                            </div>
                        )}

                        {!results && !isRunning && (
                            <div className="bg-[#0f172a] border border-slate-800 rounded-2xl p-10 flex flex-col items-center justify-center text-center">
                                <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mb-4 text-slate-600">
                                    <FlaskConical size={32} />
                                </div>
                                <h3 className="text-white font-bold text-lg">Ready to Simulate</h3>
                                <p className="text-slate-500 max-w-sm mt-2">Select a market and regime to test your strategies against historical or synthetic data.</p>
                            </div>
                        )}
                    </div>

                </div>
            </main>
        </div>
    );
}

function MetricBox({ label, value, good, bad }: any) {
    return (
        <div className="bg-[#0f172a] border border-slate-800 rounded-xl p-4 text-center">
            <div className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1">{label}</div>
            <div className={`text-2xl font-bold font-mono ${good ? 'text-green-400' : bad ? 'text-red-400' : 'text-white'}`}>
                {value}
            </div>
        </div>
    );
}


