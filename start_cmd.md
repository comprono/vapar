# How to Start the Antigravity Trading System

Follow these commands in two separate terminal windows:

### 1. Start the Backend API (Python/FastAPI)
```powershell
python -m uvicorn backend.main:app --reload
```
*The backend will be available at: http://127.0.0.1:8000*

### 2. Start the Frontend Dashboard (Next.js/React)
```powershell
cd frontend
npm run dev
```
*The dashboard will be available at: http://localhost:3000/backtest*

---
**Note:** Ensure you have installed the dependencies first:
- Backend: `pip install -r requirements.txt` (if exists) or `pip install fastapi uvicorn yfinance pandas pydantic-settings`
- Frontend: `cd frontend && npm install`
