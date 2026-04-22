class PortfolioEngine:
    def __init__(self):
        self.capital = 10000.0
        self.risk_pct = 0.02
        self.min_confidence = 0.65

    def update_constraints(self, capital: float, risk_pct: float, min_confidence: float = 0.65):
        self.capital = capital
        self.risk_pct = risk_pct
        self.min_confidence = min_confidence

    async def optimize(self, opportunities: list):
        """
        Decide actual allocations.
        """
        decisions = []
        
        for opp in opportunities:
            confidence = float(opp.get("confidence", 0.0))
            expected_return = float(opp.get("expected_return", 0.0))
            risk_score = float(opp.get("risk_score", 0.5))
            if confidence >= self.min_confidence:
                # Risk-adjusted sizing:
                # high confidence + high expected edge => closer to risk cap.
                edge = max(expected_return - (risk_score * 0.01), 0.0)
                confidence_scale = 0.5 + (confidence / 2.0)
                edge_scale = 1.0 + min(edge * 30.0, 1.0)
                allocation_pct = min(self.risk_pct * confidence_scale * edge_scale, self.risk_pct)
                allocation_amount = round(self.capital * allocation_pct, 2)

                if allocation_amount <= 0:
                    continue

                decisions.append({
                    "action": "EXECUTE",
                    "symbol": opp["symbol"],
                    "direction": opp["direction"],
                    "amount": allocation_amount,
                    "reason": f"{opp.get('strategy', 'Strategy')} | Conf {confidence:.2f}, Edge {edge:.4f}",
                    "confidence": confidence,
                })
            else:
                 decisions.append({
                    "action": "REJECT",
                    "symbol": opp["symbol"],
                    "reason": f"Low Confidence ({confidence:.2f} < {self.min_confidence:.2f})"
                })
                
        return decisions
