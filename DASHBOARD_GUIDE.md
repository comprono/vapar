# Dashboard Setup Guide

You now have a modern Real-time Dashboard code in `frontend/`.
To run it, you need to set up the environment.

## 1. Install Node.js (Required for UI)
Since `node` was missing, you must install it to run the dashboard.
*   **Download:** [nodejs.org](https://nodejs.org/en/download/) (Select "LTS" version).
*   **Install**: Run the installer and click Next -> Next...

## 2. Start the Backend (API)
The UI needs data. Start the Python API first.

**Open Terminal 1:**
```powershell
$env:PYTHONPATH = "C:\Users\paras\Documents\TB 1AG"
python -m uvicorn backend.main:app --reload
```
*You should see: `Uvicorn running on http://127.0.0.1:8000`*

## 3. Start the Frontend (UI)
Once Node is installed:

**Open Terminal 2:**
```powershell
cd frontend
npm install
npm run dev
```
*   `npm install`: Downloads the libraries (React, Tailwind, etc.) I defined in `package.json`.
*   `npm run dev`: Starts the UI server.

## 4. Open Dashboard
Go to: **http://localhost:3000** in your browser.
Click **"INITIALIZE SYSTEM"** to start the autonomous trading loop!
