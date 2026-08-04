#!/usr/bin/env sh

set -eu

grammar_repository="https://github.com/alex-pinkus/tree-sitter-swift.git"
grammar_revision="8abb3e8b33256d89127a35e87480736f74755ff9"
package_directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
temporary_directory=$(mktemp -d "${TMPDIR:-/tmp}/red-swift-grammar.XXXXXXXX")

cleanup() {
    rm -rf "$temporary_directory"
}

trap cleanup EXIT HUP INT TERM

if ! command -v tree-sitter >/dev/null 2>&1; then
    printf '%s\n' 'tree-sitter CLI is required; install it with: brew install tree-sitter' >&2
    exit 1
fi

if ! command -v cc >/dev/null 2>&1; then
    printf '%s\n' 'a C compiler is required to build the Swift grammar' >&2
    exit 1
fi

printf 'Fetching Swift grammar %s…\n' "$grammar_revision"
git clone --quiet "$grammar_repository" "$temporary_directory/source"
git -C "$temporary_directory/source" checkout --quiet "$grammar_revision"

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

printf '%s\n' 'Compiling the Swift parser and external scanner…'
cc -std=c11 -O2 -fPIC "$shared_library_flag" \
    -I "$temporary_directory/source/src" \
    "$temporary_directory/source/src/parser.c" \
    "$temporary_directory/source/src/scanner.c" \
    -o "$package_directory/grammars/swift.so"

printf 'Swift grammar ready: %s/grammars/swift.so\n' "$package_directory"
