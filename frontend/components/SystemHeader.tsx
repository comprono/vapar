import { Play, Square, Zap, Menu, Search, Bell } from "lucide-react";

interface SystemHeaderProps {
    isRunning: boolean;
    onToggle: (state: "start" | "stop") => void;
    systemStatus: string;
}

export default function SystemHeader({ isRunning, onToggle, systemStatus }: SystemHeaderProps) {
    return (
        <header className="bg-[#202124] border-b border-[#5f6368]/30 sticky top-0 z-50">
            <div className="max-w-[1700px] mx-auto px-6 h-16 flex items-center justify-between">

                {/* Left: Branding */}
                <div className="flex items-center gap-4">
                    <button className="text-[#9aa0a6] hover:text-[#e8eaed] transition-colors p-2 rounded-full hover:bg-[#303134]">
                        <Menu size={20} />
                    </button>
                    <div className="flex items-center gap-2">
                        <div className="h-8 w-8 bg-[#8ab4f8] rounded flex items-center justify-center">
                            <Zap size={20} className="text-[#202124] fill-current" />
                        </div>
                        <span className="text-[22px] font-normal text-[#e8eaed] tracking-tight">Antigravity<span className="font-bold text-[#8ab4f8]">Platform</span></span>
                    </div>
                </div>

                {/* Center: Search (Visual) */}
                <div className="hidden md:flex items-center bg-[#303134] rounded-lg h-10 w-[500px] px-4 mx-4 focus-within:bg-white focus-within:text-black group transition-colors">
                    <Search size={18} className="text-[#9aa0a6] group-focus-within:text-black mr-3" />
                    <input
                        type="text"
                        placeholder="Search markets, orders, or logs..."
                        className="bg-transparent border-none outline-none text-[#e8eaed] group-focus-within:text-black w-full text-sm placeholder:text-[#9aa0a6]"
                    />
                </div>

                {/* Right: Actions */}
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-3 mr-4 border-r border-[#5f6368]/30 pr-4">
                        <div className={`h-2.5 w-2.5 rounded-full ${isRunning ? 'bg-[#81c995]' : 'bg-[#f28b82]'}`} />
                        <span className="text-sm font-medium text-[#e8eaed] uppercase tracking-wide text-[11px]">{systemStatus}</span>
                    </div>

                    {!isRunning ? (
                        <button
                            onClick={() => onToggle("start")}
                            className="bg-[#8ab4f8] hover:bg-[#aecbfa] text-[#202124] px-6 h-9 rounded text-sm font-medium transition-colors flex items-center gap-2"
                        >
                            <Play size={16} fill="currentColor" /> Initialize
                        </button>
                    ) : (
                        <button
                            onClick={() => onToggle("stop")}
                            className="bg-[#303134] hover:bg-[#3c4043] border border-[#5f6368] text-[#f28b82] px-6 h-9 rounded text-sm font-medium transition-colors flex items-center gap-2"
                        >
                            <Square size={16} fill="currentColor" /> Stop
                        </button>
                    )}

                    <button className="text-[#9aa0a6] hover:text-[#e8eaed] p-2 rounded-full hover:bg-[#303134]">
                        <Bell size={20} />
                    </button>
                    <div className="h-8 w-8 rounded-full bg-[#a142f4] flex items-center justify-center text-white text-xs font-bold">
                        P
                    </div>
                </div>
            </div>
        </header>
    );
}
