#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

source .venv/bin/activate

export PYTHONPATH="apps/admin-service/src:packages/shared/src:packages/devkit/src:${PYTHONPATH:-}"
python -m admin_service
