# CSS for Red

CSS syntax highlighting, selector support, and CSS language server integration.

## Install

```shell
red plugin install --catalog css-language
red language trust css
```

Native grammar approval is explicit and tied to the exact installed grammar digest. The optional `vscode-css-language-server` language server is discovered on `PATH`; syntax highlighting works without it.

For local development:

```shell
python3 scripts/build_grammar.py css
red plugin install --path packs/css --trust-native-grammars
red packs/css/example/styles.css
```

## Grammar provenance

- Upstream: <https://github.com/tree-sitter/tree-sitter-css>
- Immutable grammar revision: `dda5cfc5722c429eaba1c910ca32c2c0c5bb1a3f`
- Grammar license: `MIT`
- Source: pinned Arborium grammar and highlighting queries

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.
