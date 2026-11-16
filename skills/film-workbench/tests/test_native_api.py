import json
import sys
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from dashboard_server import serve


class NativeApiTests(unittest.TestCase):
    def test_native_skill_documents_have_real_structures_without_foreign_format_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); ep=root/'EP001'; ep.mkdir()
            (ep/'劇本.md').write_text('# 夜雨\n\n## 本版鎖定\n格式備註\n\n### 1-1 車站／日／內外\n人物：甲\n\n甲（低聲）：等我。\n\n△拿起雨傘。\n',encoding='utf-8')
            (ep/'視覺設定.md').write_text('## 角色資產\n### @甲\n#### @甲_雨衣\n```text\nblue coat character\n```',encoding='utf-8')
            columns=['編號','畫面描述','攝影機描述','聲音描述','旁白對白','時長','影片生成方式','畫面prompt']
            rows=[columns,['---']*8,['S01','[場次/時間] 1-1 車站','固定','雨','甲：等我。','2.5','T2VA','rain'],['S02','[場次/時間] 1-1 街道','推近','腳步','無','3','I2VA','street']]
            (ep/'分鏡.md').write_text('\n'.join('|'+ '|'.join(row)+'|' for row in rows),encoding='utf-8')
            for shot,mode in [('S01','T2VA'),('S02','I2VA')]:
                (ep/f'H3影片提示詞_{shot}.md').write_text(f'## {shot}｜雨夜\n模式：{mode}\n```text\nintegrated_multimodal_description: [Shot 1] {shot} request\noverall_soundscape: rain\nnon_diegetic_music: N/A\n```',encoding='utf-8')
            (ep/'S99.mp4').write_bytes(b'candidate')
            server,token=serve(root); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
            base='http://127.0.0.1:'+str(server.server_port)
            def get(path):
                return json.load(urllib.request.urlopen(urllib.request.Request(base+path,headers={'X-Film-Token':token})))
            try:
                project=get('/api/projects')['projects'][0]['id']
                episode=get('/api/episode?'+urllib.parse.urlencode({'project':project,'ep':'EP001'}))
                self.assertEqual(episode['media']['candidates'],[{'path':'EP001/S99.mp4','shot_ids':[],'kind':'video','role':'video_candidate'}])
                self.assertIsNotNone(episode['script'])
                self.assertEqual(episode['script']['scenes'][0]['id'],'1-1')
                self.assertEqual(episode['script']['scenes'][0]['blocks'][0]['k'],'line')
                self.assertEqual(len(episode['board']['shots']),2)
                self.assertEqual(episode['metrics']['seconds'],5.5)
                self.assertEqual(episode['board']['shots'][0]['scene'],'1-1')
                self.assertGreaterEqual(len(episode['settings']['items']),1)
                self.assertEqual({p['shot'] for p in episode['videoPrompts']},{'S01','S02'})
                self.assertFalse(any('没有按结构读出来' in p for p in episode['problems']),episode['problems'])
                self.assertFalse(any('MOTION-' in p or 'SHOT-' in p for p in episode['problems']))
                self.assertEqual(list(episode['board']['shots'][0]['fields']),columns)
            finally:
                server.shutdown();server.server_close()
