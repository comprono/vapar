#!/usr/bin/env bash
set -euo pipefail

# Required environment:
#   PROJECT_ID
#   REGION
#   GCS_BUCKET
#
# Optional environment:
#   BRANCH (default: codex/deep-crypto-colab-training)
#   DISPLAY_NAME_PREFIX (default: deep-policy)
#   MACHINE_TYPE (default: n1-standard-8)
#   ACCELERATOR_TYPE (default: NVIDIA_TESLA_T4)
#   ACCELERATOR_COUNT (default: 1)
#   CONTAINER_IMAGE (default: us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-4.py310:latest)
#   SERVICE_ACCOUNT (optional)

if [[ -z "${PROJECT_ID:-}" || -z "${REGION:-}" || -z "${GCS_BUCKET:-}" ]]; then
  echo "Missing required env vars. Set PROJECT_ID, REGION, and GCS_BUCKET." >&2
  exit 1
fi

BRANCH="${BRANCH:-codex/deep-crypto-colab-training}"
DISPLAY_NAME_PREFIX="${DISPLAY_NAME_PREFIX:-deep-policy}"
MACHINE_TYPE="${MACHINE_TYPE:-n1-standard-8}"
ACCELERATOR_TYPE="${ACCELERATOR_TYPE:-NVIDIA_TESLA_T4}"
ACCELERATOR_COUNT="${ACCELERATOR_COUNT:-1}"
CONTAINER_IMAGE="${CONTAINER_IMAGE:-us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-4.py310:latest}"
DISPLAY_NAME="${DISPLAY_NAME_PREFIX}-$(date -u +%Y%m%d-%H%M%S)"
OUTPUT_URI="gs://${GCS_BUCKET}/vertex-runs/${DISPLAY_NAME}"

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

TRAIN_ARGS_ESCAPED="$(printf ' %q' "${TRAIN_ARGS[@]}")"
TMP_CONFIG="$(mktemp "/tmp/vertex-deep-policy-XXXX.yaml")"
trap 'rm -f "$TMP_CONFIG"' EXIT

cat >"$TMP_CONFIG" <<YAML
workerPoolSpecs:
  - machineSpec:
      machineType: ${MACHINE_TYPE}
      acceleratorType: ${ACCELERATOR_TYPE}
      acceleratorCount: ${ACCELERATOR_COUNT}
    replicaCount: 1
    containerSpec:
      imageUri: ${CONTAINER_IMAGE}
      command:
        - bash
      args:
        - -lc
        - |
          set -euo pipefail
          export PYTHONUNBUFFERED=1
          python -V
          pip install -q --upgrade pip
          pip install -q pandas numpy scipy scikit-learn yfinance python-binance google-cloud-storage
          mkdir -p /workspace && cd /workspace
          git clone --depth 1 --branch ${BRANCH} https://github.com/comprono/vapar.git repo
          cd repo
          python -u tests/run_deep_crypto_policy_walkforward.py${TRAIN_ARGS_ESCAPED} | tee /tmp/deep_policy_train.log
          python - <<'PY'
          import os
          from pathlib import Path
          from google.cloud import storage

          output_uri = "${OUTPUT_URI}"
          if not output_uri.startswith("gs://"):
              raise SystemExit("Invalid OUTPUT_URI: " + output_uri)
          bucket_name, _, prefix = output_uri[5:].partition("/")
          prefix = prefix.strip("/")

          report_dirs = sorted(Path("data/reports").glob("deep_crypto_policy_*"), key=lambda p: p.stat().st_mtime)
          if not report_dirs:
              raise SystemExit("No deep_crypto_policy report directory found")
          latest = report_dirs[-1]

          client = storage.Client()
          bucket = client.bucket(bucket_name)

          artifact_prefix = f"{prefix}/artifacts/{latest.name}"
          for path in latest.rglob("*"):
              if path.is_file():
                  rel = path.relative_to(latest).as_posix()
                  blob = bucket.blob(f"{artifact_prefix}/{rel}")
                  blob.upload_from_filename(str(path))

          log_path = Path("/tmp/deep_policy_train.log")
          if log_path.exists():
              bucket.blob(f"{prefix}/logs/deep_policy_train.log").upload_from_filename(str(log_path))

          print("Uploaded artifacts to:", f"gs://{bucket_name}/{artifact_prefix}")
          PY
baseOutputDirectory:
  outputUriPrefix: ${OUTPUT_URI}/vertex-managed
YAML

CMD=(
  gcloud ai custom-jobs create
  "--project=${PROJECT_ID}"
  "--region=${REGION}"
  "--display-name=${DISPLAY_NAME}"
  "--config=${TMP_CONFIG}"
)

if [[ -n "${SERVICE_ACCOUNT:-}" ]]; then
  CMD+=("--service-account=${SERVICE_ACCOUNT}")
fi

echo "Submitting Vertex job: ${DISPLAY_NAME}"
echo "Output prefix: ${OUTPUT_URI}"
"${CMD[@]}"

