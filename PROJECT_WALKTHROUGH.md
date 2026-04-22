# System Walkthrough: Unified Multi-Market Autonomous Trading System

## Architecture Overview
The system is built on a 4-layer architecture designed for safety, probability-based decision making, and autonomous learning.

### 1. Data Layer (`data_layer/`)
*   **Purpose**: Ingest and normalize market data.
*   **Components**:
    *   `schemas/market_data.py`: Strictly typed `Quote` and `Trade` models.
    *   `ingestors/`: `MockIngestor` (Verification), placeholders for Equity/Crypto.
    *   `storage/`: `FileStorage` for local persistence.
*   **Verification**: `tests/test_data_layer.py` confirmed data flow and normalization.

### 2. Research Layer (`research_layer/`)
*   **Purpose**: Generate probabilistic predictions and allocate capital.
*   **Components**:
    *   `models/base.py`: Enforces `Prediction` output with `expected_return` and `uncertainty`.
    *   `allocator.py`: `PortfolioAllocator` optimizes weights based on risk-adjusted returns.
    *   `backtest.py`: Replay engine for historical simulation.
*   **Verification**: `tests/test_research_layer.py` confirmed model-to-allocation logic.

### 3. Decision Layer (`decision_layer/`)
*   **Purpose**: Execute trades with strict safety checks.
*   **Components**:
    *   `bus.py`: `SignalBus` decouples research from execution.
    *   `risk.py`: `RiskCommittee` acts as a hard gatekeeper (Max Size, Min Confidence).
    *   `execution.py`: Routes orders to exchanges.
*   **Verification**: `tests/test_decision_layer.py` confirmed rejected risky trades and accepted valid ones.

### 4. Learning Layer (`learning_layer/`)
*   **Purpose**: Close the loop and adapt.
*   **Components**:
    *   `performance.py`: Calculates accuracy and realized PnL.
    *   `registry.py`: Tracks model scores and statuses (Candidate, Active, Probation).
    *   `loop.py`: Feeds PnL back to the registry to update model scores.
*   **Verification**: `tests/test_learning_layer.py` confirmed automatic model probation after losses.

## How to Run
To run the verification suite:

```bash
# Set PYTHONPATH
$env:PYTHONPATH="C:\Users\paras\Documents\TB 1AG"

# Run Tests
python tests/test_data_layer.py
python tests/test_research_layer.py
python tests/test_decision_layer.py
python tests/test_learning_layer.py

# Run Full Simulation
python tests/simulation_full_system.py
```

## Next Steps for Production
1.  **API Keys**: Add `config.py` handling for exchange keys.
2.  **Real Ingestors**: Replace `MockIngestor` with specific API implementations.
3.  **Database**: Swap `FileStorage` for `TimescaleDB`.
4.  **Models**: Train real PyTorch/Sci-Kit Learn models and wrap them in `research_layer/models`.
