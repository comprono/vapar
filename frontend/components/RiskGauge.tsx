interface RiskGaugeProps {
    value: number; // 0 to 1
    label: string;
}

export default function RiskGauge({ value, label }: RiskGaugeProps) {
    const percentage = Math.min(Math.max(value, 0), 1) * 100;

    // Google Colors
    let color = "#8ab4f8";
    if (percentage > 75) color = "#f28b82"; // Red
    else if (percentage > 40) color = "#fdb66c"; // Orange
    else color = "#81c995"; // Green (Low Risk)

    return (
        <div className="relative flex flex-col items-center justify-center p-4">
            <svg width="120" height="120" viewBox="0 0 120 120">
                {/* Background Circle */}
                <circle
                    cx="60" cy="60" r="54"
                    fill="none"
                    stroke="#3c4043"
                    strokeWidth="8"
                />
                {/* Value Circle */}
                <circle
                    cx="60" cy="60" r="54"
                    fill="none"
                    stroke={color}
                    strokeWidth="8"
                    strokeDasharray="339.292"
                    strokeDashoffset={339.292 * (1 - value)}
                    transform="rotate(-90 60 60)"
                    strokeLinecap="round"
                    className="transition-all duration-1000 ease-in-out"
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-normal text-[#e8eaed]">
                    {percentage.toFixed(0)}%
                </span>
                <span className="text-[10px] uppercase tracking-wider text-[#9aa0a6] mt-1">Risk</span>
            </div>
            <span className="text-xs uppercase tracking-widest text-[#9aa0a6] mt-2">{label}</span>
        </div>
    );
}
