"use client";

import Link from "next/link";
import { Zap, Activity, Home, Terminal, Lock, Settings } from "lucide-react";

export default function Sidebar() {
    return (
        <aside className="hidden md:flex flex-col w-20 bg-[#050505] border-r border-gray-800 items-center py-6 gap-6 z-50 h-screen fixed left-0 top-0">
            {/* Brand */}
            <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-600/20 mb-4">
                <Zap size={20} className="text-white fill-current" />
            </div>

            {/* Nav */}
            <nav className="flex flex-col gap-4 w-full px-2">
                <NavIcon icon={<Home size={20} />} href="/" active />
                <NavIcon icon={<Terminal size={20} />} href="/console" />
                <NavIcon icon={<Activity size={20} />} href="/metrics" />
                <div className="h-px bg-gray-800 w-full my-2" />
                <NavIcon icon={<Lock size={20} />} href="/admin" />
                <NavIcon icon={<Settings size={20} />} href="/settings" />
            </nav>

            <div className="mt-auto">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            </div>
        </aside>
    );
}

function NavIcon({ icon, href, active }: any) {
    return (
        <Link href={href} className={`w-full aspect-square flex items-center justify-center rounded-lg transition-all ${active
                ? "bg-blue-600/10 text-blue-500 border border-blue-600/20"
                : "text-gray-600 hover:text-gray-300 hover:bg-gray-900"
            }`}>
            {icon}
        </Link>
    );
}
