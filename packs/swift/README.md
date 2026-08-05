# Swift for Red

The official Swift language pack for the [Red editor](https://github.com/codersauce/red).

It provides Tree-sitter syntax highlighting, SwiftPM workspace detection,
four-space indentation, `//` comments, and SourceKit-LSP support for hover,
completion, go-to-definition, diagnostics, symbols, and inlay hints.

## Requirements

- Red with external language-package support
- Xcode or another Swift toolchain that provides `sourcekit-lsp`
- Git, a C compiler, and the [Tree-sitter CLI](https://github.com/tree-sitter/tree-sitter)

Install the pinned Tree-sitter CLI with:

```shell
cargo install tree-sitter-cli --version 0.25.10 --locked
```

## Install

Install the current verified release from Red's language-pack catalog:

```shell
red plugin install --catalog swift-language
```

This installs the pack without approving its native Tree-sitter grammar. After
reviewing the provenance below, approve the exact catalog-verified grammar
bytes either during install or separately:

```shell
red plugin install --catalog swift-language --trust-native-grammars
red language trust swift
```

For pack development, build the pinned Swift grammar and install this checkout
as a custom local package:

```shell
git clone https://github.com/codersauce/red-language-packs.git
cd red-language-packs
sh packs/swift/build-grammar.sh
red plugin install --path packs/swift --trust-native-grammars
```

The trust flag approves this exact locally built parser. Rebuilding or changing
the parser requires approving the new digest. To install first and approve the
parser separately:

```shell
red plugin install --path packs/swift
red language trust swift
```

If Red is already running, apply the updated language definitions with:

```vim
:languages reload
```

## Try the example

Open the included SwiftPM executable:

```shell
red example/Sources/RedSwiftExample/main.swift
```

Place the cursor on `FriendlyGreeter` and press `K` to open SourceKit hover
documentation, or press `g d` to jump to its definition. The example also
exercises documentation comments, generics, protocols, async functions,
interpolated strings, diagnostics, and inlay hints.

Run it independently with:

```shell
swift run --package-path example
```

Any existing `.swift` file works as well. SourceKit-LSP uses the closest
`Package.swift` or `.git` directory as its workspace root.

## Grammar provenance

The build uses `alex-pinkus/tree-sitter-swift`, pinned to commit
`8abb3e8b33256d89127a35e87480736f74755ff9`. This reviewed source override
retains the upstream Swift external-scanner allocation fix rather than adopting
Arborium's older scanner. Highlight and optional injection queries come from
Arborium v2.18.1, with Red-owned refinements layered on top; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
