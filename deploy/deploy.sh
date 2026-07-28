#!/usr/bin/env bash
# 兼容入口，转调 one-click-deploy.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${SCRIPT_DIR}/one-click-deploy.sh" "$@"
