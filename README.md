# Red language packs

Official language packs for the [Red editor](https://github.com/codersauce/red).

This repository is the shared authoring and release home. Every directory under
`packs/` remains an independent Red package with its own manifest, version, release,
installation state, and native-grammar approval boundary.

## Packs

- `packs/go` — Tree-sitter Go highlighting and gopls integration.
- `packs/swift` — Tree-sitter Swift highlighting and SourceKit-LSP integration.

Browse the published catalog with `red plugin catalog`, or install a pack by
its stable ID:

```shell
red plugin install --catalog go-language
red plugin install --catalog swift-language
```

Native grammar approval remains a separate, digest-bound user decision. Add
`--trust-native-grammars` only when you intend to load the verified grammar
bytes in Red's process.

## Development

Build a pack's pinned grammar, then install that checkout with Red:

```shell
sh packs/go/build-grammar.sh
red plugin install --path packs/go --trust-native-grammars
```

Use `scripts/validate_pack.py packs/go` to validate source metadata and
`scripts/package_release.py` to assemble the deterministic, target-specific bundle
consumed by Red's curated catalog. See [CONTRIBUTING.md](CONTRIBUTING.md) for
the pack contract and review checklist.

## Releases

Packs are released independently with tags such as `go/v0.1.0` and
`swift/v0.1.0`. The release workflow publishes one package bundle per runner target
and refreshes the `catalog-v1` release asset used by Red.
