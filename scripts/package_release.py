#!/usr/bin/env python3
"""Build a deterministic target bundle and its catalog metadata fragment."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import tarfile
import tomllib
import urllib.parse
from pathlib import Path

from validate_pack import safe_relative, validate


COMMIT = re.compile(r"^[0-9a-fA-F]{40}$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_file(archive: tarfile.TarFile, source: Path, relative: Path) -> None:
    data = source.read_bytes()
    info = tarfile.TarInfo(relative.as_posix())
    info.size = len(data)
    info.mode = 0o755 if os.access(source, os.X_OK) else 0o644
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    archive.addfile(info, io.BytesIO(data))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pack", type=Path)
    parser.add_argument("--target", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    pack = args.pack.resolve()
    manifest = validate(pack)
    with (pack / "catalog.toml").open("rb") as handle:
        catalog_metadata = tomllib.load(handle)
    plugin = manifest["plugin"]
    version = plugin["version"]
    slug = pack.name
    expected_tag = f"{slug}/v{version}"
    if args.tag != expected_tag:
        raise ValueError(f"release tag must be {expected_tag}, got {args.tag}")
    if not COMMIT.fullmatch(args.commit):
        raise ValueError("--commit must be a full Git commit SHA")

    repo = Path(__file__).resolve().parent.parent
    source_path = pack.relative_to(repo).as_posix()
    files = {
        Path("red-plugin.toml"),
        Path("README.md"),
        Path("LICENSE"),
        Path("THIRD_PARTY_NOTICES.md"),
    }
    grammar_digests: dict[str, str] = {}
    for language_id, language in manifest["languages"].items():
        grammar = language.get("grammar")
        if not grammar:
            continue
        if raw := grammar.get("path"):
            relative = safe_relative(raw, f"languages.{language_id}.grammar.path")
            grammar_path = pack / relative
            if not grammar_path.is_file():
                raise ValueError(f"build the grammar before packaging: missing {grammar_path}")
            files.add(relative)
            grammar_digests[language_id] = sha256(grammar_path)
        for field in ("highlights", "textobjects", "indents"):
            for raw in grammar.get(field, []):
                files.add(safe_relative(raw, f"languages.{language_id}.grammar.{field}"))
        if raw := grammar.get("injections"):
            files.add(safe_relative(raw, f"languages.{language_id}.grammar.injections"))

    args.output.mkdir(parents=True, exist_ok=True)
    asset_name = f"red-{slug}-language-pack-v{version}-{args.target}.tar.gz"
    asset_path = args.output / asset_name
    with asset_path.open("wb") as raw_output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_output, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                for relative in sorted(files, key=lambda path: path.as_posix()):
                    source = pack / relative
                    if not source.is_file():
                        raise ValueError(f"release input is missing: {source}")
                    add_file(archive, source, relative)

    encoded_tag = urllib.parse.quote(args.tag, safe="")
    asset_url = (
        "https://github.com/codersauce/red-language-packs/releases/download/"
        f"{encoded_tag}/{asset_name}"
    )
    entry = {
        "id": plugin["id"],
        "name": plugin["name"],
        "version": version,
        "red_api": plugin["red_api"],
        "description": plugin["description"],
        "repository": "codersauce/red-language-packs",
        "source_path": source_path,
        "resolved_commit": args.commit.lower(),
        "license": plugin["license"],
        "tier": catalog_metadata["tier"],
        "languages": sorted(manifest["languages"]),
        "requirements": catalog_metadata.get("requirements", []),
        "artifacts": {
            args.target: {
                "url": asset_url,
                "sha256": sha256(asset_path),
                "size": asset_path.stat().st_size,
                "grammars": grammar_digests,
            }
        },
    }
    metadata_path = args.output / f"catalog-{slug}-{args.target}.json"
    metadata_path.write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n")
    print(asset_path)
    print(metadata_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
