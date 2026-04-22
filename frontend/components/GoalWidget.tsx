interface GoalWidgetProps {
    title: string;
    current: number;
    target: number;
    progress: number;
}

export default function GoalWidget({ title, current, target, progress }: GoalWidgetProps) {
    const safeProgress = Math.min(Math.max(progress, 0), 100);

    return (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col justify-between">
            <div className="flex justify-between items-end mb-2">
                <span className="text-gray-400 text-xs font-medium uppercase">{title} GOAL</span>
                <span className="text-white text-sm font-bold">${current.toFixed(2)} <span className="text-gray-500">/ ${target}</span></span>
            </div>

            {/* Progress Bar Container */}
            <div className="h-2 w-full bg-gray-800 rounded-full overflow-hidden">
                <div
                    className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
                    style={{ width: `${safeProgress}%` }}
                />
            </div>
            <div className="text-right text-xs text-gray-500 mt-1">{safeProgress.toFixed(1)}% Completed</div>
        </div>
    );
}
