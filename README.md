# Autonomous Trading System (AG_CORE_V1)

## Setup & Run

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Install Dependencies
```bash
# Backend
pip install -r backend/requirements.txt

# Frontend
cd frontend
npm install
```

### 2. Run System
**Backend** (Trading Core):
```bash
python -m uvicorn backend.main:app --reload
```

**Frontend** (System Console):
```bash
cd frontend
npm run dev
```

### 3. Monitor
Access the **System Console** at [http://localhost:3000](http://localhost:3000).
- Click **INITIALIZE** to start the engine.
- View real-time decision logs in the terminal window.
- Check "Component Status" for health.

## 7Y Crypto AutoResearch Run

Run BTC-trained 7-year daily model research and evaluate on ETH + 10 other crypto pairs:

```bash
$env:PYTHONPATH="C:\Users\paras\Documents\antigravity files\TB 1AG"
python tests/run_crypto_autoresearch_7y.py
```

Outputs:
- JSON report: `data/reports/crypto_autoresearch_7y_*.json`
- CSV report: `data/reports/crypto_autoresearch_7y_*.csv`
- Daily verification folder: `data/reports/verification_*/`

The verification output includes:
- `model_position` vs `oracle_position` for every day
- daily return gap (`oracle_return - model_return`)
- monthly/yearly return breakdown in the JSON report

Anti-cheat rule in pipeline:
- Oracle (best-possible path) is computed only for verification and gap scoring
- Oracle labels are never used as training targets
