"use client";

import { useState } from "react";
import { Play, ShieldAlert, Wallet } from "lucide-react";

interface SetupModalProps {
    onStart: (config: { budget: number; risk_per_trade: number }) => void;
    onCancel: () => void;
}

export default function SetupModal({ onStart, onCancel }: SetupModalProps) {
    const [budget, setBudget] = useState(10000);
    const [risk, setRisk] = useState(1);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onStart({ budget, risk_per_trade: risk / 100 });
    };

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-gray-900 border border-gray-700 p-8 rounded-2xl w-full max-w-md shadow-2xl">
                <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500 mb-6 flex items-center gap-3">
                    <ShieldAlert className="text-blue-500" />
                    System Initialization
                </h2>

                <form onSubmit={handleSubmit} className="space-y-6">

                    {/* Budget Input */}
                    <div>
                        <label className="block text-gray-400 text-sm font-bold mb-2 flex items-center gap-2">
                            <Wallet size={16} /> Total Capital (USD)
                        </label>
                        <input
                            type="number"
                            value={budget}
                            onChange={(e) => setBudget(Number(e.target.value))}
                            className="w-full bg-black border border-gray-700 rounded-lg p-3 text-white focus:ring-2 focus:ring-blue-500 outline-none"
                            min="1000"
                        />
                        <p className="text-xs text-gray-600 mt-1">Minimum recommended: $1,000</p>
                    </div>

                    {/* Risk Input */}
                    <div>
                        <label className="block text-gray-400 text-sm font-bold mb-2">
                            Risk Per Trade (%)
                        </label>
                        <input
                            type="range"
                            min="0.1"
                            max="5"
                            step="0.1"
                            value={risk}
                            onChange={(e) => setRisk(Number(e.target.value))}
                            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                        />
                        <div className="flex justify-between mt-2">
                            <span className="text-white font-mono font-bold text-lg">{risk}%</span>
                            <span className="text-xs text-gray-500 uppercase tracking-widest">
                                {risk < 1 ? "Conservative" : risk > 3 ? "Aggressive" : "Moderate"}
                            </span>
                        </div>
                    </div>

                    <div className="flex gap-4 pt-4">
                        <button
                            type="button"
                            onClick={onCancel}
                            className="px-4 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg text-white font-bold flex-1 transition-all"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-4 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 rounded-lg text-white font-bold flex-1 flex items-center justify-center gap-2 shadow-lg hover:shadow-blue-500/20 transition-all"
                        >
                            <Play size={18} fill="currentColor" /> Start Engine
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
