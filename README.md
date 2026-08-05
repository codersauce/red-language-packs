# Red language packs

Official language packs for the [Red editor](https://github.com/codersauce/red).

This repository is the shared authoring and release home. Every directory under
`packs/` remains an independent Red package with its own manifest, version, release,
installation state, and native-grammar approval boundary.

## Packs

- `packs/c` — C highlighting and clangd integration.
- `packs/c-sharp` — C# highlighting and C# language server integration.
- `packs/cpp` — C++ highlighting, inherited C queries, and clangd integration.
- `packs/css` — CSS highlighting and CSS language server integration.
- `packs/dockerfile` — Dockerfile and Containerfile highlighting.
- `packs/go` — Go highlighting and gopls integration.
- `packs/html` — HTML highlighting with embedded CSS and JavaScript.
- `packs/java` — Java highlighting and JDTLS integration.
- `packs/kotlin` — Kotlin highlighting and Kotlin language server integration.
- `packs/php` — PHP highlighting and Intelephense integration.
- `packs/sql` — SQL highlighting and SQL language server integration.
- `packs/svelte` — Svelte highlighting with embedded scripts and styles.
- `packs/swift` — Swift highlighting and SourceKit-LSP integration.
- `packs/vue` — Vue single-file component highlighting and Vue language server integration.

Browse the published catalog with `red plugin catalog`, or install a pack by
its stable ID:

```shell
red plugin install --catalog go-language
red plugin install --catalog html-language
red plugin install --catalog swift-language
```

Native grammar approval remains a separate, digest-bound user decision. Add
`--trust-native-grammars` only when you intend to load the verified grammar
bytes in Red's process.

## Development

Arborium is a pinned, digest-verified build-time grammar and query source. It
is never installed as one aggregate runtime package. Red-owned metadata under
`arborium/languages/` controls each pack's identity, selectors, comments,
language-server command, reviewed query overlays, and any justified upstream
source override.

Inspect the complete upstream inventory and regenerate the reviewed packs:

```shell
python3 scripts/arborium.py inventory
python3 scripts/arborium.py sync
python3 scripts/arborium.py list
python3 scripts/validate_pack.py --all
```

Only languages with an explicit Red metadata overlay are generated. The importer
rejects unpinned upstream sources, licenses outside the allowlist, immature
quality tiers, missing reviewed metadata, and regressions in required highlight
captures. It also records optional injected-language dependencies and unsupported
injection-query features without implicitly installing another grammar. Adding a
reviewed metadata overlay scaffolds its manifest, catalog metadata, provenance,
example, query overlay, and documentation without changing another pack.

Build a pack's pinned ABI-15 grammar with Tree-sitter CLI 0.25.10, then install
that checkout with Red:

```shell
python3 scripts/build_grammar.py go
red plugin install --path packs/go --trust-native-grammars
```

Use `scripts/validate_pack.py packs/go` to validate source metadata and
`scripts/package_release.py` to assemble the deterministic, target-specific bundle
consumed by Red's curated catalog. See [CONTRIBUTING.md](CONTRIBUTING.md) for
the pack contract and review checklist.

Every language server is optional and discovered on `PATH`: for example, Go
uses `gopls`, Swift uses its toolchain-provided `sourcekit-lsp`, and C/C++ share
`clangd`. Language servers are never downloaded or bundled with grammar packages.

## Releases

Packs are released independently with tags such as `go/v0.1.0` and
`swift/v0.1.0`. The release workflow publishes one package bundle per runner target
and refreshes the `catalog-v1` release asset used by Red.
