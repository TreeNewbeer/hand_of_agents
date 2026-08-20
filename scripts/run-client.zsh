#!/usr/bin/env zsh
set -euo pipefail

if (( $# != 1 )); then
  print -u2 "usage: $0 PATH_TO_CLIENT_TOML"
  exit 2
fi

script_dir=${0:A:h}
project_dir=${script_dir:h}
cd "${project_dir}"
exec .venv/bin/hoa-client --config "$1"

