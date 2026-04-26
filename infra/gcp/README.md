# GCP Permanent Training Runbook

This project now has two durable Google Cloud paths for deep-policy training:

1. `Vertex AI CustomJob` (recommended): managed job lifecycle, no notebook limits.
2. `Persistent GPU VM` (fallback): long-running host under your control.

## 1) Vertex AI (recommended)

Use [submit_vertex_deep_policy_job.sh](/C:/Users/paras/Documents/antigravity%20files/TB%201AG/infra/gcp/submit_vertex_deep_policy_job.sh).

Prerequisites:
- `gcloud` installed and authenticated (`gcloud auth login` and `gcloud auth application-default login`)
- Vertex AI API enabled
- Billing enabled
- A Cloud Storage bucket for artifacts
- Sufficient GPU quota in your target region/zone

Minimal usage:

```bash
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export GCS_BUCKET="your-training-bucket"
export BRANCH="codex/deep-crypto-colab-training"

bash infra/gcp/submit_vertex_deep_policy_job.sh
```

Windows PowerShell usage:

```powershell
$env:PROJECT_ID="your-project-id"
$env:REGION="us-central1"
$env:GCS_BUCKET="your-training-bucket"
$env:BRANCH="codex/deep-crypto-colab-training"

powershell -ExecutionPolicy Bypass -File infra/gcp/submit_vertex_deep_policy_job.ps1
```

Windows executable launchers (repo root):
- [RUN_VERTEX_PREFLIGHT.cmd](</C:/Users/paras/Documents/antigravity files/TB 1AG/RUN_VERTEX_PREFLIGHT.cmd>)
- [RUN_VERTEX_TRAIN.cmd](</C:/Users/paras/Documents/antigravity files/TB 1AG/RUN_VERTEX_TRAIN.cmd>)
- [SHOW_VERTEX_PROGRESS.cmd](</C:/Users/paras/Documents/antigravity files/TB 1AG/SHOW_VERTEX_PROGRESS.cmd>)

Custom training args:

```bash
bash infra/gcp/submit_vertex_deep_policy_job.sh -- \
  --years 5 \
  --window-size 128 \
  --train-lookback-days 1460 \
  --calibration-lookback-days 365 \
  --min-train-samples 2048 \
  --max-train-samples 30000 \
  --max-months 36 \
  --pretrain-epochs 25 \
  --epochs 35 \
  --batch-size 512 \
  --d-model 128 \
  --n-heads 8 \
  --n-layers 4 \
  --dropout 0.10 \
  --lr 0.0003 \
  --ranking-weight 1.0 \
  --initial-capital 10
```

What this launcher does:
- Starts a Vertex `CustomJob` on GPU.
- Clones this repo branch inside the training container.
- Runs `tests/run_deep_crypto_policy_walkforward.py`.
- Uploads latest report/checkpoints to `gs://$GCS_BUCKET/vertex-runs/<job>/artifacts/...`.

Preflight validation (recommended before first run):

```powershell
powershell -ExecutionPolicy Bypass -File infra/gcp/vertex_preflight.ps1 `
  -ProjectId your-project-id `
  -Region us-central1 `
  -Bucket your-training-bucket
```

## 2) Persistent GPU VM

Use [create_persistent_gpu_vm.sh](/C:/Users/paras/Documents/antigravity%20files/TB%201AG/infra/gcp/create_persistent_gpu_vm.sh) to create a durable training host.

```bash
export PROJECT_ID="your-project-id"
export ZONE="us-central1-a"
export INSTANCE_NAME="deep-policy-trainer-01"
bash infra/gcp/create_persistent_gpu_vm.sh
```

Then SSH in and run [run_on_vm_deep_policy.sh](/C:/Users/paras/Documents/antigravity%20files/TB%201AG/infra/gcp/run_on_vm_deep_policy.sh):

```bash
gcloud compute ssh "$INSTANCE_NAME" --zone "$ZONE"

export BRANCH="codex/deep-crypto-colab-training"
export GCS_BUCKET="your-training-bucket"
bash infra/gcp/run_on_vm_deep_policy.sh
```

This VM path is useful if you want:
- one long-lived machine,
- persistent local cache,
- lower operational friction for iterative experimentation.

## Quota and cost guidance

- Use `STANDARD` provisioning for reliability.
- Use `SPOT` only if preemption is acceptable.
- Prefer `Vertex AI` for production runs and repeatability.
- Keep checkpoints/report uploads in GCS so restarts are recoverable.

## Sync checks

GitHub branch head:

```bash
git rev-parse --short HEAD
git ls-remote origin codex/deep-crypto-colab-training
```

Colab source of truth:
- If the notebook URL starts with `https://colab.research.google.com/github/...`, it is GitHub-backed.
- `Copy to Drive` means it is not yet a Drive-owned copy.
