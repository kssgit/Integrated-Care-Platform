#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

source .venv/Scripts/activate

export PYTHONPATH="apps/api/src:packages/data-pipeline/src:${PYTHONPATH:-}"
python -m data_pipeline.jobs

