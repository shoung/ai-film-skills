import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from project_reader import project_snapshot

COLS = ['編號','畫面描述','攝影機描述','聲音描述','旁白對白','時長','影片生成方式','畫面prompt']


def table(rows):
    return '|' + '|'.join(COLS) + '|\n|' + '|'.join(['---'] * 8) + '|\n' + '\n'.join('|' + '|'.join(row) + '|' for row in rows)


class SourceResolutionTests(unittest.TestCase):
    def test_explicit_csv_master_is_respected(self):
        ep=self.root/'EP01'
        (ep/'board.md').write_text(table([['S01','older','定','聲','詞','3','I2VA','p']]),encoding='utf-8')
        (ep/'board.csv').write_text(','.join(COLS)+'\nS01,current,定,聲,詞,3,I2VA,p',encoding='utf-8')
        (self.root/'入口.md').write_text('[分鏡主表](EP01/board.csv)',encoding='utf-8')
        episode=next(e for e in project_snapshot(self.root)['episodes'] if e['id']=='EP01')
        self.assertEqual(episode['shots'][0]['fields']['畫面描述'],'current')
        self.assertTrue(episode['source_resolution']['resolved'])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.root = Path(self.tmp.name)
        (self.root / 'EP01').mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_explicit_markdown_master_wins_and_keeps_source_diffs_without_duplicate_issue(self):
        ep = self.root / 'EP01'
        (ep / 'board.md').write_text(table([['S01','主內容<br>次行','定','聲','詞','3','I2VA','prompt']]), encoding='utf-8')
        (ep / 'board.csv').write_text(','.join(COLS) + '\nS01,"主內容<br>次行",定,聲,詞,3,I2VA,prompt', encoding='utf-8')
        (self.root / '入口.md').write_text('[Markdown 主表](EP01/board.md)\n[CSV](EP01/board.csv)', encoding='utf-8')
        snap = project_snapshot(self.root)
        episode = next(ep for ep in snap['episodes'] if ep['id'] == 'EP01')
        shot = episode['shots'][0]
        self.assertEqual(shot['source'], 'EP01/board.md')
        self.assertEqual(shot['fields']['畫面描述'], '主內容<br>次行')
        self.assertEqual(len(shot['supplement']['sources']), 2)
        self.assertEqual(shot['supplement']['source_resolution']['primary'], 'EP01/board.md')
        self.assertEqual(shot['supplement']['source_resolution']['conflicts'], [])
        self.assertFalse(any('待確認' in issue or '重複鏡號來源' in issue for issue in episode['issues'] + shot['issues']))

    def test_substantive_conflict_is_summarized_and_missing_ids_are_visible(self):
        ep = self.root / 'EP01'
        (ep / 'board.md').write_text(table([['S01','Markdown','定','聲','詞','3','I2VA','prompt'], ['S02','多出','定','聲','詞','3','I2VA','prompt']]), encoding='utf-8')
        (ep / 'board.csv').write_text(','.join(COLS) + '\nS01,CSV,定,聲,詞,3,I2VA,prompt', encoding='utf-8')
        episode = next(ep for ep in project_snapshot(self.root)['episodes'] if ep['id'] == 'EP01')
        self.assertEqual(len([s for s in episode['issues'] if '來源' in s or '鏡號' in s]), 1)
        shot = next(s for s in episode['shots'] if s['id'] == 'S01')
        self.assertTrue(any('畫面描述' in item.get('fields', []) for item in shot['supplement']['source_resolution']['conflicts']))
        self.assertTrue(any('S02' in str(item) for item in episode['source_resolution']['conflicts']))
        self.assertEqual(shot['fields']['畫面描述'], 'Markdown')
        self.assertFalse(any('來源內容不同' in issue for issue in shot['issues']))

    def test_duplicate_rows_within_one_file_remain_an_error(self):
        (self.root / 'EP01' / 'board.md').write_text(table([['S01','a','b','c','d','1','I2VA','p'], ['S01','a','b','c','d','1','I2VA','p']]), encoding='utf-8')
        ep = next(ep for ep in project_snapshot(self.root)['episodes'] if ep['id'] == 'EP01')
        self.assertTrue(any('重複鏡號' in issue for issue in ep['issues']))

    def test_primary_source_order_wins_over_csv_scan_order_and_parent_links_resolve(self):
        ep = self.root / 'EP01'
        (ep / 'a.csv').write_text(','.join(COLS) + '\nS01,a,b,c,d,1,I2VA,p\nS02,a,b,c,d,1,I2VA,p', encoding='utf-8')
        (ep / 'z_master.md').write_text(table([['S02','second','b','c','d','1','I2VA','p'], ['S01','first','b','c','d','1','I2VA','p']]), encoding='utf-8')
        index = self.root / 'docs'; index.mkdir()
        (index / '入口.md').write_text('[正式主表](../EP01/z_master.md)', encoding='utf-8')
        episode = next(ep for ep in project_snapshot(self.root)['episodes'] if ep['id'] == 'EP01')
        self.assertEqual([s['id'] for s in episode['shots']], ['S02', 'S01'])
        self.assertEqual(episode['source_resolution']['primary'], 'EP01/z_master.md')

    def test_multiple_explicit_masters_are_unresolved_and_warn_once(self):
        ep = self.root / 'EP01'
        (ep / 'one.md').write_text(table([['S01','one','b','c','d','1','I2VA','p']]), encoding='utf-8')
        (ep / 'two.md').write_text(table([['S01','two','b','c','d','1','I2VA','p']]), encoding='utf-8')
        (self.root / '入口.md').write_text('[Markdown 主表](EP01/one.md)\n[正式主表](EP01/two.md)', encoding='utf-8')
        episode = next(ep for ep in project_snapshot(self.root)['episodes'] if ep['id'] == 'EP01')
        self.assertFalse(episode['source_resolution']['resolved'])
        self.assertTrue(any(item.get('kind') == 'multiple_explicit_masters' for item in episode['source_resolution']['conflicts']))
        self.assertEqual(sum('同分集有多個主表宣告，請確認權威來源' in issue for issue in episode['issues']), 1)

    def test_explicit_master_does_not_hide_alternative_missing_shot_ids(self):
        ep = self.root / 'EP01'
        (ep / 'board.md').write_text(table([['S01','a','b','c','d','1','I2VA','p'], ['S02','b','b','c','d','1','I2VA','p']]), encoding='utf-8')
        (ep / 'board.csv').write_text(','.join(COLS) + '\nS01,a,b,c,d,1,I2VA,p', encoding='utf-8')
        (self.root / '入口.md').write_text('[Markdown 主表](EP01/board.md)', encoding='utf-8')
        episode = next(ep for ep in project_snapshot(self.root)['episodes'] if ep['id'] == 'EP01')
        self.assertTrue(any('分鏡來源存在差異（鏡號缺漏或多出）' in issue for issue in episode['issues']))
        self.assertTrue(any(item.get('missing_ids') == ['S02'] for item in episode['source_resolution']['conflicts']))


if __name__ == '__main__':
    unittest.main()
