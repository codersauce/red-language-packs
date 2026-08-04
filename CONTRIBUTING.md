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
- `build-grammar.sh` with immutable upstream revisions;
- `README.md`, `LICENSE`, and `THIRD_PARTY_NOTICES.md`;
- grammar queries and a representative example project.

Run the source checks and build before opening a pull request:

```shell
python3.13 scripts/validate_pack.py packs/<pack>
sh packs/<pack>/build-grammar.sh
python3.13 scripts/validate_pack.py packs/<pack>
```

Add the pack slug to the validation matrices and tag filters in `.github/workflows`
as part of the same change.

## Review checklist

- The package ID and language IDs are stable and do not collide with an existing
  pack.
- Upstream grammar source and commit are explicit, immutable, and reflected in
  `THIRD_PARTY_NOTICES.md`.
- Highlight queries have compatible licensing and useful coverage.
- Build scripts fetch only the pinned revision and fail on a mismatch.
- Language-server commands, root markers, and optional requirements work on
  representative projects.
- Generated grammar binaries and build outputs are not committed.

## Releasing one pack

Set that pack's manifest version, merge the change, and push exactly one tag in
the form `<pack>/v<manifest-version>`. The serialized release workflow builds
target-specific archives, publishes an immutable GitHub release, merges the
new entry into the stable `catalog-v1` asset, and leaves every other pack at its
current version.
