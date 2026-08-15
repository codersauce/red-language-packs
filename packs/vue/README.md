# Vue for Red

Vue single-file component highlighting, embedded JavaScript and CSS, and Vue language server integration.

## Install

```shell
red plugin install --catalog vue-language
red language trust vue
```

Native grammar approval is explicit and tied to the exact installed grammar digest. The optional `vue-language-server` language server is discovered on `PATH`; syntax highlighting works without it.

The optional [Prettier](https://prettier.io/docs/cli/) formatter is launched through `prettier` and receives the document on standard input. Install Prettier locally or globally so `prettier` is available. Formatting is available through `Space f`; enable `formatting.on_save` to run it before writes.

For local development:

```shell
python3 scripts/build_grammar.py vue
red plugin install --path packs/vue --trust-native-grammars
red packs/vue/example/App.vue
```

## Embedded languages

This grammar can highlight `css`, `javascript`, `scss`, `typescript` when those languages are available in Red. Installing this pack never implicitly installs or approves another native grammar.

## Grammar provenance

- Upstream: <https://github.com/tree-sitter-grammars/tree-sitter-vue>
- Immutable grammar revision: `22bdfa6c9fc0f5ffa44c6e938ec46869ac8a99ff`
- Grammar license: `MIT`
- Source: pinned Arborium grammar and highlighting queries

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.
