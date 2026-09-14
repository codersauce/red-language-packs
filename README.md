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
- `packs/json` — JSON and JSONC highlighting and JSON language server integration.
- `packs/kotlin` — Kotlin highlighting and Kotlin language server integration.
- `packs/php` — PHP highlighting and Intelephense integration.
- `packs/powershell` — PowerShell highlighting and PowerShell Editor Services integration.
- `packs/python` — Python and type-stub highlighting with Pyright integration.
- `packs/sql` — SQL highlighting and SQL language server integration.
- `packs/svelte` — Svelte highlighting with embedded scripts and styles.
- `packs/swift` — Swift highlighting and SourceKit-LSP integration.
- `packs/tmux` — tmux configuration and embedded format-string highlighting.
- `packs/vue` — Vue single-file component highlighting and Vue language server integration.
- `packs/zig` — Zig highlighting, ZLS integration, and `zig fmt` formatting.

Browse the published catalog with `red plugin catalog`, or install a pack by
its stable ID:

```shell
red plugin install --catalog go-language
red plugin install --catalog html-language
red plugin install --catalog powershell-language
red plugin install --catalog python-language
red plugin install --catalog swift-language
red plugin install --catalog zig-language
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

A grammar absent from the pinned Arborium inventory can use an explicit
`source.kind = "standalone"` overlay. Standalone sources must pin their own
repository, commit, archive digest, license, and review reason. They have no
Arborium quality tier. A pack can include companion grammars when its embedded
language needs a separate parser; every companion has its own reviewed source
and native grammar artifact.

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

Every language server is optional and launched through a command discovered on
`PATH`: for example, Go uses `gopls`, Swift uses its toolchain-provided
`sourcekit-lsp`, C/C++ share `clangd`, and PowerShell Editor Services runs as a
module through `pwsh`. Language servers are never downloaded or bundled with
grammar packages.

### tmux

The tmux pack contains two grammars: `tmux` for configuration commands and
`tmuxf` for embedded format strings. It recognizes the exact basenames
`.tmux.conf`, `tmux.conf`, `.tmux.conf.local`, and `tmux.conf.local`, including
`~/.config/tmux/tmux.conf`. Other `.conf` files keep their existing detection.
The pack provides syntax highlighting and `#` comments without a language server
or formatter.

Build and install both grammars from this checkout:

```shell
python3 scripts/arborium.py sync tmux
python3 scripts/build_grammar.py tmux
python3 scripts/validate_pack.py packs/tmux
red plugin install --path packs/tmux --trust-native-grammars
red packs/tmux/example/.tmux.conf
```

The source lock pins the MIT-licensed `Freed-Wu/tree-sitter-tmux` and
`Freed-Wu/tree-sitter-tmuxf` repositories independently. Runtime highlighting
uses reviewed Red queries; the original upstream highlight queries remain in
the package for provenance. See [the tmux pack](packs/tmux/README.md) for the
source revisions and supported syntax.

## Indentation

Packs with Red indentation queries include portable regression fixtures.
See [CONTRIBUTING.md](CONTRIBUTING.md#indentation-rules) for the query workflow
and end-to-end checks. These pack versions require Red host API 0.12.0.
The tmux pack has no indentation queries and remains compatible with host API
0.10.0.

## Releases

Packs are released independently with tags such as `go/v0.1.0` and
`swift/v0.1.0`. The release workflow publishes one package bundle per runner target
and refreshes the `catalog-v1` release asset used by Red.
