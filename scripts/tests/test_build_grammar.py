from __future__ import annotations

import contextlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import build_grammar


class BuildGrammarTests(unittest.TestCase):
    def test_unverified_source_patch_stops_before_any_build_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            overlay = {"language": {"id": "tmux"}, "source": {"kind": "standalone"}}
            with (
                patch.object(build_grammar, "source_patch_paths", side_effect=ValueError("patch digest mismatch")),
                patch.object(build_grammar.subprocess, "run") as run,
                self.assertRaisesRegex(ValueError, "patch digest mismatch"),
            ):
                build_grammar.build_one("tree-sitter", "tmux", overlay, Mock(), {}, source, {})
            run.assert_not_called()

    def test_reviewed_patch_is_checked_and_applied_before_grammar_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            source_patch = Path(directory) / "reviewed.patch"
            overlay = {"language": {"id": "tmux"}, "source": {"kind": "standalone"}}
            with (
                patch.object(build_grammar, "source_patch_paths", return_value=[source_patch]),
                patch.object(build_grammar.subprocess, "run") as run,
                patch.object(build_grammar, "stage_dependencies", side_effect=ValueError("stop before generate")),
                self.assertRaisesRegex(ValueError, "stop before generate"),
            ):
                build_grammar.build_one("tree-sitter", "tmux", overlay, Mock(), {}, source, {})
            self.assertEqual([call.args[0] for call in run.call_args_list], [
                ["git", "apply", "--check", str(source_patch)],
                ["git", "apply", str(source_patch)],
            ])
            self.assertTrue(all(call.kwargs["cwd"].name == "tree-sitter-tmux" for call in run.call_args_list))

    def test_standalone_companion_builds_into_the_main_pack_without_arborium(self) -> None:
        main = {"language": {"id": "tmux"}, "source": {"kind": "standalone"}}
        companion = {"language": {"id": "tmuxf"}, "source": {"kind": "standalone"}}
        for grammar in (main, companion):
            grammar["source"].update(repository="https://github.com/example/grammar", revision="a" * 40,
                                     archive_sha256="b" * 64)
        main["companions"] = [companion]
        settings = {"upstream": {"tree_sitter_cli": "0.25.10"}}
        with (
            patch.object(build_grammar, "load_settings", return_value=settings),
            patch.object(build_grammar, "load_overlay", return_value=main),
            patch.object(build_grammar, "check_cli", return_value="tree-sitter"),
            patch.object(build_grammar, "arborium_source") as arborium,
            patch.object(build_grammar, "extracted_archive", side_effect=lambda *args: contextlib.nullcontext(Path("source"))),
            patch.object(build_grammar, "standalone_definition", return_value=Mock()),
            patch.object(build_grammar, "build_one", side_effect=[Path("tmux.so"), Path("tmuxf.so")]) as build,
            patch.dict("os.environ", {}, clear=True),
        ):
            result = build_grammar.build("tmux", None)
        self.assertEqual(result, Path("tmux.so"))
        arborium.assert_not_called()
        self.assertEqual([call.args[1] for call in build.call_args_list], ["tmux", "tmux"])
        self.assertEqual([call.args[2]["language"]["id"] for call in build.call_args_list], ["tmux", "tmuxf"])

    def test_assertions_use_exact_source_ranges_including_unicode_byte_columns(self) -> None:
        output = "capture: 1 - keyword, start: (0, 3), end: (0, 6), text: `misleading`"
        source = "é set on\n".encode()
        build_grammar.validate_capture_assertions(output, source, [
            {"capture": "keyword", "text": "set", "row": 0, "column": 3},
            {"capture": "keyword", "text": "on", "must_exist": False},
        ], "test")
        with self.assertRaisesRegex(ValueError, "missing exact"):
            build_grammar.validate_capture_assertions(output, source, [
                {"capture": "keyword", "text": "set on"},
            ], "test")

    def test_negative_assertion_rejects_wrong_builtin_classification(self) -> None:
        output = "capture: 1 - variable.builtin, start: (0, 0), end: (0, 7), text: `@plugin`"
        with self.assertRaisesRegex(ValueError, "unexpected exact"):
            build_grammar.validate_capture_assertions(output, b"@plugin\n", [
                {"capture": "variable.builtin", "text": "@plugin", "must_exist": False},
            ], "test")

    def test_assertion_rejects_stale_fixture_position(self) -> None:
        with self.assertRaisesRegex(ValueError, "assertion text is not at"):
            build_grammar.validate_capture_assertions("", b"set on\n", [
                {"capture": "keyword", "text": "set", "row": 0, "column": 1},
            ], "test")

    def test_sample_loads_manifest_queries_and_checks_capture_names_not_source_words(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack = root / "packs" / "tmux"
            pack.mkdir(parents=True)
            (pack / "example.tmuxf").write_text("string\n")
            (pack / "reviewed.scm").write_text("(text) @constant")
            (pack / "red-plugin.toml").write_text(
                '[languages.tmuxf.grammar]\nhighlights = ["reviewed.scm"]\n'
            )
            grammar = root / "grammar"
            grammar.mkdir()
            overlay = {"validation": {"sample": "example.tmuxf", "required_captures": ["string"]}}
            output = "capture: 1 - constant, start: (0, 0), end: (0, 6), text: `string`"
            with (
                patch.object(build_grammar, "ROOT", root),
                patch.object(build_grammar, "query_sample", return_value=output),
                self.assertRaisesRegex(ValueError, "lost expected highlights: string"),
            ):
                build_grammar.validate_sample_highlighting("tree-sitter", "tmuxf", overlay, grammar, "tmux")
            self.assertEqual((grammar / "red-highlights.scm").read_text(), "(text) @constant")


if __name__ == "__main__":
    unittest.main()
