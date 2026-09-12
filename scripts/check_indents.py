#!/usr/bin/env python3
"""Run pack fixtures through a selected Red binary in an isolated configuration."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import tempfile

from arborium import ROOT, reviewed_languages
from validate_pack import validate


def check(pack: Path, red: Path) -> None:
    manifest = validate(pack)
    if not any(language.get("grammar", {}).get("indents") for language in manifest["languages"].values()):
        print(f"skipped {manifest['plugin']['id']}: no indentation queries declared")
        return
    for language in manifest["languages"].values():
        grammar = language.get("grammar", {})
        if grammar.get("path") and not (pack / grammar["path"]).is_file():
            raise ValueError(f"build the grammar first: {pack / grammar['path']}")
    with tempfile.TemporaryDirectory(prefix="red-indent-check-") as directory:
        environment = dict(os.environ, XDG_CONFIG_HOME=directory)
        subprocess.run([str(red), "plugin", "install", "--path", str(pack), "--trust-native-grammars"], env=environment, check=True)
        subprocess.run([str(red), "language", "check-indent", str(pack / "tests" / "indent.json")], env=environment, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", type=Path, nargs="?")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--red", type=Path, required=True)
    args = parser.parse_args()
    if bool(args.pack) == args.all:
        parser.error("provide exactly one pack or --all")
    packs = [ROOT / "packs" / name for name in reviewed_languages()] if args.all else [args.pack.resolve()]
    for pack in packs:
        check(pack, args.red.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
