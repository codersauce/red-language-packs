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
CAPTURE = re.compile(r"@([a-z][a-z0-9_.-]*)")


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
        formatter = language.get("formatter")
        if not isinstance(formatter, dict):
            fail(f"{manifest_path}: languages.{language_id}.formatter must be a table")
        for field in ("name", "command"):
            if not isinstance(formatter.get(field), str) or not formatter[field].strip():
                fail(f"{manifest_path}: languages.{language_id}.formatter.{field} must be non-empty")
        for field in ("args", "root_markers"):
            if not isinstance(formatter.get(field, []), list) or not all(
                isinstance(value, str) for value in formatter.get(field, [])
            ):
                fail(f"{manifest_path}: languages.{language_id}.formatter.{field} must contain strings")

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
    validate_arborium_overlay(pack, manifest, catalog)
    return manifest


def validate_arborium_overlay(pack: Path, manifest: dict, catalog: dict) -> None:
    overlay_path = Path(__file__).resolve().parent.parent / "arborium" / "languages" / f"{pack.name}.toml"
    if not overlay_path.is_file():
        return
    overlay = load_toml(overlay_path)
    package = overlay["package"]
    language = overlay["language"]
    identifier = language["id"]
    plugin = manifest["plugin"]
    for field in ("id", "name", "version", "red_api", "description", "license"):
        if plugin.get(field) != package.get(field):
            fail(f"{pack}: generated plugin.{field} differs from its reviewed Arborium overlay")
    definition = manifest["languages"].get(identifier)
    if not isinstance(definition, dict):
        fail(f"{pack}: reviewed Arborium language {identifier} is missing from the manifest")
    for field in ("extensions", "filenames", "aliases", "comment", "indent_width"):
        if field in language and definition.get(field) != language[field]:
            fail(f"{pack}: language.{field} differs from its reviewed Arborium overlay")
    if definition.get("lsp", {}).get("command") != overlay["lsp"]["command"]:
        fail(f"{pack}: language server differs from its reviewed external LSP command")
    if definition.get("formatter") != {
        key: overlay["formatter"][key]
        for key in ("name", "command", "args", "root_markers")
        if key in overlay["formatter"]
    }:
        fail(f"{pack}: formatter differs from its reviewed external formatter metadata")
    if catalog.get("tier") != package["catalog_tier"]:
        fail(f"{pack}: catalog tier differs from its reviewed Arborium overlay")
    requirements = catalog.get("requirements", [])
    if not any(
        requirement.get("command") == overlay["formatter"]["command"]
        and requirement.get("purpose") == overlay["formatter"]["purpose"]
        for requirement in requirements
    ):
        fail(f"{pack}: catalog omits its reviewed external formatter requirement")

    captures: set[str] = set()
    for raw in definition.get("grammar", {}).get("highlights", []):
        captures.update(CAPTURE.findall((pack / safe_relative(raw, "highlight query")).read_text()))
    missing = set(language.get("minimum_capture_scopes", [])) - captures
    if missing:
        fail(f"{pack}: required highlight scopes are missing: {', '.join(sorted(missing))}")

    if source := overlay.get("source"):
        notices = (pack / "THIRD_PARTY_NOTICES.md").read_text()
        if source["revision"] not in notices:
            fail(f"{pack}: reviewed source override is missing from third-party notices")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pack", type=Path, nargs="?")
    parser.add_argument("--all", action="store_true", help="validate every reviewed language pack")
    args = parser.parse_args()
    if bool(args.pack) == args.all:
        parser.error("provide exactly one pack or --all")
    root = Path(__file__).resolve().parent.parent
    packs = (
        [root / "packs" / path.stem for path in sorted((root / "arborium" / "languages").glob("*.toml"))]
        if args.all
        else [args.pack.resolve()]
    )
    try:
        for pack in packs:
            manifest = validate(pack)
            print(f"validated {manifest['plugin']['id']} {manifest['plugin']['version']}")
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
