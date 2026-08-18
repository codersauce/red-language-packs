# Zig for Red

Zig syntax highlighting, ZLS integration, and zig fmt formatting.

## Install

```shell
red plugin install --catalog zig-language
red language trust zig
```

Native grammar approval is explicit and tied to the exact installed grammar digest. The optional [Zig Language Server](https://github.com/zigtools/zls) language server is launched through `zls`. Install a ZLS release compatible with your Zig toolchain and ensure `zls` is available on `PATH`. Syntax highlighting works without it.

The optional [zig fmt](https://ziglang.org/documentation/master/) formatter is launched through `zig` and receives the document on standard input. Install Zig and ensure `zig` is available on `PATH`. Formatting is available through `Space f`; enable `formatting.on_save` to run it before writes.

For local development:

```shell
python3 scripts/build_grammar.py zig
red plugin install --path packs/zig --trust-native-grammars
red packs/zig/example/main.zig
```

## Grammar provenance

- Upstream: <https://github.com/tree-sitter-grammars/tree-sitter-zig>
- Immutable grammar revision: `6479aa13f32f701c383083d8b28360ebd682fb7d`
- Grammar license: `MIT`
- Source: reviewed direct grammar source and highlighting queries

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.
