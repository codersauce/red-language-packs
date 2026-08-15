# C++ for Red

C++ syntax highlighting, inherited C queries, and clangd integration.

## Install

```shell
red plugin install --catalog cpp-language
red language trust cpp
```

Native grammar approval is explicit and tied to the exact installed grammar digest. The optional `clangd` language server is discovered on `PATH`; syntax highlighting works without it.

The optional [clang-format](https://clang.llvm.org/docs/ClangFormat.html) formatter is launched through `clang-format` and receives the document on standard input. Install clang-format and ensure `clang-format` is available on `PATH`. Formatting is available through `Space f`; enable `formatting.on_save` to run it before writes.

For local development:

```shell
python3 scripts/build_grammar.py cpp
red plugin install --path packs/cpp --trust-native-grammars
red packs/cpp/example/main.cpp
```

## Grammar provenance

- Upstream: <https://github.com/tree-sitter/tree-sitter-cpp>
- Immutable grammar revision: `12bd6f7e96080d2e70ec51d4068f2f66120dde35`
- Grammar license: `MIT`
- Source: pinned Arborium grammar and highlighting queries

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.
