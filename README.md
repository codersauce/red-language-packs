# Swift for Red

The official Swift language pack for the [Red editor](https://github.com/codersauce/red).

It provides Tree-sitter syntax highlighting, SwiftPM workspace detection,
four-space indentation, `//` comments, and SourceKit-LSP support for hover,
completion, go-to-definition, diagnostics, symbols, and inlay hints.

## Requirements

- Red with external language-package support
- Xcode or another Swift toolchain that provides `sourcekit-lsp`
- Git, a C compiler, and the [Tree-sitter CLI](https://github.com/tree-sitter/tree-sitter)

On macOS, install the Tree-sitter CLI with:

```shell
brew install tree-sitter
```

## Install

Build the pinned Swift grammar and install this checkout as an external Red
package:

```shell
cd ~/code/red-swift-language-pack
sh build-grammar.sh
red plugin install --path . --trust-native-grammars
```

While language-pack support is being developed on a separate Red worktree, use
that binary explicitly:

```shell
~/code/red.fcoury-extensible-languages/target/debug/red \
  plugin install --path ~/code/red-swift-language-pack --trust-native-grammars
```

The trust flag approves this exact locally built parser. Rebuilding or changing
the parser requires approving the new digest. To install first and approve the
parser separately:

```shell
red plugin install --path .
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
`8abb3e8b33256d89127a35e87480736f74755ff9`, matching the Swift grammar
revision in Neovim's Tree-sitter registry. Highlight queries are adapted from
that grammar's MIT-licensed queries; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
