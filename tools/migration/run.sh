#!/bin/sh
# Usage: run.sh [--python EXECUTABLE] [migration.py arguments...]
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

is_python311() {
    "$1" -c 'import sys; sys.exit(sys.version_info < (3, 11))' > /dev/null 2>&1
}

python=
case ${1:-} in
    --python)
        if [ "$#" -lt 2 ]; then
            printf '%s\n' '--python needs an executable.' >&2
            exit 1
        fi
        python=$2
        shift 2
        ;;
    --python=*)
        python=${1#*=}
        shift
        ;;
esac

if [ -z "$python" ]; then
    # macOS ships an older python3 under /usr/bin; skip any candidate below 3.11.
    for candidate in python3 python; do
        if command -v "$candidate" > /dev/null 2>&1 && is_python311 "$candidate"; then
            python=$(command -v "$candidate")
            break
        fi
    done
fi
if [ -z "$python" ]; then
    bundled_python=${HOME:-}/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
    if [ -f "$bundled_python" ]; then python=$bundled_python; fi
fi
if [ -z "$python" ]; then
    printf '%s\n' 'Python 3.11+ was not found. Supply --python with an existing Python executable. Nothing was installed.' >&2
    exit 1
fi

exec "$python" -B -X utf8 "$script_dir/migration.py" "$@"
