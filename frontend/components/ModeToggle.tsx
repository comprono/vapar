"use client";

import { Shield, Zap } from "lucide-react";

interface ModeToggleProps {
    mode: "SHADOW" | "LIVE";
    onModeChange: (mode: "SHADOW" | "LIVE") => void;
    disabled: boolean;
}

export default function ModeToggle({ mode, onModeChange, disabled }: ModeToggleProps) {
    return (
        <div className="flex bg-[#0f172a] p-1 rounded-lg border border-slate-800">
            <button
                onClick={() => onModeChange("SHADOW")}
                disabled={disabled}
                className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-md text-sm font-bold transition-all ${mode === "SHADOW"
                        ? "bg-yellow-500/10 text-yellow-500 border border-yellow-500/50 shadow-[0_0_10px_rgba(234,179,8,0.2)]"
                        : "text-slate-500 hover:text-slate-300"
                    }`}
            >
                <Shield size={14} /> SHADOW
            </button>
            <button
                onClick={() => onModeChange("LIVE")}
                disabled={disabled}
                className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-md text-sm font-bold transition-all ${mode === "LIVE"
                        ? "bg-red-500/10 text-red-500 border border-red-500/50 shadow-[0_0_10px_rgba(239,68,68,0.2)]"
                        : "text-slate-500 hover:text-slate-300"
                    }`}
            >
                <Zap size={14} /> LIVE
            </button>
        </div>
    );
}
