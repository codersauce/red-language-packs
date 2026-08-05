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
from pathlib import Path

from arborium import (
    Definition,
    ROOT,
    arborium_source,
    definitions,
    extracted_archive,
    load_overlay,
    load_settings,
    reviewed_languages,
)


UNSAFE_SWIFT_ALLOCATION = re.compile(r"calloc\s*\(\s*0\s*,\s*sizeof\s*\(")


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
    settings = load_settings()
    executable = check_cli(settings["upstream"]["tree_sitter_cli"])
    overlay = load_overlay(ROOT / "arborium" / "languages" / f"{identifier}.toml")
    with arborium_source(settings, archive) as arborium:
        all_definitions = definitions(arborium)
        definition = all_definitions.get(identifier)
        if definition is None:
            raise ValueError(f"Arborium does not define language {identifier}")
        with tempfile.TemporaryDirectory(prefix=f"red-{identifier}-grammar-") as directory:
            destination = Path(directory) / "grammar"
            if override := overlay.get("source"):
                supplied = os.environ.get("RED_GRAMMAR_SOURCE_ARCHIVE")
                with extracted_archive(
                    override["repository"],
                    override["revision"],
                    override["archive_sha256"],
                    Path(supplied) if supplied else None,
                ) as source:
                    shutil.copytree(source, destination)
            else:
                shutil.copytree(definition.directory / "grammar", destination)
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

            output = ROOT / "packs" / identifier / "grammars" / f"{identifier}.so"
            output.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([executable, "build", "--output", str(output), str(destination)], check=True)
            library = ctypes.CDLL(str(output))
            symbol = overlay["language"]["symbol"]
            if not hasattr(library, symbol):
                raise ValueError(f"{identifier} grammar does not export required symbol {symbol}")
            validate_sample_highlighting(executable, identifier, overlay, destination)
            print(f"built {identifier} ABI {expected_abi} grammar: {output}")
            return output


def validate_sample_highlighting(
    executable: str,
    identifier: str,
    overlay: dict,
    grammar_directory: Path,
) -> None:
    pack = ROOT / "packs" / identifier
    validation = overlay["validation"]
    sample = pack / validation["sample"]
    if not sample.is_file():
        raise ValueError(f"{identifier} highlight sample does not exist: {sample}")
    combined = grammar_directory / "red-highlights.scm"
    query_paths = [
        pack / "queries" / "arborium-highlights.scm",
        pack / overlay["language"]["highlight_overlay"],
    ]
    combined.write_text(
        "\n".join(path.read_text(encoding="utf-8") for path in query_paths),
        encoding="utf-8",
    )
    configuration = grammar_directory / "red-tree-sitter-config.json"
    configuration.write_text(
        json.dumps({"parser-directories": [str(grammar_directory.parent)]}),
        encoding="utf-8",
    )
    captures = subprocess.check_output(
        [
            executable,
            "query",
            "--config-path",
            str(configuration),
            "--captures",
            str(combined),
            str(sample),
        ],
        cwd=grammar_directory,
        text=True,
    )
    missing = [
        capture
        for capture in validation["required_captures"]
        if re.search(rf"\b{re.escape(capture)}\b", captures) is None
    ]
    if missing:
        raise ValueError(f"{identifier} sample lost expected highlights: {', '.join(missing)}")
    print(f"verified {identifier} sample highlight captures")


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
