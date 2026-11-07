"""S03.2: only host-registered read-only roots are readable, and escapes are refused."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ai_union.adapters import documents
from ai_union.errors import Rejected


class DocumentRootTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.base = Path(self._temp.name)
        self.root = self.base / "console"
        self.root.mkdir()
        self.docs = self.base / "docs"
        (self.docs / "nested").mkdir(parents=True)
        (self.docs / "overview.md").write_bytes("# 概览\n引用 nested/a.md\n".encode("utf-8"))
        (self.docs / "nested" / "a.md").write_bytes("资料正文\n".encode("utf-8"))
        (self.docs / "binary.bin").write_bytes(b"\x00\x01binary")
        self.outside = self.base / "outside"
        self.outside.mkdir()
        (self.outside / "secret.txt").write_bytes("范围外资料\n".encode("utf-8"))
        self.register({"project-docs": str(self.docs)})

    def tearDown(self):
        self._temp.cleanup()

    def register(self, roots, *, name=documents.REGISTRY):
        (self.root / name).write_text(json.dumps({"version": 1, "roots": roots}, ensure_ascii=False), encoding="utf-8")

    def test_registered_root_lists_only_its_own_documents(self):
        root = documents.root_for(self.root, "project-docs")
        listed = documents.list_documents(root)
        self.assertEqual(listed, ["binary.bin", "nested/a.md", "overview.md"])

    def test_read_returns_exact_content_and_digest(self):
        root = documents.root_for(self.root, "project-docs")
        text, digest, size = documents.read_text(root, "nested/a.md")
        self.assertEqual(text, "资料正文\n")
        self.assertEqual(size, len("资料正文\n".encode("utf-8")))
        self.assertEqual(digest, hashlib.sha256("资料正文\n".encode("utf-8")).hexdigest())

    def test_host_paths_and_unregistered_references_are_rejected(self):
        for value in ("", "..", "C:\\docs", "/etc", "project docs", "project.docs", "x" * 65):
            with self.subTest(reference=value):
                with self.assertRaises(Rejected):
                    documents.root_for(self.root, value)
        with self.assertRaises(Rejected):
            documents.root_for(self.root, "absent-root")

    def test_absolute_and_traversal_document_paths_are_rejected(self):
        root = documents.root_for(self.root, "project-docs")
        for value in ("/etc/passwd", "C:\\Windows\\win.ini", "\\\\server\\share\\a.txt",
                      "..\\secret.txt", "../outside/secret.txt", "nested/../../outside/secret.txt",
                      "", ".", "nested", "a\x00b.md"):
            with self.subTest(relative=value):
                with self.assertRaises(Rejected):
                    documents.read_text(root, value)

    def test_binary_and_oversize_documents_are_rejected(self):
        root = documents.root_for(self.root, "project-docs")
        with self.assertRaises(Rejected):
            documents.read_text(root, "binary.bin")
        big = self.docs / "big.md"
        big.write_text("x" * (documents.MAX_BYTES + 1), encoding="utf-8")
        with self.assertRaises(Rejected):
            documents.read_text(root, "big.md")

    def test_escape_through_directory_link_is_rejected(self):
        link = self.docs / "linked"
        created = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(self.outside)],
                                 capture_output=True, text=True)
        if created.returncode != 0 or not link.exists():
            self.skipTest("host cannot create a directory junction: " + (created.stderr or created.stdout).strip())
        root = documents.root_for(self.root, "project-docs")
        with self.assertRaises(Rejected):
            documents.read_text(root, "linked/secret.txt")
        self.assertNotIn("linked/secret.txt", documents.list_documents(root))

    def test_registry_refuses_relative_missing_or_file_roots(self):
        self.register({"relative": "docs", "missing": str(self.base / "absent"), "as-file": str(self.docs / "overview.md")})
        for reference in ("relative", "missing", "as-file"):
            with self.subTest(reference=reference):
                with self.assertRaises(Rejected):
                    documents.root_for(self.root, reference)

    def test_absent_registry_means_no_root_is_available(self):
        (self.root / documents.REGISTRY).unlink()
        self.assertEqual(documents.registry(self.root), {})
        with self.assertRaises(Rejected):
            documents.root_for(self.root, "project-docs")

    def test_malformed_registry_is_rejected_instead_of_guessed(self):
        (self.root / documents.REGISTRY).write_text("{not json", encoding="utf-8")
        with self.assertRaises(Rejected):
            documents.registry(self.root)


if __name__ == "__main__":
    unittest.main()
