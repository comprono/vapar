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
- `model_action`, expected next-day edge, position size, and switching cost columns
- daily return gap (`oracle_return - model_return`)
- monthly/yearly return breakdown in the JSON report

Walk-forward rule in pipeline:
- Training uses oracle action labels only from historical training windows
- Final evaluation oracle paths are computed after walk-forward scoring for verification and gap scoring

## Local Short-Horizon AutoLoop (1-2 years, Top-10 Crypto)

Run local-only iterative training/evaluation with daily verification and compounded equity columns:

```bash
$env:PYTHONPATH="C:\Users\paras\Documents\antigravity files\TB 1AG"
python tests/run_crypto_local_autoloop.py --years 1 --iterations 4 --month-stride 1 --initial-capital 1000
```

Windows executable wrapper:

```bash
run_local_crypto_autoloop.bat --years 1 --iterations 4 --month-stride 1 --initial-capital 1000
```

Artifacts:
- Loop summary CSV/JSON: `data/reports/local_crypto_autoloop_*/`
- Per-run report JSON/CSV: `data/reports/crypto_autoresearch_*y_*.json|csv`
- Per-coin daily verification CSV (includes compounded equity): `data/reports/verification_*/`
