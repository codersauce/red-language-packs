# tmux for Red

tmux configuration syntax highlighting with embedded status formats and styles.

Recognizes the exact filenames `.tmux.conf`, `tmux.conf`, `.tmux.conf.local`, `tmux.conf.local` in any directory. Other config files keep their existing language detection.

## Install

```shell
red plugin install --catalog tmux-language
red language trust tmux
red language trust tmuxf
```

Native grammar approval is tied to each installed grammar's exact digest. No language server or formatter is required.

For local development, with Tree-sitter CLI 0.25.10 on PATH or in `TREE_SITTER`:

```shell
python3 scripts/build_grammar.py tmux
red plugin install --path packs/tmux --trust-native-grammars
red packs/tmux/example/.tmux.conf
```

## Embedded languages

This package includes `tmuxf` for embedded syntax. Each grammar has its own digest and trust decision. Companion grammars with empty filename and extension lists do not claim files automatically; they remain selectable in Red's language picker.

## Grammar provenance

- `tmux`: <https://github.com/Freed-Wu/tree-sitter-tmux>, revision `58147321fa1f00daec15dd4d371bc9e2e9373459`, license `MIT`
- `tmuxf`: <https://github.com/Freed-Wu/tree-sitter-tmuxf>, revision `bf2eee4772551c0801ece5e746c6016b9cb61ab2`, license `MIT`

The sources are pinned and SHA-256 verified independently of Arborium. The source checkout retains original queries in `queries/upstream-*-highlights.scm` for review; the manifest loads only the separately reviewed Red query files.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for complete attributions.

## Syntax coverage

The pack highlights commands, flags, built-in and user options, key bindings,
comments, strings, numbers, hooks, and `%if`/`%elif`/`%else`/`%endif` directives.
The bundled `tmuxf` grammar adds status-format variables, nested conditions,
format functions, and inline styles such as `#[fg=green,bold]` in the reviewed
format contexts. These include `set`/`setw` format options, status-left/right,
format arguments, display messages, and `if-shell -F` conditions.

Two small, digest-verified source patches cover common configuration syntax:

- [tmux.patch](patches/tmux.patch) accepts numeric option-array indices such as
  `status-format[0]`.
- [tmuxf.patch](patches/tmuxf.patch) accepts user-variable formats such as
  `#{@theme2}` and nested conditions such as
  `#{?#{==:#{host},workstation},work,home}`.

Remaining upstream limitations:

- Quote format expressions in `%if` and `%elif`; the parser does not recognize
  unquoted expressions beginning with `#{` in those directives.
- Ordinary commas in format text outside expressions can cause parser recovery.
  The surrounding text and following format expressions still receive highlighting.
- Raw style values such as `fg=white,bg=black` keep string coloring. Detailed style
  highlighting applies to inline `#[...]` styles inside format strings.

Shell-command contents and arbitrary plugin-option strings receive string
highlighting; they do not load additional language grammars.
