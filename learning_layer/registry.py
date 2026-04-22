from typing import Dict, Any

class ModelRegistry:
    """
    Central store for Model metadata and performance tracking.
    """
    def __init__(self):
        self._models: Dict[str, Dict[str, Any]] = {}

    def register_model(self, model_name: str, version: str, meta: Dict[str, Any]):
        self._models[model_name] = {
            "version": version,
            "status": "candidate",
            "score": 100.0, # Baseline score
            "meta": meta
        }
        print(f"[REGISTRY] Registered {model_name} v{version}")

    def update_score(self, model_name: str, delta: float):
        """Adjust model score based on performance feedback."""
        if model_name in self._models:
            self._models[model_name]["score"] += delta
            # Downgrade if score drops too low
            if self._models[model_name]["score"] < 50.0:
                 self._models[model_name]["status"] = "probation"
                 print(f"[REGISTRY] WARNING: {model_name} moved to PROBATION.")

    def get_model_status(self, model_name: str):
        return self._models.get(model_name)
