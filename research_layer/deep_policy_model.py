from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader


@dataclass
class DeepPolicyConfig:
    input_dim: int
    window_size: int = 96
    d_model: int = 64
    n_heads: int = 4
    n_layers: int = 2
    dropout: float = 0.10
    lr: float = 3e-4
    weight_decay: float = 1e-4
    batch_size: int = 128
    pretrain_epochs: int = 0
    epochs: int = 8
    grad_clip: float = 1.0
    ranking_weight: float = 0.65


class DeepCryptoPolicy(nn.Module):
    def __init__(self, config: DeepPolicyConfig) -> None:
        super().__init__()
        self.config = config
        self.input_projection = nn.Linear(config.input_dim, config.d_model)
        self.position_embedding = nn.Parameter(torch.zeros(1, config.window_size, config.d_model))
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.d_model,
            nhead=config.n_heads,
            dim_feedforward=config.d_model * 4,
            dropout=config.dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=config.n_layers)
        self.norm = nn.LayerNorm(config.d_model)
        self.action_head = nn.Linear(config.d_model, 3)
        self.edge_head = nn.Linear(config.d_model, 1)
        self.size_head = nn.Linear(config.d_model, 1)
        self.switch_cost_head = nn.Linear(config.d_model, 1)
        self.return_mu_head = nn.Linear(config.d_model, 1)
        self.return_scale_head = nn.Linear(config.d_model, 1)
        self.vol_head = nn.Linear(config.d_model, 1)
        self.regime_head = nn.Linear(config.d_model, 3)

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        z = self.input_projection(x)
        z = z + self.position_embedding[:, : z.shape[1], :]
        z = self.encoder(z)
        pooled = self.norm(z[:, -1, :])
        action_logits = self.action_head(pooled)
        edge = F.softplus(self.edge_head(pooled)).squeeze(-1)
        size = torch.sigmoid(self.size_head(pooled)).squeeze(-1)
        switch_cost = F.softplus(self.switch_cost_head(pooled)).squeeze(-1)
        return_mu = self.return_mu_head(pooled).squeeze(-1)
        return_scale = F.softplus(self.return_scale_head(pooled)).squeeze(-1) + 1e-4
        volatility = F.softplus(self.vol_head(pooled)).squeeze(-1)
        regime_logits = self.regime_head(pooled)
        probs = F.softmax(action_logits, dim=-1)
        forecast_edge = 0.50 * torch.abs(return_mu) + 0.50 * torch.clamp(edge - switch_cost, min=0.0)
        score = (probs[:, 2] - probs[:, 0]) * forecast_edge * size
        return {
            "action_logits": action_logits,
            "edge": edge,
            "size": size,
            "switch_cost": switch_cost,
            "return_mu": return_mu,
            "return_scale": return_scale,
            "volatility": volatility,
            "regime_logits": regime_logits,
            "score": score,
        }


def pretrain_loss(outputs: Dict[str, torch.Tensor], batch: Dict[str, torch.Tensor]) -> torch.Tensor:
    target = batch["target_return"]
    scale = torch.clamp(outputs["return_scale"], min=1e-4, max=1.0)
    gaussian_nll = 0.5 * (((target - outputs["return_mu"]) / scale) ** 2) + torch.log(scale)
    vol_loss = F.smooth_l1_loss(outputs["volatility"], batch["future_vol"], reduction="none")
    regime_loss = F.cross_entropy(outputs["regime_logits"], batch["regime"], reduction="none")
    weight = torch.clamp(batch["sample_weight"], min=1.0, max=8.0)
    total = gaussian_nll + 0.70 * vol_loss + 0.55 * regime_loss
    return torch.mean(total * weight)


def ranking_loss(outputs: Dict[str, torch.Tensor], batch: Dict[str, torch.Tensor]) -> torch.Tensor:
    scores = outputs["score"]
    selected = batch["is_selected"] > 0.5
    date_ids = batch["date_id"]
    losses = []
    for date_id in torch.unique(date_ids):
        mask = date_ids == date_id
        if int(mask.sum().detach().cpu()) < 2:
            continue
        day_scores = scores[mask]
        day_selected = selected[mask]
        if not bool(day_selected.any()) or bool(day_selected.all()):
            continue
        pos_score = day_scores[day_selected].max()
        neg_scores = day_scores[~day_selected]
        losses.append(F.softplus(0.0025 - (pos_score - neg_scores)).mean())
    if not losses:
        return torch.zeros((), dtype=scores.dtype, device=scores.device)
    return torch.stack(losses).mean()


def policy_loss(outputs: Dict[str, torch.Tensor], batch: Dict[str, torch.Tensor], ranking_weight: float = 0.65) -> torch.Tensor:
    weight = torch.clamp(batch["sample_weight"], min=1.0, max=20.0)
    action_loss = F.cross_entropy(outputs["action_logits"], batch["action"], reduction="none")
    edge_loss = F.smooth_l1_loss(outputs["edge"], batch["edge"], reduction="none")
    size_loss = F.binary_cross_entropy(outputs["size"], batch["size"], reduction="none")
    switch_loss = F.smooth_l1_loss(outputs["switch_cost"], batch["switch_cost"], reduction="none")

    direction = torch.where(batch["action"] == 2, 1.0, torch.where(batch["action"] == 0, -1.0, 0.0))
    signed_score = outputs["score"]
    margin_loss = F.relu(0.0025 - direction * signed_score)
    margin_loss = torch.where(direction.abs() > 0.0, margin_loss, signed_score.abs())

    next_return = batch["target_return"]
    differentiable_position = torch.tanh(signed_score * 80.0)
    net_return = differentiable_position * next_return - outputs["switch_cost"].detach() * differentiable_position.abs()
    pnl_loss = -torch.log(torch.clamp(1.0 + net_return, min=1e-4))
    rank_loss = ranking_loss(outputs, batch)

    total = (
        1.15 * action_loss
        + 0.75 * edge_loss
        + 0.35 * size_loss
        + 0.25 * switch_loss
        + 0.55 * margin_loss
        + 0.35 * pnl_loss
    )
    return torch.mean(total * weight) + float(ranking_weight) * rank_loss


def train_policy(
    model: DeepCryptoPolicy,
    dataset: torch.utils.data.Dataset,
    config: DeepPolicyConfig,
    device: torch.device,
    progress_prefix: str = "",
) -> Dict[str, Any]:
    loader = DataLoader(dataset, batch_size=config.batch_size, shuffle=True, drop_last=False)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.lr, weight_decay=config.weight_decay)
    model.to(device)
    history = []
    for epoch in range(int(config.epochs)):
        model.train()
        running_loss = 0.0
        seen = 0
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            outputs = model(batch["x"])
            loss = policy_loss(outputs, batch, ranking_weight=config.ranking_weight)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), config.grad_clip)
            optimizer.step()
            running_loss += float(loss.detach().cpu()) * int(batch["x"].shape[0])
            seen += int(batch["x"].shape[0])
        epoch_loss = running_loss / max(seen, 1)
        history.append({"epoch": epoch + 1, "loss": epoch_loss, "samples": seen})
        prefix = f"{progress_prefix} " if progress_prefix else ""
        print(f"[deep-policy] {prefix}epoch {epoch + 1}/{int(config.epochs)} loss={epoch_loss:.6f} samples={seen}", flush=True)
    return {"history": history, "final_loss": float(history[-1]["loss"]) if history else 0.0}


def pretrain_policy(
    model: DeepCryptoPolicy,
    dataset: torch.utils.data.Dataset,
    config: DeepPolicyConfig,
    device: torch.device,
    progress_prefix: str = "",
) -> Dict[str, Any]:
    loader = DataLoader(dataset, batch_size=config.batch_size, shuffle=True, drop_last=False)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.lr, weight_decay=config.weight_decay)
    model.to(device)
    history = []
    for epoch in range(int(config.pretrain_epochs)):
        model.train()
        running_loss = 0.0
        seen = 0
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            outputs = model(batch["x"])
            loss = pretrain_loss(outputs, batch)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), config.grad_clip)
            optimizer.step()
            running_loss += float(loss.detach().cpu()) * int(batch["x"].shape[0])
            seen += int(batch["x"].shape[0])
        epoch_loss = running_loss / max(seen, 1)
        history.append({"epoch": epoch + 1, "loss": epoch_loss, "samples": seen})
        prefix = f"{progress_prefix} " if progress_prefix else ""
        print(f"[deep-policy] {prefix}pretrain {epoch + 1}/{int(config.pretrain_epochs)} loss={epoch_loss:.6f} samples={seen}", flush=True)
    return {"history": history, "final_loss": float(history[-1]["loss"]) if history else 0.0}


@torch.no_grad()
def predict_scores(
    model: DeepCryptoPolicy,
    x: torch.Tensor,
    device: torch.device,
    batch_size: int = 512,
) -> Dict[str, torch.Tensor]:
    model.eval()
    scores = []
    actions = []
    edges = []
    sizes = []
    costs = []
    for start in range(0, int(x.shape[0]), int(batch_size)):
        part = x[start : start + batch_size].to(device)
        out = model(part)
        scores.append(out["score"].detach().cpu())
        actions.append(F.softmax(out["action_logits"], dim=-1).detach().cpu())
        edges.append(out["edge"].detach().cpu())
        sizes.append(out["size"].detach().cpu())
        costs.append(out["switch_cost"].detach().cpu())
    return {
        "score": torch.cat(scores) if scores else torch.empty(0),
        "action_probs": torch.cat(actions) if actions else torch.empty(0, 3),
        "edge": torch.cat(edges) if edges else torch.empty(0),
        "size": torch.cat(sizes) if sizes else torch.empty(0),
        "switch_cost": torch.cat(costs) if costs else torch.empty(0),
    }


def save_checkpoint(
    path: str | Path,
    model: DeepCryptoPolicy,
    config: DeepPolicyConfig,
    metadata: Dict[str, Any],
) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "config": asdict(config),
            "metadata": metadata,
        },
        str(path),
    )
