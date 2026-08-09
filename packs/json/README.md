# JSON for Red

JSON and JSONC syntax highlighting and JSON language server integration.

## Install

```shell
red plugin install --catalog json-language
red language trust json
```

Native grammar approval is explicit and tied to the exact installed grammar digest. The optional `vscode-json-language-server` language server is discovered on `PATH`; syntax highlighting works without it.

For local development:

```shell
python3 scripts/build_grammar.py json
red plugin install --path packs/json --trust-native-grammars
red packs/json/example/settings.jsonc
```

## Grammar provenance

- Upstream: <https://github.com/tree-sitter/tree-sitter-json>
- Immutable grammar revision: `001c28d7a29832b06b0e831ec77845553c89b56d`
- Grammar license: `MIT`
- Source: pinned Arborium grammar and highlighting queries

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.
