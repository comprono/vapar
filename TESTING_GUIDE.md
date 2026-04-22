# Testing Guide: Unified Autonomous System

This guide will help you run the verification scripts for the trading system.

## 1. Prerequisites
Ensure you are in the project root directory:
`c:\Users\paras\Documents\TB 1AG`

## 2. Environment Setup (Critical)
You must set the `PYTHONPATH` so Python can find the project modules.

**In PowerShell:**
```powershell
$env:PYTHONPATH = "C:\Users\paras\Documents\TB 1AG"
```

## 3. Running the "Master" Simulation
This script runs the entire system (Data -> AI -> Decision -> Learning) in a loop.

```powershell
python tests/simulation_full_system.py
```

## 4. Running Individual Layer Tests
If you want to verify specific components:

**Data Layer** (Ingestion & Storage):
```powershell
python tests/test_data_layer.py
```

**Research Layer** (Models & Allocator):
```powershell
python tests/test_research_layer.py
```

**Decision Layer** (Risk & Execution):
```powershell
python tests/test_decision_layer.py
```

**Learning Layer** (Feedback Loop):
```powershell
python tests/test_learning_layer.py
```

## 5. View Results
*   **Logs**: Check the terminal output.
*   **Data**: Check the `test_data_store/` and `sim_data/` folders for saved JSON files.
