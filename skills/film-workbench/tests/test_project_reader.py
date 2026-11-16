import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import json
import tempfile
import threading
import unittest
from pathlib import Path

from project_reader import project_snapshot, read_document

COLS = ['編號','畫面描述','攝影機描述','聲音描述','旁白對白','時長','影片生成方式','畫面prompt']

class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.root = Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def test_parse_markdown_escaped_pipe_br_multitable_and_original_order(self):
        (self.root/'storyboard.md').write_text('|'+ '|'.join(COLS)+'|\n|---|---|---|---|---|---|---|---|\n|S-8|甲 \\| 乙<br>丙|推|風|嗨|3|T2VA|prompt|\n\n其他表\n\n|'+ '|'.join(COLS)+'|\n|---|---|---|---|---|---|---|---|\n|S-2|遠景|定|景|停|無|T2VA|prompt|', encoding='utf-8')
        data = project_snapshot(self.root)
        shots = data['episodes'][0]['shots']
        self.assertEqual([s['id'] for s in shots], ['S-8','S-2'])
        self.assertEqual(shots[0]['fields']['畫面描述'], '甲 | 乙<br>丙')
        self.assertEqual(data['columns'], COLS)
    def test_csv_episode_detection_and_hidden_dirs_excluded(self):
        ep = self.root/'EP02'; ep.mkdir()
        (ep/'storyboard.csv').write_text(','.join(COLS)+'\n'+','.join(['S-4','全景','定','空','等','','','2']), encoding='utf-8')
        hidden=self.root/'.secret'; hidden.mkdir(); (hidden/'x.txt').write_text('secret')
        snap=project_snapshot(self.root)
        self.assertEqual(len(snap['episodes']),1)
        self.assertEqual(snap['episodes'][0]['id'],'EP02')
        self.assertNotIn('.secret', str(snap['files']))
    def test_qc_generation_group_and_relative_media_mapping(self):
        (self.root/'boards').mkdir(); (self.root/'qc').mkdir(); (self.root/'media').mkdir()
        (self.root/'boards'/'board.md').write_text('|'+ '|'.join(COLS)+'|\n|---|---|---|---|---|---|---|---|\n|S1|近|定|圖|動|話|聲|2|\n|S2|中|推|圖|動|話|聲|3|', encoding='utf-8')
        package={'assets':[{'id':'A1','role':'frame','path':'../media/a.png','version':'v1','sha256':'abc'}],
                 'shots':[{'id':'S1','reference_asset_ids':['A1'],'frame_asset_id':'A1'}, {'id':'S2','reference_asset_ids':['A1']}],
                 'generations':[{'id':'G1','shot_ids':['S1','S2'],'image_inputs':[{'asset_id':'A1','role':'first_frame'}]}],
                 'reviews':[{'id':'R1','shot_id':'S1','frame_asset_id':'A1','status':'pending'}]}
        (self.root/'qc'/'package.json').write_text(json.dumps(package), encoding='utf-8')
        (self.root/'media'/'a.png').write_bytes(b'png')
        shots=project_snapshot(self.root)['episodes'][0]['shots']
        self.assertEqual(shots[0]['generations'][0]['id'],'G1')
        self.assertEqual(shots[1]['generations'][0]['shot_ids'],['S1','S2'])
        self.assertEqual(shots[0]['assets'][0]['path'],'media/a.png')
        self.assertEqual(shots[0]['reviews'][0]['status'],'pending')
        self.assertIn('qc/package.json', project_snapshot(self.root)['episodes'][0]['packages'][0]['path'])

    def test_empty_project_and_grid_only_never_crash_and_columns_are_fixed(self):
        empty = project_snapshot(self.root)
        self.assertEqual(empty['columns'], COLS)
        self.assertEqual(empty['episodes'], [])
        (self.root/'EP03').mkdir()
        (self.root/'EP03'/'storyboard-grid.png').write_bytes(b'grid')
        snap=project_snapshot(self.root)
        self.assertEqual(snap['episodes'][0]['id'],'EP03')
        self.assertEqual(snap['episodes'][0]['grids'][0]['kind'],'grid')

    def test_reject_wrong_header_and_aggregate_row(self):
        (self.root/'storyboard.md').write_text('|A|B|C|D|E|F|G|H|\n|---|---|---|---|---|---|---|---|\n|S1|a|b|c|d|e|f|g|\n', encoding='utf-8')
        self.assertEqual(project_snapshot(self.root)['episodes'][0]['shots'], [])
        (self.root/'storyboard.md').write_text('|'+ '|'.join(COLS)+'|\n|---|---|---|---|---|---|---|---|\n|S1|a|b|c|d|e|f|g|\n|合計|a|b|c|d|e|f|g|', encoding='utf-8')
        shots=project_snapshot(self.root)['episodes'][0]['shots']
        self.assertEqual([shot['id'] for shot in shots],['S1'])

    def test_json_can_be_read_but_is_readonly(self):
        (self.root/'qc.json').write_text('{"status":"pending"}',encoding='utf-8')
        doc=read_document(self.root,'qc.json')
        self.assertFalse(doc['editable'])
        with self.assertRaises(PermissionError): read_document(self.root,'qc.json',content='{}',expected_version=doc['version'])

    def test_nonobject_qc_json_warns_without_requiring_schema_for_ordinary_json(self):
        (self.root/'EP01').mkdir()
        (self.root/'EP01'/'package.json').write_text('[]',encoding='utf-8')
        (self.root/'EP01'/'qa-review.json').write_text('null',encoding='utf-8')
        (self.root/'ordinary.json').write_text('[]',encoding='utf-8')
        issues=project_snapshot(self.root)['issues']
        self.assertTrue(any('package.json' in issue and '物件' in issue for issue in issues))
        self.assertTrue(any('qa-review.json' in issue and '物件' in issue for issue in issues))
        self.assertFalse(any('ordinary.json' in issue for issue in issues))

    def test_same_shot_id_is_scoped_to_package_episode(self):
        for episode, filename in [('EP01','one.png'),('EP02','two.png')]:
            asset_id='DUP'
            directory=self.root/episode
            directory.mkdir()
            (directory/'board.md').write_text('|'+ '|'.join(COLS)+'|\n|---|---|---|---|---|---|---|---|\n|S1|a|b|c|d|e|f|g|',encoding='utf-8')
            (directory/'package.json').write_text(json.dumps({'assets':[{'id':asset_id,'role':'frame','path':filename,'sha256':'x','version':'v1'}],
                'shots':[{'id':'S1','reference_asset_ids':[asset_id]}],'generations':[],'reviews':[]}),encoding='utf-8')
            (directory/filename).write_bytes(b'img')
        snap=project_snapshot(self.root)
        self.assertEqual(snap['episodes'][0]['shots'][0]['assets'][0]['path'],'EP01/one.png')
        self.assertEqual(snap['episodes'][1]['shots'][0]['assets'][0]['path'],'EP02/two.png')

    def test_root_package_binds_unique_shot_and_ambiguous_root_ids_warn(self):
        for episode in ('EP01','EP02'):
            directory=self.root/episode; directory.mkdir()
            (directory/'storyboard.md').write_text('|'+ '|'.join(COLS)+'|\n|---|---|---|---|---|---|---|---|\n|S1|a|b|c|d|e|f|g|',encoding='utf-8')
        package={'assets':[{'id':'A','role':'frame','path':'asset.png','version':'v1','sha256':'x'}],
                 'shots':[{'id':'S1','reference_asset_ids':['A']}],'generations':[],'reviews':[]}
        (self.root/'package.json').write_text(json.dumps(package),encoding='utf-8')
        snap=project_snapshot(self.root)
        shot_episodes=[ep for ep in snap['episodes'] if ep['shots']]
        self.assertTrue(all(any('重複' in issue for issue in ep['shots'][0]['issues']) for ep in shot_episodes), repr([(ep['id'], ep['shots'][0]['id'], ep['shots'][0]['issues']) for ep in shot_episodes]))
        package['shots']=[{'id':'ONLY','reference_asset_ids':['A']}]
        (self.root/'EP01'/'storyboard.md').write_text('|'+ '|'.join(COLS)+'|\n|---|---|---|---|---|---|---|---|\n|ONLY|a|b|c|d|e|f|g|',encoding='utf-8')
        (self.root/'EP02'/'storyboard.md').write_text('|'+ '|'.join(COLS)+'|\n|---|---|---|---|---|---|---|---|\n|OTHER|a|b|c|d|e|f|g|',encoding='utf-8')
        (self.root/'package.json').write_text(json.dumps(package),encoding='utf-8')
        snap=project_snapshot(self.root)
        ep01=next(ep for ep in snap['episodes'] if ep['id']=='EP01')
        self.assertEqual(ep01['shots'][0]['assets'][0]['id'],'A')

    def test_malformed_package_and_duplicate_shots_have_real_warnings(self):
        (self.root/'EP01').mkdir()
        table='|'+ '|'.join(COLS)+'|\n|---|---|---|---|---|---|---|---|\n|S1|a|b|c|d|e|f|g|\n|S1|a|b|c|d|e|f|g|'
        (self.root/'EP01'/'storyboard.md').write_text(table+'\n\n'+table,encoding='utf-8')
        (self.root/'EP01'/'package.json').write_text('{"assets":[],"shots":[]}',encoding='utf-8')
        snap=project_snapshot(self.root)
        ep=snap['episodes'][0]
        self.assertTrue(any('QC 套件' in issue for issue in snap['issues']))
        self.assertTrue(any('重複' in issue for issue in ep['issues']))
        self.assertTrue(any('多份八欄' in issue for issue in ep['issues']))
    def test_atomic_edit_conflict_and_qc_readonly(self):
        (self.root/'notes.txt').write_text('v1', encoding='utf-8')
        doc=read_document(self.root,'notes.txt')
        result=read_document(self.root,'notes.txt', content='v2', expected_version=doc['version'])
        self.assertEqual((self.root/'notes.txt').read_text(encoding='utf-8'),'v2')
        with self.assertRaises(ValueError): read_document(self.root,'notes.txt',content='v3',expected_version=doc['version'])
        (self.root/'qc.json').write_text('{}', encoding='utf-8')
        with self.assertRaises(PermissionError): read_document(self.root,'qc.json',content='{}',expected_version='x')

    def test_parallel_saves_with_same_version_allow_only_one_writer(self):
        (self.root/'notes.txt').write_text('start',encoding='utf-8')
        version=read_document(self.root,'notes.txt')['version']
        barrier=threading.Barrier(3)
        outcomes=[]
        def save(value):
            barrier.wait()
            try:
                read_document(self.root,'notes.txt',content=value,expected_version=version)
                outcomes.append('saved')
            except ValueError:
                outcomes.append('conflict')
        workers=[threading.Thread(target=save,args=(value,)) for value in ('first','second')]
        for worker in workers: worker.start()
        barrier.wait()
        for worker in workers: worker.join()
        self.assertCountEqual(outcomes,['saved','conflict'])

    def test_invalid_utf8_document_returns_recoverable_error(self):
        (self.root/'bad.txt').write_bytes(b'\xff\xfe')
        with self.assertRaises(ValueError): read_document(self.root,'bad.txt')

if __name__ == '__main__': unittest.main()
