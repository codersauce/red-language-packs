#!/usr/bin/env python3
"""Validate one self-contained Red language-pack source directory."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path, PurePosixPath

from arborium import grammar_overlays, is_standalone, load_overlay, source_patch_paths


IDENTIFIER = re.compile(r"^[a-z0-9_-]+$")
VERSION = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
CAPTURE = re.compile(r"@([a-z][a-z0-9_.-]*)")
QUERY_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|;[^\n]*|[()]|[^\s();"]+')
TEXT_PREDICATES = {
    "eq?", "not-eq?", "any-eq?", "any-not-eq?",
    "match?", "not-match?", "any-match?", "any-not-match?",
    "any-of?", "not-any-of?",
}
INDENT_CAPTURES = {"indent.begin", "indent.end", "indent.branch", "indent.ignore", "indent.zero", "indent.match", "indent.continuation"}


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


def validate_query_predicates(path: Path, *, injections: bool = False) -> None:
    """Reject runtime query operations Red does not evaluate, ignoring quoted text and comments."""
    tokens = [token for token in QUERY_TOKEN.findall(path.read_text()) if not token.startswith(";")]
    for index, token in enumerate(tokens[:-1]):
        if token != "(" or not tokens[index + 1].startswith("#"):
            continue
        operator = tokens[index + 1][1:]
        if operator in TEXT_PREDICATES:
            continue
        if injections and operator == "set!" and tokens[index + 2:index + 3] == ["injection.language"]:
            continue
        fail(f"{path}: unsupported Red query predicate or directive #{operator}")


def validate_formatter(formatter: object, label: str) -> None:
    if not isinstance(formatter, dict):
        fail(f"{label} must be a table")
    for field in ("name", "command"):
        if not isinstance(formatter.get(field), str) or not formatter[field].strip():
            fail(f"{label}.{field} must be non-empty")
    for field in ("args", "root_markers"):
        if not isinstance(formatter.get(field, []), list) or not all(
            isinstance(value, str) for value in formatter.get(field, [])
        ):
            fail(f"{label}.{field} must contain strings")


def validate(pack: Path) -> dict:
    """Audit standalone/manual queries strictly while preserving reviewed Arborium behavior."""
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
    overlay_path = Path(__file__).resolve().parent.parent / "arborium" / "languages" / f"{pack.name}.toml"
    overlay = load_overlay(overlay_path) if overlay_path.is_file() else None
    strict_query_languages = set(languages) if overlay is None else {
        grammar["language"]["id"] for grammar in grammar_overlays(overlay) if is_standalone(grammar)
    }
    for language_id, language in languages.items():
        if not IDENTIFIER.fullmatch(language_id):
            fail(f"{manifest_path}: invalid language id {language_id!r}")
        grammar = language.get("grammar")
        if not isinstance(grammar, dict):
            continue
        if "path" in grammar:
            safe_relative(grammar["path"], f"languages.{language_id}.grammar.path")
        for field in ("highlights", "textobjects", "indents"):
            for raw in grammar.get(field, []):
                relative = safe_relative(raw, f"languages.{language_id}.grammar.{field}")
                if not (pack / relative).is_file() or not (pack / relative).resolve().is_relative_to(pack.resolve()):
                    fail(f"{manifest_path}: missing or unsafe {relative}")
                if field == "highlights" and language_id in strict_query_languages:
                    validate_query_predicates(pack / relative)
                if field == "indents":
                    unsupported = set(CAPTURE.findall((pack / relative).read_text())) - INDENT_CAPTURES
                    if unsupported:
                        fail(f"{manifest_path}: unsupported indentation captures: {sorted(unsupported)}")
        if grammar.get("indents"):
            api = re.fullmatch(r"\^0\.(\d+)\.(\d+)", plugin["red_api"])
            if api is None or tuple(map(int, api.groups())) < (12, 0):
                fail(f"{manifest_path}: indentation queries require red_api ^0.12.0 or later")
            fixtures = pack / "tests" / "indent.json"
            try:
                cases = json.loads(fixtures.read_text())
            except (OSError, json.JSONDecodeError) as error:
                fail(f"{fixtures}: {error}")
            if not isinstance(cases, list) or not cases:
                fail(f"{fixtures}: expected non-empty fixture array")
            for case in cases:
                if (not isinstance(case, dict)
                    or not isinstance(case.get("name"), str) or not case["name"]
                    or case.get("language") != language_id
                    or not isinstance(case.get("source"), str)
                    or type(case.get("line")) is not int
                    or not 0 <= case["line"] < len(case["source"].split("\n"))
                    or type(case.get("expected")) is not int or case["expected"] < 0
                    or type(case.get("width", 4)) is not int or case.get("width", 4) <= 0):
                    fail(f"{fixtures}: invalid indentation fixture")
        if raw := grammar.get("injections"):
            relative = safe_relative(raw, f"languages.{language_id}.grammar.injections")
            if not (pack / relative).is_file():
                fail(f"{manifest_path}: missing {relative}")
            if language_id in strict_query_languages:
                validate_query_predicates(pack / relative, injections=True)
        if "formatter" in language:
            validate_formatter(language["formatter"], f"{manifest_path}: languages.{language_id}.formatter")

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
    if overlay is not None:
        validate_arborium_overlay(pack, manifest, catalog, overlay)
    return manifest


def validate_arborium_overlay(pack: Path, manifest: dict, catalog: dict, overlay: dict) -> None:
    package = overlay["package"]
    plugin = manifest["plugin"]
    for field in ("id", "name", "version", "red_api", "description", "license"):
        if plugin.get(field) != package.get(field):
            fail(f"{pack}: generated plugin.{field} differs from its reviewed Arborium overlay")
    if catalog.get("tier") != package["catalog_tier"]:
        fail(f"{pack}: catalog tier differs from its reviewed Arborium overlay")
    grammars = grammar_overlays(overlay)
    if set(manifest["languages"]) != {grammar["language"]["id"] for grammar in grammars}:
        fail(f"{pack}: manifest languages differ from its reviewed metadata")
    for grammar in grammars:
        validate_language_overlay(pack, manifest, catalog, grammar)


def validate_language_overlay(pack: Path, manifest: dict, catalog: dict, overlay: dict) -> None:
    language = overlay["language"]
    identifier = language["id"]
    validation = overlay.get("validation", {})
    if "reject_parse_errors" in validation and not isinstance(validation["reject_parse_errors"], bool):
        fail(f"{pack}: {identifier} reject_parse_errors must be boolean")
    for field in ("capture_assertions", "injection_assertions"):
        assertions = validation.get(field, [])
        if not isinstance(assertions, list):
            fail(f"{pack}: {identifier} {field} must be an array of tables")
        for assertion in assertions:
            if not isinstance(assertion, dict) or not all(
                isinstance(assertion.get(key), str) and assertion[key]
                for key in ("capture", "text")
            ):
                fail(f"{pack}: {identifier} {field} requires non-empty capture and text")
            if not isinstance(assertion.get("must_exist", True), bool):
                fail(f"{pack}: {identifier} {field} must_exist must be boolean")
            positions = [key in assertion for key in ("row", "column")]
            if any(positions) and (not all(positions) or not all(
                type(assertion[key]) is int and assertion[key] >= 0 for key in ("row", "column")
            )):
                fail(f"{pack}: {identifier} {field} requires non-negative row and column")
    definition = manifest["languages"].get(identifier)
    if not isinstance(definition, dict):
        fail(f"{pack}: reviewed Arborium language {identifier} is missing from the manifest")
    for field in ("extensions", "filenames", "aliases", "shebangs"):
        if definition.get(field, []) != language.get(field, []):
            fail(f"{pack}: language.{field} differs from its reviewed Arborium overlay")
    for field in ("comment", "indent_width"):
        if definition.get(field) != language.get(field):
            fail(f"{pack}: language.{field} differs from its reviewed Arborium overlay")
    if definition.get("grammar", {}).get("indents", []) != language.get("indent_queries", []):
        fail(f"{pack}: indentation queries differ from the reviewed overlay")
    lsp = overlay.get("lsp")
    expected_lsp = {
        key: lsp[key] for key in ("command", "args", "root_markers") if key in lsp
    } if lsp is not None else None
    if definition.get("lsp") != expected_lsp:
        fail(f"{pack}: language server differs from its reviewed external LSP command")
    formatter = overlay.get("formatter")
    expected_formatter = {
        key: formatter[key]
        for key in ("name", "command", "args", "root_markers")
        if key in formatter
    } if formatter is not None else None
    if definition.get("formatter") != expected_formatter:
        fail(f"{pack}: formatter differs from its reviewed external formatter metadata")
    requirements = catalog.get("requirements", [])
    for tool, label in ((lsp, "LSP"), (formatter, "formatter")):
        if tool is not None and not any(
            requirement.get("command") == tool["command"]
            and requirement.get("purpose") == tool["purpose"]
            for requirement in requirements
        ):
            fail(f"{pack}: catalog omits its reviewed external {label} requirement")

    grammar = definition.get("grammar", {})
    if is_standalone(overlay):
        source_patch_paths(overlay, pack)
        if grammar.get("highlights") != [language["highlight_overlay"]]:
            fail(f"{pack}: standalone {identifier} must load only its reviewed highlight query")
        if grammar.get("injections") != language.get("injections"):
            fail(f"{pack}: standalone {identifier} injections differ from its reviewed metadata")
        if grammar.get("path") != f"grammars/{identifier}.so" or grammar.get("symbol") != language["symbol"]:
            fail(f"{pack}: standalone {identifier} grammar differs from its reviewed metadata")

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
