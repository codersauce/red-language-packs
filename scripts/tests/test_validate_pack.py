from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import validate_pack


class ValidatePackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.pack = Path(self.temporary.name) / "syntax-only-example"
        self.pack.mkdir()
        for name in ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "build-grammar.sh"):
            (self.pack / name).write_text("example\n")
        (self.pack / "catalog.toml").write_text('tier = "official"\n')
        (self.pack / "highlights.scm").write_text("(text) @string\n")
        (self.pack / "red-plugin.toml").write_text('''schema_version = 1
[plugin]
id = "example-language"
name = "Example"
version = "0.1.0"
red_api = "^0.10.0"
description = "Syntax only"
repository = "https://github.com/codersauce/red-language-packs"
license = "MIT"
[languages.example.grammar]
path = "grammars/example.so"
highlights = ["highlights.scm"]
''')

    def test_syntax_only_pack_omits_external_tools_and_ignores_unloaded_upstream_query(self) -> None:
        (self.pack / "upstream.scm").write_text('((text) @string (#lua-match? @string "%w"))')
        manifest = validate_pack.validate(self.pack)
        self.assertNotIn("formatter", manifest["languages"]["example"])
        self.assertNotIn("lsp", manifest["languages"]["example"])

    def test_loaded_query_rejects_neovim_specific_predicate(self) -> None:
        (self.pack / "highlights.scm").write_text('((text) @string (#lua-match? @string "%w"))')
        with self.assertRaisesRegex(ValueError, "unsupported Red query.*#lua-match"):
            validate_pack.validate(self.pack)

    def test_existing_arborium_zig_queries_do_not_weaken_standalone_audit(self) -> None:
        repository = Path(validate_pack.__file__).resolve().parent.parent
        zig = repository / "packs" / "zig"
        self.assertEqual(validate_pack.validate(zig)["plugin"]["id"], "zig-language")
        standalone = Path(self.temporary.name) / "tmux"
        shutil.copytree(repository / "packs" / "tmux", standalone, ignore=shutil.ignore_patterns("grammars"))
        (standalone / "queries" / "highlights.scm").write_text('((string) @string (#lua-match? @string "%w"))')
        with self.assertRaisesRegex(ValueError, "unsupported Red query.*#lua-match"):
            validate_pack.validate(standalone)

    def test_query_audit_ignores_operators_in_comments_and_quoted_patterns(self) -> None:
        query = self.pack / "highlights.scm"
        query.write_text('; (#lua-match? @string "ignored")\n'
                         '((text) @string (#eq? @string "(#lua-match?"))\n')
        validate_pack.validate_query_predicates(query)

    def test_injection_audit_accepts_only_supported_directive(self) -> None:
        query = self.pack / "injections.scm"
        query.write_text('((text) @injection.content (#set! injection.language "tmuxf"))')
        validate_pack.validate_query_predicates(query, injections=True)
        with self.assertRaisesRegex(ValueError, "unsupported Red query"):
            validate_pack.validate_query_predicates(query)
        query.write_text('((text) @injection.content (#set! injection.combined))')
        with self.assertRaisesRegex(ValueError, "unsupported Red query"):
            validate_pack.validate_query_predicates(query, injections=True)

    def test_present_formatter_still_requires_valid_metadata(self) -> None:
        path = self.pack / "red-plugin.toml"
        path.write_text(path.read_text() + '\n[languages.example.formatter]\ncommand = "format"\n')
        with self.assertRaisesRegex(ValueError, "formatter.name must be non-empty"):
            validate_pack.validate(self.pack)

    def test_companion_declaration_checks_its_own_query_path_and_symbol(self) -> None:
        overlay = {
            "source": {"kind": "standalone", "revision": "a" * 40},
            "language": {"id": "tmuxf", "symbol": "tree_sitter_tmuxf", "highlight_overlay": "highlights.scm"},
        }
        manifest = {"languages": {"tmuxf": {"grammar": {
            "path": "grammars/tmuxf.so", "symbol": "tree_sitter_tmuxf", "highlights": ["highlights.scm"],
        }}}}
        (self.pack / "THIRD_PARTY_NOTICES.md").write_text("a" * 40)
        validate_pack.validate_language_overlay(self.pack, manifest, {}, overlay)
        manifest["languages"]["tmuxf"]["grammar"]["symbol"] = "tree_sitter_tmux"
        with self.assertRaisesRegex(ValueError, "grammar differs"):
            validate_pack.validate_language_overlay(self.pack, manifest, {}, overlay)

    def test_companion_cannot_add_unreviewed_file_selectors(self) -> None:
        overlay = {"language": {"id": "tmuxf"}}
        for field, value in (("extensions", "conf"), ("filenames", ".tmux.conf"),
                             ("aliases", "config"), ("shebangs", "sh")):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, f"language.{field} differs"):
                validate_pack.validate_language_overlay(
                    self.pack, {"languages": {"tmuxf": {field: [value]}}}, {}, overlay,
                )

    def test_syntax_only_companion_cannot_add_unreviewed_lsp_settings(self) -> None:
        overlay = {"language": {"id": "tmuxf"}}
        with self.assertRaisesRegex(ValueError, "reviewed external LSP"):
            validate_pack.validate_language_overlay(
                self.pack, {"languages": {"tmuxf": {"lsp": {"server": "other"}}}}, {}, overlay,
            )


if __name__ == "__main__":
    unittest.main()
