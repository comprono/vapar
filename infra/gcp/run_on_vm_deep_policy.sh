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
mkdir -p "${LOGDIR}"

if [[ ! -d "${WORKDIR}/.git" ]]; then
  git clone --depth 1 --branch "${BRANCH}" https://github.com/comprono/vapar.git "${WORKDIR}"
else
  git -C "${WORKDIR}" fetch origin
  git -C "${WORKDIR}" checkout "${BRANCH}"
  git -C "${WORKDIR}" pull --ff-only origin "${BRANCH}"
fi

cd "${WORKDIR}"
"${PYTHON_BIN}" -m pip install -q --upgrade pip
"${PYTHON_BIN}" -m pip install -q -r backend/requirements.txt

if "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1
import torch
print(torch.cuda.is_available())
PY
then
  :
else
  "${PYTHON_BIN}" -m pip install -q torch --index-url https://download.pytorch.org/whl/cu128
fi

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

