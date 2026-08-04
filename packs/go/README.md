# Go for Red

The official Go language pack for the [Red editor](https://github.com/codersauce/red).

It provides Tree-sitter syntax highlighting, Go module and workspace detection,
four-column indentation, line comments, and gopls support for hover,
completion, go-to-definition, diagnostics, symbols, formatting, and inlay hints.

## Requirements

- Red with external language-package support.
- Git, a C compiler, and the [Tree-sitter CLI](https://github.com/tree-sitter/tree-sitter).
- A Go toolchain and gopls for language-server features; syntax highlighting
  works without either.

On macOS:

~~~shell
brew install tree-sitter
go install golang.org/x/tools/gopls@latest
~~~

Make sure the installed gopls executable is available on your PATH.

## Install

Install the current verified release from Red's language-pack catalog:

~~~shell
red plugin install --catalog go-language
~~~

This installs the pack without approving its native Tree-sitter grammar. After
reviewing the provenance below, approve the exact catalog-verified grammar
bytes either during install or separately:

~~~shell
red plugin install --catalog go-language --trust-native-grammars
red language trust go
~~~

For pack development, build the pinned Go grammar and install this checkout as
a custom local package:

~~~shell
git clone https://github.com/codersauce/red-language-packs.git
cd red-language-packs
sh packs/go/build-grammar.sh
red plugin install --path packs/go --trust-native-grammars
~~~

The trust flag approves this exact locally built parser. Rebuilding or changing
the parser requires approving the new digest. To approve it separately:

~~~shell
red plugin install --path packs/go
red language trust go
~~~

If Red is already running, reload its language definitions:

~~~vim
:languages reload
~~~

## Try the example

Open the included Go module:

~~~shell
red example/main.go
~~~

Place the cursor on FriendlyGreeter and press K for hover documentation, or
press g d to jump to its definition. The example also exercises interfaces,
generic functions, methods, struct fields, context cancellation, channels,
strings, and built-in functions.

Run it independently:

~~~shell
cd example
go run .
go test ./...
~~~

If Go is installed with mise but not enabled globally, activate the installed
version for one command:

~~~shell
mise exec go@1.26.3 -- go -C example run .
~~~

Any existing Go source file works as well. gopls selects the nearest go.work,
go.mod, or Git repository as its workspace root.

## Grammar provenance

The build uses [tree-sitter/tree-sitter-go](https://github.com/tree-sitter/tree-sitter-go)
release v0.25.0, pinned to commit
1547678a9da59885853f5f5cc8a99cc203fa2e2c. Highlight queries are adapted from
the upstream MIT-licensed queries; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
