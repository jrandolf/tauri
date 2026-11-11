#!/usr/bin/env bash
# usage: run-wl.sh SESSION "ENV=val ..." VARIANT SCENARIO...
set -u
cd "$(dirname "$0")/.."
session=$1; envs=$2; variant=$3; shift 3
export OUT=$PWD/out/containers-env
mkdir -p "$OUT"
for scenario in "$@"; do
  env $envs NOSCAN=1 timeout 120 scripts/session.sh "$session" python3 explore/containers.py "$variant" "$scenario" 2>&1 | grep -E '^\{' | python3 -c "
import sys, json
for l in sys.stdin:
    d = json.loads(l)
    if d['tag'] in ('visible',):
        print('$envs', d['variant'], d['scenario'], d['session'], 'visible:', d['rects'])
    elif d['tag'] == 'start':
        print('$envs', d['variant'], d['scenario'], d['session'], 'gtk:', {n: (v['alloc'], v['in_toplevel']) for n, v in d['children'].items()}, 'room', d['outer'])
"
done
