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
from contextlib import ExitStack, contextmanager
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


def reviewed_eligibility(definition: Definition, settings: dict, overlay: dict) -> list[str]:
    """Apply the reviewed overlay exception for an otherwise unrated source.

    Arborium's quality tier remains authoritative for the upstream inventory.
    A pack may only clear an unset tier when its overlay explicitly documents a
    reviewed, digest-pinned source that is the same repository and revision as
    the Arborium definition. Higher-risk cases, such as a low-rated grammar or
    a source substitution, remain blocked by the normal policy.
    """
    blockers = eligibility(definition, settings)
    review = overlay.get("review", {})
    source = overlay.get("source", {})
    if (
        definition.tier is None
        and review.get("allow_unrated_arborium") is True
        and source.get("repository") == definition.repository
        and source.get("revision") == definition.revision
    ):
        blockers = [
            blocker
            for blocker in blockers
            if blocker != "Arborium quality tier requires additional review"
        ]
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


def source_query(overlay: dict, filename: str) -> str | None:
    """Read a query from a reviewed source override when one is declared."""
    source = overlay.get("source")
    if not source:
        return None
    with extracted_archive(
        source["repository"],
        source["revision"],
        source["archive_sha256"],
        None,
    ) as root:
        path = root / "queries" / filename
        if not path.is_file():
            raise ValueError(f"{source['repository']} source override has no queries/{filename}")
        return path.read_text(encoding="utf-8")


def grammar_overlays(overlay: dict) -> list[dict]:
    """Return the main grammar and explicitly reviewed companion grammars."""
    return [overlay, *overlay.get("companions", [])]


def is_standalone(overlay: dict) -> bool:
    return overlay.get("source", {}).get("kind") == "standalone"


def validate_source(overlay: dict, settings: dict) -> None:
    identifier = overlay["language"]["id"]
    source = overlay["source"]
    if source.get("kind", "override") not in {"override", "standalone"}:
        raise ValueError(f"{identifier} has an unknown grammar source kind")
    if not REVISION.fullmatch(source.get("revision", "")):
        raise ValueError(f"{identifier} source override requires a full Git commit")
    if not DIGEST.fullmatch(source.get("archive_sha256", "")):
        raise ValueError(f"{identifier} source override requires a SHA-256 archive digest")
    if not isinstance(source.get("reason"), str) or not source["reason"].strip():
        raise ValueError(f"{identifier} source override requires a review reason")
    archive_url(source.get("repository", ""), source["revision"])
    if is_standalone(overlay):
        if source.get("license") not in settings["policy"]["allowed_licenses"]:
            raise ValueError(f"{identifier} standalone source license is not approved")
        if not isinstance(source.get("has_scanner"), bool):
            raise ValueError(f"{identifier} standalone source must declare has_scanner")
    patches = source.get("patches", [])
    if not isinstance(patches, list):
        raise ValueError(f"{identifier} source patches must be a list")
    for patch in patches:
        if not isinstance(patch, dict) or not isinstance(patch.get("path"), str):
            raise ValueError(f"{identifier} source patch requires a path")
        pack_file(ROOT / "packs" / identifier, patch["path"])
        if not DIGEST.fullmatch(patch.get("sha256", "")):
            raise ValueError(f"{identifier} source patch requires a SHA-256 digest")


def standalone_definition(overlay: dict, source: Path, settings: dict) -> Definition:
    """Describe a verified standalone source without inventing an Arborium tier."""
    if not is_standalone(overlay):
        raise ValueError("standalone source requires explicit kind = 'standalone'")
    validate_source(overlay, settings)
    metadata = overlay["source"]
    language = overlay["language"]
    definition = Definition(
        identifier=language["id"],
        name=language.get("name", language["id"]),
        repository=metadata["repository"],
        revision=metadata["revision"],
        license=metadata["license"],
        tier=None,
        has_scanner=metadata["has_scanner"],
        aliases=tuple(language.get("aliases", [])),
        declared_injections=(),
        query_dependencies=(),
        directory=source,
    )
    if not definition.highlights.is_file():
        raise ValueError(f"{definition.identifier} standalone source has no highlighting query")
    if not (source / "grammar.js").is_file():
        raise ValueError(f"{definition.identifier} standalone source has no grammar.js")
    return definition


def validate_grammar_overlay(overlay: dict, settings: dict) -> None:
    identifier = overlay.get("language", {}).get("id")
    if not isinstance(identifier, str) or not re.fullmatch(r"[a-z][a-z0-9_-]*", identifier):
        raise ValueError("grammar overlay requires a valid language identifier")
    validation = overlay.get("validation", {})
    for relative in (
        overlay["language"].get("highlight_overlay"),
        overlay["language"].get("injections"),
        validation.get("sample"),
    ):
        if relative is not None:
            if not isinstance(relative, str):
                raise ValueError(f"{identifier} pack paths must be strings")
            pack_file(ROOT / "packs" / identifier, relative)
    if "source" in validation:
        copyright_lines = overlay.get("provenance", {}).get("copyright", [])
        if not copyright_lines or any(
            not isinstance(line, str) or not line.startswith("Copyright ")
            for line in copyright_lines
        ):
            raise ValueError(f"{identifier} generated pack requires reviewed upstream copyright notices")
        if not isinstance(validation["source"], str) or not validation["source"].strip():
            raise ValueError(f"{identifier} generated pack requires representative sample source")
        provenance = overlay["provenance"]
        if "query_repository" in provenance:
            if not REVISION.fullmatch(provenance.get("query_revision", "")):
                raise ValueError(f"{identifier} query provenance requires a pinned full Git commit")
            if provenance.get("query_license") not in {"Apache-2.0", "MIT"}:
                raise ValueError(f"{identifier} query provenance requires an approved explicit license")
            archive_url(provenance["query_repository"], provenance["query_revision"])
    if "source" in overlay:
        validate_source(overlay, settings)
    if is_standalone(overlay) and "source" not in validation:
        raise ValueError(f"{identifier} standalone source requires a representative sample source")
    if "lsp" in overlay:
        lsp = overlay["lsp"]
        if not isinstance(lsp, dict):
            raise ValueError(f"{identifier} lsp must be a metadata table")
        for field in ("command", "purpose"):
            if not isinstance(lsp.get(field), str) or not lsp[field].strip():
                raise ValueError(f"{identifier} lsp.{field} must be non-empty")
        for field in ("args", "root_markers"):
            values = lsp.get(field, [])
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                raise ValueError(f"{identifier} lsp.{field} must contain strings")
    if review := overlay.get("review"):
        if review.get("allow_unrated_arborium") is not True:
            raise ValueError(
                f"{identifier} reviewed Arborium exceptions must explicitly allow an unrated source"
            )
        if not str(review.get("reason", "")).strip():
            raise ValueError(f"{identifier} reviewed Arborium exceptions require a reason")
    formatter = overlay.get("formatter")
    if formatter is None:
        return
    if not isinstance(formatter, dict):
        raise ValueError(f"{identifier} formatter must be a metadata table")
    for field in ("name", "command", "purpose", "documentation", "setup"):
        if not isinstance(formatter.get(field), str) or not formatter[field].strip():
            raise ValueError(f"{identifier} formatter.{field} must be non-empty")
    if not isinstance(formatter.get("args", []), list) or not all(
        isinstance(argument, str) for argument in formatter.get("args", [])
    ):
        raise ValueError(f"{identifier} formatter.args must contain strings")
    if not isinstance(formatter.get("root_markers", []), list) or not all(
        isinstance(marker, str) and marker for marker in formatter.get("root_markers", [])
    ):
        raise ValueError(f"{identifier} formatter.root_markers must contain non-empty strings")


def load_overlay(path: Path) -> dict:
    with path.open("rb") as handle:
        overlay = tomllib.load(handle)
    if path.stem != overlay.get("language", {}).get("id"):
        raise ValueError(f"overlay filename and language identifier disagree: {path}")
    companions = overlay.get("companions", [])
    if not isinstance(companions, list) or any(not isinstance(item, dict) for item in companions):
        raise ValueError("companions must contain grammar metadata tables")
    if companions and not is_standalone(overlay):
        raise ValueError("companion grammars currently require a standalone package")
    identifiers = set()
    settings = load_settings()
    for grammar in grammar_overlays(overlay):
        validate_grammar_overlay(grammar, settings)
        identifier = grammar["language"]["id"]
        if identifier in identifiers:
            raise ValueError(f"duplicate grammar identifier {identifier}")
        identifiers.add(identifier)
    for companion in companions:
        if not is_standalone(companion):
            raise ValueError("companion grammar requires an explicit standalone source")
        if companion.get("companions"):
            raise ValueError("nested companion grammars are unsupported")
    return overlay


def toml_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_manifest(overlay: dict, has_injections: bool) -> str:
    package = overlay["package"]
    lines = ["schema_version = 1", "", "[plugin]"]
    for key in ("id", "name", "version", "red_api", "description"):
        lines.append(f"{key} = {toml_value(package[key])}")
    lines.extend(
        [
            'repository = "https://github.com/codersauce/red-language-packs"',
            f"license = {toml_value(package['license'])}",
        ]
    )
    for grammar in grammar_overlays(overlay):
        lines.extend(render_language(grammar, has_injections if grammar is overlay else False))
    return "\n".join(lines) + "\n"


def render_language(overlay: dict, has_injections: bool) -> list[str]:
    language = overlay["language"]
    identifier = language["id"]
    lines = ["", f"[languages.{identifier}]"]
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
        ]
    )
    if not is_standalone(overlay):
        lines.append('    "queries/arborium-highlights.scm",')
    lines.extend([f"    {toml_value(language['highlight_overlay'])},", "]"])
    if language.get("indent_queries"):
        lines.append(f"indents = {toml_value(language['indent_queries'])}")
    if is_standalone(overlay):
        if injections := language.get("injections"):
            lines.append(f"injections = {toml_value(injections)}")
    elif has_injections:
        lines.append('injections = "queries/injections.scm"')
    for kind, fields in (
        ("lsp", ("command", "args", "root_markers")),
        ("formatter", ("name", "command", "args", "root_markers")),
    ):
        if tool := overlay.get(kind):
            lines.extend(["", f"[languages.{identifier}.{kind}]"])
            for key in fields:
                if key in tool:
                    lines.append(f"{key} = {toml_value(tool[key])}")
    return lines


def render_catalog(overlay: dict) -> str:
    package = overlay["package"]
    requirements = []
    for grammar in grammar_overlays(overlay):
        for kind in ("lsp", "formatter"):
            if tool := grammar.get(kind):
                requirements.append(
                    "[[requirements]]\n"
                    f"command = {toml_value(tool['command'])}\n"
                    f"purpose = {toml_value(tool['purpose'])}\n"
                    "optional = true\n"
                )
    header = f"tier = {toml_value(package['catalog_tier'])}\n"
    return header + ("\n" + "\n".join(requirements) if requirements else "requirements = []\n")


def render_readme(overlay: dict, definition: Definition) -> str:
    if is_standalone(overlay):
        return render_standalone_readme(overlay)
    package = overlay["package"]
    language = overlay["language"]
    identifier = language["id"]
    lsp = overlay.get("lsp", {})
    formatter = overlay.get("formatter")
    source_description = (
        "reviewed direct grammar source and highlighting queries"
        if overlay.get("source")
        else "pinned Arborium grammar and highlighting queries"
    )
    lsp_name = lsp.get("name")
    if not lsp:
        lsp_description = "Syntax highlighting needs no language server.\n\n"
    elif lsp_name:
        lsp_description = (
            f"The optional [{lsp_name}]({lsp['documentation']}) language server is launched "
            f"through `{lsp['command']}`. {lsp['setup']} Syntax highlighting works without it.\n\n"
        )
    else:
        lsp_description = (
            f"The optional `{lsp['command']}` language server is discovered on `PATH`; syntax "
            "highlighting works without it.\n\n"
        )
    formatter_description = ""
    if formatter:
        formatter_description = (
            f"The optional [{formatter['name']}]({formatter['documentation']}) formatter is launched "
            f"through `{formatter['command']}` and receives the document on standard input. "
            f"{formatter['setup']} Formatting is available through `Space f`; enable "
            "`formatting.on_save` to run it before writes.\n\n"
        )
    injections, _, _ = injection_details(definition)
    embedded = ""
    if injections:
        names = ", ".join(f"`{name}`" for name in injections)
        embedded = (
            "\n## Embedded languages\n\n"
            f"This grammar can highlight {names} when those languages are available in Red. "
            "Installing this pack never implicitly installs or approves another native grammar.\n"
        )
    return (
        f"# {definition.name} for Red\n\n"
        f"{package['description']}.\n\n"
        "## Install\n\n"
        "```shell\n"
        f"red plugin install --catalog {package['id']}\n"
        f"red language trust {identifier}\n"
        "```\n\n"
        "Native grammar approval is explicit and tied to the exact installed grammar digest. "
        f"{lsp_description}"
        f"{formatter_description}"
        "For local development:\n\n"
        "```shell\n"
        f"python3 scripts/build_grammar.py {identifier}\n"
        f"red plugin install --path packs/{identifier} --trust-native-grammars\n"
        f"red packs/{identifier}/{overlay['validation']['sample']}\n"
        "```\n"
        f"{embedded}\n"
        "## Grammar provenance\n\n"
        f"- Upstream: <{definition.repository}>\n"
        f"- Immutable grammar revision: `{definition.revision}`\n"
        f"- Grammar license: `{definition.license}`\n"
        f"- Source: {source_description}\n\n"
        "See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.\n"
    )


def render_standalone_readme(overlay: dict) -> str:
    package = overlay["package"]
    grammars = grammar_overlays(overlay)
    identifier = overlay["language"]["id"]
    trust = "\n".join(f"red language trust {item['language']['id']}" for item in grammars)
    filenames = ", ".join(f"`{name}`" for name in overlay["language"].get("filenames", []))
    provenance = "\n".join(
        f"- `{item['language']['id']}`: <{item['source']['repository']}>, "
        f"revision `{item['source']['revision']}`, license `{item['source']['license']}`"
        for item in grammars
    )
    companion_text = ""
    if len(grammars) > 1:
        companions = ", ".join(f"`{item['language']['id']}`" for item in grammars[1:])
        companion_text = (
            "\n## Embedded languages\n\n"
            f"This package includes {companions} for embedded syntax. Each grammar has its "
            "own digest and trust decision. Companion grammars with empty filename and "
            "extension lists do not claim files automatically; they remain selectable in "
            "Red's language picker.\n"
        )
    tools = [item[kind] for item in grammars for kind in ("lsp", "formatter") if item.get(kind)]
    tool_text = "No language server or formatter is required.\n"
    if tools:
        tool_text = "Optional tools: " + "; ".join(
            f"`{tool['command']}` ({tool['purpose']})" for tool in tools
        ) + ".\n"
    return (
        f"# {overlay['language'].get('name', identifier)} for Red\n\n"
        f"{package['description']}.\n\n"
        f"Recognizes the exact filenames {filenames} in any directory. "
        "Other config files keep their existing language detection.\n\n"
        "## Install\n\n```shell\n"
        f"red plugin install --catalog {package['id']}\n{trust}\n```\n\n"
        "Native grammar approval is tied to each installed grammar's exact digest. "
        f"{tool_text}\n"
        "For local development, with Tree-sitter CLI 0.25.10 on PATH or in `TREE_SITTER`:\n\n"
        "```shell\n"
        f"python3 scripts/build_grammar.py {identifier}\n"
        f"red plugin install --path packs/{identifier} --trust-native-grammars\n"
        f"red packs/{identifier}/{overlay['validation']['sample']}\n```\n"
        f"{companion_text}\n"
        "## Grammar provenance\n\n"
        f"{provenance}\n\n"
        "The sources are pinned and SHA-256 verified independently of Arborium. "
        "The source checkout retains original queries in `queries/upstream-*-highlights.scm` for review; "
        "the manifest loads only the separately reviewed Red query files.\n\n"
        "See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.\n"
        + ("\n" + overlay["documentation"]["notes"].rstrip() + "\n" if overlay.get("documentation", {}).get("notes") else "")
    )


def render_license(copyright_lines: list[str]) -> str:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    marker = "\n\nPermission is hereby granted"
    _, separator, permissions = license_text.partition(marker)
    if not separator:
        raise ValueError("repository MIT license does not contain the expected permission text")
    attribution = "\n".join(copyright_lines)
    return f"MIT License\n\n{attribution}{separator}{permissions}"


def render_notices(
    overlay: dict,
    definition: Definition,
    all_definitions: dict[str, Definition],
    settings: dict,
    source: Path,
) -> str:
    entries: list[tuple[Definition, dict]] = [(definition, overlay)]
    seen = {definition.identifier}
    pending = list(definition.query_dependencies)
    while pending:
        identifier = pending.pop(0)
        if identifier in seen:
            continue
        dependency = all_definitions[identifier]
        dependency_overlay = load_overlay(ROOT / "arborium" / "languages" / f"{identifier}.toml")
        entries.append((dependency, dependency_overlay))
        seen.add(identifier)
        pending.extend(dependency.query_dependencies)

    sections = ["# Third-party notices\n"]
    for item, item_overlay in entries:
        sections.append(
            f"## {item.name} Tree-sitter grammar and highlighting queries\n\n"
            f"- Project: <{item.repository}>\n"
            f"- Revision: `{item.revision}`\n"
            f"- License: `{item.license}`\n\n"
            "```text\n"
            f"{render_license(item_overlay['provenance']['copyright']).rstrip()}\n"
            "```\n"
        )
        if repository := item_overlay["provenance"].get("query_repository"):
            provenance = item_overlay["provenance"]
            if provenance["query_license"] == "Apache-2.0":
                apache = (source / "LICENSE-APACHE").read_text(encoding="utf-8")
                terms, marker, _ = apache.partition("\nEND OF TERMS AND CONDITIONS")
                if not marker:
                    raise ValueError("Arborium Apache license does not contain its complete terms")
                query_license = f"{terms}{marker}\n"
            else:
                query_license = render_license(provenance["copyright"])
            sections.append(
                f"## {item.name} highlighting query source\n\n"
                f"- Project: <{repository}>\n"
                f"- Revision: `{provenance['query_revision']}`\n"
                f"- License: `{provenance['query_license']}`\n\n"
                "```text\n"
                f"{query_license.rstrip()}\n"
                "```\n"
            )
    upstream = settings["upstream"]
    arborium_license = (source / "LICENSE-MIT").read_text(encoding="utf-8")
    sections.append(
        "## Arborium grammar and query curation\n\n"
        f"- Project: <{upstream['repository']}>\n"
        f"- Revision: `{upstream['revision']}`\n"
        "- License: `MIT OR Apache-2.0`; distributed here under MIT\n\n"
        "```text\n"
        f"{arborium_license.rstrip()}\n"
        "```\n"
    )
    return "\n".join(sections)


def generated_scaffold(
    pack: Path,
    overlay: dict,
    definition: Definition,
    all_definitions: dict[str, Definition],
    settings: dict,
    source: Path,
    check: bool,
) -> None:
    identifier = definition.identifier
    query_overlay = (
        f"; Red-owned {definition.name} highlighting refinements.\n"
        "; Arborium supplies the reviewed base query; add Red-specific overrides here.\n"
    )
    wrapper = (
        "#!/usr/bin/env sh\n\n"
        "set -eu\n\n"
        'repository_directory=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)\n'
        f'exec python3 "$repository_directory/scripts/build_grammar.py" {identifier} "$@"\n'
    )
    generated_files = {
        ".gitignore": f"/grammars/{identifier}.so\n",
        "README.md": render_readme(overlay, definition),
        "LICENSE": (ROOT / "LICENSE").read_text(encoding="utf-8"),
        "THIRD_PARTY_NOTICES.md": render_notices(
            overlay, definition, all_definitions, settings, source
        ),
        "build-grammar.sh": wrapper,
        overlay["validation"]["sample"]: overlay["validation"]["source"],
    }
    for relative, contents in generated_files.items():
        check_or_write(pack / relative, contents, check)
    scaffold_owned_file(pack / overlay["language"]["highlight_overlay"], query_overlay, check)


def reviewed_languages() -> list[str]:
    paths = sorted((ROOT / "arborium" / "languages").glob("*.toml"), key=lambda path: path.stem)
    owners: dict[str, str] = {}
    for path in paths:
        overlay = load_overlay(path)
        for grammar in grammar_overlays(overlay):
            identifier = grammar["language"]["id"]
            if identifier in owners:
                raise ValueError(
                    f"grammar identifier {identifier} is declared by both "
                    f"{owners[identifier]} and {path.stem} packages"
                )
            owners[identifier] = path.stem
    return [path.stem for path in paths]


def check_or_write(path: Path, contents: str, check: bool) -> None:
    if check:
        if not path.is_file() or path.read_text(encoding="utf-8") != contents:
            raise ValueError(f"generated Arborium output is stale: {path.relative_to(ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def scaffold_owned_file(path: Path, contents: str, check: bool) -> None:
    """Create a maintainer-owned scaffold once without replacing reviewed edits."""
    if path.is_file():
        return
    if check:
        raise ValueError(f"reviewed Arborium output is missing: {path.relative_to(ROOT)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def pack_file(pack: Path, relative: str) -> Path:
    """Keep metadata-selected outputs inside their own package."""
    path = Path(relative)
    if not relative or path.is_absolute() or ".." in path.parts or "\\" in relative:
        raise ValueError(f"pack file must be a safe relative path: {relative}")
    result = pack / path
    if not result.resolve().is_relative_to(pack.resolve()):
        raise ValueError(f"pack file escapes its package: {relative}")
    return result


def source_patch_paths(overlay: dict, pack: Path) -> list[Path]:
    """Verify every reviewed patch before the builder applies any of them."""
    result = []
    for patch in overlay.get("source", {}).get("patches", []):
        path = pack_file(pack, patch["path"])
        if file_digest(path) != patch["sha256"]:
            raise ValueError(f"source patch digest mismatch: {patch['path']}")
        result.append(path)
    return result


def standalone_notices(grammars: list[tuple[dict, Definition]]) -> str:
    sections = ["# Third-party notices\n"]
    for overlay, definition in grammars:
        license_path = definition.directory / "LICENSE"
        if not license_path.is_file():
            raise ValueError(f"{definition.identifier} standalone source has no LICENSE")
        source = overlay["source"]
        patches = "".join(
            f"- Reviewed local patch: `{patch['path']}`, SHA-256 `{patch['sha256']}`\n"
            for patch in source.get("patches", [])
        )
        sections.append(
            f"## {definition.name} grammar and adapted highlighting queries\n\n"
            f"- Project: <{definition.repository}>\n"
            f"- Revision: `{definition.revision}`\n"
            f"- Source archive SHA-256: `{source['archive_sha256']}`\n"
            f"- License: `{definition.license}`\n"
            f"- Source review: {source['reason']}\n"
            f"{patches}\n"
            "```text\n"
            f"{license_path.read_text(encoding='utf-8').rstrip()}\n"
            "```\n"
        )
    return "\n".join(sections)


def synchronize_standalone(overlay: dict, settings: dict, check: bool) -> None:
    """Generate one package from explicitly reviewed, digest-verified sources."""
    identifier = overlay["language"]["id"]
    pack = ROOT / "packs" / identifier
    with ExitStack() as stack:
        grammars = []
        for item in grammar_overlays(overlay):
            source_patch_paths(item, pack)
            source = item["source"]
            directory = stack.enter_context(extracted_archive(
                source["repository"], source["revision"], source["archive_sha256"], None
            ))
            definition = standalone_definition(item, directory, settings)
            grammars.append((item, definition))
        wrapper = (
            "#!/usr/bin/env sh\n\nset -eu\n\n"
            'repository_directory=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)\n'
            f'exec python3 "$repository_directory/scripts/build_grammar.py" {identifier} "$@"\n'
        )
        generated = {
            ".gitignore": "".join(f"/grammars/{item.identifier}.so\n" for _, item in grammars),
            "red-plugin.toml": render_manifest(overlay, False),
            "catalog.toml": render_catalog(overlay),
            "README.md": render_standalone_readme(overlay),
            "LICENSE": (ROOT / "LICENSE").read_text(encoding="utf-8"),
            "THIRD_PARTY_NOTICES.md": standalone_notices(grammars),
            "build-grammar.sh": wrapper,
        }
        for item, definition in grammars:
            language = item["language"]
            sample = item["validation"]
            generated[sample["sample"]] = sample["source"]
            generated[f"queries/upstream-{definition.identifier}-highlights.scm"] = (
                definition.highlights.read_text(encoding="utf-8")
            )
            reviewed = pack_file(pack, language["highlight_overlay"])
            scaffold_owned_file(
                reviewed,
                f"; Reviewed {definition.name} query for Red. Original upstream query is retained separately.\n",
                check,
            )
            captures = set(CAPTURE.findall(reviewed.read_text(encoding="utf-8")))
            missing = set(language.get("minimum_capture_scopes", [])) - captures
            if missing:
                raise ValueError(f"{definition.identifier} lost required highlight scopes: {', '.join(sorted(missing))}")
            if injections := language.get("injections"):
                if not pack_file(pack, injections).is_file():
                    raise ValueError(f"{definition.identifier} is missing reviewed injection queries")
        for relative, contents in generated.items():
            check_or_write(pack_file(pack, relative), contents, check)


def synchronize(source: Path, settings: dict, selected: list[str], check: bool) -> list[str]:
    reviewed_languages()
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
        if is_standalone(overlay):
            synchronize_standalone(overlay, settings, check)
            updated.append(identifier)
            continue
        definition = all_definitions.get(identifier)
        if definition is None:
            raise ValueError(f"Arborium does not define selected language {identifier}")
        if blockers := reviewed_eligibility(definition, settings, overlay):
            raise ValueError(f"{identifier} cannot be published: {'; '.join(blockers)}")
        pack = ROOT / "packs" / identifier
        if "source" in overlay["validation"]:
            generated_scaffold(pack, overlay, definition, all_definitions, settings, source, check)
        if not pack.is_dir():
            raise ValueError(f"reviewed pack directory does not exist: {pack}")
        query = source_query(overlay, "highlights.scm") or compose_highlights(
            definition, all_definitions
        )
        overlay_path = pack / overlay["language"]["highlight_overlay"]
        if not overlay_path.is_file():
            raise ValueError(f"missing reviewed query overlay: {overlay_path}")
        captures = set(CAPTURE.findall(query + "\n" + overlay_path.read_text(encoding="utf-8")))
        missing = set(overlay["language"].get("minimum_capture_scopes", [])) - captures
        if missing:
            raise ValueError(f"{identifier} lost required highlight scopes: {', '.join(sorted(missing))}")
        for raw in overlay["language"].get("indent_queries", []):
            relative = Path(raw)
            if relative.is_absolute() or ".." in relative.parts or not (pack / relative).is_file():
                raise ValueError(f"{identifier} has a missing or unsafe indentation query: {raw}")
        check_or_write(pack / "queries" / "arborium-highlights.scm", query, check)
        if injection_query := source_query(overlay, "injections.scm"):
            check_or_write(pack / "queries" / "injections.scm", injection_query, check)
        elif definition.injections.is_file():
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
    list_parser = commands.add_parser("list", help="list explicitly reviewed Red language packs")
    list_parser.add_argument("--json", action="store_true", help="emit a JSON array")
    args = parser.parse_args()
    try:
        settings = load_settings()
        if args.command == "list":
            languages = reviewed_languages()
            print(json.dumps(languages) if args.json else "\n".join(languages))
            return 0
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
