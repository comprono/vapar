#!/usr/bin/env bash
set -euo pipefail

# Required env:
#   PROJECT_ID
#   ZONE
#   INSTANCE_NAME
#
# Optional env:
#   MACHINE_TYPE (default: n1-standard-8)
#   GPU_TYPE (default: nvidia-tesla-t4)
#   GPU_COUNT (default: 1)
#   BOOT_DISK_GB (default: 200)
#   PROVISIONING_MODEL (default: STANDARD; set SPOT for cheaper preemptible)
#   SERVICE_ACCOUNT (optional)

if [[ -z "${PROJECT_ID:-}" || -z "${ZONE:-}" || -z "${INSTANCE_NAME:-}" ]]; then
  echo "Missing required env vars. Set PROJECT_ID, ZONE, INSTANCE_NAME." >&2
  exit 1
fi

MACHINE_TYPE="${MACHINE_TYPE:-n1-standard-8}"
GPU_TYPE="${GPU_TYPE:-nvidia-tesla-t4}"
GPU_COUNT="${GPU_COUNT:-1}"
BOOT_DISK_GB="${BOOT_DISK_GB:-200}"
PROVISIONING_MODEL="${PROVISIONING_MODEL:-STANDARD}"

CMD=(
  gcloud compute instances create "${INSTANCE_NAME}"
  "--project=${PROJECT_ID}"
  "--zone=${ZONE}"
  "--machine-type=${MACHINE_TYPE}"
  "--accelerator=type=${GPU_TYPE},count=${GPU_COUNT}"
  "--maintenance-policy=TERMINATE"
  "--restart-on-failure"
  "--provisioning-model=${PROVISIONING_MODEL}"
  "--boot-disk-size=${BOOT_DISK_GB}GB"
  "--boot-disk-type=pd-ssd"
  "--image-family=common-cu128-ubuntu-2204-nvidia-570"
  "--image-project=deeplearning-platform-release"
  "--scopes=https://www.googleapis.com/auth/cloud-platform"
  "--tags=deep-policy-trainer"
)

if [[ -n "${SERVICE_ACCOUNT:-}" ]]; then
  CMD+=("--service-account=${SERVICE_ACCOUNT}")
fi

echo "Creating VM ${INSTANCE_NAME} in ${ZONE} (${PROVISIONING_MODEL}) ..."
"${CMD[@]}"
echo "VM created. SSH with:"
echo "  gcloud compute ssh ${INSTANCE_NAME} --project=${PROJECT_ID} --zone=${ZONE}"

