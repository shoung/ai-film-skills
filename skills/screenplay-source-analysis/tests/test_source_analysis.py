import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

MODULE = Path(__file__).parents[1] / "scripts" / "novel_index.py"
SPEC = importlib.util.spec_from_file_location("source_analysis_index", MODULE)
indexer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(indexer)


class SourceAnalysisWorkbenchTests(unittest.TestCase):
    def test_traditional_two_and_jie_unit_headings_are_indexed_as_chapters(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "novel.txt"
            source.write_text("第兩節 轉折\n" + "甲" * 60 + "\n第三節 追尋\n" + "乙" * 60 + "\n", encoding="utf-8")
            result = indexer.build_index(source)
        self.assertEqual(result["chapter_count"], 2)
        self.assertEqual([row["source_number"] for row in result["chapters"]], [2, 3])
        self.assertEqual([row["unit"] for row in result["chapters"]], ["節", "節"])
        self.assertEqual(result["chapters"][0]["source_number"], 2)

    def test_index_records_content_fingerprint_and_detects_same_size_change(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "novel.txt"
            saved_index = Path(directory) / "index.json"
            source.write_text("第一章\n" + "甲" * 60 + "\n第二章\n" + "乙" * 60 + "\n", encoding="utf-8")
            built = indexer.build_index(source)
            saved_index.write_text(json.dumps(built, ensure_ascii=False), encoding="utf-8")
            source.write_text("第一章\n" + "丙" * 60 + "\n第二章\n" + "乙" * 60 + "\n", encoding="utf-8")
            verification = indexer.verify_index(saved_index, source)
        self.assertFalse(verification["verified"])
        self.assertTrue(any("sha256" in message.lower() for message in verification["problems"]))

    def test_index_without_source_fingerprint_cannot_be_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "novel.txt"
            saved_index = Path(directory) / "index.json"
            source.write_text("第一章\n" + "甲" * 60 + "\n第二章\n" + "乙" * 60 + "\n", encoding="utf-8")
            built = indexer.build_index(source)
            built["source"].pop("sha256")
            saved_index.write_text(json.dumps(built, ensure_ascii=False), encoding="utf-8")
            verification = indexer.verify_index(saved_index, source)
        self.assertFalse(verification["verified"])
        self.assertTrue(any("sha256" in message.lower() for message in verification["problems"]))

    def test_chapter_spans_cover_source_and_coverage_is_range_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "novel.txt"
            index_path = root / "index.json"
            analysis = root / "chapters"
            analysis.mkdir()
            source.write_text("第一章\n" + "甲" * 60 + "\n第二章\n" + "乙" * 60 + "\n第三章\n" + "丙" * 60 + "\n", encoding="utf-8")
            built = indexer.build_index(source)
            index_path.write_text(json.dumps(built, ensure_ascii=False), encoding="utf-8")
            (analysis / "ch-2-extract.md").write_text("來源位置：第 2 章，原文第 4-5 行。\n", encoding="utf-8")
            result = indexer.coverage(index_path, analysis, start=2, end=2)
        self.assertEqual([(x["line_start"], x["line_end"]) for x in built["chapters"]], [(1, 2), (3, 4), (5, 7)])
        self.assertTrue(result["complete"])
        self.assertEqual(result["range"], [2, 2])

    def test_strict_coverage_rejects_old_analysis_after_source_and_index_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "novel.txt"
            index_path = root / "index.json"
            analysis = root / "chapters"
            analysis.mkdir()
            source.write_text("第一章\n" + "甲" * 60 + "\n第二章\n" + "乙" * 60 + "\n", encoding="utf-8")
            old_index = indexer.build_index(source)
            old_hash = old_index["source"]["sha256"]
            (analysis / "ch-1-extract.md").write_text(f"<!-- source_sha256: {old_hash} -->\n舊分析\n", encoding="utf-8")
            source.write_text("第一章\n" + "丙" * 60 + "\n第二章\n" + "乙" * 60 + "\n", encoding="utf-8")
            new_index = indexer.build_index(source)
            index_path.write_text(json.dumps(new_index, ensure_ascii=False), encoding="utf-8")
            result = indexer.coverage(index_path, analysis, require_source_hash=True)
        self.assertFalse(result["complete"])
        self.assertEqual(result["stale_files"], ["ch-1-extract.md"])
        self.assertEqual(result["unverified_files"], [])

    def test_strict_coverage_requires_source_hash_marker_and_accepts_matching_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "novel.txt"
            index_path = root / "index.json"
            analysis = root / "chapters"
            analysis.mkdir()
            source.write_text("第一章\n" + "甲" * 60 + "\n第二章\n" + "乙" * 60 + "\n", encoding="utf-8")
            built = indexer.build_index(source)
            index_path.write_text(json.dumps(built, ensure_ascii=False), encoding="utf-8")
            extract = analysis / "ch-1-extract.md"
            extract.write_text("分析內容\n", encoding="utf-8")
            unverified = indexer.coverage(index_path, analysis, start=1, end=1, require_source_hash=True)
            with redirect_stdout(io.StringIO()):
                cli_result = indexer.main([
                    "coverage", str(index_path), str(analysis), "--start", "1", "--end", "1",
                    "--require-source-hash",
                ])
            extract.write_text(f"標題\n<!-- source_sha256: {built['source']['sha256']} -->\n分析內容\n", encoding="utf-8")
            late_marker = indexer.coverage(
                index_path, analysis, start=1, end=1, require_source_hash=True
            )
            extract.write_text(f"<!-- source_sha256: {built['source']['sha256']} -->\n分析內容\n", encoding="utf-8")
            verified = indexer.coverage(index_path, analysis, start=1, end=1, require_source_hash=True)
            built["source"].pop("sha256")
            index_path.write_text(json.dumps(built, ensure_ascii=False), encoding="utf-8")
            index_missing_source_hash = indexer.coverage(
                index_path, analysis, start=1, end=1, require_source_hash=True
            )
        self.assertFalse(unverified["complete"])
        self.assertEqual(cli_result, 1)
        self.assertEqual(unverified["unverified_files"], ["ch-1-extract.md"])
        self.assertEqual(late_marker["unverified_files"], ["ch-1-extract.md"])
        self.assertTrue(verified["complete"])
        self.assertEqual(verified["stale_files"], [])
        self.assertFalse(index_missing_source_hash["complete"])
        self.assertEqual(index_missing_source_hash["unverified_files"], ["ch-1-extract.md"])


if __name__ == "__main__":
    unittest.main()
