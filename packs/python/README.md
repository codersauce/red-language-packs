# Python for Red

Python syntax highlighting, type stub support, project detection, and Pyright integration.

## Install

```shell
red plugin install --catalog python-language
red language trust python
```

Native grammar approval is explicit and tied to the exact installed grammar digest. The optional [Pyright](https://github.com/microsoft/pyright/blob/main/docs/installation.md) language server is launched through `pyright-langserver`. Install Pyright and ensure `pyright-langserver` is available on `PATH`. Syntax highlighting works without it.

For local development:

```shell
python3 scripts/build_grammar.py python
red plugin install --path packs/python --trust-native-grammars
red packs/python/example/main.py
```

## Grammar provenance

- Upstream: <https://github.com/tree-sitter/tree-sitter-python>
- Immutable grammar revision: `26855eabccb19c6abf499fbc5b8dc7cc9ab8bc64`
- Grammar license: `MIT`
- Source: pinned Arborium grammar and highlighting queries

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.
