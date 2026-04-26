#!/usr/bin/env bash
set -euo pipefail

# Run this script on your GPU VM.
#
# Optional env:
#   BRANCH (default: codex/deep-crypto-colab-training)
#   GCS_BUCKET (optional, for artifact sync)
#   PYTHON_BIN (default: python3)
#
# Optional args:
#   Training args passed directly to tests/run_deep_crypto_policy_walkforward.py

BRANCH="${BRANCH:-codex/deep-crypto-colab-training}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
WORKDIR="${HOME}/vapar"
LOGDIR="${WORKDIR}/logs"

if [[ ! -d "${WORKDIR}/.git" ]]; then
  if [[ -e "${WORKDIR}" ]]; then
    BACKUP_DIR="${WORKDIR}.non_git.$(date -u +%Y%m%d_%H%M%S)"
    echo "Found non-Git workdir at ${WORKDIR}; moving it to ${BACKUP_DIR}"
    mv "${WORKDIR}" "${BACKUP_DIR}"
  fi
  git clone --depth 1 --branch "${BRANCH}" https://github.com/comprono/vapar.git "${WORKDIR}"
else
  git -C "${WORKDIR}" fetch --depth 1 origin "${BRANCH}"
  git -C "${WORKDIR}" checkout -B "${BRANCH}" "origin/${BRANCH}"
  git -C "${WORKDIR}" reset --hard "origin/${BRANCH}"
fi

cd "${WORKDIR}"
echo "Training repo HEAD: $(git rev-parse --short HEAD)"
echo "Training repo branch: $(git branch --show-current)"
LOGDIR="${WORKDIR}/logs"
mkdir -p "${LOGDIR}"
"${PYTHON_BIN}" -m pip install -q --upgrade pip
"${PYTHON_BIN}" -m pip install -q -r backend/requirements.txt

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "nvidia-smi not found; installing Google Compute Engine NVIDIA driver..."
  curl -fsSL https://storage.googleapis.com/compute-gpu-installation-us/installer/latest/cuda_installer.pyz -o /tmp/cuda_installer.pyz
  sudo "${PYTHON_BIN}" /tmp/cuda_installer.pyz install_driver
fi
nvidia-smi

if "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1
import torch
raise SystemExit(0 if torch.cuda.is_available() else 1)
PY
then
  :
else
  echo "Installing CUDA-enabled PyTorch wheel..."
  "${PYTHON_BIN}" -m pip install -q --upgrade torch --index-url https://download.pytorch.org/whl/cu128
fi

"${PYTHON_BIN}" - <<'PY'
import torch
print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
if torch.cuda.is_available():
    print("cuda_device", torch.cuda.get_device_name(0))
else:
    raise SystemExit("CUDA is still not available after driver/PyTorch setup.")
PY

TRAIN_ARGS=("$@")
if [[ "${#TRAIN_ARGS[@]}" -eq 0 ]]; then
  TRAIN_ARGS=(
    --years 5
    --window-size 128
    --train-lookback-days 1460
    --calibration-lookback-days 365
    --min-train-samples 2048
    --max-train-samples 30000
    --max-months 36
    --pretrain-epochs 25
    --epochs 35
    --batch-size 512
    --d-model 128
    --n-heads 8
    --n-layers 4
    --dropout 0.10
    --lr 0.0003
    --ranking-weight 1.0
    --initial-capital 10
  )
fi

STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOGFILE="${LOGDIR}/deep_policy_${STAMP}.log"
echo "Starting training. Log: ${LOGFILE}"
set -o pipefail
"${PYTHON_BIN}" -u tests/run_deep_crypto_policy_walkforward.py "${TRAIN_ARGS[@]}" | tee "${LOGFILE}"

LATEST_REPORT="$(ls -dt data/reports/deep_crypto_policy_* 2>/dev/null | head -n 1 || true)"
if [[ -n "${LATEST_REPORT}" ]]; then
  echo "Latest report: ${LATEST_REPORT}"
  if [[ -n "${GCS_BUCKET:-}" ]]; then
    RUN_ID="$(basename "${LATEST_REPORT}")"
    gcloud storage rsync -r "${LATEST_REPORT}" "gs://${GCS_BUCKET}/vm-runs/${RUN_ID}/"
    gcloud storage cp "${LOGFILE}" "gs://${GCS_BUCKET}/vm-runs/${RUN_ID}/deep_policy_train.log"
    echo "Synced to gs://${GCS_BUCKET}/vm-runs/${RUN_ID}/"
  fi
fi
