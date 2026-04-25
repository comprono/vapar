from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from backend.backtest.data_loader import DataLoader
from research_layer import crypto_autoresearch as ca


@dataclass
class SequenceDatasetConfig:
    window_size: int = 96
    train_lookback_days: int = 730
    calibration_lookback_days: int = 365
    min_train_samples: int = 512
    max_samples: int | None = None


class CryptoSequenceDataset(Dataset):
    def __init__(
        self,
        x: np.ndarray,
        action: np.ndarray,
        edge: np.ndarray,
        size: np.ndarray,
        switch_cost: np.ndarray,
        target_return: np.ndarray,
        future_vol: np.ndarray,
        regime: np.ndarray,
        is_selected: np.ndarray,
        date_id: np.ndarray,
        sample_weight: np.ndarray,
    ) -> None:
        self.x = torch.tensor(x, dtype=torch.float32)
        self.action = torch.tensor(action, dtype=torch.long)
        self.edge = torch.tensor(edge, dtype=torch.float32)
        self.size = torch.tensor(size, dtype=torch.float32)
        self.switch_cost = torch.tensor(switch_cost, dtype=torch.float32)
        self.target_return = torch.tensor(target_return, dtype=torch.float32)
        self.future_vol = torch.tensor(future_vol, dtype=torch.float32)
        self.regime = torch.tensor(regime, dtype=torch.long)
        self.is_selected = torch.tensor(is_selected, dtype=torch.float32)
        self.date_id = torch.tensor(date_id, dtype=torch.long)
        self.sample_weight = torch.tensor(sample_weight, dtype=torch.float32)

    def __len__(self) -> int:
        return int(self.x.shape[0])

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        return {
            "x": self.x[idx],
            "action": self.action[idx],
            "edge": self.edge[idx],
            "size": self.size[idx],
            "switch_cost": self.switch_cost[idx],
            "target_return": self.target_return[idx],
            "future_vol": self.future_vol[idx],
            "regime": self.regime[idx],
            "is_selected": self.is_selected[idx],
            "date_id": self.date_id[idx],
            "sample_weight": self.sample_weight[idx],
        }


def load_crypto_feature_frames(
    symbols: List[str],
    years: int,
    cache_dir: str = "data/cache",
) -> Tuple[Dict[str, pd.DataFrame], List[str]]:
    end_date = (date.today() + timedelta(days=1)).isoformat()
    start_date = (date.today() - timedelta(days=int(years * 365))).isoformat()
    loader = DataLoader(cache_dir=cache_dir)
    raw = loader.load_multiple(symbols=symbols, start_date=start_date, end_date=end_date, interval="1d")

    prepared: Dict[str, pd.DataFrame] = {}
    feature_cols: List[str] = []
    for symbol in symbols:
        if symbol not in raw:
            continue
        frame, cols = ca._prepare_feature_frame(raw[symbol])
        if len(frame) < max(140, min(365, years * 120)):
            continue
        prepared[symbol] = frame
        if not feature_cols:
            feature_cols = cols

    feature_cols = ca._add_cross_sectional_features(prepared, feature_cols)
    ca._add_oracle_action_labels(prepared, list(prepared), ca.TRADE_COST_RATE)
    return prepared, feature_cols


def month_starts(prepared: Dict[str, pd.DataFrame], ref_symbol: str = "BTC-USD") -> List[pd.Timestamp]:
    if ref_symbol not in prepared:
        ref_symbol = next(iter(prepared))
    return ca._iter_month_starts(prepared[ref_symbol].index)


def fit_feature_normalizer(
    prepared: Dict[str, pd.DataFrame],
    symbols: Iterable[str],
    feature_cols: List[str],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> Tuple[np.ndarray, np.ndarray]:
    chunks = []
    for symbol in symbols:
        if symbol not in prepared:
            continue
        frame = prepared[symbol]
        part = frame[(frame.index >= start) & (frame.index < end)]
        if not part.empty:
            chunks.append(part[feature_cols].to_numpy(dtype=np.float32))
    if not chunks:
        mean = np.zeros(len(feature_cols), dtype=np.float32)
        std = np.ones(len(feature_cols), dtype=np.float32)
        return mean, std
    values = np.concatenate(chunks, axis=0)
    mean = np.nanmean(values, axis=0).astype(np.float32)
    std = np.nanstd(values, axis=0).astype(np.float32)
    std = np.where(std < 1e-6, 1.0, std).astype(np.float32)
    return mean, std


def build_sequence_arrays(
    prepared: Dict[str, pd.DataFrame],
    symbols: Iterable[str],
    feature_cols: List[str],
    start: pd.Timestamp,
    end: pd.Timestamp,
    config: SequenceDatasetConfig,
    mean: np.ndarray,
    std: np.ndarray,
) -> Tuple[Dict[str, np.ndarray], List[Dict[str, Any]]]:
    xs: List[np.ndarray] = []
    actions: List[int] = []
    edges: List[float] = []
    sizes: List[float] = []
    switch_costs: List[float] = []
    target_returns: List[float] = []
    future_vols: List[float] = []
    regimes: List[int] = []
    selected_flags: List[float] = []
    date_ids: List[int] = []
    weights: List[float] = []
    meta: List[Dict[str, Any]] = []

    for symbol in symbols:
        if symbol not in prepared:
            continue
        frame = prepared[symbol].sort_index()
        values = frame[feature_cols].to_numpy(dtype=np.float32)
        values = (values - mean.reshape(1, -1)) / std.reshape(1, -1)
        local_dates = frame.index
        targets = frame["target"].to_numpy(dtype=np.float32)
        trailing_vol = pd.Series(targets, index=frame.index).rolling(20, min_periods=5).std().fillna(0.0).to_numpy(dtype=np.float32)
        mask_positions = np.where((local_dates >= start) & (local_dates < end))[0]
        for pos in mask_positions:
            left = pos - config.window_size + 1
            if left < 0:
                continue
            row = frame.iloc[pos]
            if pd.isna(row.get("target")):
                continue
            window = values[left : pos + 1]
            if not np.isfinite(window).all():
                continue
            action = int(row.get("oracle_action_label", 1))
            edge = float(row.get("oracle_gross_edge", 0.0))
            size = float(row.get("oracle_position_size", 0.0))
            switch_cost = float(row.get("oracle_switching_cost", 0.0))
            is_selected = float(bool(row.get("oracle_is_selected", False)))
            horizon_targets = targets[pos : min(pos + 5, len(targets))]
            future_vol = float(np.nanstd(horizon_targets)) if len(horizon_targets) > 1 else abs(float(row["target"]))
            vol_ref = max(float(trailing_vol[pos]), 1e-6)
            abs_target = abs(float(row["target"]))
            if abs_target < 0.50 * vol_ref:
                regime = 0
            elif float(row["target"]) > 0.0:
                regime = 2
            else:
                regime = 1
            sample_weight = 1.0 + 4.0 * is_selected + 8.0 * max(edge, 0.0)

            xs.append(window.astype(np.float32))
            actions.append(action)
            edges.append(max(edge, 0.0))
            sizes.append(np.clip(size, 0.0, 1.0))
            switch_costs.append(max(switch_cost, 0.0))
            target_returns.append(float(row["target"]))
            future_vols.append(max(future_vol, 0.0))
            regimes.append(int(regime))
            selected_flags.append(is_selected)
            date_ids.append(int(pd.Timestamp(local_dates[pos]).strftime("%Y%m%d")))
            weights.append(float(sample_weight))
            meta.append({"symbol": symbol, "date": pd.Timestamp(local_dates[pos])})

    if config.max_samples and len(xs) > config.max_samples:
        rng = np.random.default_rng(42)
        idx = np.sort(rng.choice(len(xs), size=int(config.max_samples), replace=False))
        xs = [xs[i] for i in idx]
        actions = [actions[i] for i in idx]
        edges = [edges[i] for i in idx]
        sizes = [sizes[i] for i in idx]
        switch_costs = [switch_costs[i] for i in idx]
        target_returns = [target_returns[i] for i in idx]
        future_vols = [future_vols[i] for i in idx]
        regimes = [regimes[i] for i in idx]
        selected_flags = [selected_flags[i] for i in idx]
        date_ids = [date_ids[i] for i in idx]
        weights = [weights[i] for i in idx]
        meta = [meta[i] for i in idx]

    arrays = {
        "x": np.asarray(xs, dtype=np.float32),
        "action": np.asarray(actions, dtype=np.int64),
        "edge": np.asarray(edges, dtype=np.float32),
        "size": np.asarray(sizes, dtype=np.float32),
        "switch_cost": np.asarray(switch_costs, dtype=np.float32),
        "target_return": np.asarray(target_returns, dtype=np.float32),
        "future_vol": np.asarray(future_vols, dtype=np.float32),
        "regime": np.asarray(regimes, dtype=np.int64),
        "is_selected": np.asarray(selected_flags, dtype=np.float32),
        "date_id": np.asarray(date_ids, dtype=np.int64),
        "sample_weight": np.asarray(weights, dtype=np.float32),
    }
    return arrays, meta


def make_dataset(arrays: Dict[str, np.ndarray]) -> CryptoSequenceDataset:
    return CryptoSequenceDataset(
        x=arrays["x"],
        action=arrays["action"],
        edge=arrays["edge"],
        size=arrays["size"],
        switch_cost=arrays["switch_cost"],
        target_return=arrays["target_return"],
        future_vol=arrays["future_vol"],
        regime=arrays["regime"],
        is_selected=arrays["is_selected"],
        date_id=arrays["date_id"],
        sample_weight=arrays["sample_weight"],
    )
