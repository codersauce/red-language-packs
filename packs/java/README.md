# Java for Red

Java syntax highlighting, Maven and Gradle project detection, and JDTLS integration.

## Install

```shell
red plugin install --catalog java-language
red language trust java
```

Native grammar approval is explicit and tied to the exact installed grammar digest. The optional `jdtls` language server is discovered on `PATH`; syntax highlighting works without it.

The optional [google-java-format](https://github.com/google/google-java-format) formatter is launched through `google-java-format` and receives the document on standard input. Install google-java-format and ensure `google-java-format` is available on `PATH`. Formatting is available through `Space f`; enable `formatting.on_save` to run it before writes.

For local development:

```shell
python3 scripts/build_grammar.py java
red plugin install --path packs/java --trust-native-grammars
red packs/java/example/Greeter.java
```

## Grammar provenance

- Upstream: <https://github.com/tree-sitter/tree-sitter-java>
- Immutable grammar revision: `e10607b45ff745f5f876bfa3e94fbcc6b44bdc11`
- Grammar license: `MIT`
- Source: pinned Arborium grammar and highlighting queries

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.
