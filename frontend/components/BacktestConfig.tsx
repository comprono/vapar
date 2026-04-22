"use client";

import React, { useState, useEffect } from "react";
import { Play, RotateCcw, Share2 } from "lucide-react";

interface BacktestConfigProps {
    onRunBacktest: (config: BacktestConfig, optimize?: boolean) => void;
    loading: boolean;
}

export interface BacktestConfig {
    symbols: string[];
    start_date: string;
    end_date: string;
    strategy: string;
    initial_capital: number;
    min_confidence: number;
    risk_per_trade: number;
}

export default function BacktestConfig({ onRunBacktest, loading }: BacktestConfigProps) {
    const [config, setConfig] = useState<{
        symbolsStr: string;
        start_date: string;
        end_date: string;
        strategy: string;
        initial_capital: number;
        min_confidence: number;
        risk_per_trade: number;
    }>({
        symbolsStr: "BTC-USD, ETH-USD, SOL-USD",
        start_date: "2023-01-01",
        end_date: "2024-01-01",
        strategy: "Ensemble",
        initial_capital: 10000,
        min_confidence: 0.55,
        risk_per_trade: 0.05
    });

    const [universes, setUniverses] = useState<Record<string, string[]>>({});

    useEffect(() => {
        fetch("http://127.0.0.1:8000/api/backtest/universes")
            .then(res => res.json())
            .then(data => setUniverses(data))
            .catch(err => console.error("Failed to load universes", err));
    }, []);

    const handleUniverseSelect = (uniKey: string) => {
        const symbols = universes[uniKey];
        if (symbols) {
            setConfig({ ...config, symbolsStr: symbols.join(", ") });
        }
    };

    const handleSubmit = (optimize = false) => {
        const symbols = config.symbolsStr.split(",").map(s => s.trim()).filter(s => s !== "");
        onRunBacktest({
            ...config,
            symbols
        }, optimize);
    };

    return (
        <div className="bg-[#0f172a]/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 mb-8 shadow-2xl shadow-cyan-500/5">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
                <div>
                    <h2 className="text-2xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent italic">Decision Intelligence</h2>
                    <p className="text-sm text-slate-500 mt-1">Multi-strategy ensemble & automated asset selection</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={() => handleSubmit(true)}
                        disabled={loading}
                        className="group relative flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-bold px-6 py-4 rounded-xl transition-all duration-300 shadow-lg shadow-indigo-500/20 hover:scale-[1.02]"
                    >
                        {loading ? <RotateCcw size={18} className="animate-spin" /> : <Play size={18} fill="white" />}
                        {loading ? "Searching..." : "Hyper-Optimize"}
                    </button>
                    <button
                        onClick={() => handleSubmit(false)}
                        disabled={loading}
                        className="group relative flex items-center gap-2 bg-cyan-500 hover:bg-cyan-400 disabled:bg-slate-700 disabled:cursor-not-allowed text-black font-bold px-8 py-4 rounded-xl transition-all duration-300 shadow-lg shadow-cyan-500/20 hover:scale-[1.02]"
                    >
                        <div className="absolute inset-0 bg-white/20 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity" />
                        {loading ? <RotateCcw size={20} className="animate-spin" /> : <Play size={20} fill="black" />}
                        {loading ? "Simulating..." : "Execute Simulation"}
                    </button>
                </div>
            </div>

            <div className="mb-6">
                <div className="space-y-3 mb-6">
                    <label className="text-[10px] text-slate-500 font-black uppercase tracking-widest flex items-center gap-2">
                        Asset Universes
                    </label>
                    <div className="flex flex-wrap gap-2">
                        <button
                            onClick={() => {
                                if (universes["ALL_ASSETS_COMBINED"]) {
                                    setConfig({ ...config, symbolsStr: universes["ALL_ASSETS_COMBINED"].join(", ") });
                                }
                            }}
                            className="px-3 py-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-black uppercase hover:bg-indigo-500/20 transition-all shadow-[0_0_10px_rgba(99,102,241,0.1)]"
                        >
                            🌍 Select All Markets
                        </button>

                        {Object.entries(universes).map(([name, list]) => (
                            name !== "ALL_ASSETS_COMBINED" && (
                                <button
                                    key={name}
                                    onClick={() => handleUniverseSelect(name)}
                                    className="px-3 py-1.5 rounded-lg bg-slate-800/50 border border-slate-700 text-slate-400 text-[10px] font-bold uppercase hover:bg-slate-700 hover:text-white transition-all"
                                >
                                    {name.replace(/_/g, " ")}
                                </button>
                            )
                        ))}
                    </div>
                </div>

                <div className="space-y-2">
                    <label className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Target Asset List</label>
                    <textarea
                        value={config.symbolsStr}
                        onChange={(e) => setConfig({ ...config, symbolsStr: e.target.value })}
                        className="w-full bg-slate-900/50 border border-slate-800 rounded-xl px-4 py-3 text-white text-xs font-mono focus:border-cyan-500/50 focus:outline-none transition-all placeholder:text-slate-700"
                        rows={3}
                        placeholder="BTC-USD, ETH-USD, AAPL..."
                    />
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {/* Strategy */}
                <div>
                    <label className="block text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Intelligence Mode</label>
                    <select
                        value={config.strategy}
                        onChange={(e) => setConfig({ ...config, strategy: e.target.value })}
                        className="w-full bg-[#0b1221] border border-slate-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 appearance-none cursor-pointer font-bold"
                    >
                        <option value="Ensemble">🤖 Auto-Ensemble (Logic AI)</option>
                        <option value="TrendFollower">Trend Follower (BB)</option>
                        <option value="Momentum">Momentum (MA Cross)</option>
                        <option value="MeanReversion">Mean Reversion (RSI)</option>
                    </select>
                </div>

                {/* Initial Capital */}
                <div>
                    <label className="block text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Initial Liquidity</label>
                    <div className="relative">
                        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">$</span>
                        <input
                            type="number"
                            value={config.initial_capital}
                            onChange={(e) => setConfig({ ...config, initial_capital: Number(e.target.value) })}
                            className="w-full bg-[#0b1221] border border-slate-800 rounded-xl pl-8 pr-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 transition-all"
                        />
                    </div>
                </div>

                {/* Start Date */}
                <div>
                    <label className="block text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Analysis Window Start</label>
                    <input
                        type="date"
                        value={config.start_date}
                        onChange={(e) => setConfig({ ...config, start_date: e.target.value })}
                        className="w-full bg-[#0b1221] border border-slate-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 invert-[0.9] dark:invert-0"
                    />
                </div>

                {/* End Date */}
                <div>
                    <label className="block text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">Analysis Window End</label>
                    <input
                        type="date"
                        value={config.end_date}
                        onChange={(e) => setConfig({ ...config, end_date: e.target.value })}
                        className="w-full bg-[#0b1221] border border-slate-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                    />
                </div>

                {/* Min Confidence */}
                <div>
                    <label className="flex justify-between text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">
                        Confidence Threshold
                        <span className="text-cyan-400">{(config.min_confidence * 100).toFixed(0)}%</span>
                    </label>
                    <input
                        type="range"
                        min="0.4"
                        max="0.95"
                        step="0.05"
                        value={config.min_confidence}
                        onChange={(e) => setConfig({ ...config, min_confidence: Number(e.target.value) })}
                        className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                    />
                </div>

                {/* Risk Per Trade */}
                <div>
                    <label className="flex justify-between text-xs text-slate-400 font-bold uppercase tracking-wider mb-2">
                        Risk Per Asset
                        <span className="text-cyan-400">{(config.risk_per_trade * 100).toFixed(1)}%</span>
                    </label>
                    <input
                        type="range"
                        min="0.01"
                        max="0.20"
                        step="0.01"
                        value={config.risk_per_trade}
                        onChange={(e) => setConfig({ ...config, risk_per_trade: Number(e.target.value) })}
                        className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                    />
                </div>
            </div>
        </div>
    );
}
