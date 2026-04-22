import json
import os
from datetime import datetime
from typing import Dict, List, Any

class ReportManager:
    """Manages saving and loading of backtest results."""
    
    def __init__(self, base_dir: str = "data/reports"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        
    def save_report(self, results: Dict[str, Any]) -> str:
        """Save backtest results to a JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy = results.get("strategy", "Unknown")
        filename = f"report_{strategy}_{timestamp}.json"
        filepath = os.path.join(self.base_dir, filename)
        
        # Add metadata
        results["report_id"] = filename
        results["generated_at"] = datetime.now().isoformat()
        
        with open(filepath, "w") as f:
            json.dump(results, f, indent=2, default=str)
            
        print(f"[ReportManager] Saved report: {filepath}")
        return filename
        
    def list_reports(self) -> List[Dict[str, str]]:
        """List all saved reports with basic metadata."""
        reports = []
        for filename in os.listdir(self.base_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.base_dir, filename)
                try:
                    stats = os.stat(filepath)
                    reports.append({
                        "id": filename,
                        "strategy": filename.split("_")[1],
                        "date": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        "size_kb": round(stats.st_size / 1024, 2)
                    })
                except Exception:
                    continue
        return sorted(reports, key=lambda x: x["date"], reverse=True)
        
    def get_report(self, report_id: str) -> Dict[str, Any]:
        """Load a specific report by ID."""
        filepath = os.path.join(self.base_dir, report_id)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Report {report_id} not found")
            
        with open(filepath, "r") as f:
            return json.load(f)

report_manager = ReportManager()
