# Dockerfile for Red

Dockerfile and Containerfile syntax highlighting and Docker language server integration.

## Install

```shell
red plugin install --catalog dockerfile-language
red language trust dockerfile
```

Native grammar approval is explicit and tied to the exact installed grammar digest. The optional `docker-langserver` language server is discovered on `PATH`; syntax highlighting works without it.

The optional [dockerfmt](https://github.com/reteps/dockerfmt) formatter is launched through `dockerfmt` and receives the document on standard input. Install dockerfmt and ensure `dockerfmt` is available on `PATH`. Formatting is available through `Space f`; enable `formatting.on_save` to run it before writes.

For local development:

```shell
python3 scripts/build_grammar.py dockerfile
red plugin install --path packs/dockerfile --trust-native-grammars
red packs/dockerfile/example/Dockerfile
```

## Grammar provenance

- Upstream: <https://github.com/camdencheek/tree-sitter-dockerfile>
- Immutable grammar revision: `971acdd908568b4531b0ba28a445bf0bb720aba5`
- Grammar license: `MIT`
- Source: pinned Arborium grammar and highlighting queries

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.
