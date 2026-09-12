# Contributing a language pack

Each directory under `packs/` is an independently versioned Red language
package. A catalog entry means Red's maintainers have reviewed the package's
metadata, license, grammar provenance, pinned upstream revision, and release
build. It does not grant runtime trust to native grammar code; every user keeps
that approval boundary locally.

## Required files

A pack must contain:

- `red-plugin.toml` with one or more language definitions and no Husk entrypoint,
  native companion, activation hook, or keymap;
- `catalog.toml` with its review tier and external tool requirements;
- a reviewed source-only metadata overlay in `arborium/languages/<pack>.toml`;
- the shared `scripts/build_grammar.py` builder, with an optional POSIX wrapper;
- `README.md`, `LICENSE`, and `THIRD_PARTY_NOTICES.md`;
- grammar queries and a representative example project.

Run the source checks and build before opening a pull request:

```shell
python3 scripts/arborium.py inventory --check
python3 scripts/arborium.py sync --check
PYTHONPATH=scripts python3 -m unittest discover -s scripts/tests
python3.13 scripts/validate_pack.py packs/<pack>
python3.13 scripts/build_grammar.py <pack>
python3.13 scripts/validate_pack.py packs/<pack>
```

Validation matrices and release tags discover reviewed pack slugs directly from
`arborium/languages/`; adding a reviewed metadata file automatically includes its
independent grammar in every supported target build.

An Arborium definition with no quality tier remains blocked by default. A
reviewed overlay may opt into the narrow exception only when it includes an
exact, digest-pinned source override for the same repository and commit plus a
`[review]` rationale. This records Red's independent source review without
changing Arborium's upstream inventory or allowing low-rated grammars through.

## Review checklist

- The package ID and language IDs are stable and do not collide with an existing
  pack.
- Upstream grammar source and commit are explicit, immutable, and reflected in
  `THIRD_PARTY_NOTICES.md`.
- Arborium's archive and every source override have an exact SHA-256 digest;
  source overrides explain why the reviewed upstream source differs. Local source
  patches declare package-relative paths and SHA-256 digests, are applied only
  after source verification, and use LF line endings through `.gitattributes`.
- Sources outside Arborium explicitly use `source.kind = "standalone"` and
  receive a separate review of their repository, commit, digest, license, and
  grammar coverage. Do not invent an Arborium quality tier for these sources.
- Arborium's numeric quality tier is not confused with Red's `official` or
  `curated` package tier.
- Highlight queries have compatible licensing and useful coverage.
- Generated base queries preserve Red-owned overlays and required capture
  scopes; inherited queries are not duplicated.
- Builds use Tree-sitter CLI 0.25.10, generate ABI 15, verify the grammar's
  exported symbol, and include any required external scanner.
- Optional injected languages never silently install or approve another native
  grammar.
- Language-server commands, formatter commands, root markers, and optional
  requirements work on representative projects. Formatters must read the
  document from stdin and emit only the formatted document on stdout.
- Generated grammar binaries and build outputs are not committed.

## Standalone sources and companion grammars

Use a standalone source only when the pinned Arborium inventory does not supply
the grammar needed by the pack. Keep the metadata in
`arborium/languages/<pack>.toml` so discovery, validation, builds, and releases
continue to use the shared tooling. The `[source]` table must include:

```toml
[source]
kind = "standalone"
repository = "https://github.com/owner/tree-sitter-example"
revision = "<full lowercase 40-character Git commit>"
archive_sha256 = "<SHA-256 of the pinned GitHub source archive>"
reason = "Why this independently reviewed source is needed"
license = "MIT"
has_scanner = false
```

Supply representative sample source and upstream copyright notices alongside
the existing package and language metadata. `language.highlight_overlay` is
the complete reviewed runtime query for a standalone grammar. Synchronization
retains the original query as `queries/upstream-<language-id>-highlights.scm`
for provenance; the manifest does not load it. Declare a reviewed
`language.injections` query when the grammar needs embedded-language support.

Add `[[companions]]` entries for additional grammars shipped by the same pack.
Each companion has its own `[companions.language]`, `[companions.source]`,
`[companions.validation]`, and `[companions.provenance]` tables. It must satisfy
the same source review and validation requirements as the primary grammar.
An injection-only companion can omit filename and extension selectors. The
builder produces each grammar separately, and the manifest declares both
artifacts so installation and digest-bound trust cover them.

The `tmux` pack is the reference: the primary grammar recognizes only
`.tmux.conf`, `tmux.conf`, `.tmux.conf.local`, and `tmux.conf.local`; its `tmuxf`
companion handles embedded formats. Neither grammar declares an LSP or
formatter. Tool metadata is optional: omit the table and its catalog requirement
when the pack does not provide that capability.

For this pack, run:

```shell
python3 scripts/arborium.py sync tmux
PYTHONPATH=scripts python3 -m unittest discover -s scripts/tests
python3 scripts/build_grammar.py tmux
python3 scripts/validate_pack.py packs/tmux
python3 scripts/arborium.py sync tmux --check
```

Verify representative configuration files in Red after installing the local
pack, including filename detection, nested formats, edits and undo, comments,
and opening an unrelated `.conf` file. Record the runtime result separately from
source validation and grammar-query checks.

## Releasing one pack

Set that pack's manifest version, merge the change, and push exactly one tag in
the form `<pack>/v<manifest-version>`. The serialized release workflow builds
target-specific archives, publishes an immutable GitHub release, merges the
new entry into the stable `catalog-v1` asset, and leaves every other pack at its
current version.

## Indentation rules

Packs that provide indentation rules declare `language.indent_queries` in their
Arborium metadata and ship the corresponding Red-owned query files plus
`tests/indent.json`.
The importer preserves these files and emits `grammar.indents` in the manifest.
They require Red host API `^0.12.0`; release the compatible editor before
publishing these pack versions.

The tmux pack omits indentation queries and fixtures and keeps its host API
requirement at `^0.10.0`. Syntax-only packs can omit indentation metadata.

The grammar builder compiles the queries against the pinned native grammar.
After building, run the fixtures through the actual matching Red binary:

```shell
python3 scripts/check_indents.py packs/c --red /path/to/red
python3 scripts/check_indents.py --all --red /path/to/red
```

The runner uses disposable configuration and grammar-trust stores. It does not
change the developer's installed packs or trust decisions. Cover an opening
line, a closing delimiter, and relevant language-specific edge cases. Python
keeps Red's existing language-aware provider while its queries are migrated.
See Red's `docs/LANGUAGES.md` for the versioned query and fixture contract.
