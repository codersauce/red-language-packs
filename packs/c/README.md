# C for Red

C syntax highlighting, project detection, and clangd integration.

## Install

```shell
red plugin install --catalog c-language
red language trust c
```

Native grammar approval is explicit and tied to the exact installed grammar digest. The optional `clangd` language server is discovered on `PATH`; syntax highlighting works without it.

The optional [clang-format](https://clang.llvm.org/docs/ClangFormat.html) formatter is launched through `clang-format` and receives the document on standard input. Install clang-format and ensure `clang-format` is available on `PATH`. Formatting is available through `Space f`; enable `formatting.on_save` to run it before writes.

For local development:

```shell
python3 scripts/build_grammar.py c
red plugin install --path packs/c --trust-native-grammars
red packs/c/example/main.c
```

## Grammar provenance

- Upstream: <https://github.com/tree-sitter/tree-sitter-c>
- Immutable grammar revision: `ae19b676b13bdcc13b7665397e6d9b14975473dd`
- Grammar license: `MIT`
- Source: pinned Arborium grammar and highlighting queries

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.
