import { LucideIcon } from "lucide-react";

interface MetricCardProps {
    label: string;
    value: string;
    subValue?: string;
    icon: LucideIcon;
    trend?: "up" | "down" | "neutral";
}

export default function MetricCard({ label, value, subValue, icon: Icon, trend }: MetricCardProps) {
    return (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-all">
            <div className="flex justify-between items-start mb-2">
                <span className="text-gray-400 text-xs font-medium uppercase tracking-wider">{label}</span>
                <Icon size={16} className="text-gray-500" />
            </div>
            <div className="text-2xl font-bold text-white">{value}</div>
            {subValue && (
                <div className={`text-xs mt-1 ${trend === "up" ? "text-green-400" : trend === "down" ? "text-red-400" : "text-gray-500"}`}>
                    {subValue}
                </div>
            )}
        </div>
    );
}
