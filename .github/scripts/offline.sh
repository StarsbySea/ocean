#!/usr/bin/env bash
set -euo pipefail
if (( $# == 0 )); then
  printf 'Usage: %s COMMAND [ARG ...]\n' "$0" >&2
  exit 64
fi
command -v unshare >/dev/null
command -v setpriv >/dev/null
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
original_ns=$(readlink /proc/self/ns/net)
original_uid=$(id -u)
original_gid=$(id -g)
exec unshare --user --map-current-user --net --keep-caps -- \
  setpriv --no-new-privs --bounding-set=-all --inh-caps=-all --ambient-caps=-all -- \
  env -u BASH_ENV -u ENV /bin/bash --noprofile --norc "$script_dir/offline-guard.sh" "$original_ns" "$original_uid" "$original_gid" "$@"
