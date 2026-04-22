import { Terminal, Clock, Info, AlertTriangle, Bug } from "lucide-react";
import { useEffect, useRef } from "react";

interface LogConsoleProps {
    logs: string[];
}

export default function LogConsole({ logs }: LogConsoleProps) {
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (bottomRef.current) {
            bottomRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [logs]);

    return (
        <div className="flex flex-col h-64 bg-[#292a2d] font-mono text-sm leading-6">
            <div className="px-4 py-2 border-b border-[#5f6368]/30 bg-[#303134] flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <span className="text-[#e8eaed] font-medium text-xs">Logs Explorer</span>
                    <div className="flex gap-2 text-[10px]">
                        <span className="px-2 py-0.5 rounded bg-[#8ab4f8]/20 text-[#8ab4f8] cursor-pointer hover:bg-[#8ab4f8]/30">INFO</span>
                        <span className="px-2 py-0.5 rounded bg-[#f28b82]/20 text-[#f28b82] cursor-pointer hover:bg-[#f28b82]/30">ERROR</span>
                        <span className="px-2 py-0.5 rounded bg-[#81c995]/20 text-[#81c995] cursor-pointer hover:bg-[#81c995]/30">EXEC</span>
                    </div>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar text-[11px] md:text-[13px]">
                {logs.length === 0 && (
                    <div className="text-[#9aa0a6] text-center mt-10">No log entries found.</div>
                )}
                {logs.map((log, i) => {
                    const isError = log.includes("ERROR") || log.includes("CRITICAL");
                    const isTrade = log.includes("EXECUTE") || log.includes("Market");

                    return (
                        <div key={i} className="flex gap-3 hover:bg-[#3c4043] -mx-4 px-4 py-0.5">
                            <span className="text-[#9aa0a6] select-none w-20 shrink-0 border-r border-[#5f6368]/30">
                                {log.split(']')[0].replace('[', '')}
                            </span>
                            <span className={`${isError ? "text-[#f28b82]" :
                                    isTrade ? "text-[#81c995] font-medium" :
                                        "text-[#e8eaed]"
                                }`}>
                                {log.split('] ')[1]}
                            </span>
                        </div>
                    );
                })}
                <div ref={bottomRef} />
            </div>
        </div>
    );
}
