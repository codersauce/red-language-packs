# PHP for Red

PHP syntax highlighting, Composer project detection, and Intelephense integration.

## Install

```shell
red plugin install --catalog php-language
red language trust php
```

Native grammar approval is explicit and tied to the exact installed grammar digest. The optional `intelephense` language server is discovered on `PATH`; syntax highlighting works without it.

For local development:

```shell
python3 scripts/build_grammar.py php
red plugin install --path packs/php --trust-native-grammars
red packs/php/example/index.php
```

## Embedded languages

This grammar can highlight `phpdoc` when those languages are available in Red. Installing this pack never implicitly installs or approves another native grammar.

## Grammar provenance

- Upstream: <https://github.com/tree-sitter/tree-sitter-php>
- Immutable grammar revision: `7d07b41ce2d442ca9a90ed85d0075eccc17ae315`
- Grammar license: `MIT`
- Source: pinned Arborium grammar and highlighting queries

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.
