# HTML for Red

HTML syntax highlighting, embedded CSS and JavaScript, and HTML language server integration.

## Install

```shell
red plugin install --catalog html-language
red language trust html
```

Native grammar approval is explicit and tied to the exact installed grammar digest. The optional `vscode-html-language-server` language server is discovered on `PATH`; syntax highlighting works without it.

The optional [Prettier](https://prettier.io/docs/cli/) formatter is launched through `prettier` and receives the document on standard input. Install Prettier locally or globally so `prettier` is available. Formatting is available through `Space f`; enable `formatting.on_save` to run it before writes.

For local development:

```shell
python3 scripts/build_grammar.py html
red plugin install --path packs/html --trust-native-grammars
red packs/html/example/index.html
```

## Embedded languages

This grammar can highlight `css`, `javascript` when those languages are available in Red. Installing this pack never implicitly installs or approves another native grammar.

## Grammar provenance

- Upstream: <https://github.com/tree-sitter/tree-sitter-html>
- Immutable grammar revision: `73a3947324f6efddf9e17c0ea58d454843590cc0`
- Grammar license: `MIT`
- Source: pinned Arborium grammar and highlighting queries

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.
