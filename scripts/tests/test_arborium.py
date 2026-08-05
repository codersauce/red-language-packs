"""Regression coverage for provenance, publication policy, and query composition."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

import arborium
import build_grammar
import merge_catalog
import validate_pack


class ArboriumImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.settings = arborium.load_settings()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def definition(
        self,
        identifier: str,
        query: str = "(identifier) @variable\n",
        *,
        tier: int | None = 1,
        revision: str = "a" * 40,
        license: str = "MIT",
        dependencies: tuple[str, ...] = (),
        injections: str | None = None,
    ) -> arborium.Definition:
        directory = self.root / identifier / "def"
        (directory / "queries").mkdir(parents=True)
        (directory / "queries" / "highlights.scm").write_text(query)
        if injections is not None:
            (directory / "queries" / "injections.scm").write_text(injections)
        return arborium.Definition(
            identifier=identifier,
            name=identifier.title(),
            repository=f"https://github.com/example/tree-sitter-{identifier}",
            revision=revision,
            license=license,
            tier=tier,
            has_scanner=False,
            aliases=(),
            declared_injections=(),
            query_dependencies=dependencies,
            directory=directory,
        )

    def test_publication_policy_rejects_unpinned_sources_unapproved_licenses_and_low_tiers(self) -> None:
        cases = [
            (self.definition("unpinned", revision="main"), "immutable full commit"),
            (self.definition("copyleft", license="GPL-3.0"), "not approved"),
            (self.definition("immature", tier=4), "additional review"),
            (self.definition("unknown-tier", tier=None), "additional review"),
        ]
        for definition, expected in cases:
            with self.subTest(identifier=definition.identifier):
                blockers = arborium.eligibility(definition, self.settings)
                self.assertTrue(any(expected in blocker for blocker in blockers))

    def test_query_inheritance_prepends_missing_parent_without_duplicating_existing_parent(self) -> None:
        javascript = self.definition("javascript", "(identifier) @variable\n")
        typescript = self.definition(
            "typescript",
            "(identifier) @variable\n\n(type_identifier) @type\n",
            dependencies=("javascript",),
        )
        vue = self.definition("vue", "(element) @tag\n", dependencies=("javascript",))
        definitions = {entry.identifier: entry for entry in (javascript, typescript, vue)}

        inherited = arborium.compose_highlights(typescript, definitions)
        self.assertEqual(inherited.count("(identifier) @variable"), 1)
        self.assertEqual(
            arborium.compose_highlights(vue, definitions),
            "(identifier) @variable\n\n(element) @tag\n",
        )

    def test_query_inheritance_rejects_circular_dependencies(self) -> None:
        first = self.definition("first", dependencies=("second",))
        second = self.definition("second", dependencies=("first",))

        with self.assertRaisesRegex(ValueError, "circular"):
            arborium.compose_highlights(first, {"first": first, "second": second})

    def test_injection_inventory_identifies_static_dynamic_and_unsupported_features(self) -> None:
        definition = self.definition(
            "html",
            injections=(
                '((raw_text) @injection.content (#set! injection.language "javascript"))\n'
                '((text) @injection.language (#set! injection.combined))\n'
                '(#offset! @injection.content 0 1 0 -1)\n'
            ),
        )

        languages, unsupported, dynamic = arborium.injection_details(definition)

        self.assertEqual(languages, ["javascript"])
        self.assertEqual(unsupported, ["combined", "offset"])
        self.assertTrue(dynamic)

    def test_archive_verification_rejects_changed_source_bytes(self) -> None:
        archive = self.root / "source.tar.gz"
        archive.write_bytes(b"unexpected source")

        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            arborium.verified_archive(
                "https://github.com/example/grammar",
                "a" * 40,
                hashlib.sha256(b"approved source").hexdigest(),
                archive,
            )

    def test_swift_override_requires_the_reviewed_fixed_scanner_source(self) -> None:
        overlay = arborium.load_overlay(arborium.ROOT / "arborium" / "languages" / "swift.toml")

        self.assertEqual(overlay["source"]["revision"], "8abb3e8b33256d89127a35e87480736f74755ff9")
        self.assertTrue(overlay["source"]["reason"])
        self.assertTrue(build_grammar.UNSAFE_SWIFT_ALLOCATION.search("calloc(0, sizeof(state))"))
        self.assertFalse(build_grammar.UNSAFE_SWIFT_ALLOCATION.search("calloc(1, sizeof(state))"))

    def test_go_overlay_preserves_user_visible_highlight_scopes(self) -> None:
        overlay = arborium.load_overlay(arborium.ROOT / "arborium" / "languages" / "go.toml")
        query = (arborium.ROOT / "packs" / "go" / overlay["language"]["highlight_overlay"]).read_text()
        captures = set(arborium.CAPTURE.findall(query))

        self.assertTrue(set(overlay["language"]["minimum_capture_scopes"]).issubset(captures))

    def test_overlay_keeps_each_language_server_external(self) -> None:
        go = arborium.load_overlay(arborium.ROOT / "arborium" / "languages" / "go.toml")
        swift = arborium.load_overlay(arborium.ROOT / "arborium" / "languages" / "swift.toml")

        self.assertEqual(go["lsp"]["command"], "gopls")
        self.assertEqual(swift["lsp"]["command"], "sourcekit-lsp")

    def test_reviewed_language_inventory_includes_each_independent_requested_pack(self) -> None:
        self.assertEqual(
            arborium.reviewed_languages(),
            [
                "c",
                "c-sharp",
                "cpp",
                "css",
                "dockerfile",
                "go",
                "html",
                "java",
                "kotlin",
                "php",
                "sql",
                "svelte",
                "swift",
                "vue",
            ],
        )

    def test_every_reviewed_language_keeps_a_distinct_package_and_external_server(self) -> None:
        package_ids = set()
        for identifier in arborium.reviewed_languages():
            overlay = arborium.load_overlay(
                arborium.ROOT / "arborium" / "languages" / f"{identifier}.toml"
            )
            package_id = overlay["package"]["id"]
            self.assertNotIn(package_id, package_ids)
            package_ids.add(package_id)
            self.assertTrue(overlay["lsp"]["command"])

    def test_kotlin_query_preserves_pinned_apache_provenance(self) -> None:
        kotlin = arborium.load_overlay(arborium.ROOT / "arborium" / "languages" / "kotlin.toml")

        self.assertEqual(kotlin["package"]["license"], "MIT")
        self.assertEqual(kotlin["provenance"]["query_license"], "Apache-2.0")
        self.assertEqual(
            kotlin["provenance"]["query_revision"], "f8ab59861eed4a1c168505e3433462ed800f2bae"
        )

    def test_kotlin_notices_separate_apache_query_and_arborium_attributions(self) -> None:
        notices = (arborium.ROOT / "packs" / "kotlin" / "THIRD_PARTY_NOTICES.md").read_text()
        query_attribution, arborium_attribution = notices.split(
            "## Arborium grammar and query curation", maxsplit=1
        )

        self.assertIn("https://github.com/nvim-treesitter/nvim-treesitter", query_attribution)
        self.assertIn("Apache-2.0", query_attribution)
        self.assertNotIn("Amos Wenger", query_attribution)
        self.assertIn("Amos Wenger", arborium_attribution)

    def test_inherited_grammars_preserve_parent_source_attributions(self) -> None:
        cases = [
            ("cpp", "https://github.com/tree-sitter/tree-sitter-c"),
            ("svelte", "https://github.com/tree-sitter/tree-sitter-html"),
            ("vue", "https://github.com/tree-sitter/tree-sitter-html"),
        ]
        for identifier, inherited_repository in cases:
            with self.subTest(language=identifier):
                notices = (
                    arborium.ROOT / "packs" / identifier / "THIRD_PARTY_NOTICES.md"
                ).read_text()
                self.assertIn(inherited_repository, notices)

    def test_every_generated_pack_ignores_its_compiled_native_grammar(self) -> None:
        for identifier in arborium.reviewed_languages():
            overlay = arborium.load_overlay(
                arborium.ROOT / "arborium" / "languages" / f"{identifier}.toml"
            )
            if "source" not in overlay["validation"]:
                continue
            ignored = (arborium.ROOT / "packs" / identifier / ".gitignore").read_text()
            self.assertIn(f"/grammars/{identifier}.so", ignored)

    def test_generated_pack_requires_reviewed_upstream_copyright(self) -> None:
        overlay = self.root / "example.toml"
        overlay.write_text(
            '[language]\nid = "example"\n[validation]\nsource = "example"\n',
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "reviewed upstream copyright"):
            arborium.load_overlay(overlay)

    def test_scanner_staging_preserves_header_and_nested_include_dependencies(self) -> None:
        destination = self.root / "scanner"
        (destination / "src").mkdir(parents=True)
        (destination / "common").mkdir()
        (destination / "scanner.c").write_text('#include "tag.h"\n#include "common/scanner.h"\n')
        (destination / "tag.h").write_text("/* tag declarations */\n")
        (destination / "common" / "scanner.h").write_text("/* scanner declarations */\n")
        definition = self.definition("scanner")

        scanner = build_grammar.stage_scanner(destination, definition)

        self.assertEqual(scanner, destination / "src" / "scanner.c")
        self.assertTrue((destination / "src" / "tag.h").is_file())
        self.assertTrue((destination / "src" / "common" / "scanner.h").is_file())

    def test_grammar_dependencies_are_staged_as_local_tree_sitter_packages(self) -> None:
        html = self.definition("html")
        vue = self.definition("vue", dependencies=("html",))
        grammar = html.directory / "grammar"
        grammar.mkdir()
        (grammar / "grammar.js").write_text("module.exports = grammar({name: 'html'});\n")
        destination = self.root / "vue-build"
        destination.mkdir()

        build_grammar.stage_dependencies(destination, vue, {"html": html, "vue": vue})

        self.assertTrue((destination / "node_modules" / "tree-sitter-html" / "grammar.js").is_file())

    def test_all_grammar_builds_follow_reviewed_metadata_without_hard_coded_pack_names(self) -> None:
        with (
            patch.object(build_grammar, "reviewed_languages", return_value=["html", "vue"]),
            patch.object(build_grammar, "build") as build,
            patch("sys.argv", ["build_grammar.py", "--all"]),
        ):
            self.assertEqual(build_grammar.main(), 0)

        build.assert_has_calls([call("html", None), call("vue", None)])

    def test_pinned_inventory_keeps_review_gates_and_optional_injection_dependencies(self) -> None:
        inventory = json.loads((arborium.ROOT / "arborium" / "inventory.json").read_text())
        entries = {entry["id"]: entry for entry in inventory["languages"]}

        self.assertEqual(len(entries), 112)
        self.assertEqual(sum(entry["eligible"] for entry in entries.values()), 62)
        self.assertEqual(entries["swift"]["injected_languages"], ["comment", "regex"])
        self.assertEqual(entries["vue"]["query_dependencies"], ["html"])
        self.assertFalse(entries["x86asm"]["eligible"])

    def test_pack_validation_rejects_language_server_drift_from_reviewed_metadata(self) -> None:
        destination = self.root / "go"
        shutil.copytree(
            arborium.ROOT / "packs" / "go",
            destination,
            ignore=shutil.ignore_patterns("grammars"),
        )
        manifest = destination / "red-plugin.toml"
        manifest.write_text(manifest.read_text().replace('command = "gopls"', 'command = "other-lsp"'))

        with self.assertRaisesRegex(ValueError, "reviewed external LSP"):
            validate_pack.validate(destination)

    def test_catalog_release_preserves_existing_packages_and_merges_independent_targets(self) -> None:
        base = self.root / "base.json"
        first = self.root / "first.json"
        second = self.root / "second.json"
        output = self.root / "catalog.json"
        base.write_text(json.dumps({"schema_version": 1, "packages": [{"id": "swift-language"}]}))
        common = {"id": "go-language", "version": "0.2.0"}
        first.write_text(
            json.dumps({**common, "artifacts": {"aarch64-apple-darwin": {"sha256": "first"}}})
        )
        second.write_text(
            json.dumps({**common, "artifacts": {"x86_64-pc-windows-msvc": {"sha256": "second"}}})
        )

        with patch(
            "sys.argv",
            [
                "merge_catalog.py",
                "--base",
                str(base),
                "--metadata",
                str(first),
                str(second),
                "--output",
                str(output),
            ],
        ):
            self.assertEqual(merge_catalog.main(), 0)

        catalog = json.loads(output.read_text())
        packages = {package["id"]: package for package in catalog["packages"]}
        self.assertEqual(set(packages), {"go-language", "swift-language"})
        self.assertEqual(
            set(packages["go-language"]["artifacts"]),
            {"aarch64-apple-darwin", "x86_64-pc-windows-msvc"},
        )


if __name__ == "__main__":
    unittest.main()
