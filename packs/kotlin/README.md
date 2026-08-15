# Kotlin for Red

Kotlin syntax highlighting, Gradle project detection, and Kotlin language server integration.

## Install

```shell
red plugin install --catalog kotlin-language
red language trust kotlin
```

Native grammar approval is explicit and tied to the exact installed grammar digest. The optional `kotlin-language-server` language server is discovered on `PATH`; syntax highlighting works without it.

The optional [ktlint](https://ktlint.github.io/ktlint/latest/install/cli/) formatter is launched through `ktlint` and receives the document on standard input. Install ktlint and ensure `ktlint` is available on `PATH`. Formatting is available through `Space f`; enable `formatting.on_save` to run it before writes.

For local development:

```shell
python3 scripts/build_grammar.py kotlin
red plugin install --path packs/kotlin --trust-native-grammars
red packs/kotlin/example/Main.kt
```

## Grammar provenance

- Upstream: <https://github.com/fwcd/tree-sitter-kotlin>
- Immutable grammar revision: `57fb4560ba8641865bc0baa6b3f413b236112c4c`
- Grammar license: `MIT`
- Source: pinned Arborium grammar and highlighting queries

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.
