#!/usr/bin/env bash
set -euo pipefail
original_ns=$1
original_uid=$2
original_gid=$3
shift 3
fail() { printf 'offline: %s\n' "$*" >&2; exit 125; }
[[ $(readlink /proc/self/ns/net) != "$original_ns" ]] || fail 'network namespace unchanged'
[[ $(id -u) == "$original_uid" && $(id -g) == "$original_gid" ]] || fail 'identity changed'
awk 'BEGIN { ok=1 }
  /^Cap(Inh|Prm|Eff|Bnd|Amb):/ { count++; if ($2 !~ /^0+$/) ok=0 }
  /^NoNewPrivs:/ { nnp=$2 }
  END { exit !(ok && count==5 && nnp==1) }' /proc/self/status || fail 'privilege checks failed'
awk 'NR > 2 { sub(/^[[:space:]]+/, "", $0); split($0,a,":"); if(a[1] != "lo") bad=1; else lo=1 }
  END { exit (bad || !lo) }' /proc/net/dev || fail 'unexpected network interfaces'
exec "$@"
