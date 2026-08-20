#!/usr/bin/env zsh
set -euo pipefail

script_dir=${0:A:h}
project_dir=${script_dir:h}
cd "${project_dir}"

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

exec .venv/bin/hoa-server

