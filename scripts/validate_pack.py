#!/usr/bin/env python3
"""Validate one self-contained Red language-pack source directory."""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path, PurePosixPath


IDENTIFIER = re.compile(r"^[a-z0-9_-]+$")
VERSION = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def fail(message: str) -> None:
    raise ValueError(message)


def safe_relative(raw: str, label: str) -> Path:
    path = PurePosixPath(raw)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        fail(f"{label} must be a safe package-relative path: {raw!r}")
    return Path(*path.parts)


def load_toml(path: Path) -> dict:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        fail(f"failed to read {path}: {error}")


def validate(pack: Path) -> dict:
    manifest_path = pack / "red-plugin.toml"
    catalog_path = pack / "catalog.toml"
    manifest = load_toml(manifest_path)
    catalog = load_toml(catalog_path)

    if manifest.get("schema_version") != 1:
        fail(f"{manifest_path}: schema_version must be 1")
    plugin = manifest.get("plugin")
    if not isinstance(plugin, dict):
        fail(f"{manifest_path}: missing [plugin]")
    plugin_id = plugin.get("id", "")
    if not IDENTIFIER.fullmatch(plugin_id):
        fail(f"{manifest_path}: invalid plugin id {plugin_id!r}")
    version = plugin.get("version", "")
    if not VERSION.fullmatch(version):
        fail(f"{manifest_path}: version must be SemVer")
    for field in ("name", "red_api", "description", "repository", "license"):
        if not isinstance(plugin.get(field), str) or not plugin[field].strip():
            fail(f"{manifest_path}: plugin.{field} must be non-empty")
    if plugin["repository"] != "https://github.com/codersauce/red-language-packs":
        fail(f"{manifest_path}: plugin.repository must name the canonical monorepo")

    languages = manifest.get("languages")
    if not isinstance(languages, dict) or not languages:
        fail(f"{manifest_path}: a language pack must define [languages.*]")
    for language_id, language in languages.items():
        if not IDENTIFIER.fullmatch(language_id):
            fail(f"{manifest_path}: invalid language id {language_id!r}")
        grammar = language.get("grammar")
        if not isinstance(grammar, dict):
            continue
        if "path" in grammar:
            safe_relative(grammar["path"], f"languages.{language_id}.grammar.path")
        for field in ("highlights",):
            for raw in grammar.get(field, []):
                relative = safe_relative(raw, f"languages.{language_id}.grammar.{field}")
                if not (pack / relative).is_file():
                    fail(f"{manifest_path}: missing {relative}")
        if raw := grammar.get("injections"):
            relative = safe_relative(raw, f"languages.{language_id}.grammar.injections")
            if not (pack / relative).is_file():
                fail(f"{manifest_path}: missing {relative}")

    if catalog.get("tier") not in {"official", "curated"}:
        fail(f"{catalog_path}: tier must be official or curated")
    for requirement in catalog.get("requirements", []):
        if not isinstance(requirement, dict):
            fail(f"{catalog_path}: requirements must be tables")
        if not IDENTIFIER.fullmatch(requirement.get("command", "")):
            fail(f"{catalog_path}: invalid requirement command")
        if not str(requirement.get("purpose", "")).strip():
            fail(f"{catalog_path}: requirement purpose must be non-empty")

    for required in ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "build-grammar.sh"):
        if not (pack / required).is_file():
            fail(f"{pack}: missing {required}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pack", type=Path)
    args = parser.parse_args()
    try:
        manifest = validate(args.pack.resolve())
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print(f"validated {manifest['plugin']['id']} {manifest['plugin']['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
