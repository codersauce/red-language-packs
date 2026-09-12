"""Standalone source review and syntax-only companion package contracts."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

import arborium


class StandaloneSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.settings = arborium.load_settings()
        self.source = self.root / "source"
        (self.source / "queries").mkdir(parents=True)
        (self.source / "grammar.js").write_text("module.exports = grammar({name: 'example'});\n")
        (self.source / "queries" / "highlights.scm").write_text("(word) @string\n")

    def overlay(self, *, companion: bool = False) -> dict:
        overlay = {
            "package": {
                "id": "example-language",
                "name": "Example language support",
                "version": "0.1.0",
                "red_api": "^0.10.0",
                "description": "Example syntax highlighting",
                "license": "MIT",
                "catalog_tier": "official",
            },
            "language": {
                "id": "example",
                "name": "Example",
                "filenames": [".example.conf", "example.conf"],
                "comment": "# %s",
                "symbol": "tree_sitter_example",
                "highlight_overlay": "queries/highlights.scm",
                "injections": "queries/injections.scm",
            },
            "source": {
                "kind": "standalone",
                "repository": "https://github.com/example/tree-sitter-example",
                "revision": "a" * 40,
                "archive_sha256": "b" * 64,
                "reason": "The pinned Arborium inventory does not include this grammar.",
                "license": "MIT",
                "has_scanner": False,
            },
            "validation": {"sample": "example/.example.conf", "source": "set value on\n"},
            "provenance": {"copyright": ["Copyright (c) 2026 Example Author"]},
        }
        if companion:
            child = copy.deepcopy(overlay)
            del child["package"]
            child["language"] = {
                "id": "example_format",
                "name": "Example format",
                "symbol": "tree_sitter_example_format",
                "highlight_overlay": "queries/format-highlights.scm",
            }
            child["source"]["repository"] = "https://github.com/example/tree-sitter-example-format"
            child["source"]["revision"] = "c" * 40
            child["source"]["archive_sha256"] = "d" * 64
            child["validation"] = {"sample": "example/format.txt", "source": "#{name}\n"}
            overlay["companions"] = [child]
        return overlay

    def write_overlay(self, overlay: dict) -> Path:
        lines = []

        def section(prefix: str, values: dict) -> None:
            for key, value in values.items():
                if isinstance(value, dict):
                    lines.append(f"[{prefix}{key}]")
                    lines.extend(f"{field} = {arborium.toml_value(item)}" for field, item in value.items())
                    lines.append("")

        section("", overlay)
        for companion in overlay.get("companions", []):
            lines.append("[[companions]]")
            section("companions.", companion)
        path = self.root / "example.toml"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def test_standalone_definition_requires_explicit_source_kind(self) -> None:
        overlay = self.overlay()
        del overlay["source"]["kind"]

        self.assertFalse(arborium.is_standalone(overlay))
        with self.assertRaisesRegex(ValueError, "explicit kind"):
            arborium.standalone_definition(overlay, self.source, self.settings)

    def test_reviewed_standalone_source_has_no_fabricated_arborium_tier(self) -> None:
        overlay = arborium.load_overlay(self.write_overlay(self.overlay()))

        definition = arborium.standalone_definition(overlay, self.source, self.settings)

        self.assertTrue(arborium.is_standalone(overlay))
        self.assertEqual(definition.identifier, "example")
        self.assertEqual(definition.name, "Example")
        self.assertEqual(definition.repository, overlay["source"]["repository"])
        self.assertEqual(definition.revision, "a" * 40)
        self.assertEqual(definition.license, "MIT")
        self.assertIsNone(definition.tier)
        self.assertFalse(definition.has_scanner)
        # Explicit standalone review must not weaken the existing Arborium gate.
        self.assertTrue(any("additional review" in item for item in arborium.eligibility(definition, self.settings)))

    def test_each_grammar_rejects_invalid_source_review_metadata(self) -> None:
        invalid = {
            "kind": "unreviewed",
            "repository": "https://example.com/tree-sitter-example",
            "revision": "main",
            "archive_sha256": "not-a-digest",
            "reason": " ",
            "license": "GPL-3.0",
            "has_scanner": "false",
        }
        for companion in (False, True):
            for field, value in invalid.items():
                with self.subTest(companion=companion, field=field):
                    overlay = self.overlay(companion=companion)
                    grammar = overlay["companions"][0] if companion else overlay
                    grammar["source"][field] = value
                    with self.assertRaises(ValueError):
                        arborium.load_overlay(self.write_overlay(overlay))

    def test_standalone_requires_sample_and_copyright_review(self) -> None:
        for missing in ("sample_source", "copyright"):
            with self.subTest(missing=missing):
                overlay = self.overlay()
                if missing == "sample_source":
                    del overlay["validation"]["source"]
                else:
                    overlay["provenance"]["copyright"] = []
                with self.assertRaises(ValueError):
                    arborium.load_overlay(self.write_overlay(overlay))

    def test_each_grammar_rejects_paths_outside_its_package(self) -> None:
        for companion in (False, True):
            for section, field in (
                ("language", "highlight_overlay"),
                ("language", "injections"),
                ("validation", "sample"),
            ):
                for path in ("../../outside", "/outside", "..\\outside"):
                    with self.subTest(companion=companion, field=field, path=path):
                        overlay = self.overlay(companion=companion)
                        grammar = overlay["companions"][0] if companion else overlay
                        grammar[section][field] = path
                        with self.assertRaises(ValueError):
                            arborium.load_overlay(self.write_overlay(overlay))

    def test_explicit_empty_tool_metadata_is_rejected(self) -> None:
        for companion in (False, True):
            for tool in ("lsp", "formatter"):
                with self.subTest(companion=companion, tool=tool):
                    overlay = self.overlay(companion=companion)
                    grammar = overlay["companions"][0] if companion else overlay
                    grammar[tool] = {}
                    with self.assertRaises(ValueError):
                        arborium.load_overlay(self.write_overlay(overlay))

    def test_arborium_readme_renders_only_declared_optional_tools(self) -> None:
        base = self.overlay()
        definition = arborium.standalone_definition(base, self.source, self.settings)
        del base["source"]["kind"]
        base["lsp"] = {
            "command": "example-language-server",
            "purpose": "Example completion",
        }
        base["formatter"] = {
            "name": "Example Formatter",
            "command": "example-formatter",
            "purpose": "Example formatting",
            "documentation": "https://example.com/formatter",
            "setup": "Install the formatter on PATH.",
        }
        for omitted in (("lsp",), ("formatter",), ("lsp", "formatter")):
            with self.subTest(omitted=omitted):
                overlay = copy.deepcopy(base)
                for tool in omitted:
                    del overlay[tool]
                loaded = arborium.load_overlay(self.write_overlay(overlay))

                readme = arborium.render_readme(loaded, definition)

                for tool, command in (
                    ("lsp", "example-language-server"),
                    ("formatter", "example-formatter"),
                ):
                    if tool in omitted:
                        self.assertNotIn(command, readme)
                    else:
                        self.assertIn(command, readme)

    def test_source_archive_tampering_fails_before_extraction_or_download(self) -> None:
        overlay = self.overlay()
        archive = self.root / "standalone.tar.gz"
        archive.write_bytes(b"changed source archive")
        digest = hashlib.sha256(b"reviewed source archive").hexdigest()
        with patch("arborium.urllib.request.urlopen") as download:
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                with arborium.extracted_archive(
                    overlay["source"]["repository"],
                    overlay["source"]["revision"],
                    digest,
                    archive,
                ):
                    self.fail("tampered archive was extracted")
            download.assert_not_called()

    def test_standalone_requires_grammar_and_upstream_highlight_sources(self) -> None:
        for relative in ("grammar.js", "queries/highlights.scm"):
            with self.subTest(source=relative):
                path = self.source / relative
                contents = path.read_text()
                path.unlink()
                try:
                    with self.assertRaises(ValueError):
                        arborium.standalone_definition(self.overlay(), self.source, self.settings)
                finally:
                    path.write_text(contents)

    def test_syntax_only_package_has_no_external_tool_requirements(self) -> None:
        overlay = arborium.load_overlay(self.write_overlay(self.overlay()))

        manifest = tomllib.loads(arborium.render_manifest(overlay, True))
        catalog = tomllib.loads(arborium.render_catalog(overlay))

        language = manifest["languages"]["example"]
        self.assertNotIn("lsp", language)
        self.assertNotIn("formatter", language)
        self.assertEqual(catalog.get("requirements", []), [])
        self.assertEqual(catalog["tier"], "official")
        self.assertEqual(language["grammar"]["highlights"], ["queries/highlights.scm"])
        self.assertEqual(language["grammar"]["injections"], "queries/injections.scm")
        self.assertEqual(language["filenames"], [".example.conf", "example.conf"])
        self.assertNotIn("extensions", language)

    def test_companion_manifest_declares_both_independent_grammar_artifacts(self) -> None:
        overlay = arborium.load_overlay(self.write_overlay(self.overlay(companion=True)))

        manifest = tomllib.loads(arborium.render_manifest(overlay, True))

        self.assertEqual(set(manifest["languages"]), {"example", "example_format"})
        for grammar_overlay in arborium.grammar_overlays(overlay):
            identifier = grammar_overlay["language"]["id"]
            language = manifest["languages"][identifier]
            grammar = language["grammar"]
            self.assertEqual(grammar["path"], f"grammars/{identifier}.so")
            self.assertEqual(grammar["symbol"], grammar_overlay["language"]["symbol"])
            self.assertEqual(grammar["highlights"], [grammar_overlay["language"]["highlight_overlay"]])
            self.assertNotIn("lsp", language)
            self.assertNotIn("formatter", language)
        companion = manifest["languages"]["example_format"]
        self.assertNotIn("filenames", companion)
        self.assertNotIn("extensions", companion)
        self.assertNotIn("injections", companion["grammar"])

    def test_duplicate_companion_identity_is_rejected(self) -> None:
        overlay = self.overlay(companion=True)
        overlay["companions"][0]["language"]["id"] = "example"

        with self.assertRaisesRegex(ValueError, "duplicate grammar identifier"):
            arborium.load_overlay(self.write_overlay(overlay))

    def write_inventory(self, overlays: list[dict]) -> Path:
        inventory = Path(tempfile.mkdtemp(prefix="inventory-", dir=self.root))
        metadata = inventory / "arborium" / "languages"
        metadata.mkdir(parents=True)
        (inventory / "arborium" / "source.toml").write_text(
            (arborium.ROOT / "arborium" / "source.toml").read_text()
        )
        for overlay in overlays:
            identifier = overlay["language"]["id"]
            (metadata / f"{identifier}.toml").write_text(self.write_overlay(overlay).read_text())
        return inventory

    def test_inventory_retains_package_slugs_without_listing_companions_as_packs(self) -> None:
        first = self.overlay(companion=True)
        second = self.overlay()
        second["language"]["id"] = "example-other"
        inventory = self.write_inventory([first, second])

        with patch.object(arborium, "ROOT", inventory):
            self.assertEqual(arborium.reviewed_languages(), ["example", "example-other"])

    def test_inventory_rejects_companion_collisions_with_another_package(self) -> None:
        for other_companion in (False, True):
            with self.subTest(other_companion=other_companion):
                first = self.overlay(companion=True)
                second = self.overlay(companion=other_companion)
                second["language"]["id"] = "other"
                if not other_companion:
                    first["companions"][0]["language"]["id"] = "other"
                inventory = self.write_inventory([first, second])
                with patch.object(arborium, "ROOT", inventory):
                    with self.assertRaisesRegex(ValueError, "both example and other packages"):
                        arborium.reviewed_languages()


if __name__ == "__main__":
    unittest.main()
