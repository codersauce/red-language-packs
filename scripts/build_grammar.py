#!/usr/bin/env python3
"""Build one independently trusted ABI-15 grammar from verified upstream sources."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from contextlib import ExitStack
from pathlib import Path

from arborium import (
    Definition,
    ROOT,
    arborium_source,
    definitions,
    extracted_archive,
    grammar_overlays,
    is_standalone,
    load_overlay,
    load_settings,
    reviewed_languages,
    source_patch_paths,
    standalone_definition,
)


UNSAFE_SWIFT_ALLOCATION = re.compile(r"calloc\s*\(\s*0\s*,\s*sizeof\s*\(")
CAPTURE_RANGE = re.compile(
    r"capture:\s*\d+ - ([\w.-]+), start: \((\d+), (\d+)\), end: \((\d+), (\d+)\)"
)


def check_cli(expected: str) -> str:
    executable = os.environ.get("TREE_SITTER", "tree-sitter")
    try:
        version = subprocess.check_output([executable, "--version"], text=True).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError(f"Tree-sitter CLI {expected} is required: {error}") from error
    if version.split()[:2] != ["tree-sitter", expected]:
        raise ValueError(f"Tree-sitter CLI must be exactly {expected}, found {version}")
    return executable


def stage_dependencies(
    destination: Path, definition: Definition, all_definitions: dict[str, Definition]
) -> None:
    for identifier in definition.query_dependencies:
        dependency = all_definitions.get(identifier)
        if dependency is None:
            raise ValueError(f"{definition.identifier} inherits unknown grammar {identifier}")
        package = destination / "node_modules" / f"tree-sitter-{identifier}"
        if package.exists():
            continue
        shutil.copytree(dependency.directory / "grammar", package)
        stage_dependencies(package, dependency, all_definitions)


def stage_scanner(destination: Path, definition: Definition) -> Path:
    scanner = destination / "src" / "scanner.c"
    if not scanner.is_file() and (source_scanner := destination / "scanner.c").is_file():
        shutil.copy2(source_scanner, scanner)
    if definition.has_scanner and not scanner.is_file():
        raise ValueError(f"{definition.identifier} declares an external scanner but none was generated")
    if scanner.is_file():
        for header in destination.glob("*.h"):
            shutil.copy2(header, scanner.parent / header.name)
        for directory in destination.iterdir():
            if directory.is_dir() and directory.name not in {"src", "node_modules"}:
                if any(directory.rglob("*.h")):
                    shutil.copytree(directory, scanner.parent / directory.name, dirs_exist_ok=True)
    return scanner


def build(identifier: str, archive: Path | None) -> Path:
    reviewed_languages()
    settings = load_settings()
    executable = check_cli(settings["upstream"]["tree_sitter_cli"])
    overlay = load_overlay(ROOT / "arborium" / "languages" / f"{identifier}.toml")
    grammars = grammar_overlays(overlay)
    outputs = []
    with ExitStack() as stack:
        all_definitions = {}
        if any(not is_standalone(grammar) for grammar in grammars):
            arborium = stack.enter_context(arborium_source(settings, archive))
            all_definitions = definitions(arborium)
        for grammar in grammars:
            language_id = grammar["language"]["id"]
            definition = all_definitions.get(language_id)
            source = None
            if override := grammar.get("source"):
                environment_key = f"RED_GRAMMAR_SOURCE_ARCHIVE_{language_id.upper().replace('-', '_')}"
                supplied = os.environ.get(environment_key)
                if supplied is None and language_id == identifier:
                    supplied = os.environ.get("RED_GRAMMAR_SOURCE_ARCHIVE")
                source = stack.enter_context(extracted_archive(
                    override["repository"],
                    override["revision"],
                    override["archive_sha256"],
                    Path(supplied) if supplied else None,
                ))
                if is_standalone(grammar):
                    definition = standalone_definition(grammar, source, settings)
            if definition is None:
                raise ValueError(f"Arborium does not define language {language_id}")
            outputs.append(build_one(
                executable, identifier, grammar, definition, all_definitions,
                source or definition.directory / "grammar", settings,
            ))
    return outputs[0]


def build_one(
    executable: str,
    pack_identifier: str,
    overlay: dict,
    definition: Definition,
    all_definitions: dict[str, Definition],
    source: Path,
    settings: dict,
) -> Path:
    identifier = overlay["language"]["id"]
    with tempfile.TemporaryDirectory(prefix=f"red-{identifier}-grammar-") as directory:
        grammar_name = f"tree-sitter-{identifier}" if is_standalone(overlay) else "grammar"
        destination = Path(directory) / grammar_name
        shutil.copytree(source, destination)
        for source_patch in source_patch_paths(overlay, ROOT / "packs" / pack_identifier):
            subprocess.run(["git", "apply", "--check", str(source_patch)], cwd=destination, check=True)
            subprocess.run(["git", "apply", str(source_patch)], cwd=destination, check=True)
        stage_dependencies(destination, definition, all_definitions)

        configuration = destination / "tree-sitter.json"
        if not configuration.is_file():
            configuration.write_text(
                json.dumps(
                    {
                        "grammars": [
                            {
                                "name": overlay["language"].get("grammar_name", identifier),
                                "camelcase": definition.name,
                                "scope": f"source.{identifier}",
                                "path": ".",
                                "file-types": [
                                    *overlay["language"].get("extensions", []),
                                    *overlay["language"].get("filenames", []),
                                ],
                            }
                        ],
                        "metadata": {
                            "version": "0.0.0",
                            "license": definition.license,
                            "description": f"Pinned {definition.name} grammar for Red",
                        },
                        "bindings": {"c": True},
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

        subprocess.run(
            [executable, "generate", "--abi", str(settings["upstream"]["grammar_abi"])],
            cwd=destination,
            check=True,
        )
        scanner = stage_scanner(destination, definition)
        if identifier == "swift" and UNSAFE_SWIFT_ALLOCATION.search(scanner.read_text(encoding="utf-8")):
            raise ValueError("Swift scanner contains the unsafe zero-byte calloc allocation")

        parser = destination / "src" / "parser.c"
        contents = parser.read_text(encoding="utf-8")
        expected_abi = settings["upstream"]["grammar_abi"]
        if not re.search(rf"#define LANGUAGE_VERSION\s+{expected_abi}\b", contents):
            raise ValueError(f"{identifier} parser does not declare Tree-sitter ABI {expected_abi}")

        output = ROOT / "packs" / pack_identifier / "grammars" / f"{identifier}.so"
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([executable, "build", "--output", str(output), str(destination)], check=True)
        library = ctypes.CDLL(str(output))
        symbol = overlay["language"]["symbol"]
        if not hasattr(library, symbol):
            raise ValueError(f"{identifier} grammar does not export required symbol {symbol}")
        validate_sample_highlighting(executable, identifier, overlay, destination, pack_identifier)
        validate_indentation_queries(executable, identifier, overlay, destination, pack_identifier)
        print(f"built {identifier} ABI {expected_abi} grammar: {output}")
        return output


def validate_indentation_queries(
    executable: str,
    identifier: str,
    overlay: dict,
    grammar_directory: Path,
    pack_identifier: str | None = None,
) -> None:
    pack = ROOT / "packs" / (pack_identifier or identifier)
    paths = overlay["language"].get("indent_queries", [])
    if not paths:
        return
    combined = grammar_directory / "red-indents.scm"
    combined.write_text("\n".join((pack / path).read_text() for path in paths))
    configuration = grammar_directory / "red-tree-sitter-config.json"
    scope_args = ["--scope", f"source.{identifier}"] if is_standalone(overlay) else []
    subprocess.run(
        [executable, "query", "--config-path", str(configuration), *scope_args,
         str(combined), str(pack / overlay["validation"]["sample"])],
        cwd=grammar_directory, check=True, stdout=subprocess.DEVNULL,
    )
    print(f"verified {identifier} indentation query")


def validate_sample_highlighting(
    executable: str,
    identifier: str,
    overlay: dict,
    grammar_directory: Path,
    pack_identifier: str | None = None,
) -> None:
    pack = ROOT / "packs" / (pack_identifier or identifier)
    validation = overlay["validation"]
    sample = pack / validation["sample"]
    if not sample.is_file():
        raise ValueError(f"{identifier} highlight sample does not exist: {sample}")
    combined = grammar_directory / "red-highlights.scm"
    with (pack / "red-plugin.toml").open("rb") as handle:
        manifest = tomllib.load(handle)
    query_paths = [pack / path for path in manifest["languages"][identifier]["grammar"]["highlights"]]
    combined.write_text(
        "\n".join(path.read_text(encoding="utf-8") for path in query_paths),
        encoding="utf-8",
    )
    configuration = grammar_directory / "red-tree-sitter-config.json"
    configuration.write_text(
        json.dumps({"parser-directories": [str(grammar_directory.parent)]}),
        encoding="utf-8",
    )
    scope = f"source.{identifier}" if is_standalone(overlay) else None
    scope_args = ["--scope", scope] if scope else []
    if validation.get("reject_parse_errors", False):
        parsed = subprocess.check_output(
            [executable, "parse", "--config-path", str(configuration), *scope_args, "--quiet", "--json", str(sample)],
            cwd=grammar_directory,
            text=True,
        )
        summaries = json.loads(parsed).get("parse_summaries", [])
        if len(summaries) != 1 or not summaries[0].get("successful", False):
            raise ValueError(f"{identifier} sample contains parse errors")
    captures = query_sample(executable, configuration, combined, sample, grammar_directory, scope)
    captured_names = {match.group(1) for match in CAPTURE_RANGE.finditer(captures)}
    missing = [capture for capture in validation["required_captures"] if capture not in captured_names]
    if missing:
        raise ValueError(f"{identifier} sample lost expected highlights: {', '.join(missing)}")
    validate_capture_assertions(
        captures, sample.read_bytes(), validation.get("capture_assertions", []), identifier,
    )
    if assertions := validation.get("injection_assertions"):
        injection_path = manifest["languages"][identifier]["grammar"].get("injections")
        if not injection_path:
            raise ValueError(f"{identifier} has injection assertions without a loaded injection query")
        captures = query_sample(executable, configuration, pack / injection_path, sample, grammar_directory, scope)
        validate_capture_assertions(captures, sample.read_bytes(), assertions, f"{identifier} injection")
    print(f"verified {identifier} sample highlight captures")


def query_sample(
    executable: str, configuration: Path, query: Path, sample: Path, directory: Path, scope: str | None = None,
) -> str:
    return subprocess.check_output(
        [
            executable,
            "query",
            "--config-path",
            str(configuration),
            *(["--scope", scope] if scope else []),
            "--captures",
            str(query),
            str(sample),
        ],
        cwd=directory,
        text=True,
    )


def validate_capture_assertions(output: str, source: bytes, assertions: list[dict], label: str) -> None:
    """Compare exact captured source bytes and optional zero-based byte positions."""
    lines = source.split(b"\n")
    offsets = [0]
    for line in lines[:-1]:
        offsets.append(offsets[-1] + len(line) + 1)

    def offset(row: int, column: int) -> int:
        if row < 0 or row >= len(lines) or column < 0 or column > len(lines[row]):
            raise ValueError(f"{label} capture position is outside the sample: ({row}, {column})")
        return offsets[row] + column

    captures = []
    for match in CAPTURE_RANGE.finditer(output):
        name = match.group(1)
        row, column, end_row, end_column = map(int, match.groups()[1:])
        captures.append((name, row, column, source[offset(row, column):offset(end_row, end_column)]))
    for assertion in assertions:
        capture = assertion["capture"]
        expected = assertion["text"].encode("utf-8")
        position = None
        if "row" in assertion or "column" in assertion:
            if "row" not in assertion or "column" not in assertion:
                raise ValueError(f"{label} capture assertion requires both row and column")
            position = (assertion["row"], assertion["column"])
            start = offset(*position)
            if source[start:start + len(expected)] != expected:
                raise ValueError(f"{label} assertion text is not at {position}: {assertion['text']!r}")
        matched = any(
            name == capture and text == expected and (position is None or (row, column) == position)
            for name, row, column, text in captures
        )
        if matched != assertion.get("must_exist", True):
            requirement = "missing" if assertion.get("must_exist", True) else "unexpected"
            raise ValueError(f"{label} {requirement} exact @{capture} capture for {assertion['text']!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("language", nargs="?")
    parser.add_argument("--all", action="store_true", help="build every reviewed independent grammar")
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    if bool(args.language) == args.all:
        parser.error("provide exactly one language or --all")
    try:
        for identifier in reviewed_languages() if args.all else [args.language]:
            build(identifier, args.archive)
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
