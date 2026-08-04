#!/usr/bin/env sh

set -eu

grammar_repository="https://github.com/tree-sitter/tree-sitter-go.git"
grammar_tag="v0.25.0"
grammar_revision="1547678a9da59885853f5f5cc8a99cc203fa2e2c"
package_directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
temporary_directory=$(mktemp -d -t red-go-grammar.XXXXXXXX)

cleanup() {
    rm -rf "$temporary_directory"
}

trap cleanup EXIT HUP INT TERM

if ! command -v tree-sitter >/dev/null 2>&1; then
    printf '%s\n' 'tree-sitter CLI is required; install it with: brew install tree-sitter' >&2
    exit 1
fi

if ! command -v cc >/dev/null 2>&1; then
    printf '%s\n' 'a C compiler is required to build the Go grammar' >&2
    exit 1
fi

printf 'Fetching Go grammar %s (%s)…\n' "$grammar_tag" "$grammar_revision"
git init --quiet "$temporary_directory/source"
git -C "$temporary_directory/source" fetch --quiet --depth 1 \
    "$grammar_repository" "$grammar_revision"
git -C "$temporary_directory/source" checkout --quiet --detach FETCH_HEAD

checked_out_revision=$(git -C "$temporary_directory/source" rev-parse HEAD)
if [ "$checked_out_revision" != "$grammar_revision" ]; then
    printf 'Unexpected Go grammar revision: %s\n' "$checked_out_revision" >&2
    exit 1
fi

printf '%s\n' 'Generating Tree-sitter ABI 15 parser…'
(
    cd "$temporary_directory/source"
    tree-sitter generate --abi 15
)

mkdir -p "$package_directory/grammars"

case $(uname -s) in
    Darwin)
        shared_library_flag=-dynamiclib
        ;;
    Linux)
        shared_library_flag=-shared
        ;;
    *)
        printf 'Unsupported platform: %s\n' "$(uname -s)" >&2
        exit 1
        ;;
esac

printf '%s\n' 'Compiling the Go parser…'
cc -std=c11 -O2 -fPIC "$shared_library_flag" \
    -I "$temporary_directory/source/src" \
    "$temporary_directory/source/src/parser.c" \
    -o "$package_directory/grammars/go.so"

printf 'Go grammar ready: %s/grammars/go.so\n' "$package_directory"
