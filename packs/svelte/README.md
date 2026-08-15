# Svelte for Red

Svelte syntax highlighting, embedded JavaScript and CSS, and Svelte language server integration.

## Install

```shell
red plugin install --catalog svelte-language
red language trust svelte
```

Native grammar approval is explicit and tied to the exact installed grammar digest. The optional `svelteserver` language server is discovered on `PATH`; syntax highlighting works without it.

The optional [Prettier Svelte](https://github.com/sveltejs/prettier-plugin-svelte) formatter is launched through `prettier` and receives the document on standard input. Install Prettier and `prettier-plugin-svelte` in the project or globally. Formatting is available through `Space f`; enable `formatting.on_save` to run it before writes.

For local development:

```shell
python3 scripts/build_grammar.py svelte
red plugin install --path packs/svelte --trust-native-grammars
red packs/svelte/example/App.svelte
```

## Embedded languages

This grammar can highlight `css`, `javascript`, `scss`, `typescript` when those languages are available in Red. Installing this pack never implicitly installs or approves another native grammar.

## Grammar provenance

- Upstream: <https://github.com/tree-sitter-grammars/tree-sitter-svelte>
- Immutable grammar revision: `ae5199db47757f785e43a14b332118a5474de1a2`
- Grammar license: `MIT`
- Source: pinned Arborium grammar and highlighting queries

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.
