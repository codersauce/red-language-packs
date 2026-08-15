# C# for Red

C# syntax highlighting, .NET project detection, and C# language server integration.

## Install

```shell
red plugin install --catalog c-sharp-language
red language trust c-sharp
```

Native grammar approval is explicit and tied to the exact installed grammar digest. The optional `csharp-ls` language server is discovered on `PATH`; syntax highlighting works without it.

The optional [CSharpier](https://csharpier.com/docs/CLI) formatter is launched through `dotnet` and receives the document on standard input. Install CSharpier as a global or local .NET tool so `dotnet csharpier` is available. Formatting is available through `Space f`; enable `formatting.on_save` to run it before writes.

For local development:

```shell
python3 scripts/build_grammar.py c-sharp
red plugin install --path packs/c-sharp --trust-native-grammars
red packs/c-sharp/example/Program.cs
```

## Grammar provenance

- Upstream: <https://github.com/tree-sitter/tree-sitter-c-sharp>
- Immutable grammar revision: `485f0bae0274ac9114797fc10db6f7034e4086e3`
- Grammar license: `MIT`
- Source: pinned Arborium grammar and highlighting queries

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.
