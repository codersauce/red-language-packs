from pathlib import Path
import json
import shutil
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import arborium
import check_indents
import package_release
import validate_pack


class IndentationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.pack = self.root / "packs" / "go"
        shutil.copytree(arborium.ROOT / "packs" / "go", self.pack, ignore=shutil.ignore_patterns("grammars"))

    def test_every_pack_declares_indentation_or_explicit_syntax_only_support(self):
        for name in arborium.reviewed_languages():
            with self.subTest(language=name):
                manifest = validate_pack.validate(arborium.ROOT / "packs" / name)
                if name == "tmux":
                    self.assertEqual(set(manifest["languages"]), {"tmux", "tmuxf"})
                    for language in manifest["languages"].values():
                        self.assertNotIn("indents", language["grammar"])
                    self.assertFalse((arborium.ROOT / "packs" / name / "tests" / "indent.json").exists())
                else:
                    self.assertTrue(manifest["languages"][name]["grammar"]["indents"])

    def test_unknown_capture_and_escaping_path_are_rejected(self):
        query = self.pack / "queries" / "indents.scm"
        query.write_text('"{" @indent.unknown\n')
        with self.assertRaisesRegex(ValueError, "unsupported indentation captures"):
            validate_pack.validate(self.pack)
        manifest = self.pack / "red-plugin.toml"
        manifest.write_text(manifest.read_text().replace('"queries/indents.scm"', '"../indents.scm"'))
        with self.assertRaisesRegex(ValueError, "safe package-relative"):
            validate_pack.validate(self.pack)

    def test_syntax_only_pack_skips_native_build_and_red_invocation(self):
        pack = self.root / "packs" / "tmux"
        shutil.copytree(arborium.ROOT / "packs" / "tmux", pack, ignore=shutil.ignore_patterns("grammars"))

        with patch.object(check_indents.subprocess, "run") as run, patch("builtins.print") as message:
            check_indents.check(pack, self.root / "red")

        run.assert_not_called()
        message.assert_called_once_with("skipped tmux-language: no indentation queries declared")

    def test_invalid_fixture_coordinates_are_rejected(self):
        path = self.pack / "tests" / "indent.json"
        cases = json.loads(path.read_text())
        cases[0]["line"] = -1
        path.write_text(json.dumps(cases))
        with self.assertRaisesRegex(ValueError, "invalid indentation fixture"):
            validate_pack.validate(self.pack)

    def test_release_archive_contains_declared_indentation_queries(self):
        manifest = validate_pack.validate(self.pack)
        grammar = self.pack / manifest["languages"]["go"]["grammar"]["path"]
        grammar.parent.mkdir()
        grammar.write_bytes(b"fixture grammar")
        output = self.root / "dist"
        version = manifest["plugin"]["version"]
        with patch.object(package_release, "__file__", str(self.root / "scripts" / "package_release.py")), patch("sys.argv", ["package_release.py", str(self.pack), "--target", "aarch64-apple-darwin", "--commit", "1" * 40, "--tag", f"go/v{version}", "--output", str(output)]):
            self.assertEqual(package_release.main(), 0)
        with tarfile.open(next(output.glob("*.tar.gz"))) as archive:
            self.assertIn("queries/indents.scm", archive.getnames())


if __name__ == "__main__":
    unittest.main()
