# SQL for Red

SQL syntax highlighting, query navigation, and SQL language server integration.

## Install

```shell
red plugin install --catalog sql-language
red language trust sql
```

Native grammar approval is explicit and tied to the exact installed grammar digest. The optional `sqls` language server is discovered on `PATH`; syntax highlighting works without it.

For local development:

```shell
python3 scripts/build_grammar.py sql
red plugin install --path packs/sql --trust-native-grammars
red packs/sql/example/query.sql
```

## Grammar provenance

- Upstream: <https://github.com/DerekStride/tree-sitter-sql>
- Immutable grammar revision: `fe77f6868d6cdea593052a6af390116495093dc1`
- Grammar license: `MIT`
- Source: pinned Arborium grammar and highlighting queries

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.
