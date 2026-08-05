#!/usr/bin/env sh

set -eu

repository_directory=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
exec python3 "$repository_directory/scripts/build_grammar.py" svelte "$@"
