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

Add the pack slug to the validation matrices and tag filters in `.github/workflows`
as part of the same change.

## Review checklist

- The package ID and language IDs are stable and do not collide with an existing
  pack.
- Upstream grammar source and commit are explicit, immutable, and reflected in
  `THIRD_PARTY_NOTICES.md`.
- Arborium's archive and every source override have an exact SHA-256 digest;
  source overrides explain why the reviewed upstream source differs.
- Arborium's numeric quality tier is not confused with Red's `official` or
  `curated` package tier.
- Highlight queries have compatible licensing and useful coverage.
- Generated base queries preserve Red-owned overlays and required capture
  scopes; inherited queries are not duplicated.
- Builds use Tree-sitter CLI 0.25.10, generate ABI 15, verify the grammar's
  exported symbol, and include any required external scanner.
- Optional injected languages never silently install or approve another native
  grammar.
- Language-server commands, root markers, and optional requirements work on
  representative projects.
- Generated grammar binaries and build outputs are not committed.

## Releasing one pack

Set that pack's manifest version, merge the change, and push exactly one tag in
the form `<pack>/v<manifest-version>`. The serialized release workflow builds
target-specific archives, publishes an immutable GitHub release, merges the
new entry into the stable `catalog-v1` asset, and leaves every other pack at its
current version.
