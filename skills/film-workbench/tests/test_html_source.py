import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import project_reader


class HtmlSourceTests(unittest.TestCase):
    def test_existing_html_overview_is_visible_as_read_only_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = '<h1>設定卡總覽</h1><script>throw new Error("never execute")</script>'
            (root / '設定卡總覽.html').write_text(source, encoding='utf-8')
            snapshot = project_reader.project_snapshot(root)
            self.assertIn('設定卡總覽.html', [item['path'] for item in snapshot['files']])
            document = project_reader.read_document(root, '設定卡總覽.html')
            self.assertEqual(document['content'], source)
            self.assertFalse(document['editable'])
            with self.assertRaises(PermissionError):
                project_reader.read_document(root, '設定卡總覽.html', 'changed', document['version'])


if __name__ == '__main__':
    unittest.main()
