#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

source .venv/bin/activate

export PYTHONPATH="apps/api/src:packages/shared/src:packages/devkit/src:packages/data-pipeline/src:packages/geo-engine/src:packages/trust-safety/src:${PYTHONPATH:-}"
python -m api.event_parking_monitor
