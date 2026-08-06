# PowerShell for Red

PowerShell syntax highlighting, module detection, and PowerShell Editor Services integration.

## Install

```shell
red plugin install --catalog powershell-language
red language trust powershell
```

Native grammar approval is explicit and tied to the exact installed grammar digest. The optional [PowerShell Editor Services](https://github.com/PowerShell/PowerShellEditorServices#usage) language server is launched through `pwsh`. Install its released module on PowerShell's module path before opening a project. Syntax highlighting works without it.

For local development:

```shell
python3 scripts/build_grammar.py powershell
red plugin install --path packs/powershell --trust-native-grammars
red packs/powershell/example/Get-Greeting.ps1
```

## Grammar provenance

- Upstream: <https://github.com/airbus-cert/tree-sitter-powershell>
- Immutable grammar revision: `9379c77984af1f3d3d7e3cc5e897de3496725280`
- Grammar license: `MIT`
- Source: pinned Arborium grammar and highlighting queries

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.
