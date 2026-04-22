"use client";

import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import { Play, Square, Shield, Activity, Database, Brain, Lock } from "lucide-react";

// --- Types ---
interface LogEntry {
    time: string;
    level: string;
    message: string;
}

interface SystemState {
    status: "STARTING" | "RUNNING" | "STOPPED" | "ERROR";
    mode: "SHADOW" | "LIVE";
    system_risk_score: number;
    active_markets: number;
    components: {
        data: boolean;
        research: boolean;
        decision: boolean;
        execution: boolean;
    };
    logs: LogEntry[];
    metrics: {
        latency_ms: number;
        throughput: number;
        cpu_usage: number;
    };
}

const DEFAULT_STATE: SystemState = {
    status: "STOPPED",
    mode: "SHADOW",
    system_risk_score: 0.0,
    active_markets: 0,
    components: { data: false, research: false, decision: false, execution: false },
    logs: [],
    metrics: { latency_ms: 0, throughput: 0, cpu_usage: 0 }
};

export default function Dashboard() {
    const [state, setState] = useState<SystemState>(DEFAULT_STATE);
    const [selectedMode, setSelectedMode] = useState<"SHADOW" | "LIVE">("SHADOW");

    // Polling System State
    useEffect(() => {
        const interval = setInterval(async () => {
            try {
                // Mocking response for UI development if backend is offline
                // In prod: const res = await fetch("http://127.0.0.1:8000/api/engine/status");
                // const data = await res.json();

                // Temporary Mock Data for Visualization
                setState(prev => ({
                    ...prev,
                    metrics: {
                        latency_ms: Math.floor(Math.random() * 50) + 10,
                        throughput: Math.floor(Math.random() * 100),
                        cpu_usage: Math.floor(Math.random() * 30) + 10,
                    }
                }));
            } catch (e) { console.error(e); }
        }, 1000);
        return () => clearInterval(interval);
    }, []);

    const handleAction = async (action: "start" | "stop") => {
        try {
            await fetch(`http://127.0.0.1:8000/api/engine/${action}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mode: selectedMode }),
            });
            setState(prev => ({ ...prev, status: action === "start" ? "RUNNING" : "STOPPED" }));
        } catch (e) { console.error(e); }
    };

    return (
        <div className="min-h-screen bg-[#0a0a0a] text-gray-200 font-mono flex">
            <Sidebar />

            <main className="flex-1 md:ml-20 p-6 grid grid-cols-12 gap-6">

                {/* --- HEADER / CONTROLS --- */}
                <header className="col-span-12 flex items-center justify-between border-b border-gray-800 pb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-white tracking-tight">System Internals</h1>
                        <p className="text-xs text-gray-500 mt-1">
                            ENGINE_ID: <span className="text-blue-400">AG_CORE_V1</span> |
                            BUILD: <span className="text-blue-400">PROD_RELEASE</span>
                        </p>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="flex bg-gray-900 rounded p-1 border border-gray-800">
                            {["SHADOW", "LIVE"].map((m) => (
                                <button
                                    key={m}
                                    onClick={() => setSelectedMode(m as any)}
                                    disabled={state.status === "RUNNING"}
                                    className={`px-4 py-1.5 text-xs font-bold rounded transition-all ${selectedMode === m
                                            ? (m === "SHADOW" ? "bg-yellow-900/50 text-yellow-500 border border-yellow-700" : "bg-red-900/50 text-red-500 border border-red-700")
                                            : "text-gray-500 hover:text-gray-300"
                                        }`}
                                >
                                    {m} MODE
                                </button>
                            ))}
                        </div>

                        {state.status === "STOPPED" ? (
                            <button
                                onClick={() => handleAction("start")}
                                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded font-bold text-sm transition-all"
                            >
                                <Play size={16} fill="currentColor" /> INITIALIZE
                            </button>
                        ) : (
                            <button
                                onClick={() => handleAction("stop")}
                                className="flex items-center gap-2 bg-red-900/50 border border-red-500/50 text-red-500 px-6 py-2 rounded font-bold text-sm hover:bg-red-900/70"
                            >
                                <Square size={16} fill="currentColor" /> HALT
                            </button>
                        )}
                    </div>
                </header>

                {/* --- METRICS ROW --- */}
                <div className="col-span-12 grid grid-cols-4 gap-4">
                    <MetricCard label="CPU Usage" value={`${state.metrics.cpu_usage}%`} icon={<Activity size={16} />} color="blue" />
                    <MetricCard label="Event Latency" value={`${state.metrics.latency_ms}ms`} icon={<ZapIcon />} color="purple" />
                    <MetricCard label="Active Markets" value={state.active_markets.toString()} icon={<Database size={16} />} color="green" />
                    <MetricCard label="Risk Score" value={state.system_risk_score.toFixed(2)} icon={<Shield size={16} />} color={state.system_risk_score > 0.5 ? "red" : "green"} />
                </div>

                {/* --- MAIN CONSOLES --- */}

                {/* 1. Component Health */}
                <div className="col-span-12 md:col-span-4 bg-gray-900/50 border border-gray-800 rounded-lg p-4">
                    <h3 className="text-sm font-bold text-gray-400 mb-4 flex items-center gap-2">
                        <Activity size={16} /> Component Status
                    </h3>
                    <div className="space-y-2">
                        <ComponentStatus name="Data Ingestion Layer" status="ONLINE" latency="12ms" />
                        <ComponentStatus name="Research / ML Engine" status="STANDBY" latency="--" />
                        <ComponentStatus name="Decision Core" status="ONLINE" latency="4ms" />
                        <ComponentStatus name="Execution Gatekeeper" status="LOCKED" latency="0ms" />
                    </div>
                </div>

                {/* 2. Live Logs */}
                <div className="col-span-12 md:col-span-8 bg-gray-900/50 border border-gray-800 rounded-lg p-4 flex flex-col h-[300px]">
                    <h3 className="text-sm font-bold text-gray-400 mb-4 flex items-center gap-2">
                        <Brain size={16} /> System Event Stream
                    </h3>
                    <div className="flex-1 overflow-y-auto font-mono text-xs space-y-1 p-2 bg-black rounded border border-gray-800">
                        <LogLine time="10:42:01" level="INFO" msg="System initialized in SHADOW mode" />
                        <LogLine time="10:42:02" level="INFO" msg="Database connection established (SQLite)" />
                        <LogLine time="10:42:02" level="DEBUG" msg="Loaded 24 market definitions" />
                        <LogLine time="10:42:05" level="WARN" msg="High latency on provider: Binance" />
                        {state.logs.map((L, i) => (
                            <LogLine key={i} time={L.time} level={L.level} msg={L.message} />
                        ))}
                    </div>
                </div>

            </main>
        </div>
    );
}

// --- Subcomponents ---

function MetricCard({ label, value, icon, color }: any) {
    const colors: any = {
        blue: "text-blue-400 border-blue-900/30",
        purple: "text-purple-400 border-purple-900/30",
        green: "text-emerald-400 border-emerald-900/30",
        red: "text-red-400 border-red-900/30",
    };
    return (
        <div className={`bg-gray-900/30 border ${colors[color]} rounded p-4 flex items-center justify-between`}>
            <div>
                <p className="text-xs text-gray-500 uppercase font-bold">{label}</p>
                <p className={`text-2xl font-bold ${colors[color].split(" ")[0]}`}>{value}</p>
            </div>
            <div className={`p-2 rounded-full bg-gray-800/50 ${colors[color].split(" ")[0]}`}>{icon}</div>
        </div>
    );
}

function ComponentStatus({ name, status, latency }: any) {
    const isOnline = status === "ONLINE";
    return (
        <div className="flex items-center justify-between p-2 bg-black/40 rounded border border-gray-800">
            <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${isOnline ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-gray-600"}`} />
                <span className="text-xs font-medium text-gray-300">{name}</span>
            </div>
            <div className="flex items-center gap-4">
                <span className="text-[10px] text-gray-600 font-mono">{latency}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${isOnline ? "bg-emerald-900/30 text-emerald-500" : "bg-gray-800 text-gray-500"}`}>
                    {status}
                </span>
            </div>
        </div>
    );
}

function LogLine({ time, level, msg }: any) {
    const levelColors: any = {
        INFO: "text-blue-400",
        WARN: "text-yellow-400",
        ERROR: "text-red-400",
        DEBUG: "text-gray-500"
    };
    return (
        <div className="flex gap-3 hover:bg-gray-900/50 px-1 rounded">
            <span className="text-gray-600 w-16 mb-0.5">{time}</span>
            <span className={`w-12 font-bold ${levelColors[level] || "text-gray-400"}`}>{level}</span>
            <span className="text-gray-300">{msg}</span>
        </div>
    );
}

function ZapIcon() { // Simple fallback icon
    return (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
        </svg>
    )
}
