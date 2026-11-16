import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from project_reader import project_snapshot

COLS = ['編號','畫面描述','攝影機描述','聲音描述','旁白對白','時長','影片生成方式','畫面prompt']


class LegacyAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.root = Path(self.tmp.name)

    def tearDown(self): self.tmp.cleanup()

    def test_version_and_episode_id_can_be_used_as_one_route_segment(self):
        folder=self.root/'第六版'/'EP001'
        folder.mkdir(parents=True)
        (folder/'board.md').write_text('|'+ '|'.join(COLS)+'|\n|'+ '|'.join(['---']*8)+'|\n|S01|圖|機|聲|詞|3|I2VA|prompt|',encoding='utf-8')
        episodes=project_snapshot(self.root)['episodes']
        self.assertEqual(len(episodes),1)
        self.assertNotIn('/',episodes[0]['id'])
        self.assertIn('EP001',episodes[0]['id'])

    def test_grid_guide_explicitly_lists_inserted_shots(self):
        table = '|'+ '|'.join(COLS)+'|\n|'+ '|'.join(['---']*8)+'|\n'
        table += '\n'.join('|'+ '|'.join([sid,'圖','機','聲','詞','3','I2VA','prompt'])+'|' for sid in ('S01A','S01B','S01C','S10A','S100'))
        (self.root / 'board.md').write_text(table, encoding='utf-8')
        (self.root / '25宮格_S01-S21.png').write_bytes(b'x')
        (self.root / '使用說明.md').write_text('- [第1張 S01–S21（含S01A/B/C、S10A）](25宮格_S01-S21.png)', encoding='utf-8')
        shots = project_snapshot(self.root)['episodes'][0]['shots']
        for shot in shots[:4]:
            grids = [m for m in shot['supplement']['media'] if m['role'] == 'grid']
            self.assertEqual(len(grids), 1, shot['id'])
            self.assertEqual(grids[0]['evidence'], 'grid_index')
        self.assertFalse(any(m['role']=='grid' for m in shots[4]['supplement']['media']))

    def test_nine_column_preserves_notes_and_canonical_eight_fields(self):
        header = [COLS[0], '修改', *COLS[1:]]
        (self.root / 'board.md').write_text('|'+ '|'.join(header)+'|\n|'+ '|'.join(['---']*9)+'|\n|S01|補充動作|描述|攝影|聲音|台詞|5|I2VA|提示詞|', encoding='utf-8')
        snap = project_snapshot(self.root)
        shot = snap['episodes'][0]['shots'][0]
        self.assertEqual(snap['columns'], COLS)
        self.assertEqual(list(shot['fields']), COLS)
        self.assertEqual(shot['fields']['畫面描述'], '描述')
        self.assertEqual(shot['supplement']['notes'], ['補充動作'])

    def test_same_id_sources_merge_but_conflicting_fields_stay_separate(self):
        header = [COLS[0], '修改', *COLS[1:]]
        row = ['S01', '另一註記', '不同畫面', '攝影', '聲音', '台詞', '5', 'I2VA', '提示詞']
        for name in ('a.md', 'b.csv'):
            p = self.root / name
            if name.endswith('.md'):
                p.write_text('|'+ '|'.join(header)+'|\n|'+ '|'.join(['---']*9)+'|\n|S01|註記|原畫面|攝影|聲音|台詞|5|I2VA|提示詞|', encoding='utf-8')
            else:
                p.write_text(','.join(header)+'\n'+','.join(row), encoding='utf-8')
        episode = project_snapshot(self.root)['episodes'][0]
        shot = episode['shots'][0]
        self.assertEqual(len(shot['supplement']['sources']), 2)
        self.assertEqual(shot['fields']['畫面描述'], '原畫面')
        self.assertEqual(shot['supplement']['sources'][1]['fields']['畫面描述'], '不同畫面')
        self.assertTrue(any('來源' in issue and '差異' in issue for issue in episode['issues']))
        self.assertTrue(shot['supplement']['source_resolution']['conflicts'])

    def test_version_scope_and_media_prompt_boundaries(self):
        v6 = self.root / '第六版分鏡'; v6.mkdir()
        v5 = self.root / '第五版分鏡'; v5.mkdir()
        table = '|'+ '|'.join(COLS)+'|\n|'+ '|'.join(['---']*8)+'|\n|S01|動作|鏡頭|聲音|台詞|3|I2VA|畫面詞|'
        (v6 / 'board.md').write_text(table, encoding='utf-8')
        (v5 / 'board.md').write_text(table, encoding='utf-8')
        prod = self.root / '第六版影片製作'; (prod / 'H3提示詞').mkdir(parents=True); (prod / '1080P單幀').mkdir()
        (prod / 'H3提示詞' / 'H3影片提示詞.md').write_text('## S01｜第一鏡\n```text\nfirst prompt\n```\n## S010｜其他鏡\n```text\nwrong\n```', encoding='utf-8')
        (prod / '1080P單幀' / 'S01_start.png').write_bytes(b'x')
        (prod / '1080P單幀' / 'S010_start.png').write_bytes(b'x')
        (prod / '生成影片').mkdir()
        (prod / '生成影片' / 'S01-S02.mp4').write_bytes(b'x')
        snap = project_snapshot(self.root)
        eps = {ep['id']: ep for ep in snap['episodes']}
        a = next(ep for key, ep in eps.items() if '第六版' in key)['shots'][0]
        self.assertNotEqual(next(key for key in eps if '第五版' in key), next(key for key in eps if '第六版' in key))
        self.assertEqual([p['text'] for p in a['supplement']['prompts']], ['first prompt'])
        roles = {(m['path'].split('/')[-1], m['role']) for m in a['supplement']['media']}
        self.assertIn(('S01_start.png', 'first_frame'), roles)
        self.assertIn(('S01-S02.mp4', 'video_candidate'), roles)
        self.assertNotIn(('S010_start.png', 'first_frame'), roles)

    def test_duplicate_sources_bind_package_to_one_logical_shot(self):
        (self.root / 'board.md').write_text('|'+ '|'.join(COLS)+'|\n|'+ '|'.join(['---']*8)+'|\n|S01|動作|鏡頭|聲音|台詞|3|I2VA|畫面詞|', encoding='utf-8')
        (self.root / 'board.csv').write_text(','.join(COLS)+'\nS01,動作,鏡頭,聲音,台詞,3,I2VA,畫面詞', encoding='utf-8')
        (self.root / 'asset.png').write_bytes(b'image')
        package = {'assets': [{'id': 'A1', 'role': 'reference', 'path': 'asset.png'}],
                   'shots': [{'id': 'S01', 'reference_asset_ids': ['A1']}],
                   'generations': [{'id': 'G1', 'shot_ids': ['S01']}],
                   'reviews': [{'id': 'R1', 'shot_id': 'S01', 'status': 'pending'}]}
        (self.root / 'package.json').write_text(__import__('json').dumps(package), encoding='utf-8')
        shot = project_snapshot(self.root)['episodes'][0]['shots'][0]
        self.assertEqual(len(shot['supplement']['sources']), 2)
        self.assertEqual([a['id'] for a in shot['assets']], ['A1'])
        self.assertEqual([g['id'] for g in shot['generations']], ['G1'])
        self.assertEqual([r['id'] for r in shot['reviews']], ['R1'])

    def test_grouped_suffix_ids_are_exact_and_do_not_match_s010(self):
        (self.root / 'board.md').write_text('|'+ '|'.join(COLS)+'|\n|'+ '|'.join(['---']*8)+'|\n|S01A|a|b|c|d|1|I2VA|p|\n|S01B|a|b|c|d|1|I2VA|p|\n|S010|a|b|c|d|1|I2VA|p|', encoding='utf-8')
        (self.root / 'S01A-S01B.mp4').write_bytes(b'video')
        (self.root / 'S010.mp4').write_bytes(b'video')
        shots = project_snapshot(self.root)['episodes'][0]['shots']
        by_id = {s['id']: s for s in shots}
        grouped = next(m for m in by_id['S01A']['supplement']['media'] if m['role'] == 'video_candidate')
        self.assertEqual(grouped['shot_ids'], ['S01A', 'S01B'])
        self.assertFalse(any(m['path'] == 'S010.mp4' for m in by_id['S01A']['supplement']['media']))
        self.assertEqual([m['path'] for m in by_id['S010']['supplement']['media'] if m['role'] == 'video_candidate'], ['S010.mp4'])


if __name__ == '__main__': unittest.main()
