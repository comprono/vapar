import { RefreshCw, ArrowRight } from "lucide-react";
import { useState } from "react";

export default function ControlPanel() {
    const [amt, setAmt] = useState(10000);
    const [risk, setRisk] = useState(0.02);
    const [confidence, setConfidence] = useState(0.65);
    const [loading, setLoading] = useState(false);

    const handleEngage = async () => {
        setLoading(true);
        try {
            // 1. Send Configuration
            console.log("Sending Config:", { amt, risk, confidence });
            const configRes = await fetch("http://127.0.0.1:8000/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    capital_base: amt,
                    risk_tolerance_pct: risk,
                    min_confidence: confidence,
                    active_markets: ["BTC", "ETH", "SPY"]
                })
            });

            if (!configRes.ok) {
                const err = await configRes.text();
                throw new Error(`Config failed: ${err}`);
            }

            // 2. Start Engine
            const startRes = await fetch("http://127.0.0.1:8000/api/engine/start", { method: "POST" });
            if (!startRes.ok) throw new Error("Start failed");

            alert("System Engaged! Monitoring Real Markets.");

        } catch (e: any) {
            console.error(e);
            alert(`Failed to engage system: ${e.message}`);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-[#0f172a] border border-slate-800 rounded-2xl p-6 h-full shadow-xl relative overflow-hidden">
            {/* Header */}
            <div className="flex justify-between items-start mb-6 relative z-10">
                <div>
                    <h3 className="text-lg font-bold text-white">Control Center</h3>
                    <p className="text-xs text-slate-400 mt-1">Configure automated execution</p>
                </div>
                <RefreshCw size={16} className={`text-slate-500 hover:text-cyan-400 cursor-pointer transition-colors ${loading ? 'animate-spin' : ''}`} />
            </div>

            {/* Input Group 1 */}
            <div className="space-y-4 relative z-10">
                <div className="bg-[#0b1221] rounded-xl p-4 border border-slate-800 hover:border-slate-700 transition-colors">
                    <div className="flex justify-between mb-2">
                        <span className="text-xs text-slate-400 font-medium uppercase">Capital Allocation</span>
                        <span className="text-xs text-slate-500">Balance: $100,000.00</span>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="bg-slate-800 rounded-full px-3 py-1.5 flex items-center gap-2">
                            <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center text-[10px] text-black font-bold">$</div>
                            <span className="text-sm font-bold">USD</span>
                        </div>
                        <input
                            type="number"
                            className="bg-transparent text-right w-full text-xl font-mono focus:outline-none"
                            value={amt}
                            onChange={(e) => setAmt(Number(e.target.value))}
                        />
                    </div>
                </div>

                <div className="flex justify-center -my-2 relative z-20">
                    <div className="bg-slate-700 p-1.5 rounded-full border-4 border-[#0f172a]">
                        <ArrowRight size={14} className="transform rotate-90 text-white" />
                    </div>
                </div>

                <div className="bg-[#0b1221] rounded-xl p-4 border border-slate-800 hover:border-slate-700 transition-colors">
                    <div className="flex justify-between mb-2">
                        <span className="text-xs text-slate-400 font-medium uppercase">Risk Tolerance</span>
                        <span className="text-xs text-slate-500">Per-Trade Risk</span>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="bg-slate-800 rounded-full px-3 py-1.5 flex items-center gap-2">
                            <div className="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center text-[10px] text-white font-bold">%</div>
                            <span className="text-sm font-bold">RISK</span>
                        </div>
                        <input
                            type="number"
                            className="bg-transparent text-right w-full text-xl font-mono focus:outline-none"
                            value={Number((risk * 100).toFixed(2))}
                            step={0.1}
                            onChange={(e) => setRisk(Number(e.target.value) / 100)}
                        />
                    </div>
                </div>

                {/* NEW: Confidence Threshold */}
                <div className="bg-[#0b1221] rounded-xl p-4 border border-slate-800 hover:border-slate-700 transition-colors">
                    <div className="flex justify-between mb-3">
                        <span className="text-xs text-slate-400 font-medium uppercase">AI Confidence Filter</span>
                        <span className="text-xs text-cyan-400 font-bold">{(confidence * 100).toFixed(0)}%</span>
                    </div>
                    <input
                        type="range"
                        min="0.5"
                        max="0.95"
                        step="0.05"
                        value={confidence}
                        onChange={(e) => setConfidence(Number(e.target.value))}
                        className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                    />
                    <p className="text-xs text-slate-500 mt-2">Only execute trades with AI confidence above this threshold</p>
                </div>
            </div>

            {/* Info Metrics */}
            <div className="mt-6 space-y-3 text-sm relative z-10">
                <div className="flex justify-between text-slate-400">
                    <span>Expected Exposure</span>
                    <span className="text-white font-mono">${(amt * risk).toFixed(2)} USD</span>
                </div>
                <div className="flex justify-between text-slate-400">
                    <span>Min Trade Confidence</span>
                    <span className="text-cyan-400">{(confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="flex justify-between text-slate-400">
                    <span>AI Fee</span>
                    <span className="text-white">Free</span>
                </div>
            </div>

            {/* Action Button */}
            <button
                onClick={handleEngage}
                disabled={loading}
                className="w-full mt-6 bg-cyan-500 hover:bg-cyan-400 text-[#0b1426] font-bold py-4 rounded-xl shadow-lg shadow-cyan-500/20 transition-all transform active:scale-95 disabled:opacity-50"
            >
                {loading ? "INITIALIZING..." : "Engage Autonomous Mode"}
            </button>

            {/* Background Decor */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/5 rounded-full blur-2xl pointer-events-none"></div>
            <div className="absolute bottom-0 left-0 w-32 h-32 bg-blue-600/5 rounded-full blur-2xl pointer-events-none"></div>
        </div>
    );
}
