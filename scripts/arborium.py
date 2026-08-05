#!/usr/bin/env python3
"""Import pinned Arborium definitions without making Arborium a Red runtime dependency."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tarfile
import tempfile
import tomllib
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parent.parent
REVISION = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
CAPTURE = re.compile(r"@([a-z][a-z0-9_.-]*)")
STATIC_INJECTION = re.compile(r'\(#set!\s+injection\.language\s+"([^"\n]+)"\s*\)')
UNSUPPORTED_INJECTION = re.compile(
    r"\(#(?:set!\s+injection\.(combined|include-children)|offset!)"
)


@dataclass(frozen=True)
class Definition:
    identifier: str
    name: str
    repository: str
    revision: str
    license: str
    tier: int | None
    has_scanner: bool
    aliases: tuple[str, ...]
    declared_injections: tuple[str, ...]
    query_dependencies: tuple[str, ...]
    directory: Path

    @property
    def highlights(self) -> Path:
        return self.directory / "queries" / "highlights.scm"

    @property
    def injections(self) -> Path:
        return self.directory / "queries" / "injections.scm"


def load_settings(root: Path = ROOT) -> dict:
    with (root / "arborium" / "source.toml").open("rb") as handle:
        settings = tomllib.load(handle)
    upstream = settings.get("upstream", {})
    if settings.get("schema_version") != 1:
        raise ValueError("Arborium source lock must use schema_version 1")
    if not REVISION.fullmatch(upstream.get("revision", "")):
        raise ValueError("Arborium revision must be a full, lowercase Git commit")
    if not DIGEST.fullmatch(upstream.get("archive_sha256", "")):
        raise ValueError("Arborium archive must have a full SHA-256 digest")
    return settings


def archive_url(repository: str, revision: str) -> str:
    prefix = "https://github.com/"
    if not repository.startswith(prefix):
        raise ValueError(f"grammar repositories must use GitHub HTTPS: {repository}")
    owner_repo = repository.removeprefix(prefix).removesuffix(".git").strip("/")
    if len(owner_repo.split("/")) != 2 or not REVISION.fullmatch(revision):
        raise ValueError(f"invalid immutable GitHub source: {repository}@{revision}")
    return f"https://codeload.github.com/{owner_repo}/tar.gz/{revision}"


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verified_archive(repository: str, revision: str, digest: str, supplied: Path | None) -> Path:
    if supplied is None:
        cache = Path(tempfile.gettempdir()) / "red-language-pack-sources"
        cache.mkdir(parents=True, exist_ok=True)
        supplied = cache / f"{revision}.tar.gz"
        if not supplied.exists():
            temporary = supplied.with_suffix(".download")
            try:
                with urllib.request.urlopen(archive_url(repository, revision), timeout=120) as source:
                    with temporary.open("wb") as output:
                        while chunk := source.read(1024 * 1024):
                            output.write(chunk)
                temporary.replace(supplied)
            finally:
                temporary.unlink(missing_ok=True)
    actual = file_digest(supplied)
    if actual.lower() != digest.lower():
        raise ValueError(f"source archive digest mismatch: expected {digest}, got {actual}")
    return supplied


@contextmanager
def extracted_archive(repository: str, revision: str, digest: str, supplied: Path | None) -> Iterator[Path]:
    archive = verified_archive(repository, revision, digest, supplied)
    with tempfile.TemporaryDirectory(prefix="red-language-pack-source-") as directory:
        destination = Path(directory)
        with tarfile.open(archive, "r:gz") as bundle:
            bundle.extractall(destination, filter="data")
        roots = list(destination.iterdir())
        if len(roots) != 1 or not roots[0].is_dir():
            raise ValueError("source archive must contain exactly one root directory")
        yield roots[0]


@contextmanager
def arborium_source(settings: dict, supplied: Path | None = None) -> Iterator[Path]:
    upstream = settings["upstream"]
    if supplied is None and (configured := os.environ.get("RED_ARBORIUM_ARCHIVE")):
        supplied = Path(configured)
    with extracted_archive(
        upstream["repository"],
        upstream["revision"],
        upstream["archive_sha256"],
        supplied,
    ) as source:
        yield source


def scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def block_values(lines: list[str], name: str) -> tuple[str, ...]:
    values: list[str] = []
    inside = False
    for line in lines:
        if re.fullmatch(rf"    {re.escape(name)}:\s*", line):
            inside = True
            continue
        if inside:
            match = re.match(r"      - ([^#\n]+?)(?:\s+#.*)?$", line)
            if match:
                values.append(scalar(match.group(1)))
                continue
            if line.strip() and len(line) - len(line.lstrip()) <= 4:
                break
    return tuple(values)


def parse_definition(path: Path) -> Definition:
    lines = path.read_text(encoding="utf-8").splitlines()
    top: dict[str, str] = {}
    grammar: dict[str, str] = {}
    for line in lines:
        if match := re.match(r"^(repo|commit|license):\s*(.*?)\s*$", line):
            top[match.group(1)] = scalar(match.group(2))
        elif match := re.match(r"  - id:\s*(.*?)\s*$", line):
            if "id" in grammar:
                raise ValueError(f"multiple grammar definitions are unsupported: {path}")
            grammar["id"] = scalar(match.group(1))
        elif match := re.match(r"    (name|tier|has_scanner):\s*(.*?)\s*$", line):
            grammar[match.group(1)] = scalar(match.group(2))
    identifier = grammar.get("id")
    if not identifier:
        raise ValueError(f"missing Arborium grammar identifier in {path}")
    tier = grammar.get("tier")
    dependencies = tuple(
        match.group(1)
        for line in lines
        if (match := re.match(r"          - crate:\s*arborium-([a-z0-9_-]+)\s*$", line))
    )
    directory = path.parent
    return Definition(
        identifier=identifier,
        name=grammar.get("name", identifier),
        repository=top.get("repo", ""),
        revision=top.get("commit", ""),
        license=top.get("license", ""),
        tier=int(tier) if tier and tier.isdigit() else None,
        has_scanner=grammar.get("has_scanner") == "true"
        or (directory / "grammar" / "scanner.c").is_file(),
        aliases=block_values(lines, "aliases"),
        declared_injections=block_values(lines, "injections"),
        query_dependencies=dependencies,
        directory=directory,
    )


def definitions(source: Path) -> dict[str, Definition]:
    result: dict[str, Definition] = {}
    for path in sorted(source.glob("langs/*/*/def/arborium.yaml")):
        definition = parse_definition(path)
        if definition.identifier in result:
            raise ValueError(f"duplicate Arborium grammar identifier: {definition.identifier}")
        result[definition.identifier] = definition
    if not result:
        raise ValueError("Arborium source contains no language definitions")
    return result


def eligibility(definition: Definition, settings: dict) -> list[str]:
    policy = settings["policy"]
    blockers = []
    if not REVISION.fullmatch(definition.revision):
        blockers.append("upstream grammar revision is not an immutable full commit")
    if not definition.repository.startswith("https://github.com/"):
        blockers.append("upstream grammar repository is not a supported GitHub HTTPS source")
    if definition.license not in policy["allowed_licenses"]:
        blockers.append(f"grammar license {definition.license!r} is not approved")
    if definition.tier is None or definition.tier > policy["maximum_quality_tier"]:
        blockers.append("Arborium quality tier requires additional review")
    if not definition.highlights.is_file():
        blockers.append("grammar has no Arborium highlighting query")
    return blockers


def injection_details(definition: Definition) -> tuple[list[str], list[str], bool]:
    if not definition.injections.is_file():
        return sorted(definition.declared_injections), [], False
    source = definition.injections.read_text(encoding="utf-8")
    languages = set(definition.declared_injections)
    languages.update(STATIC_INJECTION.findall(source))
    unsupported = sorted(
        {
            match.group(1) or "offset"
            for match in UNSUPPORTED_INJECTION.finditer(source)
        }
    )
    return sorted(languages), unsupported, "@injection.language" in source


def inventory(source: Path, settings: dict) -> dict:
    entries = []
    for definition in definitions(source).values():
        dependencies, unsupported, dynamic = injection_details(definition)
        blockers = eligibility(definition, settings)
        entries.append(
            {
                "id": definition.identifier,
                "name": definition.name,
                "repository": definition.repository,
                "revision": definition.revision,
                "license": definition.license,
                "quality_tier": definition.tier,
                "external_scanner": definition.has_scanner,
                "aliases": list(definition.aliases),
                "query_dependencies": list(definition.query_dependencies),
                "injected_languages": dependencies,
                "dynamic_injection_language": dynamic,
                "unsupported_injection_features": unsupported,
                "eligible": not blockers,
                "publication_blockers": blockers,
            }
        )
    entries.sort(key=lambda entry: entry["id"])
    return {
        "schema_version": 1,
        "upstream": {
            "repository": settings["upstream"]["repository"],
            "tag": settings["upstream"]["tag"],
            "revision": settings["upstream"]["revision"],
            "archive_sha256": settings["upstream"]["archive_sha256"],
        },
        "languages": entries,
    }


def compose_highlights(
    definition: Definition,
    all_definitions: dict[str, Definition],
    active: frozenset[str] = frozenset(),
) -> str:
    if definition.identifier in active:
        raise ValueError(f"circular Arborium query inheritance at {definition.identifier}")
    own = definition.highlights.read_text(encoding="utf-8").strip()
    parts = []
    for identifier in definition.query_dependencies:
        dependency = all_definitions.get(identifier)
        if dependency is None:
            raise ValueError(f"{definition.identifier} inherits unknown query {identifier}")
        inherited = compose_highlights(dependency, all_definitions, active | {definition.identifier})
        if inherited.strip() not in own and all(inherited.strip() not in part for part in parts):
            parts.append(inherited.strip())
    parts.append(own)
    return "\n\n".join(parts) + "\n"


def load_overlay(path: Path) -> dict:
    with path.open("rb") as handle:
        overlay = tomllib.load(handle)
    identifier = overlay.get("language", {}).get("id")
    if path.stem != identifier:
        raise ValueError(f"overlay filename and language identifier disagree: {path}")
    if source := overlay.get("source"):
        if not REVISION.fullmatch(source.get("revision", "")):
            raise ValueError(f"{identifier} source override requires a full Git commit")
        if not DIGEST.fullmatch(source.get("archive_sha256", "")):
            raise ValueError(f"{identifier} source override requires a SHA-256 archive digest")
        if not str(source.get("reason", "")).strip():
            raise ValueError(f"{identifier} source override requires a review reason")
    return overlay


def toml_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_manifest(overlay: dict, has_injections: bool) -> str:
    package = overlay["package"]
    language = overlay["language"]
    lsp = overlay["lsp"]
    identifier = language["id"]
    lines = ["schema_version = 1", "", "[plugin]"]
    for key in ("id", "name", "version", "red_api", "description"):
        lines.append(f"{key} = {toml_value(package[key])}")
    lines.extend(
        [
            'repository = "https://github.com/codersauce/red-language-packs"',
            f"license = {toml_value(package['license'])}",
            "",
            f"[languages.{identifier}]",
        ]
    )
    for key in ("extensions", "filenames", "aliases", "comment", "indent_width"):
        if key in language:
            lines.append(f"{key} = {toml_value(language[key])}")
    lines.extend(
        [
            "",
            f"[languages.{identifier}.grammar]",
            f'path = "grammars/{identifier}.so"',
            f"symbol = {toml_value(language['symbol'])}",
            "highlights = [",
            '    "queries/arborium-highlights.scm",',
            f"    {toml_value(language['highlight_overlay'])},",
            "]",
        ]
    )
    if has_injections:
        lines.append('injections = "queries/injections.scm"')
    lines.extend(["", f"[languages.{identifier}.lsp]"])
    for key in ("command", "args", "root_markers"):
        if key in lsp:
            lines.append(f"{key} = {toml_value(lsp[key])}")
    return "\n".join(lines) + "\n"


def render_catalog(overlay: dict) -> str:
    package = overlay["package"]
    lsp = overlay["lsp"]
    return (
        f"tier = {toml_value(package['catalog_tier'])}\n\n"
        "[[requirements]]\n"
        f"command = {toml_value(lsp['command'])}\n"
        f"purpose = {toml_value(lsp['purpose'])}\n"
        "optional = true\n"
    )


def check_or_write(path: Path, contents: str, check: bool) -> None:
    if check:
        if not path.is_file() or path.read_text(encoding="utf-8") != contents:
            raise ValueError(f"generated Arborium output is stale: {path.relative_to(ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def synchronize(source: Path, settings: dict, selected: list[str], check: bool) -> list[str]:
    all_definitions = definitions(source)
    overlays = sorted((ROOT / "arborium" / "languages").glob("*.toml"))
    if selected:
        requested = set(selected)
        overlays = [path for path in overlays if path.stem in requested]
        missing = requested - {path.stem for path in overlays}
        if missing:
            raise ValueError(f"no Red metadata overlay exists for: {', '.join(sorted(missing))}")
    updated = []
    for path in overlays:
        overlay = load_overlay(path)
        identifier = overlay["language"]["id"]
        definition = all_definitions.get(identifier)
        if definition is None:
            raise ValueError(f"Arborium does not define selected language {identifier}")
        if blockers := eligibility(definition, settings):
            raise ValueError(f"{identifier} cannot be published: {'; '.join(blockers)}")
        pack = ROOT / "packs" / identifier
        if not pack.is_dir():
            raise ValueError(f"reviewed pack directory does not exist: {pack}")
        query = compose_highlights(definition, all_definitions)
        overlay_path = pack / overlay["language"]["highlight_overlay"]
        if not overlay_path.is_file():
            raise ValueError(f"missing reviewed query overlay: {overlay_path}")
        captures = set(CAPTURE.findall(query + "\n" + overlay_path.read_text(encoding="utf-8")))
        missing = set(overlay["language"].get("minimum_capture_scopes", [])) - captures
        if missing:
            raise ValueError(f"{identifier} lost required highlight scopes: {', '.join(sorted(missing))}")
        check_or_write(pack / "queries" / "arborium-highlights.scm", query, check)
        if definition.injections.is_file():
            check_or_write(
                pack / "queries" / "injections.scm",
                definition.injections.read_text(encoding="utf-8"),
                check,
            )
        check_or_write(pack / "red-plugin.toml", render_manifest(overlay, definition.injections.is_file()), check)
        check_or_write(pack / "catalog.toml", render_catalog(overlay), check)
        updated.append(identifier)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="use an already-downloaded verified Arborium archive")
    commands = parser.add_subparsers(dest="command", required=True)
    inventory_parser = commands.add_parser("inventory", help="inventory every pinned Arborium language")
    inventory_parser.add_argument("--check", action="store_true")
    inventory_parser.add_argument("--output", type=Path, default=ROOT / "arborium" / "inventory.json")
    sync_parser = commands.add_parser("sync", help="generate reviewed independent language packs")
    sync_parser.add_argument("--check", action="store_true")
    sync_parser.add_argument("languages", nargs="*")
    args = parser.parse_args()
    try:
        settings = load_settings()
        with arborium_source(settings, args.archive) as source:
            if args.command == "inventory":
                contents = json.dumps(inventory(source, settings), indent=2, sort_keys=True) + "\n"
                check_or_write(args.output.resolve(), contents, args.check)
                print(f"{'verified' if args.check else 'generated'} {args.output}")
            else:
                languages = synchronize(source, settings, args.languages, args.check)
                print(f"{'verified' if args.check else 'generated'} {', '.join(languages)}")
        return 0
    except (OSError, ValueError, tarfile.TarError, tomllib.TOMLDecodeError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
